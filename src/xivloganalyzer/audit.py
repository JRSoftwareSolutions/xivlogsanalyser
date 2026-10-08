"""Calls whose blame rests on weak evidence, so they can be checked one kind at a time."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from xivloganalyzer.brief import load_judgments
from xivloganalyzer.judge import CONTEXT_SHARES, GROUP_LABELS

# Labels that stand in for players the log did not name, and shares that sit beside the owners.
UNNAMED = GROUP_LABELS
_CONTEXT = CONTEXT_SHARES
# Deaths to one cast land within this many seconds of each other.
_CAST_S = 1.5

FLAGS = {
    "unknown": "The killing blow is not understood. What should this hit mean?",
    "unnamed": "The blame is a group label. Can the log name the player (debuffs, hit lists, deaths, positions)?",
    "mass-self": "Three or more players died to one cast, each blamed on themselves. Did one earlier action cause all of them?",
    "raw-after-death": "A raw death after someone already died in the pull. Was the party short, or still healthy?",
    "thin-split": "Three or more players split it. Is one of them the real cause?",
    "degraded": "The call was made without an input it reads (see `check`). Fetch it and reanalyze.",
    "mass-wall": "The pull's first mistake is three or more players dying with no damage packet at once. Was it the deathwall, or a hit the log did not record?",
}


def _self_only(row: dict) -> bool:
    blames = row.get("blames") or []
    return len(blames) == 1 and blames[0].get("who") == row.get("name")


def flag_rows(rows: list[dict]) -> dict[str, list[dict]]:
    """Each flag, and the deaths that raise it."""
    pulls: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        pulls[int(row.get("fight") or 0)].append(row)
    found: dict[str, list[dict]] = {flag: [] for flag in FLAGS}
    for pull in pulls.values():
        pull.sort(key=lambda row: (row.get("phase") or 0, row.get("t") or 0, row.get("name") or ""))
        for index, row in enumerate(pull):
            if row.get("outcome") == "environment":
                continue
            if row.get("outcome") == "unknown":
                found["unknown"].append(row)
                continue
            blames = row.get("blames") or []
            if row.get("missing"):
                found["degraded"].append(row)
            if any(blame.get("who") in UNNAMED for blame in blames):
                found["unnamed"].append(row)
            if len([blame for blame in blames if blame.get("who") not in _CONTEXT]) >= 3:
                found["thin-split"].append(row)
            if row.get("outcome") == "fail" and not row.get("first") and _self_only(row):
                cast = [
                    other for other in pull
                    if other.get("mechanic_id") == row.get("mechanic_id")
                    and other.get("phase") == row.get("phase")
                    and abs((other.get("t") or 0) - (row.get("t") or 0)) <= _CAST_S
                    and other.get("outcome") == "fail"
                    and _self_only(other)
                ]
                if len(cast) >= 3 and row.get("mechanic_id") != "deathwall":
                    found["mass-self"].append(row)
            if row.get("mechanic_id") == "deathwall":
                together = [
                    other for other in pull
                    if other.get("mechanic_id") == "deathwall" and other.get("phase") == row.get("phase")
                    and abs((other.get("t") or 0) - (row.get("t") or 0)) <= _CAST_S
                ]
                if len(together) >= 3 and any(other.get("first") for other in together):
                    found["mass-wall"].append(row)
            earlier = [
                other for other in pull[:index]
                if (other.get("phase"), other.get("t")) < (row.get("phase"), row.get("t"))
            ]
            if row.get("outcome") == "raw" and earlier:
                found["raw-after-death"].append(row)
    return found


def _owners(row: dict) -> str:
    return "; ".join(
        f"{blame.get('who')} {int(blame.get('confidence') or 0)}%" for blame in row.get("blames") or []
    ) or "none"


def audit_text(report: Path, flag: str | None = None, limit: int = 8) -> str:
    rows = load_judgments(report)
    found = flag_rows(rows)
    flags = [flag] if flag else list(FLAGS)
    lines = [f"{report.name} · {len(rows)} deaths"]
    for name in flags:
        hits = found[name]
        lines.append("")
        lines.append(f"{name} ({len(hits)}) — {FLAGS[name]}")
        if not hits:
            continue
        by_mech = Counter(str(row.get("mechanic")) for row in hits)
        lines.append("  " + ", ".join(f"{count} {mech}" for mech, count in by_mech.most_common()))
        shown = hits if flag else hits[:limit]
        for row in shown:
            lines.append(
                f"  pull {row.get('fight')} {row.get('t')}s · {row.get('name')} · {row.get('mechanic')}"
                f" — {row.get('outcome')} · {row.get('cause', '?')} · {_owners(row)}"
            )
        if len(shown) < len(hits):
            lines.append(f"  … {len(hits) - len(shown)} more (--flag {name})")
    return "\n".join(lines) + "\n"
