"""Compact session digests for review without loading full JSON into context."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from xivloganalyzer.dashboard import session_clock
from xivloganalyzer.inputs import problems, read_inputs
from xivloganalyzer.night import night_lines

# Default detail lines: the ones that still need a judgment pass or own the headline.
_DEFAULT_DETAIL = frozenset({"unknown", "raw"})
_OUTCOME_ORDER = ("raw", "fail", "low", "unknown", "environment")
_OUTCOME_SHORT = {
    "raw": "r",
    "fail": "f",
    "low": "l",
    "unknown": "u",
    "environment": "e",
}


def load_judgments(report: Path) -> list[dict]:
    path = report / "judgments.json"
    if not path.is_file():
        raise SystemExit(
            f"No judgments.json in {report}. Run: python -m xivloganalyzer analyze {report.name}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_outcomes(raw: str | None) -> frozenset[str] | None:
    if not raw:
        return None
    parts = {piece.strip().lower() for piece in raw.split(",") if piece.strip()}
    unknown = parts - set(_OUTCOME_ORDER)
    if unknown:
        raise SystemExit(f"Unknown outcome(s): {', '.join(sorted(unknown))}")
    return frozenset(parts)


def filter_judgments(
    judgments: list[dict],
    *,
    pull: int | None = None,
    mechanic: str | None = None,
    outcomes: frozenset[str] | None = None,
) -> list[dict]:
    rows = judgments
    if pull is not None:
        rows = [row for row in rows if int(row.get("fight") or 0) == pull]
    if mechanic:
        needle = mechanic.casefold()
        rows = [
            row
            for row in rows
            if needle in str(row.get("mechanic") or "").casefold()
            or needle in str(row.get("ability") or "").casefold()
            or needle == str(row.get("guid") or "")
            or needle == str(row.get("mechanic_id") or "").casefold()
        ]
    if outcomes is not None:
        rows = [row for row in rows if row.get("outcome") in outcomes]
    return rows


def _blame_line(row: dict) -> str:
    blames = row.get("blames") or []
    if not blames:
        return ""
    parts = []
    for blame in blames:
        who = blame.get("who") or "?"
        confidence = blame.get("confidence")
        text = str(who) if confidence is None else f"{who} {int(confidence)}%"
        if blame.get("via"):
            text += f" (via {', '.join(blame['via'])})"
        parts.append(text)
    basis = f" [{row['basis']}]" if row.get("basis") else ""
    return "Fault: " + "; ".join(parts) + basis


def format_death(row: dict) -> str:
    """One death in the same shape as the review-mechanic block, minus markdown."""
    guid = row.get("guid") or 0
    mechanic = row.get("mechanic") or row.get("ability") or "Unknown"
    if guid and row.get("outcome") == "unknown":
        label = f"{mechanic} ({guid})"
    else:
        label = mechanic
    when = f" · {row['time']}" if row.get("time") else ""
    lines = [
        f"Pull {row.get('fight')} · {row.get('name')} · {label} — {row.get('outcome')}{when}",
        str(row.get("went_wrong") or "").strip() or "(no line)",
    ]
    blame = _blame_line(row)
    if blame:
        lines.append(blame)
    if row.get("missing"):
        lines.append(f"Judged without: {', '.join(row['missing'])}")
    if row.get("first"):
        lines.append("First mistake of the pull.")
    elif row.get("late"):
        lines.append("After the pull was lost.")
    return "\n".join(lines)


def _count_line(counts: Counter) -> str:
    bits = []
    for key in _OUTCOME_ORDER:
        if counts.get(key):
            bits.append(f"{counts[key]} {key}")
    return ", ".join(bits) if bits else "0 deaths"


def _pull_line(pull: int, counts: Counter, first: str = "") -> str:
    bits = []
    for key in _OUTCOME_ORDER:
        n = counts.get(key) or 0
        if n:
            bits.append(f"{_OUTCOME_SHORT[key]}{n}")
    line = f"{pull} {' '.join(bits)}"
    if first:
        line += f" · first: {first}"
    return line


def _tally(rows: list[dict], key: str) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for row in rows:
        label = row.get(key) or row.get("ability") or "?"
        counter[str(label)] += 1
    return counter.most_common()


def format_brief(
    report: Path,
    judgments: list[dict],
    *,
    pull: int | None = None,
    mechanic: str | None = None,
    outcomes: frozenset[str] | None = None,
    detail: str = "default",
) -> str:
    """Build a short text digest for one session."""
    if detail not in {"default", "all", "none"}:
        raise SystemExit("--detail must be default, all, or none")

    meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
    when = session_clock(report, meta)
    filtered = filter_judgments(
        judgments, pull=pull, mechanic=mechanic, outcomes=outcomes
    )
    scoped = bool(pull is not None or mechanic or outcomes is not None)
    all_counts = Counter(row.get("outcome") or "?" for row in judgments)
    counts = Counter(row.get("outcome") or "?" for row in filtered)

    lines: list[str] = []
    title = when.get("title") or ""
    owner = when.get("owner") or ""
    clock = " ".join(
        piece for piece in (when.get("dayLabel"), when.get("timeLabel")) if piece
    )
    header = f"{report.name}"
    if title or owner:
        header += f" · {owner}" if owner else ""
        if title:
            header += f", {title}" if owner else f" · {title}"
    if clock:
        header += f" · {clock}"
    lines.append(header)
    lines.append(_count_line(all_counts if not scoped else counts))
    inputs = read_inputs(report) or {}
    skipped = (inputs.get("deaths") or {}).get("not_judged_by_reason") or {}
    if skipped and not scoped:
        total = sum(skipped.values())
        why = "; ".join(f"{count} {reason}" for reason, count in skipped.items())
        lines.append(f"not judged: {total} deaths ({why})")
    gaps = problems(inputs) if inputs else []
    if gaps and not scoped:
        lines.append(f"inputs missing: {len(gaps)} kinds, calls on them are weaker. Run: python -m xivloganalyzer check {report.name}")
    if scoped:
        scope_bits = []
        if pull is not None:
            scope_bits.append(f"pull {pull}")
        if mechanic:
            scope_bits.append(f"mechanic {mechanic}")
        if outcomes is not None:
            scope_bits.append("outcomes " + ",".join(sorted(outcomes)))
        lines.append("filter: " + "; ".join(scope_bits))
        lines.append(f"showing {len(filtered)} of {len(judgments)} deaths")

    if not scoped:
        night = night_lines(judgments)
        if night:
            lines.append("")
            lines += night
        raw_rows = [row for row in judgments if row.get("outcome") == "raw"]
        if raw_rows:
            lines.append("")
            lines.append("Raw by mechanic")
            for name, n in _tally(raw_rows, "mechanic"):
                lines.append(f"  {n} {name}")
        fail_rows = [row for row in judgments if row.get("outcome") == "fail"]
        if fail_rows:
            lines.append("")
            lines.append("Fail by mechanic")
            for name, n in _tally(fail_rows, "mechanic")[:12]:
                lines.append(f"  {n} {name}")
            extra = len(_tally(fail_rows, "mechanic")) - 12
            if extra > 0:
                lines.append(f"  … {extra} more")

    by_pull: dict[int, Counter] = {}
    firsts: dict[int, str] = {}
    for row in filtered if scoped else judgments:
        fight = int(row.get("fight") or 0)
        by_pull.setdefault(fight, Counter())[row.get("outcome") or "?"] += 1
        if row.get("first_mistake"):
            firsts.setdefault(fight, str(row["first_mistake"]))
    if by_pull:
        lines.append("")
        lines.append(f"Pulls ({len(by_pull)})")
        for fight in sorted(by_pull):
            lines.append(_pull_line(fight, by_pull[fight], firsts.get(fight, "")))

    if detail == "none":
        return "\n".join(lines).rstrip() + "\n"

    if detail == "all":
        detail_rows = [
            row for row in filtered if row.get("outcome") != "environment"
        ]
    elif scoped:
        # A pull or mechanic slice: show every matched death that still has a packet.
        detail_rows = [
            row for row in filtered if row.get("outcome") != "environment"
        ]
        if outcomes is not None:
            detail_rows = list(filtered)
    else:
        detail_rows = [
            row for row in filtered if row.get("outcome") in _DEFAULT_DETAIL
        ]

    unknown = [row for row in detail_rows if row.get("outcome") == "unknown"]
    other = [row for row in detail_rows if row.get("outcome") != "unknown"]

    if unknown:
        lines.append("")
        lines.append(f"Unknown ({len(unknown)})")
        for row in unknown:
            lines.append(format_death(row))
            lines.append("")

    if other:
        label = "Deaths" if scoped or detail == "all" else "Raw"
        lines.append(f"{label} ({len(other)})")
        for row in other:
            lines.append(format_death(row))
            lines.append("")

    if detail != "none" and not detail_rows:
        lines.append("")
        lines.append("No detail deaths in this slice.")

    return "\n".join(lines).rstrip() + "\n"


def brief_text(
    report: Path,
    *,
    pull: int | None = None,
    mechanic: str | None = None,
    outcome: str | None = None,
    detail: str = "default",
) -> str:
    judgments = load_judgments(report)
    return format_brief(
        report,
        judgments,
        pull=pull,
        mechanic=mechanic,
        outcomes=_parse_outcomes(outcome),
        detail=detail,
    )


def write_brief(report: Path, text: str) -> Path:
    path = report / "brief.txt"
    path.write_text(text, encoding="utf-8")
    return path
