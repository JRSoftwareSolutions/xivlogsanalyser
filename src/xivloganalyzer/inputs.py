"""What a dropped log is missing, so a call that fell back to less evidence never goes unnoticed.

`check_inputs` lists, for one report: the ability files the reached phases need
and do not have, the pulls with no positions or no mitigation replay, the players
with no max HP, buff ids on death packets that have no name, and every death row
that was not judged, with why. `analyze` writes it to `inputs.json` and prints a
one-line warning. `python -m xivloganalyzer check <code>` prints it in full.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from xivloganalyzer.catalog import FightPack
from xivloganalyzer.extract import COMBINED_DOTS, STATUS_GUID, DeathFact, _qualifying_phases, fetched_guids

INPUTS = "inputs.json"


def reached_phases(meta: dict, pack: FightPack) -> set[int]:
    """The judged phases any pull of this encounter reached."""
    found: set[int] = set()
    for fight in meta.get("fights") or []:
        if pack.zone_id is not None and fight.get("zoneID") != pack.zone_id:
            continue
        found.update(phase.id for phase, _start, _end in _qualifying_phases(fight, pack))
    return found


def required_guids(pack: FightPack, phases: set[int]) -> dict[int, str]:
    """Every ability file the judge reads for these phases: the mechanics and their soaks."""
    found: dict[int, str] = {}
    for mechanic in pack.mechanics:
        if mechanic.phase not in phases:
            continue
        for guid in mechanic.guids:
            found.setdefault(guid, mechanic.name)
        for needs in mechanic.needs_everyone:
            for guid in needs.soak:
                found.setdefault(guid, f"{mechanic.name} soak")
    if any(guid >= STATUS_GUID for guid in found):
        found.setdefault(COMBINED_DOTS, "combined damage over time")
    return dict(sorted(found.items()))


def check_inputs(
    report: Path, pack: FightPack, meta: dict, facts: list[DeathFact], skipped: list[dict],
) -> dict:
    """Everything this report is missing. Plain data, sorted, so the file never changes by itself."""
    phases = reached_phases(meta, pack)
    fetched = fetched_guids(report)
    required = required_guids(pack, phases)
    judged = sorted({fact.fight for fact in facts})
    no_positions = [fight for fight in judged if not (report / "positions" / f"fight-{fight:02d}.json").is_file()]
    no_replay = [fight for fight in judged if not (report / "mitigations" / f"fight-{fight:02d}.json").is_file()]
    unnamed = sorted({buff for fact in facts for buff in fact.buffs if buff.isdigit()})
    no_max_hp = sorted({fact.name for fact in facts if fact.max_hp is None})
    gaps = Counter(gap for fact in facts for gap in fact.missing)
    by_reason = Counter(f"{row['phase_name']}: {row['reason']}" for row in skipped)
    return {
        "phases": sorted(phases),
        "abilities": [
            {"guid": guid, "name": name} for guid, name in required.items() if guid not in fetched
        ],
        "no_positions": no_positions,
        "no_mitigations": no_replay,
        "no_max_hp": no_max_hp,
        "unnamed_buffs": unnamed,
        "deaths": {
            "judged": len(facts),
            "with_gaps": sum(1 for fact in facts if fact.missing),
            "gaps": dict(sorted(gaps.items())),
            "not_judged": len(skipped),
            "not_judged_by_reason": dict(sorted(by_reason.items())),
        },
        "skipped": sorted(skipped, key=lambda row: (row["fight"], row["time"], row["name"])),
    }


def write_inputs(report: Path, result: dict) -> Path:
    path = report / INPUTS
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return path


def read_inputs(report: Path) -> dict | None:
    path = report / INPUTS
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def problems(result: dict) -> list[str]:
    """One line per kind of gap, empty when the log has everything the judge reads."""
    lines = []
    abilities = result.get("abilities") or []
    if abilities:
        names = ", ".join(f"{row['guid']} {row['name']}" for row in abilities)
        lines.append(f"{len(abilities)} ability files not fetched: {names}")
    if result.get("no_positions"):
        lines.append(f"{len(result['no_positions'])} pulls with no positions: {_ids(result['no_positions'])}")
    if result.get("no_mitigations"):
        lines.append(f"{len(result['no_mitigations'])} pulls with no mitigation replay: {_ids(result['no_mitigations'])}")
    if result.get("no_max_hp"):
        lines.append(f"No max HP for {', '.join(result['no_max_hp'])}")
    if result.get("unnamed_buffs"):
        lines.append(f"Buff ids with no name: {', '.join(result['unnamed_buffs'])}")
    deaths = result.get("deaths") or {}
    if deaths.get("with_gaps"):
        top = ", ".join(f"{gap} {count}" for gap, count in sorted(deaths["gaps"].items(), key=lambda kv: -kv[1]))
        lines.append(f"{deaths['with_gaps']} of {deaths['judged']} calls were made without: {top}")
    return lines


def inputs_text(code: str, result: dict) -> str:
    deaths = result["deaths"]
    lines = [f"{code} · phases judged {', '.join(str(p) for p in result['phases']) or 'none'}"]
    lines.append(
        f"{deaths['judged']} deaths judged, {deaths['not_judged']} not judged"
    )
    for reason, count in deaths["not_judged_by_reason"].items():
        lines.append(f"  {count} {reason}")
    found = problems(result)
    lines.append("")
    if found:
        lines.append("Missing inputs")
        lines += [f"  {line}" for line in found]
    else:
        lines.append("Every input the judge reads is there.")
    return "\n".join(lines) + "\n"


def _ids(ids: list[int]) -> str:
    shown = ", ".join(str(fight) for fight in ids[:12])
    return shown + (f" and {len(ids) - 12} more" if len(ids) > 12 else "")
