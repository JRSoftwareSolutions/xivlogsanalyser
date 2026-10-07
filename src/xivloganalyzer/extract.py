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
# A damage-over-time kill, such as Frostbite, links its status instead of an action.
KB_RE = re.compile(r'#(action|status)/(-?\d+)"[\s\S]*?<span class="school-\d+" style="">([^<]+)')
# Logs number a status as this plus its game id.
STATUS_GUID = 1_000_000
# Every damage-over-time tick in one instant, summed. Logs split it evenly across
# the statuses that ticked, so a single status's share is too small.
COMBINED_DOTS = 500000
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
    divers: list[dict] = field(default_factory=list)
    in_spot: dict[str, bool] = field(default_factory=dict)
    prior_debuffs: list[dict] = field(default_factory=list)
    down: list[str] = field(default_factory=list)
    unsoaked: list[str] = field(default_factory=list)
    doubled: list[str] = field(default_factory=list)
    marked: list[str] = field(default_factory=list)
    dropped_by: list[str] = field(default_factory=list)
    cohort: list[str] = field(default_factory=list)
    dead: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


VULN_GUIDS = {1002940, 1002941}
CLIP_WINDOW_MS = 7000
# A dive marker comes off a few hundred milliseconds before its landing hits.
DIVE_BEFORE_MS = 2500
DIVE_AFTER_MS = 1000
ARENA_CENTER = 10000
# The deaths table clock reads one to two seconds after the killing hit's timestamp.
# A death with no killing blow only has that clock, so it is moved back by the middle.
CLOCK_LAG_MS = 1500
# A cascade debuff counts for a death when it landed before the death, or in the same instant.
DEBUFF_SLACK_MS = 1000
# Weakness. A raised player carries it, so they are back in the fight.
RAISE_GUID = 1000043
# Deaths to one cast land within this much of each other.
CAST_MS = 3000


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


