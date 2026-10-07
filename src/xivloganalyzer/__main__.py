"""Drop a log in, or rebuild every saved session after a correction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from xivloganalyzer.brief import brief_text, write_brief
from xivloganalyzer.catalog import repo_root
from xivloganalyzer.pipeline import analyze, reanalyze, report_dirs


def _resolve(arg: str, root: Path) -> Path:
    path = Path(arg)
    if path.is_dir() and (path / "fights.json").is_file():
        return path
    for folder in report_dirs(root):
        if folder.name == arg:
            return folder
    raise SystemExit(f"No dropped log named {arg}. Put it in reports/{arg}/")


def main() -> None:
    parser = argparse.ArgumentParser(prog="xivloganalyzer")
    parser.add_argument(
        "command",
        choices=("analyze", "reanalyze", "brief"),
        help="analyze one log, rebuild every log, or print a session digest",
    )
    parser.add_argument("report", nargs="?", help="report folder or code")
    parser.add_argument("--pull", type=int, help="brief: only this pull id")
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
        summaries = reanalyze(root)
        if not summaries:
            raise SystemExit("No logs in reports/ or data/.")
        for name, counts in summaries.items():
            print(
                f"{name}: {counts['raw']} raw, {counts['fail']} failed, "
                f"{counts['low']} already down, {counts['environment']} no packet, "
                f"{counts['unknown']} not understood"
            )
        print(f"dashboard: {root / 'dashboard.html'}")
        return
    if args.command == "analyze":
        if not args.report:
            raise SystemExit("analyze needs a report folder or its code.")
        counts = analyze(_resolve(args.report, root), root)
        print(
            f"{args.report}: {counts['raw']} raw, {counts['fail']} failed, "
            f"{counts['low']} already down, {counts['environment']} no packet, "
            f"{counts['unknown']} not understood"
        )
        print(f"dashboard: {root / 'dashboard.html'}")
        return
    if not args.report:
        raise SystemExit("brief needs a report folder or its code.")
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
