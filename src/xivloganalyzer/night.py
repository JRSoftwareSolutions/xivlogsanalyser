"""What lost each pull of a night, and who owns its deaths.

Built from the saved calls: each judgment's `first_causes` (the mistake that lost
the pull, per mechanic, with its owners), `blames`, and `carried`. The brief prints
it and the session page shows it above the pulls.

A share that came through an earlier death, such as an empty tower left by a
player who was already dead, is counted apart from the deaths a player owns by
their own mistake. One mistake can leave several later mechanics short, and
counting those as theirs too makes them look like they fail more mechanics.
A player's own mistake after the pull was lost, more than a second after its
first death, is left out: the pull could no longer succeed.
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
    passed_on: Counter[str] = Counter()
    late = 0
    for row in rows:
        if row.get("outcome") not in {"fail", "raw", "low"}:
            continue
        carried = set(row.get("carried") or [])
        if row.get("late") and any(
            blame["who"] not in CONTEXT_SHARES and blame["who"] not in carried
            for blame in row.get("blames") or []
        ):
            late += 1
        for blame in row.get("blames") or []:
            if blame["who"] in CONTEXT_SHARES:
                continue
            if blame["who"] in carried:
                passed_on[blame["who"]] += (blame.get("confidence") or 0) / 100
            elif not row.get("late"):
                owned[blame["who"]] += (blame.get("confidence") or 0) / 100
    named = (
        set(starters) | set(owned) | set(passed_on)
        | {who for counter in owners_of.values() for who in counter}
    )
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
        "passed_on": [(who, round(share, 1)) for who, share in passed_on.most_common()],
        # Deaths with an owner's own share after the pull was lost, left out of `owned`.
        "late": late,
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
    lines = [f"What lost each pull ({tally['pulls']} pulls; a pull can be lost to two at once)"]
    for row in tally["started"]:
        who = ", ".join(f"{name} {count}" for name, count in row["owners"])
        lines.append(f"  {row['pulls']} {row['mechanic']}: {who}")
    lines.append("")
    lines.append("Who lost pulls")
    lines += _people(tally["starters"], str)
    lines.append("")
    lines.append("Deaths owned by their own mistake while the pull could succeed, by share")
    lines += _people(tally["owned"], _number)
    if tally["late"]:
        lines.append(f"  left out: {tally['late']} deaths after the pull was already lost")
    if tally["passed_on"]:
        lines.append("")
        lines.append("Passed on from an earlier death, by share")
        lines += _people(tally["passed_on"], _number)
    return lines