def _load_events(report: Path, kind: str = "damage") -> dict[int, list[dict]]:
    """Events of one type by guid. `calculateddamage` is the snapshot, which keeps
    a target who died before the damage landed."""
    by_guid: dict[int, list[dict]] = defaultdict(list)
    folder = report / "abilities"
    if not folder.is_dir():
        return by_guid
    for path in folder.glob("ab_*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for event in payload.get("events") or []:
            if event.get("type") != kind:
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


def _combined_tick(combined: list[dict], tick: dict) -> dict | None:
    """The summed tick from the same instant as this status's share, if there is one."""
    for event in combined:
        if (
            event.get("fight") == tick.get("fight")
            and event.get("targetID") == tick.get("targetID")
            and event["timestamp"] == tick["timestamp"]
        ):
            return event
    return None


def _snapshot_size(events: list[dict], fight: int, timestamp: int) -> int | None:
    """Targets of the last snapshot before the hit. It keeps a target who died before
    the damage landed, which the damage rows drop."""
    in_fight = [event for event in events if event.get("fight") == fight]
    before = [
        cluster for cluster in _clusters(in_fight)
        if cluster[0]["timestamp"] <= timestamp and timestamp - cluster[0]["timestamp"] <= 2500
    ]
    if not before:
        return None
    return len({event["targetID"] for event in before[-1]})


def _cohort(events: list[dict], fight: int, event: dict | None, names: dict[int, str]) -> list[str]:
    """Everyone the killing packet hit, survivors included, in hit order."""
    packet = (event or {}).get("packetID")
    if packet is None:
        return []
    found: list[str] = []
    for other in sorted(events, key=lambda row: row["timestamp"]):
        if other.get("fight") != fight or other.get("packetID") != packet:
            continue
        name = names.get(other.get("targetID"))
        if name and name not in found:
            found.append(name)
    return found


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

    def named(self, fight: int, name: str) -> list[tuple[int, float, float]]:
        """Every sample of the actors with this name, once each, in time order."""
        pull = self._pull(fight)
        if pull is None:
            return []
        actors, rows = pull
        found = set()
        for actor, info in actors.items():
            if info.get("name") == name:
                found.update(rows.get(int(actor)) or [])
        return sorted(found)

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


def _positions(report: Path, fight: int, cache: dict[int, dict]) -> dict[int, list]:
    """Replay samples by actor, as (timestamp, x, y, facing). x and y are hundredths of a yalm."""
    if fight not in cache:
        by_actor: dict[int, list] = defaultdict(list)
        path = report / "positions" / f"fight-{fight:02d}.json"
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            for ts, actor, x, y, facing, *_rest in payload.get("samples") or []:
                by_actor[actor].append((ts, x, y, facing))
        cache[fight] = by_actor
    return cache[fight]


def _place(places: dict[int, list], actor: int | None, timestamp: int) -> tuple | None:
    """Yalms from the arena center, and the compass facing, at the sample nearest this moment."""
    samples = [sample for sample in places.get(actor) or [] if abs(sample[0] - timestamp) <= 1500]
    if not samples:
        return None
    _ts, x, y, facing = min(samples, key=lambda sample: abs(sample[0] - timestamp))
    return round((x - ARENA_CENTER) / 100, 2), round((y - ARENA_CENTER) / 100, 2), _compass(facing)


def _compass(facing: int | None) -> str | None:
    """The replay facing is hundredths of a radian. +x is east and +y is south."""
    if facing is None:
        return None
    theta = facing / 100.0
    dx, dy = math.cos(theta), math.sin(theta)
    if abs(dx) >= abs(dy):
        return "east" if dx > 0 else "west"
    return "south" if dy > 0 else "north"


def _divers(
    tables: dict[int, dict],
    places: dict[int, list],
    fight: int,
    target: int | None,
    timestamp: int | None,
    markers: dict,
    names: dict[int, str],
) -> list[dict]:
    """Players whose dive marker resolved on this landing, and where they stood.

    `x` and `y` are yalms from the arena center. Positive x is east and positive y
    is south. `facing` is where they looked at the snapshot, and `apart` is yalms
    from the player who died.
    """
    payload = tables.get(fight)
    if payload is None or timestamp is None or not markers:
        return []
    here = _place(places, target, timestamp)
    divers = []
    for aura in payload.get("auras") or []:
        if aura[1] != "removedebuff" or aura[2] not in markers:
            continue
        if not -DIVE_BEFORE_MS <= aura[0] - timestamp <= DIVE_AFTER_MS:
            continue
        actor = aura[5]
        if actor not in names:
            continue
        marker = markers[aura[2]]
        row = {
            "name": names[actor], "marker": marker.name, "side": marker.side,
            "should_face": marker.facing, "x": None, "y": None, "facing": None, "apart": None,
        }
        spot = _place(places, actor, timestamp)
        if spot:
            row["x"], row["y"], row["facing"] = spot
            if here:
                row["apart"] = round(math.hypot(spot[0] - here[0], spot[1] - here[1]), 2)
        divers.append(row)
    return sorted(divers, key=lambda row: row["name"])


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
    snapshots = _load_events(report, "calculateddamage")
    marker_casts = _marker_packets(report, pack)
    marker_guids = {guid for mech in pack.mechanics if mech.marker_owns_clip for guid in mech.guids}
    marker_spots = {guid: mech.spots for mech in pack.mechanics if mech.spots for guid in mech.guids}
    positions = _Positions(report)
    mitigation_tables = load_mitigations(report)
    places: dict[int, dict] = {}

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
        timed: list[tuple[int | None, DeathFact]] = []
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
                # The only timestamps in this row are hits they lived, not the death.
                timestamp = fight["start_time"] + round(_clock_seconds(when) * 1000) - CLOCK_LAG_MS
                lived = [int(ts) for ts in TS_RE.findall(row)]
                if lived:
                    timestamp = max(timestamp, max(lived) + 1)
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
                timed.append((timestamp, fact))
                continue
            guid = int(kb_match.group(2))
            if kb_match.group(1) == "status":
                guid += STATUS_GUID
            ability = unescape(kb_match.group(3)).strip()
            tip = _tooltip(row, guid)
            event = None
            if timestamp is not None:
                event = _closest_event(by_guid.get(guid, []), fight["id"], target, timestamp)
                if event is not None and guid >= STATUS_GUID:
                    event = _combined_tick(by_guid.get(COMBINED_DOTS, []), event) or event
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
                stack = _snapshot_size(snapshots.get(guid, []), fight["id"], timestamp)
                if stack is None:
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
            fact.cohort = _cohort(
                snapshots.get(guid, []) + by_guid.get(guid, []), fight["id"], event, names_by_id,
            )
            clip = _clipped_by(
                marker_casts, fight["id"], target, timestamp, mits, names_by_id,
                direct=guid in marker_guids,
            )
            mechanic = pack.mechanic_for(guid, phase.id)
            if mechanic and mechanic.dive_markers:
                fact.divers = _divers(
                    mitigation_tables, _positions(report, fight["id"], places), fight["id"],
                    target, timestamp, mechanic.dive_markers, names_by_id,
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
            timed.append((timestamp, fact))
        raises = _raises(mitigation_tables.get(fight["id"]), names_by_id)
        roster = _fight_roster(meta, fight["id"])
        for timestamp, fact in timed:
            if timestamp is not None:
                fact.dead = [
                    name for name in roster
                    if name != fact.name and _still_dead(name, timed, timestamp, raises)
                ]
        _missing_bodies(
            timed, pack, by_guid, fight["id"], _fight_roster(meta, fight["id"]), raises, names_by_id,
        )
        _drop_owners(
            timed, pack, fight["id"], positions, mitigation_tables.get(fight["id"]), raises, names_by_id,
        )
    facts.sort(key=lambda fact: (fact.fight, fact.phase, fact.t, fact.name))
    return facts


def _fight_roster(meta: dict, fight_id: int) -> list[str]:
    skip = {"LimitBreak", "NPC", "Pet"}
    return [
        actor["name"]
        for actor in meta.get("friendlies") or []
        if actor.get("type") not in skip and f".{fight_id}." in str(actor.get("fights") or "")
    ]


def _raises(table: dict | None, players: dict[int, str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for aura in (table or {}).get("auras") or []:
        if aura[1] != "applydebuff" or aura[2] != RAISE_GUID:
            continue
        name = players.get(aura[5])
        if name:
            found.setdefault(name, []).append(int(aura[0]))
    return found


def _missing_bodies(
    timed: list[tuple[int | None, DeathFact]],
    pack: FightPack,
    by_guid: dict[int, list[dict]],
    fight_id: int,
    roster: list[str],
    raises: dict[str, list[int]],
    names_by_id: dict[int, str],
) -> None:
    """Who was missing from a mechanic that needs every player.

    `down` is dead and not raised when the cast landed. With a soak, the cast landed
    at its first soak hit, `unsoaked` is everyone alive who that soak missed, and
    `doubled` are the players who shared one soak, such as two in one tower.
    """
    for timestamp, fact in timed:
        if timestamp is None:
            continue
        mechanic = pack.mechanic_for(fact.guid, fact.phase)
        needs = mechanic.needs_everyone if mechanic else None
        if needs is None:
            continue
        cast = [
            (ts, other) for ts, other in timed
            if ts is not None and other.guid in mechanic.guids and abs(ts - timestamp) <= CAST_MS
        ]
        first = min(ts for ts, _ in cast)
        victims = {other.name for _, other in cast}
        soaked: set[str] = set()
        at = first - round(needs.lead * 1000)
        if needs.soak:
            hits = [
                event
                for guid in needs.soak
                for event in by_guid.get(guid, [])
                if event.get("fight") == fight_id and at <= event["timestamp"] <= first
            ]
            if not hits:
                continue
            at = min(event["timestamp"] for event in hits)
            soaked = {names_by_id.get(event.get("targetID")) for event in hits}
            shared: dict[tuple, set[str]] = defaultdict(set)
            for event in hits:
                name = names_by_id.get(event.get("targetID"))
                if name:
                    shared[(event.get("sourceID"), event.get("sourceInstance"))].add(name)
            fact.doubled = [
                name for name in roster
                if any(name in group and len(group) > 1 for group in shared.values())
            ]
        died: dict[str, int] = {}
        for ts, other in timed:
            if ts is not None and ts < at:
                died[other.name] = max(died.get(other.name, ts), ts)
        fact.down = [
            name for name in roster
            if name in died and name not in victims
            and not any(died[name] < raised <= at for raised in raises.get(name, []))
        ]
        if needs.soak:
            fact.unsoaked = [name for name in roster if name not in soaked and name not in fact.down]


def _still_dead(
    name: str, timed: list[tuple[int | None, DeathFact]], at: int, raises: dict[str, list[int]],
) -> bool:
    """Died before this moment, and was not raised since."""
    deaths = [ts for ts, other in timed if ts is not None and ts < at and other.name == name]
    if not deaths:
        return False
    return not any(max(deaths) < raised <= at for raised in raises.get(name, []))


def _trails(landed: list[tuple[int, float, float]]) -> list[list[tuple[int, float, float]]]:
    """Drops chained into one trail per holder. Each wave lands together, one drop per holder."""
    trails: list[list[tuple[int, float, float]]] = []
    for ts in sorted({row[0] for row in landed}):
        wave = [row for row in landed if row[0] == ts]
        if not trails:
            trails = [[row] for row in wave]
            continue
        if len(wave) == 2 and len(trails) == 2:
            straight = math.dist(trails[0][-1][1:], wave[0][1:]) + math.dist(trails[1][-1][1:], wave[1][1:])
            crossed = math.dist(trails[0][-1][1:], wave[1][1:]) + math.dist(trails[1][-1][1:], wave[0][1:])
            if crossed < straight:
                wave = [wave[1], wave[0]]
            trails[0].append(wave[0])
            trails[1].append(wave[1])
            continue
        for row in wave:
            min(trails, key=lambda trail: math.dist(trail[-1][1:], row[1:])).append(row)
    return trails


def _drop_owners(
    timed: list[tuple[int | None, DeathFact]],
    pack: FightPack,
    fight_id: int,
    positions: _Positions,
    table: dict | None,
    raises: dict[str, list[int]],
    names_by_id: dict[int, str],
) -> None:
    """Whose drops exploded together.

    `marked` are the holders of the marker debuff. Each wave of drops is a moment
    with a sample of the dropped actor at a new spot. An explosion is a moment
    whose samples all sit on earlier drops. A holder dead before the last drops ahead of it, and not raised, is
    `down`: their drops pile up on one spot. Otherwise `dropped_by` are the
    holders whose drops it sits on.
    """
    for timestamp, fact in timed:
        mechanic = pack.mechanic_for(fact.guid, fact.phase)
        drops = mechanic.drops if mechanic else None
        if drops is None or timestamp is None:
            continue
        start = timestamp - round(drops.within * 1000)
        holders: dict[str, int] = {}
        for aura in (table or {}).get("auras") or []:
            if aura[1] == "applydebuff" and aura[2] == drops.debuff and start <= aura[0] <= timestamp:
                name = names_by_id.get(aura[5])
                if name:
                    holders.setdefault(name, int(aura[5]))
        fact.marked = list(holders)
        samples = [
            row for row in positions.named(fight_id, drops.actor)
            if start <= row[0] <= timestamp and (row[1], row[2]) != (0.0, 0.0)
        ]
        landed: list[tuple[int, float, float]] = []
        blasts: dict[int, list[tuple[int, float, float]]] = {}
        for at in sorted({row[0] for row in samples}):
            wave = [row for row in samples if row[0] == at]
            if all(any(math.dist(row[1:], drop[1:]) <= drops.reach for drop in landed) for row in wave):
                blasts[at] = wave
            else:
                landed.extend(wave)
        if not blasts:
            continue
        blast_at = max(blasts)
        waves = [row[0] for row in landed if row[0] < blast_at]
        if not waves:
            continue
        fact.down = [
            name for name in holders
            if name != fact.name and _still_dead(name, timed, max(waves), raises)
        ]
        if fact.down:
            continue
        trails = _trails([row for row in landed if row[0] < blast_at])
        owners: dict[int, str] = {}
        for index, trail in enumerate(trails):
            first = trail[0]
            near = []
            for name, actor in holders.items():
                if name in owners.values():
                    continue
                spot = positions.at(fight_id, actor, first[0], 1500)
                if spot is not None:
                    near.append((math.dist(spot, first[1:]), name))
            if near:
                owners[index] = min(near)[1]
        dropped: list[str] = []
        for row in blasts[blast_at]:
            reach, index = min(
                (math.dist(row[1:], drop[1:]), index)
                for index, trail in enumerate(trails)
                for drop in trail
            )
            if reach > drops.reach or index not in owners:
                dropped = []
                break
            if owners[index] not in dropped:
                dropped.append(owners[index])
        fact.dropped_by = dropped


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
