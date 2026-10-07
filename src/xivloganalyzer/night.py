"""What started each pull of a night, and who owns its deaths.

Built from the saved calls: each judgment's `first_causes` (the pull's first
mistake per mechanic, with its owners) and `blames`. The brief prints it and
the session page shows it above the pulls.
"""

from __future__ import annotations

from collections import Counter

from xivloganalyzer.judge import CONTEXT_SHARES, GROUP_LABELS


def night_tally(rows: list[dict]) -> dict:
    causes: dict[int, list[dict]] = {}
    for row in rows:
        causes.setdefault(int(row.get("fight") or 0), row.get("first_causes") or [])
    started: Counter[str] = Counter()
    owners_of: dict[str, Counter[str]] = {}
    starters: Counter[str] = Counter()
    for pull_causes in causes.values():
        in_pull: set[str] = set()
        for cause in pull_causes:
            started[cause["mechanic"]] += 1
            owners_of.setdefault(cause["mechanic"], Counter()).update(cause["owners"])
            in_pull.update(cause["owners"])
        starters.update(in_pull)
    owned: Counter[str] = Counter()
    for row in rows:
        if row.get("outcome") not in {"fail", "raw", "low"}:
            continue
        for blame in row.get("blames") or []:
            if blame["who"] not in CONTEXT_SHARES:
                owned[blame["who"]] += (blame.get("confidence") or 0) / 100
    named = set(starters) | set(owned) | {who for counter in owners_of.values() for who in counter}
    return {
        "pulls": len(causes),
        # Owners that are a group label, not a player.
        "labels": sorted(named & GROUP_LABELS),
        "started": [
            {"mechanic": mechanic, "pulls": n, "owners": owners_of[mechanic].most_common()}
            for mechanic, n in started.most_common()
        ],
        "starters": starters.most_common(),
        "owned": [(who, round(share, 1)) for who, share in owned.most_common()],
    }


def _number(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _people(pairs: list, fmt) -> list[str]:
    named = [(who, n) for who, n in pairs if who not in GROUP_LABELS]
    labels = [(who, n) for who, n in pairs if who in GROUP_LABELS]
    lines = []
    if named:
        lines.append("  " + ", ".join(f"{who} {fmt(n)}" for who, n in named))
    if labels:
        lines.append("  nobody named: " + ", ".join(f"{who} {fmt(n)}" for who, n in labels))
    return lines


def night_lines(rows: list[dict]) -> list[str]:
    tally = night_tally(rows)
    if not tally["started"]:
        return []
    lines = [f"What started each pull ({tally['pulls']} pulls; a pull can start with two)"]
    for row in tally["started"]:
        who = ", ".join(f"{name} {count}" for name, count in row["owners"])
        lines.append(f"  {row['pulls']} {row['mechanic']}: {who}")
    lines.append("")
    lines.append("Who started pulls")
    lines += _people(tally["starters"], str)
    lines.append("")
    lines.append("Deaths owned, by share")
    lines += _people(tally["owned"], _number)
    return lines
