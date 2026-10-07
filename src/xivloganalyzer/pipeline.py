"""Extract a dropped log, judge it, and rebuild every saved session.

A report is judged again only when its stamp (`stamp.py`) says the rules, the
analyzer code, or its log changed since the last run.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from xivloganalyzer.calls import Change, diff_calls, saved_calls, write_calls
from xivloganalyzer.catalog import FightPack, load_catalog, pack_for_zone, repo_root
from xivloganalyzer.dashboard import (
    attach_debuffs,
    build_timeline,
    session_clock,
    session_payload,
    session_summary,
    write_dashboard,
    write_session_page,
)
from xivloganalyzer.extract import extract_report, write_facts
from xivloganalyzer.frames import attach_frames
from xivloganalyzer.inputs import check_inputs, write_inputs
from xivloganalyzer.judge import judge_report, roster_from_meta, write_judgments
from xivloganalyzer.stamp import check, engine_version, read_stamp, write_stamp


def report_dirs(root: Path | None = None) -> list[Path]:
    root = root or repo_root()
    found = []
    for folder in ("reports", "data"):
        base = root / folder
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if (child / "fights.json").is_file() and (child / "deaths-html.json").is_file():
                found.append(child)
    return found


@dataclass
class Outcome:
    """One report after a run. `reason` is why it was judged again, empty when it was skipped.
    `changes` are the calls that differ from the ones saved before this run."""

    name: str
    counts: Counter
    judged: bool
    reason: str = ""
    changes: list[Change] = field(default_factory=list)


def _meta(report: Path) -> dict:
    return json.loads((report / "fights.json").read_text(encoding="utf-8"))


def _pack(report: Path, meta: dict, catalog: list[FightPack]) -> FightPack:
    zone_ids = {fight.get("zoneID") for fight in meta["fights"]}
    for zone_id in zone_ids:
        pack = pack_for_zone(zone_id, catalog)
        if pack is not None:
            return pack
    raise SystemExit(f"No fight knowledge matches zone {sorted(zone_ids)} in {report.name}")


def _analyze(report: Path, pack: FightPack, meta: dict, engine: str) -> tuple[Counter, dict, list[Change]]:
    before = saved_calls(report)
    skipped: list[dict] = []
    facts = extract_report(report, pack, skipped)
    judgments = judge_report(facts, pack, roster_from_meta(meta, pack))
    write_facts(report, facts)
    write_judgments(report, judgments)
    write_calls(report, [item.to_dict() for item in judgments])
    write_inputs(report, check_inputs(report, pack, meta, facts, skipped))
    changes = diff_calls(before, saved_calls(report) or []) if before is not None else []
    when = session_clock(report, meta)
    payload = session_payload(judgments, pack, report.name, when, meta)
    attach_debuffs(report, payload, pack, meta)
    attach_frames(report, payload, pack)
    judged = {pull["id"] for pull in payload["pulls"]}
    payload["overview"] = build_timeline(meta, when, judged, pack)
    write_session_page(report, payload)
    counts = Counter(item.outcome for item in judgments)
    summary = session_summary(payload, "")
    write_stamp(report, pack.folder, counts, summary, engine)
    return counts, summary, changes


def _run(reports: list[Path], root: Path, force: set[str]) -> list[Outcome]:
    catalog = load_catalog(root)
    engine = engine_version()
    outcomes = []
    summaries = []
    for report in reports:
        report = report.resolve()
        meta = _meta(report)
        pack = _pack(report, meta, catalog)
        if report.name in force:
            reason = "requested"
        else:
            fresh = check(report, pack.folder, engine)
            reason = "" if fresh.current else fresh.reason
        changes: list[Change] = []
        if reason:
            counts, summary, changes = _analyze(report, pack, meta, engine)
        else:
            stamp = read_stamp(report)
            counts, summary = Counter(stamp["counts"]), stamp["summary"]
        outcomes.append(Outcome(report.name, counts, bool(reason), reason, changes))
        summaries.append(summary)
    if summaries:
        write_dashboard(root, summaries)
    return outcomes


def analyze(report: Path, root: Path | None = None) -> Outcome:
    """Judge this report, judge any other saved report that is out of date, rebuild the dashboard."""
    root = root or repo_root()
    report = report.resolve()
    others = [folder for folder in report_dirs(root) if folder.resolve() != report]
    outcomes = _run([report, *others], root, force={report.name})
    return outcomes[0]


def reanalyze(root: Path | None = None, everything: bool = False) -> list[Outcome]:
    """Judge every saved report whose rules, code, or log changed. `everything` judges them all."""
    root = root or repo_root()
    reports = report_dirs(root)
    force = {report.name for report in reports} if everything else set()
    return _run(reports, root, force)


def status(root: Path | None = None) -> list[tuple[str, str]]:
    """Each saved report and why it is out of date, empty when it is current. Writes nothing."""
    root = root or repo_root()
    catalog = load_catalog(root)
    engine = engine_version()
    rows = []
    for report in report_dirs(root):
        pack = _pack(report, _meta(report), catalog)
        rows.append((report.name, check(report, pack.folder, engine).reason))
    return rows
