"""One line per death: what it was, who owns it, and what decided that.

`calls.tsv` is written next to `judgments.json` each time a report is judged, so a
change to any call shows up as one changed line in a diff. A death is keyed by
pull, the log's own clock time, and the player. None of those move when the
rules change. `changes` lists the calls that differ from another git revision,
and `reanalyze` prints how many calls each run changed.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from xivloganalyzer.judge import CONTEXT_SHARES

CALLS = "calls.tsv"
COLUMNS = ("fight", "time", "name", "t", "mechanic", "outcome", "cause", "basis", "owners", "missing")

Key = tuple[int, str, str]
_OWNER = re.compile(r"^(.*?) (\d+)(?: \(via (.*)\))?$")


def key(row: dict) -> Key:
    """Pull, clock time in the log, and player. Unique in a report, and stable across rule changes."""
    return int(row["fight"]), str(row["time"]), str(row["name"])


def key_text(death: Key) -> str:
    fight, time, name = death
    return f"pull {fight} {time} {name}"


def owners_text(blames: list[dict]) -> str:
    parts = []
    for blame in blames:
        text = f"{blame['who']} {int(blame.get('confidence') or 0)}"
        if blame.get("via"):
            text += f" (via {', '.join(blame['via'])})"
        parts.append(text)
    return "; ".join(parts)


def parse_owners(text: str) -> list[dict]:
    found = []
    for part in filter(None, (piece.strip() for piece in text.split("; "))):
        match = _OWNER.match(part)
        if not match:
            found.append({"who": part, "confidence": 0})
            continue
        blame = {"who": match.group(1), "confidence": int(match.group(2))}
        if match.group(3):
            blame["via"] = match.group(3).split(", ")
        found.append(blame)
    return found


def named_owners(blames: list[dict]) -> list[str]:
    """Who owns the death, without the shares that only sit beside an owner."""
    return [blame["who"] for blame in blames if blame["who"] not in CONTEXT_SHARES]


def call_row(row: dict) -> dict:
    """The parts of one saved judgment that make the call."""
    return {
        "fight": int(row["fight"]),
        "time": str(row["time"]),
        "name": row["name"],
        "t": f"{float(row['t']):.1f}",
        "mechanic": row.get("mechanic") or "",
        "outcome": row.get("outcome") or "",
        "cause": row.get("cause") or "",
        "basis": row.get("basis") or "",
        "owners": owners_text(row.get("blames") or []),
        "missing": ", ".join(row.get("missing") or []),
    }


def call_rows(judgments: list[dict]) -> list[dict]:
    rows = [call_row(row) for row in judgments]
    return sorted(rows, key=lambda row: (row["fight"], float(row["t"]), row["name"]))


def calls_text(judgments: list[dict]) -> str:
    lines = ["\t".join(COLUMNS)]
    for row in call_rows(judgments):
        lines.append("\t".join(str(row[column]) for column in COLUMNS))
    return "\n".join(lines) + "\n"


def write_calls(report: Path, judgments: list[dict]) -> Path:
    path = report / CALLS
    path.write_text(calls_text(judgments), encoding="utf-8")
    return path


def read_calls(text: str) -> list[dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = line.split("\t")
        row = dict(zip(header, values + [""] * (len(header) - len(values))))
        row["fight"] = int(row["fight"])
        rows.append(row)
    return rows


def saved_calls(report: Path) -> list[dict] | None:
    """The calls in the report's saved judgments, or None when it was never judged."""
    path = report / "judgments.json"
    if not path.is_file():
        return None
    return call_rows(json.loads(path.read_text(encoding="utf-8")))


def calls_at(report: Path, rev: str, root: Path) -> list[dict] | None:
    """The calls this report had at a git revision. None when it did not exist there."""
    relative = report.resolve().relative_to(root.resolve()).as_posix()
    for name, parse in ((CALLS, read_calls), ("judgments.json", lambda text: call_rows(json.loads(text)))):
        result = subprocess.run(
            ["git", "show", f"{rev}:{relative}/{name}"],
            cwd=root, capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0:
            return parse(result.stdout)
    return None


@dataclass
class Change:
    death: Key
    before: dict | None
    after: dict | None

    @property
    def kind(self) -> str:
        if self.before is None:
            return "new"
        if self.after is None:
            return "gone"
        if self.before["outcome"] != self.after["outcome"]:
            return "outcome"
        if _owners(self.before) != _owners(self.after):
            return "owners"
        return "reason"


def _owners(row: dict) -> list[tuple[str, int]]:
    return [(blame["who"], blame["confidence"]) for blame in parse_owners(row["owners"])]


def _call(row: dict) -> tuple:
    return row["mechanic"], row["outcome"], row["cause"], tuple(_owners(row))


def diff_calls(before: list[dict], after: list[dict]) -> list[Change]:
    """Deaths whose mechanic, outcome, cause, or owners differ. Text, basis, and gaps alone do not count."""
    old = {key(row): row for row in before}
    new = {key(row): row for row in after}
    changes = []
    for death in sorted(set(old) | set(new)):
        left, right = old.get(death), new.get(death)
        if left is None or right is None or _call(left) != _call(right):
            changes.append(Change(death, left, right))
    return changes


def _side(row: dict | None) -> str:
    if row is None:
        return "not judged"
    owners = ", ".join(f"{who} {share}" for who, share in _owners(row)) or "nobody"
    return f"{row['outcome']}/{row['cause']} {owners}"


def change_line(change: Change, note: str = "") -> str:
    row = change.after or change.before
    line = f"{key_text(change.death)} · {row['mechanic']} · {_side(change.before)} → {_side(change.after)}"
    return f"{line} {note}".rstrip()


def change_summary(changes: list[Change]) -> str:
    if not changes:
        return "no calls changed"
    counts: dict[str, int] = {}
    for change in changes:
        counts[change.kind] = counts.get(change.kind, 0) + 1
    order = ("outcome", "owners", "reason", "new", "gone")
    parts = [f"{counts[kind]} {kind}" for kind in order if counts.get(kind)]
    return f"{len(changes)} calls changed ({', '.join(parts)})"
