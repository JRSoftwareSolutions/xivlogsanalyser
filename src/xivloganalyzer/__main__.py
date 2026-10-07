"""Drop a log in, or rebuild every saved session after a correction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from xivloganalyzer.audit import FLAGS, audit_text
from xivloganalyzer.brief import brief_text, write_brief
from xivloganalyzer.catalog import repo_root
from xivloganalyzer.pipeline import analyze, reanalyze, report_dirs, status


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="xivloganalyzer")
    parser.add_argument(
        "command",
        choices=("analyze", "reanalyze", "status", "brief", "audit"),
        help=(
            "analyze one log, rebuild every out-of-date log, list which logs are "
            "out of date, print a session digest, or list calls on weak evidence"
        ),
    )
    parser.add_argument("report", nargs="?", help="report folder or code")
    parser.add_argument(
        "--all",
        action="store_true",
        help="reanalyze: judge every log again, even the ones that are up to date",
    )
    parser.add_argument("--pull", type=int, help="brief: only this pull id")
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
    args = parser.parse_args()
    root = repo_root()
    if args.command == "reanalyze":
        outcomes = reanalyze(root, everything=args.all)
        if not outcomes:
            raise SystemExit("No logs in reports/ or data/.")
        for item in outcomes:
            why = f"judged again, {item.reason}" if item.judged else "up to date"
            print(f"{item.name}: {_counts(item.counts)} ({why})")
        print(f"dashboard: {root / 'dashboard.html'}")
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
        counts = analyze(_resolve(args.report, root), root)
        print(f"{args.report}: {_counts(counts)}")
        print(f"dashboard: {root / 'dashboard.html'}")
        return
    if not args.report:
        raise SystemExit(f"{args.command} needs a report folder or its code.")
    if args.command == "audit":
        print(audit_text(_resolve(args.report, root), flag=args.flag), end="")
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
