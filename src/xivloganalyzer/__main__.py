"""Drop a log in, or rebuild every saved session after a correction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from xivloganalyzer.audit import FLAGS, audit_text
from xivloganalyzer.brief import brief_text, write_brief
from xivloganalyzer.calls import calls_at, change_line, change_summary, diff_calls, saved_calls
from xivloganalyzer.catalog import load_catalog, pack_for_zone, repo_root
from xivloganalyzer.evidence import evidence_text
from xivloganalyzer.inputs import inputs_text, problems, read_inputs
from xivloganalyzer.pipeline import analyze, reanalyze, report_dirs, status
from xivloganalyzer.verified import check_report, failures, keys, record, verify_text

# How many changed calls a run prints before pointing at `changes`.
SHOWN_CHANGES = 12


def _resolve(arg: str, root: Path) -> Path:
    path = Path(arg)
    if path.is_dir() and (path / "fights.json").is_file():
        return path
    for folder in report_dirs(root):
        if folder.name == arg:
            return folder
    raise SystemExit(f"No dropped log named {arg}. Put it in reports/{arg}/")


def _counts(counts) -> str:
    return (
        f"{counts['raw']} raw, {counts['fail']} failed, "
        f"{counts['low']} already down, {counts['environment']} no packet, "
        f"{counts['unknown']} not understood"
    )


def _print_changes(name: str, changes, root: Path, limit: int | None = SHOWN_CHANGES) -> None:
    checked = keys(root, name)
    shown = changes if limit is None else changes[:limit]
    for change in shown:
        by = checked.get(change.death)
        print(f"  {change_line(change, f'[checked by {by}]' if by else '')}")
    if len(shown) < len(changes):
        print(f"  … {len(changes) - len(shown)} more. Run: python -m xivloganalyzer changes {name}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="xivloganalyzer")
    parser.add_argument(
        "command",
        choices=("analyze", "reanalyze", "status", "brief", "audit", "check", "evidence", "changes", "verify", "confirm"),
        help=(
            "analyze one log, rebuild every out-of-date log, list which logs are "
            "out of date, print a session digest, list calls on weak evidence, "
            "list the inputs a log is missing, print one pull's evidence, list calls that changed since a git "
            "revision, compare calls with the checked ones, or record a checked call"
        ),
    )
    parser.add_argument("report", nargs="?", help="report folder or code")
    parser.add_argument(
        "--all",
        action="store_true",
        help="reanalyze: judge every log again, even the ones that are up to date",
    )
    parser.add_argument("--pull", type=int, help="brief, evidence, confirm: this pull id")
    parser.add_argument("--blind", action="store_true", help="evidence: leave out the judge's calls")
    parser.add_argument("--flag", choices=tuple(FLAGS), help="audit: list every death with this flag")
    parser.add_argument(
        "--mechanic",
        help="brief: filter by mechanic name, ability, guid, or mechanic id",
    )
    parser.add_argument(
        "--outcome",
        help="brief: comma list of outcomes (raw,fail,low,unknown,environment)",
    )
    parser.add_argument(
        "--detail",
        choices=("default", "all", "none"),
        default="default",
        help="brief: death lines (default=unknown+raw; all=non-environment; none=counts only)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="brief: also write brief.txt in the report folder",
    )
    parser.add_argument("--since", default="HEAD", help="changes: git revision to compare with (default HEAD)")
    parser.add_argument("--strict", action="store_true", help="verify: also fail on calls checked by review")
    parser.add_argument("--name", help="confirm: the player who died")
    parser.add_argument("--time", help="confirm: the log's clock time of the death, such as 1:01")
    parser.add_argument("--owners", help="confirm: comma list of who owns it, without Party mitigation")
    parser.add_argument("--by", choices=("user", "review"), default="user", help="confirm: who checked it")
    parser.add_argument("--why", default="", help="confirm: one line on why")
    args = parser.parse_args()
    root = repo_root()
    if args.command == "reanalyze":
        outcomes = reanalyze(root, everything=args.all)
        if not outcomes:
            raise SystemExit("No logs in reports/ or data/.")
        for item in outcomes:
            why = f"judged again, {item.reason}" if item.judged else "up to date"
            print(f"{item.name}: {_counts(item.counts)} ({why})")
            if item.changes:
                print(f"  {change_summary(item.changes)} since the last saved run")
                _print_changes(item.name, item.changes, root)
        print(f"dashboard: {root / 'dashboard.html'}")
        return
    if args.command in {"changes", "verify"}:
        reports = [_resolve(args.report, root)] if args.report else report_dirs(root)
        if not reports:
            raise SystemExit("No logs in reports/ or data/.")
        if args.command == "verify":
            checks = [item for report in reports for item in check_report(root, report)]
            print(verify_text(checks), end="")
            if failures(checks, strict=args.strict):
                raise SystemExit(1)
            return
        for report in reports:
            before = calls_at(report, args.since, root)
            if before is None:
                print(f"{report.name}: not saved at {args.since}")
                continue
            changes = diff_calls(before, saved_calls(report) or [])
            print(f"{report.name}: {change_summary(changes)} since {args.since}")
            _print_changes(report.name, changes, root, limit=None)
        return
    if args.command == "status":
        rows = status(root)
        if not rows:
            raise SystemExit("No logs in reports/ or data/.")
        for name, reason in rows:
            print(f"{name}: {reason or 'up to date'}")
        if any(reason for _name, reason in rows):
            print("Run python -m xivloganalyzer reanalyze to judge those again.")
            raise SystemExit(1)
        return
    if args.command == "analyze":
        if not args.report:
            raise SystemExit("analyze needs a report folder or its code.")
        report = _resolve(args.report, root)
        outcome = analyze(report, root)
        print(f"{args.report}: {_counts(outcome.counts)}")
        if outcome.changes:
            print(f"  {change_summary(outcome.changes)} since the last saved run")
            _print_changes(report.name, outcome.changes, root)
        gaps = problems(read_inputs(report) or {})
        if gaps:
            print(f"warning: {len(gaps)} kinds of missing input. Run: python -m xivloganalyzer check {report.name}")
        print(f"dashboard: {root / 'dashboard.html'}")
        return
    if not args.report:
        raise SystemExit(f"{args.command} needs a report folder or its code.")
    if args.command == "audit":
        print(audit_text(_resolve(args.report, root), flag=args.flag), end="")
        return
    if args.command == "confirm":
        if args.pull is None or not args.name:
            raise SystemExit("confirm needs --pull and --name.")
        owners = None if args.owners is None else [who.strip() for who in args.owners.split(",") if who.strip()]
        call = record(
            root, _resolve(args.report, root), args.pull, args.name, args.time,
            args.outcome, owners, args.by, args.why,
        )
        print(f"checked: pull {call['fight']} {call['time']} {call['name']} · {call['mechanic']} · "
              f"{call['outcome']}, {', '.join(call['owners']) or 'nobody'} (by {call['by']})")
        return
    if args.command == "evidence":
        if args.pull is None:
            raise SystemExit("evidence needs --pull.")
        report = _resolve(args.report, root)
        meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
        catalog = load_catalog(root)
        pack = next(
            (found for zone in {fight.get("zoneID") for fight in meta["fights"]} if (found := pack_for_zone(zone, catalog))),
            None,
        )
        if pack is None:
            raise SystemExit(f"No fight knowledge matches {report.name}.")
        print(evidence_text(report, pack, args.pull, blind=args.blind), end="")
        return
    if args.command == "check":
        report = _resolve(args.report, root)
        result = read_inputs(report)
        if result is None:
            raise SystemExit(f"{report.name} has not been analyzed. Run: python -m xivloganalyzer analyze {report.name}")
        print(inputs_text(report.name, result), end="")
        if problems(result):
            raise SystemExit(1)
        return
    report = _resolve(args.report, root)
    text = brief_text(
        report,
        pull=args.pull,
        mechanic=args.mechanic,
        outcome=args.outcome,
        detail=args.detail,
    )
    print(text, end="")
    if args.write:
        path = write_brief(report, text)
        print(f"wrote: {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
