"""Drop a log in, or rebuild every saved session after a correction."""

from __future__ import annotations

import argparse
from pathlib import Path

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
    parser.add_argument("command", choices=("analyze", "reanalyze"))
    parser.add_argument("report", nargs="?")
    args = parser.parse_args()
    root = repo_root()
    if args.command == "reanalyze":
        summaries = reanalyze(root)
        if not summaries:
            raise SystemExit("No logs in reports/ or data/.")
    else:
        if not args.report:
            raise SystemExit("analyze needs a report folder or its code.")
        summaries = {args.report: analyze(_resolve(args.report, root), root)}
    for name, counts in summaries.items():
        print(
            f"{name}: {counts['raw']} raw, {counts['fail']} failed, "
            f"{counts['low']} already down, {counts['environment']} no packet, "
            f"{counts['unknown']} not understood"
        )
    print(f"dashboard: {root / 'dashboard.html'}")


if __name__ == "__main__":
    main()
