"""Which rules a saved report was judged with, so reanalyze only redoes what changed.

Every report folder gets an `analysis.json` after it is judged. It holds three
fingerprints: `rules` (the fight pack folder, e.g. `fights/dsr/`), `engine` (the
analyzer code and page template), and `log` (the dropped log files). It also
holds a fingerprint of each page it wrote, the outcome counts, and the session's
dashboard entry, so the dashboard can be rebuilt without judging the report
again. A report is up to date when all of that still matches. All pulls in a
report share one stamp, because the session page is written as a whole.

The stamp has no timestamps and line endings are ignored, so it reads the same
on every machine and only changes when a judgment can change.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

STAMP = "analysis.json"
OUTPUTS = ("facts.json", "judgments.json", "session.html", "inputs.json")
# Written in the report folder but not part of the log.
NOT_LOG = {STAMP, "brief.txt", "detail.js", *OUTPUTS}
OUTCOMES = ("raw", "fail", "low", "environment", "unknown")
# What the analyzer is made of. Anything else in the package folder is not read.
ENGINE_FILES = {".py", ".html", ".png"}


def _files(
    folder: Path, skip: set[str] = frozenset(), suffixes: set[str] | None = None,
) -> list[tuple[str, Path]]:
    """Files under `folder`, without hidden files and caches, so stray local files do not count."""
    found = []
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(folder).parts
        if "__pycache__" in parts or any(part.startswith(".") for part in parts):
            continue
        if suffixes is not None and path.suffix not in suffixes:
            continue
        name = "/".join(parts)
        if name in skip:
            continue
        found.append((name, path))
    return sorted(found)


def _digest(files: list[tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for name, path in files:
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()[:16]


def rules_version(pack_dir: Path) -> str:
    return _digest(_files(pack_dir, suffixes={".json"}))


def engine_version() -> str:
    return _digest(_files(Path(__file__).parent, suffixes=ENGINE_FILES))


def log_version(report: Path) -> str:
    return _digest(_files(report, NOT_LOG))


def _outputs(report: Path) -> dict[str, str]:
    return {
        name: _digest([(name, report / name)]) if (report / name).is_file() else ""
        for name in OUTPUTS
    }


def read_stamp(report: Path) -> dict | None:
    path = report / STAMP
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@dataclass
class Freshness:
    current: bool
    reason: str = ""


def check(report: Path, pack_dir: Path, engine: str | None = None) -> Freshness:
    """Up to date, or the first reason the saved pages may be wrong."""
    stamp = read_stamp(report)
    if stamp is None:
        return Freshness(False, "never analyzed")
    if stamp.get("rules") != rules_version(pack_dir):
        return Freshness(False, f"rules changed ({pack_dir.parent.name}/{pack_dir.name})")
    if stamp.get("engine") != (engine or engine_version()):
        return Freshness(False, "analyzer code changed")
    if stamp.get("log") != log_version(report):
        return Freshness(False, "log files changed")
    if stamp.get("outputs") != _outputs(report):
        return Freshness(False, "saved pages missing or edited")
    if not isinstance(stamp.get("summary"), dict):
        return Freshness(False, "stamp has no dashboard entry")
    return Freshness(True)


def write_stamp(
    report: Path, pack_dir: Path, counts: Counter, summary: dict, engine: str | None = None,
) -> Path:
    stamp = {
        "rules": rules_version(pack_dir),
        "engine": engine or engine_version(),
        "log": log_version(report),
        "outputs": _outputs(report),
        "counts": {name: counts.get(name, 0) for name in OUTCOMES},
        "summary": summary,
    }
    path = report / STAMP
    path.write_text(json.dumps(stamp, indent=1) + "\n", encoding="utf-8")
    return path
