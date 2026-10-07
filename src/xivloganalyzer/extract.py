"""Turn a dropped report folder into death facts.

Facts are the numbers. Judgments are applied later, so a parameter change
does not require reading the log again.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path

from xivloganalyzer.catalog import FightPack, MarkerSpots
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
    clipped_by: list[str] = field(default_factory=list)
    clip_guid: int | None = None
    in_spot: dict[str, bool] = field(default_factory=dict)
    prior_debuffs: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


VULN_GUIDS = {1002940, 1002941}
CLIP_WINDOW_MS = 7000
# The deaths table clock reads one to two seconds after the killing hit's timestamp.
# A death with no killing blow only has that clock, so it is moved back by the middle.
CLOCK_LAG_MS = 1500
# A cascade debuff counts for a death when it landed before the death, or in the same instant.
DEBUFF_SLACK_MS = 1000


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


def _marker_packets(report: Path, pack: FightPack) -> dict[tuple, list[tuple]]:
    """Each marker cast as (first hit, guid, targets in hit order), keyed by fight and caster.

    One packet lands on its targets nearest the center first, a few tens of
    milliseconds apart, so the marker is first. The snapshot row keeps a target
    who died before the hit landed. Damage rows with no packet id are not real hits.
    """
    guids = {guid for mech in pack.mechanics if mech.marker_owns_clip for guid in mech.guids}
    grouped: dict[tuple, list[tuple[int, int, int]]] = defaultdict(list)
    for guid in guids:
        path = report / "abilities" / f"ab_{guid}.json"
        if not path.is_file():
            continue
        events = json.loads(path.read_text(encoding="utf-8")).get("events") or []
        for index, event in enumerate(events):
            packet = event.get("packetID")
            if event.get("type") not in {"damage", "calculateddamage"}:
                continue
            if packet is None or event.get("targetID") is None:
                continue
            key = (event.get("fight"), event.get("sourceID"), guid, packet)
            grouped[key].append((event["timestamp"], index, event["targetID"]))
    casts: dict[tuple, list[tuple]] = defaultdict(list)
    for (fight, source, guid, _packet), hits in grouped.items():
        hits.sort()
        targets: list[int] = []
        for _ts, _index, target in hits:
            if target not in targets:
                targets.append(target)
        casts[(fight, source)].append((hits[0][0], guid, targets))
    return casts


@dataclass
class _Clip:
    holders: list[int]
    guid: int
    landed: int
    holds_marker: bool


def _clipped_by(
    casts: dict[tuple, list[tuple]],
    fight: int,
    target: int | None,
    timestamp: int | None,
    mitigations: list[dict],
    names: dict[int, str],
    direct: bool = False,
) -> _Clip | None:
    """Marker holders whose cast left the vulnerability this player died with.

    When this player held a marker too and their own cast hit one of those
    holders, the two markers overlapped, and this player is listed first.
    A death to the marker cast itself (`direct`) needs no vulnerability: the
    packets show whose leap it was.
    """
    if target is None or timestamp is None:
        return None
    recent = [
        (first, source, guid, targets)
        for (cast_fight, source), rows in casts.items()
        if cast_fight == fight
        for first, guid, targets in rows
        if -500 <= timestamp - first <= CLIP_WINDOW_MS
    ]
    casters = {source for _first, source, _guid, _targets in recent}
    if not direct and not any(
        mit.get("guid") in VULN_GUIDS and mit.get("on_id") == target and mit.get("by_id") in casters
        for mit in mitigations
    ):
        return None
    holders: list[int] = []
    clip_guid = None
    landed = None
    for first, _source, guid, targets in recent:
        if target in targets[1:] and targets[0] in names and targets[0] not in holders:
            holders.append(targets[0])
            clip_guid = guid
            landed = first if landed is None else min(landed, first)
    if not holders or clip_guid is None or landed is None:
        return None
    holds_marker = any(targets[0] == target for _f, _s, _g, targets in recent)
    if any(targets[0] == target and set(holders) & set(targets) for _f, _s, _g, targets in recent):
        holders.insert(0, target)
    return _Clip(holders, clip_guid, landed, holds_marker)


class _Positions:
    """Replay positions from `positions/fight-NN.json`, in yalms from the arena center."""

    def __init__(self, report: Path):
        self.report = report
        self._loaded: dict[int, tuple[dict, dict[int, list[tuple[int, float, float]]]] | None] = {}

    def _pull(self, fight: int):
        if fight not in self._loaded:
            path = self.report / "positions" / f"fight-{fight:02d}.json"
            if not path.is_file():
                self._loaded[fight] = None
            else:
                payload = json.loads(path.read_text(encoding="utf-8"))
                by_actor: dict[int, list[tuple[int, float, float]]] = defaultdict(list)
                for ts, actor, x, y, *_rest in payload.get("samples") or []:
                    if actor is not None and ts is not None:
                        by_actor[int(actor)].append((int(ts), (x - 10000) / 100, (y - 10000) / 100))
                for rows in by_actor.values():
                    rows.sort()
                self._loaded[fight] = (payload.get("actors") or {}, by_actor)
        return self._loaded[fight]

    def at(self, fight: int, actor: int, timestamp: int, slack_ms: int) -> tuple[float, float] | None:
        pull = self._pull(fight)
        if pull is None:
            return None
        rows = pull[1].get(int(actor)) or []
        best = min(rows, key=lambda row: abs(row[0] - timestamp), default=None)
        if best is None or abs(best[0] - timestamp) > slack_ms:
            return None
        return best[1], best[2]

    def boss(self, fight: int, name: str, timestamp: int) -> tuple[float, float] | None:
        pull = self._pull(fight)
        if pull is None:
            return None
        actors, _rows = pull
        found = None
        for actor, info in actors.items():
            if info.get("name") != name or info.get("type") != "Boss":
                continue
            spot = self.at(fight, int(actor), timestamp, 2000)
            if spot and math.hypot(*spot) <= 30:
                found = spot
        return found


def _in_spot(
    positions: _Positions,
    spots: MarkerSpots,
    fight: int,
    landed: int,
    people: dict[int, bool],
    names: dict[int, str],
) -> dict[str, bool]:
    """Who stood where they should when the markers landed.

    `people` maps each player to whether they held a marker. A holder should be
    on a spot. Anyone else should be out of reach of every spot.
    """
    boss = positions.boss(fight, spots.boss, landed)
    if boss is None:
        return {}
    heading = math.atan2(boss[1], boss[0])
    marks = []
    for angle in spots.angles:
        for side in (1, -1):
            turn = heading + side * math.radians(angle)
            mark = (spots.edge * math.cos(turn), spots.edge * math.sin(turn))
            if all(math.dist(mark, other) > 0.5 for other in marks):
                marks.append(mark)
    verdict = {}
    for actor, holds in people.items():
        spot = positions.at(fight, actor, landed, 1000)
        if spot is None or actor not in names:
            continue
        nearest = min(math.dist(spot, mark) for mark in marks)
        verdict[names[actor]] = nearest <= spots.tolerance if holds else nearest > spots.radius
    return verdict


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


def _window_for(windows: list[tuple], timestamp: int) -> tuple | None:
    for phase, start, end in windows:
        if start - 500 <= timestamp < end:
            return (phase, start, end)
    return None


def _cascade_debuffs(
    table: dict | None, pack: FightPack, players: dict[int, str],
) -> list[tuple[int, int | None, str, str]]:
    """Damage Down and Hysteria landing on players, not pets: (applied, removed, player, debuff)."""
    if not table or not pack.cascade_debuffs:
        return []
    wanted = set(pack.cascade_debuffs)
    pending: dict[tuple[str, str], list[int]] = {}
    rows: list[list] = []
    for aura in table.get("auras") or []:
        if aura[3] not in wanted:
            continue
        name = players.get(aura[5])
        if not name:
            continue
        key = (name, aura[3])
        if aura[1] == "applydebuff":
            row = [int(aura[0]), None, name, aura[3]]
            rows.append(row)
            pending.setdefault(key, []).append(len(rows) - 1)
        elif aura[1] == "removedebuff" and pending.get(key):
            rows[pending[key].pop(0)][1] = int(aura[0])
    return [tuple(row) for row in rows]


def _prior_debuffs(debuffs: list[tuple], windows: list[tuple], timestamp: int | None) -> list[dict]:
    if timestamp is None:
        return []
    found = []
    for applied, removed, name, debuff in debuffs:
        if applied > timestamp + DEBUFF_SLACK_MS:
            continue
        window = _window_for(windows, applied)
        if window is None:
            continue
        phase, start, _end = window
        found.append(
            {
                "name": name,
                "debuff": debuff,
                "phase": phase.id,
                "t": round((applied - start) / 1000, 1),
                "until": round((removed - start) / 1000, 1) if removed is not None else None,
            }
        )
    return found


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
    names_by_id = {actor["id"]: actor["name"] for actor in meta.get("friendlies") or []}
    by_guid = _load_events(report)
    marker_casts = _marker_packets(report, pack)
    marker_guids = {guid for mech in pack.mechanics if mech.marker_owns_clip for guid in mech.guids}
    marker_spots = {guid: mech.spots for mech in pack.mechanics if mech.spots for guid in mech.guids}
    positions = _Positions(report)
    mitigation_tables = load_mitigations(report)

    facts: list[DeathFact] = []
    for fight in meta["fights"]:
        if pack.zone_id is not None and fight.get("zoneID") != pack.zone_id:
            continue
        windows = _qualifying_phases(fight, pack)
        if not windows:
            continue
        html = deaths.get(fight["id"], "")
        debuffs = _cascade_debuffs(mitigation_tables.get(fight["id"]), pack, names_by_id)
        boss_pct = round(fight.get("bossPercentage", 0) / 100, 1)
        for row in ROW_RE.findall(html):
            name_match = NAME_RE.search(row)
            time_match = TIME_RE.search(row)
            if not name_match or not time_match:
                continue
            name = unescape(name_match.group(2)).strip()
            job = actors.get(name, {}).get("type") or name_match.group(1)
            when = time_match.group(1).strip()
            head = row.split("last-three-events")[0]
            kb_match = KB_RE.search(head)
            if kb_match:
                ts_match = TS_RE.search(row)
                timestamp = int(ts_match.group(1)) if ts_match else None
            else:
                # The only timestamp in this row is the last hit they lived, not the death.
                timestamp = fight["start_time"] + round(_clock_seconds(when) * 1000) - CLOCK_LAG_MS
            window = None
            if timestamp is not None:
                window = _window_for(windows, timestamp)
                if window is None:
                    continue
            else:
                window = windows[-1]
            phase, start, _end = window
            target = actors.get(name, {}).get("id")
            if not kb_match:
                fact = _fact(
                    fight, phase, start, timestamp, when, name, job, pack, 0, "Environment",
                    0, None, None, None, 0, None, [], boss_pct, party,
                    mitigations_for(mitigation_tables, fight["id"], target, None, 0, timestamp),
                )
                fact.prior_debuffs = _prior_debuffs(debuffs, windows, timestamp)
                facts.append(fact)
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
            fact = _fact(
                fight, phase, start, timestamp, when, name, job, pack, guid, ability,
                total, hp, unmit, mult, int(absorb), stack, buffs, boss_pct, party, mits,
            )
            clip = _clipped_by(
                marker_casts, fight["id"], target, timestamp, mits, names_by_id,
                direct=guid in marker_guids,
            )
            if clip is not None:
                fact.clipped_by = [names_by_id[holder] for holder in clip.holders]
                fact.clip_guid = clip.guid
                spots = marker_spots.get(clip.guid)
                if spots is not None and target is not None:
                    people = {holder: True for holder in clip.holders}
                    people[target] = clip.holds_marker
                    fact.in_spot = _in_spot(
                        positions, spots, fight["id"], clip.landed, people, names_by_id,
                    )
            fact.prior_debuffs = _prior_debuffs(debuffs, windows, timestamp)
            facts.append(fact)
    facts.sort(key=lambda fact: (fact.fight, fact.phase, fact.t, fact.name))
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
