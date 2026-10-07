"""Calls a person or a reviewer checked, and whether the judge agrees with them.

`reviews/<code>/verified.json` holds one entry per checked death:

    {"fight": 68, "time": "1:01", "name": "Kitana Kahn", "mechanic": "Skyward Leap",
     "outcome": "fail", "owners": ["Assigned mitigation"], "by": "user",
     "why": "Full HP with no mitigation.",
     "first_pass": {"outcome": "fail", "owners": ["Assigned mitigation"]}}

`by` is "user" for a call the person made, and "review" for one an agent made
from the evidence and nobody has overruled. `owners` leaves out the shares
that only sit beside an owner (Party mitigation, Earlier damage, Earlier
mistake); leave it out to check only the outcome. `first_pass` is what the
judge said before the call was checked. It is how often the judge is right on
a log nobody has corrected yet.

The folder is not part of a report's fingerprint, so recording a call never
makes a log out of date. `verify` fails when a call by the user no longer
matches, so a rule change cannot quietly undo a correction.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from xivloganalyzer.calls import Key, key, key_text, named_owners, parse_owners, saved_calls

VERIFIED = "verified.json"
SOURCES = ("user", "review")


def verified_path(root: Path, code: str) -> Path:
    return root / "reviews" / code / VERIFIED


def load_verified(root: Path, code: str) -> list[dict]:
    path = verified_path(root, code)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("calls") or []


def save_verified(root: Path, code: str, calls: list[dict]) -> Path:
    path = verified_path(root, code)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(calls, key=lambda call: (int(call["fight"]), _seconds(call["time"]), call["name"]))
    path.write_text(json.dumps({"calls": ordered}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _seconds(clock: str) -> float:
    total = 0.0
    for part in str(clock).split(":"):
        total = total * 60 + float(part)
    return total


def _current(row: dict) -> dict:
    return {"outcome": row["outcome"], "owners": named_owners(parse_owners(row["owners"]))}


def differences(call: dict, current: dict) -> list[str]:
    """What the judge says that the checked call does not. Empty when they agree."""
    found = []
    if call.get("outcome") and call["outcome"] != current["outcome"]:
        found.append(f"outcome {current['outcome']}, checked {call['outcome']}")
    if call.get("owners") is not None and sorted(call["owners"]) != sorted(current["owners"]):
        judged = ", ".join(current["owners"]) or "nobody"
        checked = ", ".join(call["owners"]) or "nobody"
        found.append(f"owners {judged}, checked {checked}")
    return found


@dataclass
class Check:
    code: str
    call: dict
    row: dict | None
    found: list[str] = field(default_factory=list)

    @property
    def agrees(self) -> bool:
        return self.row is not None and not self.found

    @property
    def first_pass_agrees(self) -> bool | None:
        first = self.call.get("first_pass")
        if not first:
            return None
        return not differences(self.call, {"outcome": first.get("outcome"), "owners": first.get("owners") or []})


def check_report(root: Path, report: Path) -> list[Check]:
    calls = load_verified(root, report.name)
    rows = {key(row): row for row in saved_calls(report) or []}
    checks = []
    for call in calls:
        row = rows.get(key(call))
        found = ["not in the judged deaths"] if row is None else differences(call, _current(row))
        checks.append(Check(report.name, call, row, found))
    return checks


def failures(checks: list[Check], strict: bool = False) -> list[Check]:
    """Checked calls the judge no longer agrees with. Only the user's count, unless `strict`."""
    return [item for item in checks if not item.agrees and (strict or item.call.get("by") == "user")]


def _rate(good: int, total: int) -> str:
    return f"{good} of {total}" + (f" ({round(100 * good / total)}%)" if total else "")


def verify_text(checks: list[Check]) -> str:
    if not checks:
        return "No checked calls. Record them in reviews/<code>/verified.json.\n"
    lines = []
    by_code: dict[str, list[Check]] = defaultdict(list)
    for item in checks:
        by_code[item.code].append(item)
    for code, items in by_code.items():
        sources = Counter(item.call.get("by") or "review" for item in items)
        noun = "call" if len(items) == 1 else "calls"
        lines.append(f"{code} · {len(items)} checked {noun}: " + ", ".join(
            f"{sources[source]} by {'the user' if source == 'user' else 'review'}" for source in SOURCES if sources[source]
        ))
        lines.append(f"  the judge agrees now: {_rate(sum(item.agrees for item in items), len(items))}")
        firsts = [item.first_pass_agrees for item in items if item.first_pass_agrees is not None]
        if firsts:
            lines.append(f"  the judge agreed before the check: {_rate(sum(firsts), len(firsts))}")
    mechanics: dict[str, list[Check]] = defaultdict(list)
    for item in checks:
        mechanics[item.call.get("mechanic") or (item.row or {}).get("mechanic") or "?"].append(item)
    lines.append("")
    lines.append("By mechanic (agree now / checked · agreed before the check)")
    for mechanic, items in sorted(mechanics.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        firsts = [item.first_pass_agrees for item in items if item.first_pass_agrees is not None]
        first = f" · {sum(firsts)}/{len(firsts)}" if firsts else ""
        lines.append(f"  {mechanic}: {sum(item.agrees for item in items)}/{len(items)}{first}")
    wrong = [item for item in checks if not item.agrees]
    if wrong:
        lines.append("")
        lines.append("Disagreements")
        for item in wrong:
            mechanic = item.call.get("mechanic") or (item.row or {}).get("mechanic") or "?"
            death = key_text(key(item.call))
            lines.append(f"  {item.code} {death} · {mechanic} ({item.call.get('by') or 'review'}): {'; '.join(item.found)}")
            if item.call.get("why"):
                lines.append(f"    why: {item.call['why']}")
    return "\n".join(lines) + "\n"


def record(
    root: Path, report: Path, fight: int, name: str, time: str | None = None,
    outcome: str | None = None, owners: list[str] | None = None, by: str = "user", why: str = "",
) -> dict:
    """Add or replace one checked call. What the judge says now is kept as its first pass,
    so record the call before the rules are changed to match it."""
    rows = [row for row in saved_calls(report) or [] if row["fight"] == fight and row["name"] == name]
    if time is not None:
        rows = [row for row in rows if row["time"] == time]
    if len(rows) != 1:
        options = ", ".join(f"{row['time']} {row['mechanic']}" for row in rows) or "none"
        raise SystemExit(f"Pull {fight} {name}: {len(rows)} deaths match ({options}). Pass --time.")
    row = rows[0]
    current = _current(row)
    calls = [call for call in load_verified(root, report.name) if key(call) != key(row)]
    previous = next((call for call in load_verified(root, report.name) if key(call) == key(row)), None)
    call = {
        "fight": fight,
        "time": row["time"],
        "name": name,
        "mechanic": row["mechanic"],
        "outcome": outcome or current["outcome"],
        "owners": owners if owners is not None else current["owners"],
        "by": by,
        "why": why,
        "first_pass": (previous or {}).get("first_pass") or current,
    }
    calls.append(call)
    save_verified(root, report.name, calls)
    return call


def keys(root: Path, code: str) -> dict[Key, str]:
    """Each checked death and who checked it."""
    return {key(call): call.get("by") or "review" for call in load_verified(root, code)}
