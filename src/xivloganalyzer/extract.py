"""Turn a dropped report folder into death facts.

Facts are the numbers. Judgments are applied later, so a parameter change
does not require reading the log again.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path

from xivloganalyzer.catalog import FightPack
from xivloganalyzer.mitigations import load_mitigations, mitigations_for

ROW_RE = re.compile(r'<tr style="cursor:pointer".*?</script>', re.S)
NAME_RE = re.compile(r'class="main-table-link ([^"]+)">([^<]+)')
TIME_RE = re.compile(r'class="main-table-number">([^<]+)')
KB_RE = re.compile(r'action/(-?\d+)"[\s\S]*?<span class="school-\d+" style="">([^<]+)')
TS_RE = re.compile(r"timestamp: (\d+)")
EVENT_RE = re.compile(
    r"guid: (-?\d+), type: '\d+' \}, type: '(\w+)'\s*, amount: (-?\d+)([\s\S]*?)\n\}"
)
DAMAGE_BAR_RE = re.compile(r'class="main-table-number damage"[^>]*>([\d,]+|1-Shot)')


@dataclass
class DeathFact:
    fight: int
    phase: int
    phase_name: str
    t: float
    time: str
    name: str
    job: str
    role: str
    guid: int
    ability: str
    total: int
    hp: int | None
    max_hp: int | None
    unmitigated: int | None
    multiplier: float | None
    absorb: int
    stack: int | None
    buffs: list[str]
    boss_pct: float
    pull_ms: int
    mitigations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _grab(tail: str, key: str) -> int | None:
    match = re.search(rf", {key}: (-?\d+(?:\.\d+)?)", tail)
    if not match:
        return None
    value = float(match.group(1))
    return int(value) if value.is_integer() else value


def _tooltip(row: str, guid: int) -> dict | None:
    chosen = None
    for match in EVENT_RE.finditer(row):
        if int(match.group(1)) != guid or match.group(2) != "damage":
            continue
        tail = match.group(4)
        packet = {
            "amount": int(match.group(3)),
            "overkill": _grab(tail, "overkill") or 0,
            "absorbed": _grab(tail, "absorbed") or 0,
            "unmitigated": _grab(tail, "unmitigatedAmount"),
            "multiplier": _grab(tail, "multiplier"),
        }
        chosen = packet
        if packet["overkill"]:
            return packet
    return chosen


def _damage_bar(row: str) -> int:
    match = DAMAGE_BAR_RE.search(row)
    if not match or match.group(1) == "1-Shot":
        return 0
    return int(match.group(1).replace(",", ""))


def _load_events(report: Path) -> dict[int, list[dict]]:
    by_guid: dict[int, list[dict]] = defaultdict(list)
    folder = report / "abilities"
    if not folder.is_dir():
        return by_guid
    for path in folder.glob("ab_*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for event in payload.get("events") or []:
            if event.get("type") != "damage":
                continue
            guid = (event.get("ability") or {}).get("guid")
            if guid is None:
                continue
            by_guid[int(guid)].append(event)
    return by_guid


def _clusters(events: list[dict], window_ms: int = 1500) -> list[list[dict]]:
    ordered = sorted(events, key=lambda event: event["timestamp"])
    groups: list[list[dict]] = []
    current: list[dict] = []
    for event in ordered:
        if not current or event["timestamp"] - current[0]["timestamp"] <= window_ms:
            current.append(event)
        else:
            groups.append(current)
            current = [event]
    if current:
        groups.append(current)
    return groups


def _closest_event(events: list[dict], fight: int, target: int | None, timestamp: int) -> dict | None:
    near = [
        event
        for event in events
        if event.get("fight") == fight
        and (target is None or event.get("targetID") == target)
        and abs(event["timestamp"] - timestamp) <= 4000
    ]
    if not near:
        return None
    killers = [event for event in near if event.get("overkill")]
    pool = killers or near
    return min(pool, key=lambda event: abs(event["timestamp"] - timestamp))


def _stack_size(events: list[dict], fight: int, timestamp: int) -> int | None:
    in_fight = [event for event in events if event.get("fight") == fight]
    best = None
    best_dt = 10**9
    for cluster in _clusters(in_fight):
        dt = min(abs(event["timestamp"] - timestamp) for event in cluster)
        if dt < best_dt:
            best, best_dt = cluster, dt
    if best is None or best_dt > 2500:
        return None
    return len({event["targetID"] for event in best})


def _buff_names(event: dict, auras: dict[str, str]) -> list[str]:
    raw = event.get("buffs") or ""
    names = []
    for piece in str(raw).split("."):
        if not piece:
            continue
        names.append(auras.get(piece, piece))
    return names


def _phase_window(fight: dict, phase_id: int) -> tuple[int, int]:
    phases = fight.get("phases") or []
    start = fight["start_time"]
    for phase in phases:
        if phase["id"] == phase_id:
            start = phase["startTime"]
            break
    end = fight["end_time"]
    later = [phase["startTime"] for phase in phases if phase["id"] > phase_id]
    if later:
        end = min(end, min(later))
    return start, end


def _clock_seconds(when: str) -> float:
    parts = when.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return 0.0


def _qualifying_phases(fight: dict, pack: FightPack) -> list[tuple]:
    found = []
    last = fight.get("lastPhaseForPercentageDisplay") or 0
    for phase in pack.phases:
        if last < phase.id:
            continue
        start, end = _phase_window(fight, phase.id)
        if end - start < phase.min_duration_ms:
            continue
        found.append((phase, start, end))
    return found


def extract_report(report: Path, pack: FightPack) -> list[DeathFact]:
    meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
    deaths = {
        item["id"]: item.get("html") or ""
        for item in json.loads((report / "deaths-html.json").read_text(encoding="utf-8"))
    }
    auras = {}
    aura_path = report / "aura_map.json"
    if aura_path.exists():
        auras = json.loads(aura_path.read_text(encoding="utf-8"))
    party = {}
    party_path = report / "party.json"
    if party_path.exists():
        party = json.loads(party_path.read_text(encoding="utf-8"))
    actors = {actor["name"]: actor for actor in meta.get("friendlies") or []}
    by_guid = _load_events(report)
    mitigation_tables = load_mitigations(report)

    facts: list[DeathFact] = []
    for fight in meta["fights"]:
        if pack.zone_id is not None and fight.get("zoneID") != pack.zone_id:
            continue
        windows = _qualifying_phases(fight, pack)
        if not windows:
            continue
        html = deaths.get(fight["id"], "")
        boss_pct = round(fight.get("bossPercentage", 0) / 100, 1)
        for row in ROW_RE.findall(html):
            name_match = NAME_RE.search(row)
            time_match = TIME_RE.search(row)
            if not name_match or not time_match:
                continue
            name = unescape(name_match.group(2)).strip()
            job = actors.get(name, {}).get("type") or name_match.group(1)
            when = time_match.group(1).strip()
            ts_match = TS_RE.search(row)
            timestamp = int(ts_match.group(1)) if ts_match else None
            window = None
            if timestamp is not None:
                for phase, start, end in windows:
                    if start - 500 <= timestamp < end:
                        window = (phase, start, end)
                        break
                if window is None:
                    continue
            else:
                window = windows[-1]
            phase, start, _end = window
            head = row.split("last-three-events")[0]
            kb_match = KB_RE.search(head)
            target = actors.get(name, {}).get("id")
            if not kb_match:
                facts.append(
                    _fact(
                        fight, phase, start, timestamp, when, name, job, pack, 0, "Environment",
                        0, None, None, None, 0, None, [], boss_pct, party,
                        mitigations_for(mitigation_tables, fight["id"], target, None, 0, timestamp),
                    )
                )
                continue
            guid = int(kb_match.group(1))
            ability = unescape(kb_match.group(2)).strip()
            tip = _tooltip(row, guid)
            event = None
            if timestamp is not None:
                event = _closest_event(by_guid.get(guid, []), fight["id"], target, timestamp)
            amount = (event or {}).get("amount")
            overkill = (event or {}).get("overkill") or 0
            absorb = (event or {}).get("absorbed") or 0
            unmit = (event or {}).get("unmitigatedAmount")
            mult = (event or {}).get("multiplier")
            buffs = _buff_names(event, auras) if event else []
            if event is None and tip:
                amount = tip["amount"]
                overkill = tip["overkill"]
                absorb = tip["absorbed"]
                unmit = tip["unmitigated"]
                mult = tip["multiplier"]
            total = 0
            hp = None
            if amount is not None:
                total = int(amount) + int(overkill) + int(absorb)
                if overkill:
                    hp = int(amount)
            if total <= 0:
                total = _damage_bar(row)
            stack = None
            if timestamp is not None and guid in by_guid:
                stack = _stack_size(by_guid[guid], fight["id"], timestamp)
            if mult is not None:
                mult = float(mult)
            source = (event or {}).get("sourceID")
            mits = mitigations_for(
                mitigation_tables, fight["id"], target, source, guid, timestamp,
            )
            facts.append(
                _fact(
                    fight, phase, start, timestamp, when, name, job, pack, guid, ability,
                    total, hp, unmit, mult, int(absorb), stack, buffs, boss_pct, party, mits,
                )
            )
    facts.sort(key=lambda fact: (fact.fight, fact.t, fact.name))
    return facts


def _fact(
    fight, phase, start, timestamp, when, name, job, pack, guid, ability,
    total, hp, unmit, mult, absorb, stack, buffs, boss_pct, party, mitigations,
) -> DeathFact:
    if timestamp is None:
        t = round(_clock_seconds(when) - (start - fight["start_time"]) / 1000, 1)
    else:
        t = round((timestamp - start) / 1000, 1)
    return DeathFact(
        fight=fight["id"],
        phase=phase.id,
        phase_name=phase.name,
        t=t,
        time=when,
        name=name,
        job=job,
        role=pack.role_of(job),
        guid=guid,
        ability=ability,
        total=int(total or 0),
        hp=hp,
        max_hp=party.get(name),
        unmitigated=int(unmit) if unmit is not None else None,
        multiplier=mult,
        absorb=absorb,
        stack=stack,
        buffs=buffs,
        boss_pct=boss_pct,
        pull_ms=fight["end_time"] - start,
        mitigations=mitigations,
    )


def write_facts(report: Path, facts: list[DeathFact]) -> Path:
    path = report / "facts.json"
    path.write_text(
        json.dumps([fact.to_dict() for fact in facts], indent=2),
        encoding="utf-8",
    )
    return path


def read_facts(report: Path) -> list[DeathFact]:
    rows = json.loads((report / "facts.json").read_text(encoding="utf-8"))
    return [DeathFact(**row) for row in rows]
