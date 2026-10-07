"""One pull's evidence, cast by cast, so a call can be checked against what the log shows.

Every damage hit on a player from the fetched ability files, the hits the
mitigation replay saw where no ability file was fetched, the statuses that
decide blame (markers, numbers, vulnerabilities, Damage Down, Hysteria), and
each death's packet, in time order. Then the judge's calls for the pull, unless
`blind` is set: a reviewer who reads the evidence first and the calls after
makes an independent call.

    python -m xivloganalyzer evidence <code> --pull 14 [--blind]
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from xivloganalyzer.calls import saved_calls
from xivloganalyzer.catalog import FightPack
from xivloganalyzer.extract import _load_events
from xivloganalyzer.mitigations import load_mitigations
from xivloganalyzer.roster import pull_players

# Status names that decide blame on any fight, besides the pack's own markers.
_STATUS_WORDS = ("Vulnerability Up", "Weakness", "Brink of Death", "Heavy", "Prey", "Transcendent")


def _k(value: int | float | None) -> str:
    if value is None:
        return "?"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return f"{value / 1000:.0f}k"


def _marker_names(pack: FightPack) -> dict[int, str]:
    """Status ids the pack reads as markers or numbers, by name."""
    found: dict[int, str] = {}
    for mechanic in pack.mechanics:
        for guid, marker in mechanic.dive_markers.items():
            found[guid] = marker.name
        for needs in mechanic.needs_everyone:
            for guid in needs.holders:
                found.setdefault(guid, f"{mechanic.name} holder")
        if mechanic.drops is not None:
            found.setdefault(mechanic.drops.debuff, f"{mechanic.name} marker")
    return found


def _watched(name: str, pack: FightPack) -> bool:
    return name in pack.cascade_debuffs or any(word in name for word in _STATUS_WORDS)


def evidence_text(report: Path, pack: FightPack, fight_id: int, blind: bool = False) -> str:
    meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
    fight = next((row for row in meta["fights"] if row["id"] == fight_id), None)
    if fight is None:
        raise SystemExit(f"Pull {fight_id} is not in {report.name}.")
    party = pull_players(meta, fight_id)
    names = {actor["id"]: actor["name"] for actor in meta.get("friendlies") or []}
    phases = sorted(fight.get("phases") or [], key=lambda row: row["startTime"])

    def clock(ts: int) -> str:
        current = None
        for phase in phases:
            if phase["startTime"] <= ts:
                current = phase
        if current is None:
            return f"P1 {(ts - fight['start_time']) / 1000:6.1f}"
        return f"P{current['id']} {(ts - current['startTime']) / 1000:6.1f}"

    lines = [
        f"pull {fight_id} · {report.name} · wipe at {fight.get('bossPercentage', 0) / 100:.1f}%"
        f" · {(fight['end_time'] - fight['start_time']) / 1000:.0f}s",
        "party: " + ", ".join(f"{actor['name']} ({actor.get('type')})" for actor in party),
    ]
    rows: list[tuple[int, int, str]] = []

    facts_path = report / "facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path.is_file() else []
    starts = {phase["id"]: phase["startTime"] for phase in phases}
    for fact in facts:
        if fact["fight"] != fight_id:
            continue
        ts = fact.get("ts") or round(starts.get(fact["phase"], fight["start_time"]) + fact["t"] * 1000)
        hp = f"{fact['hp']:,}/{fact['max_hp']:,}" if fact.get("hp") is not None and fact.get("max_hp") else "HP ?"
        blow = fact["ability"] if fact.get("guid") else "no packet (deathwall)"
        text = (
            f"DEATH {fact['name']} ({fact['time']}): {blow} took {_k(fact.get('total'))}"
            f" unmitigated {_k(fact.get('unmitigated'))} x{fact.get('multiplier')} shield {_k(fact.get('absorb'))} at {hp}"
        )
        if fact.get("buffs"):
            text += f" · buffs {', '.join(fact['buffs'])}"
        if fact.get("missing"):
            text += f" · judged without {', '.join(fact['missing'])}"
        rows.append((ts, 0, text))

    by_guid = _load_events(report)
    seen_guids = set()
    casts: dict[tuple, list[dict]] = defaultdict(list)
    for guid, events in by_guid.items():
        for event in events:
            if event.get("fight") != fight_id or event.get("targetID") not in names:
                continue
            seen_guids.add(guid)
            ability = (event.get("ability") or {}).get("name") or str(guid)
            casts[(ability, event.get("sourceID"), event.get("packetID") or event["timestamp"] // 1500)].append(event)
    for (ability, source, _packet), hits in casts.items():
        hits.sort(key=lambda event: event["timestamp"])
        bits = []
        for event in hits:
            mult = event.get("multiplier")
            died = " DIED" if event.get("overkill") else ""
            scaled = "" if mult in (None, 1) else f" x{mult}"
            bits.append(f"{names[event['targetID']]} {_k(event.get('unmitigatedAmount') or event.get('amount'))}{scaled}{died}")
        instance = hits[0].get("sourceInstance")
        where = f"{source}/{instance}" if instance else f"{source}"
        rows.append((hits[0]["timestamp"], 1, f"HIT {ability} (source {where}, {len(hits)}): " + "; ".join(bits)))

    table = load_mitigations(report).get(fight_id)
    if table:
        actors = table.get("actors") or {}
        mechanic_of = {guid: mechanic.name for mechanic in pack.mechanics for guid in mechanic.guids}
        replay: dict[tuple, list[tuple]] = defaultdict(list)
        for hit in table.get("hits") or []:
            ts, target, _source, guid = hit[:4]
            if guid in mechanic_of and guid not in seen_guids and target in names:
                replay[(guid, ts // 700)].append((ts, target, hit[4]))
        for (guid, _bucket), hits in replay.items():
            hits.sort()
            bits = [f"{names[target]}{'' if mult in (None, 1) else f' x{mult}'}" for _ts, target, mult in hits]
            rows.append((hits[0][0], 1, f"HIT {mechanic_of[guid]} (replay only, no amounts): " + "; ".join(bits)))
        markers = _marker_names(pack)
        for aura in table.get("auras") or []:
            ts, action, guid, name, source, target = aura[:6]
            if target not in names or action not in ("applydebuff", "removedebuff", "applybuff", "removebuff"):
                continue
            label = markers.get(guid) or (name if _watched(str(name), pack) else None)
            if not label:
                continue
            sign = "+" if action.startswith("apply") else "-"
            who = (actors.get(str(source)) or {}).get("name") or names.get(source, source)
            via = f" via {aura[8]}" if len(aura) > 8 and aura[8] and sign == "+" else ""
            rows.append((ts, 2, f"{sign}{label} on {names[target]}" + (f" (from {who}{via})" if sign == "+" else "")))
    else:
        lines.append("no mitigation replay for this pull: no markers, debuffs, or replay hits")

    for ts, _order, text in sorted(rows):
        lines.append(f"{clock(ts)}  {text}")

    if not blind:
        calls = [row for row in saved_calls(report) or [] if row["fight"] == fight_id]
        if calls:
            lines.append("")
            lines.append("The judge's calls")
            for row in calls:
                missing = f" · without {row['missing']}" if row["missing"] else ""
                lines.append(
                    f"  {row['time']} {row['name']} · {row['mechanic']} · {row['outcome']}/{row['cause']}"
                    f" · {row['owners'] or 'nobody'} [{row['basis']}]{missing}"
                )
    return "\n".join(lines) + "\n"
