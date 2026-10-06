"""Extract a dropped log, judge it, and rebuild every saved session."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from xivloganalyzer.catalog import load_catalog, pack_for_zone, repo_root
from xivloganalyzer.dashboard import (
    build_timeline,
    session_clock,
    session_payload,
    write_library,
    write_session_page,
)
from xivloganalyzer.extract import extract_report, write_facts
from xivloganalyzer.judge import judge_report, write_judgments


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


def _analyze(report: Path, root: Path) -> tuple[Counter, dict]:
    report = report.resolve()
    catalog = load_catalog(root)
    import json

    meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
    zone_ids = {fight.get("zoneID") for fight in meta["fights"]}
    pack = None
    for zone_id in zone_ids:
        pack = pack_for_zone(zone_id, catalog)
        if pack is not None:
            break
    if pack is None:
        raise SystemExit(f"No fight knowledge matches zone {sorted(zone_ids)} in {report.name}")
    facts = extract_report(report, pack)
    judgments = judge_report(facts, pack)
    write_facts(report, facts)
    write_judgments(report, judgments)
    when = session_clock(report, meta)
    payload = session_payload(judgments, pack, report.name, when, meta)
    judged = {pull["id"] for pull in payload["pulls"]}
    payload["overview"] = build_timeline(meta, when, judged)
    write_session_page(report, payload)
    return Counter(item.outcome for item in judgments), payload


def analyze(report: Path, root: Path | None = None) -> Counter:
    root = root or repo_root()
    counts, payload = _analyze(report, root)
    others = []
    for folder in report_dirs(root):
        if folder.name == report.name:
            continue
        if (folder / "judgments.json").is_file():
            _counts, other = _analyze(folder, root)
            others.append(other)
    write_library(root, [payload, *others])
    return counts


def reanalyze(root: Path | None = None) -> dict[str, Counter]:
    root = root or repo_root()
    summaries = {}
    payloads = []
    for report in report_dirs(root):
        counts, payload = _analyze(report, root)
        summaries[report.name] = counts
        payloads.append(payload)
    if payloads:
        write_library(root, payloads)
    return summaries
