"""Turn a dropped report folder into death facts.

Facts are the numbers. Judgments are applied later, so a parameter change
does not require reading the log again.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path

from xivloganalyzer.catalog import FightPack, MarkerSpots
from xivloganalyzer.mitigations import load_mitigations, mitigations_for, replay_multiplier
from xivloganalyzer.roster import actor_for, players, pull_players

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
    group: list[str] = field(default_factory=list)
    self_hits: list[dict] = field(default_factory=list)
    # The death's own log timestamp in milliseconds, for ordering deaths in one instant.
    ts: int | None = None
    # Inputs this call could not read, such as "positions" or "ability 25567".
    missing: list[str] = field(default_factory=list)
    # The report's off tank, on deaths to a hit only the off tank takes.
    off_tank: str = ""
    # The report's main tank, on deaths to a hit only the main tank takes.
    main_tank: str = ""
    # Who drew the hit that stunned them in place, such as the tether holder whose bash hit them.
    stunned_by: list[str] = field(default_factory=list)
    # On a death at the deathwall: whose landing knocked them into it.
    knocked_by: list[str] = field(default_factory=list)
    # Who baited the cone that hit them from outside the stack.
    baited_by: list[str] = field(default_factory=list)
    # The ability that put the latest Vulnerability Up on them before the hit, such as "Darkdragon Dive",
    # and how many milliseconds before the death it landed.
    amp_via: str = ""
    amp_ms: int | None = None

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
# A hit they lived this long before dying can still be why they were low.
SELF_HIT_MS = 10000
# Mechanics where any hit is the player's own mistake.
SELF_CATEGORIES = {"gaze", "dodge", "puddle", "orb"}


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


def fetched_guids(report: Path) -> set[int]:
    """Abilities whose file was fetched, even when no hit landed in it."""
    folder = report / "abilities"
    found = set()
    for path in folder.glob("ab_*.json") if folder.is_dir() else []:
        try:
            found.add(int(path.stem[3:]))
        except ValueError:
            continue
    return found


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


def aura_names(report: Path, tables: dict[int, dict] | None = None) -> dict[str, str]:
    """Buff and debuff names by id, as the packets write them ("1001191").

    The ability files and the replay auras both name every buff they carry.
    `aura_map.json`, when present, overrides them.
    """
    names: dict[str, str] = {}
    folder = report / "abilities"
    if folder.is_dir():
        for path in sorted(folder.glob("ab_*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for aura in payload.get("auraAbilities") or []:
                if aura.get("guid") is not None and aura.get("name"):
                    names[str(aura["guid"])] = aura["name"]
    for table in (tables if tables is not None else load_mitigations(report)).values():
        for aura in table.get("auras") or []:
            if aura[2] is not None and aura[3]:
                names.setdefault(str(aura[2]), aura[3])
    override = report / "aura_map.json"
    if override.is_file():
        names.update(json.loads(override.read_text(encoding="utf-8")))
    return names


def _replay_hits(tables: dict[int, dict], have: set[int]) -> dict[int, list[dict]]:
    """Hits from the replay's hit list, for abilities with no ability file.

    The replay lists only hits that met a mitigation or a shield, so these prove
    who was hit and when, never who was not. They carry no amount and no tower
    instance. Each is marked `replay`.
    """
    found: dict[int, list[dict]] = defaultdict(list)
    for fight, table in tables.items():
        for row in table.get("hits") or []:
            ts, target, source, guid = row[:4]
            if guid is None or int(guid) in have:
                continue
            found[int(guid)].append({
                "timestamp": int(ts), "fight": fight, "targetID": target, "sourceID": source,
                "ability": {"guid": int(guid)}, "type": "damage", "multiplier": row[4], "replay": True,
            })
    return found


def _base_max_hp(
    by_guid: dict[int, list[dict]], names: dict[int, str], tables: dict[int, dict], buffs: dict[str, float],
) -> dict[str, int]:
    """Each player's max HP from the hits that killed them.

    A killing hit's amount is the HP they had, so the largest one is their max
    whenever they ever died from full. A hit while a max-HP buff such as Thrill of
    Battle was on is divided back down by that buff.
    """
    seen: dict[str, Counter] = defaultdict(Counter)
    for events in by_guid.values():
        for event in events:
            name = names.get(event.get("targetID"))
            if not name or not event.get("overkill") or not event.get("amount"):
                continue
            factor = _buff_factor(tables.get(event.get("fight")), event["targetID"], event["timestamp"], buffs)
            seen[name][round(int(event["amount"]) / factor)] += 1
    return {name: max(counts) for name, counts in seen.items()}


def max_hp_bases(party: dict[str, int], seen: dict[str, int]) -> dict[str, int]:
    """Base max HP: what the log shows, and `party.json` only to fill a small gap.

    A player who never died from full shows a little less than their max, so a
    `party.json` value up to 5% above it is taken. A larger one was written with a
    max-HP buff on, and the log wins.
    """
    found = dict(party)
    for name, value in seen.items():
        listed = party.get(name)
        found[name] = listed if listed is not None and value <= listed <= value * 1.05 else value
    return found


def _buff_factor(table: dict | None, target: int | None, timestamp: int | None, buffs: dict[str, float]) -> float:
    """The max-HP multiplier from buffs on this player at this moment."""
    if not table or not buffs or target is None or timestamp is None:
        return 1.0
    active: dict[str, bool] = {}
    for aura in table.get("auras") or []:
        # A buff that drops in the same instant as the hit dropped because they died.
        if aura[0] >= timestamp:
            break
        if aura[5] != target or aura[3] not in buffs:
            continue
        if aura[1] in ("applybuff", "refreshbuff"):
            active[aura[3]] = True
        elif aura[1] == "removebuff":
            active[aura[3]] = False
    factor = 1.0
    for name, on in active.items():
        if on:
            factor *= buffs[name]
    return factor


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


def _self_hits(
    by_guid: dict[int, list[dict]],
    pack: FightPack,
    fight: int,
    target: int | None,
    timestamp: int | None,
    role: str,
    killing: dict | None,
) -> list[dict]:
    """Hits of the player's own mistakes that they lived in the seconds before this death.

    A gaze they looked at, a puddle, a ring, or an orb. A tank's own tether is
    their job, so a tank-only hit on a tank is not one.
    """
    if target is None or timestamp is None:
        return []
    found = []
    for mechanic in pack.mechanics:
        if not mechanic.any_hit_is_fail or mechanic.category not in SELF_CATEGORIES:
            continue
        if mechanic.tanks_only and role == "tank":
            continue
        for guid in mechanic.guids:
            for event in by_guid.get(guid, []):
                if event is killing or event.get("fight") != fight or event.get("targetID") != target:
                    continue
                # A shield it used up is a shield the next hit did not meet.
                hp = int(event.get("amount") or 0)
                shield = int(event.get("absorbed") or 0)
                if event.get("overkill") or hp + shield <= 0:
                    continue
                ago = timestamp - event["timestamp"]
                if 0 < ago <= SELF_HIT_MS:
                    found.append({
                        "ability": mechanic.name,
                        "guid": guid,
                        "ago": round(ago / 1000, 1),
                        "amount": hp + shield,
                        "hp": hp,
                        "shield": shield,
                    })
    return sorted(found, key=lambda hit: hit["ago"], reverse=True)


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
) -> list[tuple[int, int | None, str, str, str]]:
    """Damage Down and Hysteria landing on players, not pets: (applied, removed, player, debuff, via).
    `via` is the ability that applied it, such as "Eternal Conviction", or empty."""
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
            via = str(aura[8] or "") if len(aura) > 8 else ""
            row = [int(aura[0]), None, name, aura[3], via]
            rows.append(row)
            pending.setdefault(key, []).append(len(rows) - 1)
        elif aura[1] == "removedebuff" and pending.get(key):
            rows[pending[key].pop(0)][1] = int(aura[0])
    return [tuple(row) for row in rows]


def _amp_source(table: dict | None, target: int | None, timestamp: int | None) -> tuple[str, int | None]:
    """The ability that put the latest Vulnerability Up on this player before this moment,
    and how many milliseconds before it."""
    if not table or target is None or timestamp is None:
        return "", None
    found, when = "", None
    for aura in table.get("auras") or []:
        if aura[0] > timestamp:
            break
        if aura[5] == target and aura[1] in ("applydebuff", "refreshdebuff") and "Vulnerability Up" in str(aura[3]):
            found = str(aura[8] or "") if len(aura) > 8 else ""
            when = timestamp - int(aura[0])
    return found.strip().removeprefix("the "), when


def _prior_debuffs(debuffs: list[tuple], windows: list[tuple], timestamp: int | None) -> list[dict]:
    if timestamp is None:
        return []
    found = []
    for applied, removed, name, debuff, via in debuffs:
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
                "via": via,
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


def _gaps(
    report: Path, fight: int, tables: dict[int, dict], fact: DeathFact, by_guid: dict[int, list[dict]] | None,
) -> list[str]:
    """Inputs that were not there for this death, so its call fell back to less."""
    gaps = []
    if by_guid is not None and fact.guid and fact.guid not in fetched_guids(report):
        gaps.append(f"ability {fact.guid}")
    if not (report / "positions" / f"fight-{fight:02d}.json").is_file():
        gaps.append("positions")
    if fight not in tables:
        gaps.append("mitigations")
    if fact.max_hp is None:
        gaps.append("max HP")
    return gaps


def _skip_row(
    skipped: list | None, meta: dict, fight: dict, name: str, when: str, timestamp: int | None, reason: str,
) -> None:
    if skipped is None:
        return
    phase, label = _phase_label(meta, fight, timestamp)
    skipped.append({"fight": fight["id"], "name": name, "time": when, "phase": phase, "phase_name": label, "reason": reason})


def _skip_rows(skipped: list | None, meta: dict, fight: dict, html: str, reason: str) -> None:
    for row in ROW_RE.findall(html):
        name_match = NAME_RE.search(row)
        time_match = TIME_RE.search(row)
        if not name_match or not time_match:
            continue
        when = time_match.group(1).strip()
        ts_match = TS_RE.search(row)
        timestamp = int(ts_match.group(1)) if ts_match else fight["start_time"] + round(_clock_seconds(when) * 1000)
        _skip_row(skipped, meta, fight, unescape(name_match.group(2)).strip(), when, timestamp, reason)


def off_tank(report: Path, meta: dict, pack: FightPack, by_guid: dict[int, list[dict]]) -> str:
    """The report's off tank: `assignments.off_tank` in session.json, or else the
    tank the off-tank hit (Heavenly Heel) landed on in the most pulls."""
    return _assigned_tank(report, meta, pack, by_guid, "off_tank")


def main_tank(report: Path, meta: dict, pack: FightPack, by_guid: dict[int, list[dict]]) -> str:
    """The report's main tank: `assignments.main_tank` in session.json, or else the
    tank the main-tank hit (Ascalon's Might) landed on in the most pulls."""
    return _assigned_tank(report, meta, pack, by_guid, "main_tank")


def _assigned_tank(
    report: Path, meta: dict, pack: FightPack, by_guid: dict[int, list[dict]], seat: str,
) -> str:
    sidecar = report / "session.json"
    if sidecar.is_file():
        named = (json.loads(sidecar.read_text(encoding="utf-8")).get("assignments") or {}).get(seat)
        if named:
            return named
    tanks = {actor["id"]: actor["name"] for actor in players(meta) if pack.role_of(actor.get("type") or "") == "tank"}
    pulls: dict[str, set[int]] = defaultdict(set)
    for mechanic in pack.mechanics:
        if not getattr(mechanic, seat):
            continue
        for guid in mechanic.guids:
            for event in by_guid.get(guid, []):
                name = tanks.get(event.get("targetID"))
                if name:
                    pulls[name].add(event.get("fight"))
    if not pulls:
        return ""
    return max(sorted(pulls), key=lambda name: len(pulls[name]))


def _phase_label(meta: dict, fight: dict, timestamp: int | None) -> tuple[int, str]:
    """The log's own phase at this moment: its id and name, such as (1, "P1: Adelphel...")."""
    names = []
    for row in meta.get("phases") or []:
        if row.get("boss") == fight.get("boss"):
            names = row.get("phases") or []
    current = 1
    for phase in sorted(fight.get("phases") or [], key=lambda row: row["startTime"]):
        if timestamp is not None and phase["startTime"] <= timestamp:
            current = phase["id"]
    name = names[current - 1] if 0 < current <= len(names) else f"Phase {current}"
    return current, name


def extract_report(report: Path, pack: FightPack, skipped: list | None = None) -> list[DeathFact]:
    """Every death in the judged phases, as facts. Death rows outside them go to `skipped`, with why."""
    meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
    deaths = {
        item["id"]: item.get("html") or ""
        for item in json.loads((report / "deaths-html.json").read_text(encoding="utf-8"))
    }
    party = {}
    party_path = report / "party.json"
    if party_path.exists():
        party = json.loads(party_path.read_text(encoding="utf-8"))
    names_by_id = {actor["id"]: actor["name"] for actor in meta.get("friendlies") or []}
    by_guid = _load_events(report)
    snapshots = _load_events(report, "calculateddamage")
    mitigation_tables = load_mitigations(report)
    auras = aura_names(report, mitigation_tables)
    fetched = fetched_guids(report)
    assigned_off_tank = off_tank(report, meta, pack, by_guid)
    seats = _seat_partners(pack, snapshots, by_guid, names_by_id)
    assigned_main_tank = main_tank(report, meta, pack, by_guid)
    hit_lists = {**_replay_hits(mitigation_tables, fetched), **by_guid}
    base_hp = max_hp_bases(party, _base_max_hp(by_guid, names_by_id, mitigation_tables, pack.max_hp_buffs))
    marker_casts = _marker_packets(report, pack)
    marker_guids = {guid for mech in pack.mechanics if mech.marker_owns_clip for guid in mech.guids}
    marker_spots = {guid: mech.spots for mech in pack.mechanics if mech.spots for guid in mech.guids}
    positions = _Positions(report)
    places: dict[int, dict] = {}

    facts: list[DeathFact] = []
    listed = {fight["id"] for fight in meta["fights"]}
    for fight_id, html in sorted(deaths.items()):
        if fight_id not in listed:
            _skip_rows(skipped, meta, {"id": fight_id, "start_time": 0}, html, "the pull is not in fights.json")
    for fight in meta["fights"]:
        if pack.zone_id is not None and fight.get("zoneID") != pack.zone_id:
            _skip_rows(skipped, meta, fight, deaths.get(fight["id"], ""), "another encounter")
            continue
        windows = _qualifying_phases(fight, pack)
        html = deaths.get(fight["id"], "")
        if not windows:
            _skip_rows(skipped, meta, fight, html, "the pull never reached a judged phase")
            continue
        debuffs = _cascade_debuffs(mitigation_tables.get(fight["id"]), pack, names_by_id)
        boss_pct = round(fight.get("bossPercentage", 0) / 100, 1)
        timed: list[tuple[int | None, DeathFact]] = []
        for row in ROW_RE.findall(html):
            name_match = NAME_RE.search(row)
            time_match = TIME_RE.search(row)
            if not name_match or not time_match:
                continue
            name = unescape(name_match.group(2)).strip()
            actor = actor_for(meta, name, fight["id"], name_match.group(1)) or {}
            job = actor.get("type") or name_match.group(1)
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
                    _skip_row(skipped, meta, fight, name, when, timestamp, "outside the judged phases")
                    continue
            else:
                window = windows[-1]
            phase, start, _end = window
            target = actor.get("id")
            if not kb_match:
                fact = _fact(
                    fight, phase, start, timestamp, when, name, job, pack, 0, "Environment",
                    0, None, None, None, 0, None, [], boss_pct,
                    _max_hp(base_hp, name, mitigation_tables.get(fight["id"]), target, timestamp, pack),
                    mitigations_for(mitigation_tables, fight["id"], target, None, 0, timestamp),
                )
                fact.prior_debuffs = _prior_debuffs(debuffs, windows, timestamp)
                fact.ts = timestamp
                fact.knocked_by = _knocked_by(pack, snapshots, by_guid, fight["id"], target, timestamp, names_by_id)
                fact.missing = _gaps(report, fight["id"], mitigation_tables, fact, None)
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
            elif event is None:
                # No ability file for this hit: the replay may still have seen its multiplier.
                mult = replay_multiplier(mitigation_tables, fight["id"], target, guid, timestamp)
            source = (event or {}).get("sourceID")
            mits = mitigations_for(
                mitigation_tables, fight["id"], target, source, guid, timestamp,
            )
            fact = _fact(
                fight, phase, start, timestamp, when, name, job, pack, guid, ability,
                total, hp, unmit, mult, int(absorb), stack, buffs, boss_pct,
                _max_hp(base_hp, name, mitigation_tables.get(fight["id"]), target, timestamp, pack), mits,
            )
            fact.cohort = _cohort(
                snapshots.get(guid, []) + by_guid.get(guid, []), fight["id"], event, names_by_id,
            )
            fact.self_hits = _self_hits(by_guid, pack, fight["id"], target, timestamp, fact.role, event)
            clip = _clipped_by(
                marker_casts, fight["id"], target, timestamp, mits, names_by_id,
                direct=guid in marker_guids,
            )
            mechanic = pack.mechanic_for(guid, phase.id)
            if mechanic and mechanic.off_tank:
                fact.off_tank = assigned_off_tank
            if mechanic and mechanic.main_tank:
                fact.main_tank = assigned_main_tank
            if mechanic and mechanic.baited:
                fact.baited_by = _baited_by(
                    mechanic.baited, event, snapshots.get(guid, []), _positions(report, fight["id"], places),
                    fight["id"], target, timestamp, fact.t, names_by_id,
                )
            if mechanic and mechanic.stun:
                fact.stunned_by = _stunned_by(
                    mechanic.stun, mitigation_tables.get(fight["id"]), snapshots, by_guid, positions,
                    fight["id"], target, timestamp, names_by_id,
                )
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
            fact.ts = timestamp
            fact.amp_via, fact.amp_ms = _amp_source(mitigation_tables.get(fight["id"]), target, timestamp)
            fact.missing = _gaps(report, fight["id"], mitigation_tables, fact, by_guid)
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
            timed, pack, hit_lists, fight["id"], _fight_roster(meta, fight["id"]), raises, names_by_id,
            mitigation_tables.get(fight["id"]),
            {actor["name"]: pack.role_of(actor.get("type") or "") for actor in pull_players(meta, fight["id"])},
            fetched, marker_casts, snapshots,
        )
        _extra_hits(
            timed, pack, snapshots, fight["id"], _fight_roster(meta, fight["id"]), raises,
            mitigation_tables.get(fight["id"]), names_by_id,
        )
        _drop_owners(
            timed, pack, fight["id"], positions, mitigation_tables.get(fight["id"]), raises, names_by_id,
        )
        _alternating_groups(
            timed, pack, snapshots, by_guid, fight["id"], _fight_roster(meta, fight["id"]), raises, names_by_id,
            seats,
        )
        _ice_pairs(
            timed, pack, snapshots, fight["id"],
            {actor["name"]: pack.role_of(actor.get("type") or "") for actor in pull_players(meta, fight["id"])},
            raises, mitigation_tables.get(fight["id"]), names_by_id,
        )
    facts.sort(key=lambda fact: (fact.fight, fact.phase, fact.t, fact.name))
    return facts


def _fight_roster(meta: dict, fight_id: int) -> list[str]:
    names: list[str] = []
    for actor in pull_players(meta, fight_id):
        if actor["name"] not in names:
            names.append(actor["name"])
    return names


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
    table: dict | None = None,
    roles: dict[str, str] | None = None,
    fetched: set[int] = frozenset(),
    marker_casts: dict[tuple, list[tuple]] | None = None,
    snapshots: dict[int, list[dict]] | None = None,
) -> None:
    """Who was missing from a mechanic that needs every player, or every holder of a debuff.

    `down` is dead and not raised when the cast landed. With a soak, the cast landed
    at its first soak hit, `unsoaked` is everyone alive who that soak missed, and
    `doubled` are the players who shared one soak, such as two in one tower. A stack
    is shared when it snapshots, so a player in its snapshot took a share even when
    they died before the damage landed.
    """
    for timestamp, fact in timed:
        if timestamp is None:
            continue
        mechanic = pack.mechanic_for(fact.guid, fact.phase)
        needs = next((row for row in (mechanic.needs_everyone if mechanic else []) if row.covers(fact.t)), None)
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
        # The full hit list comes only from an ability file. The replay's proves who was hit, not who was not.
        complete = False
        if needs.soak:
            window = [
                event
                for guid in needs.soak
                for event in by_guid.get(guid, [])
                if event.get("fight") == fight_id
            ]
            # A stack is the killing cast itself: its hits land a few milliseconds apart around the deaths.
            until = first + STACK_SLACK_MS if needs.stack else first
            if needs.stack:
                window += [
                    event
                    for guid in needs.soak
                    for event in (snapshots or {}).get(guid, [])
                    if event.get("fight") == fight_id
                ]
            hits = [event for event in window if at <= event["timestamp"] <= until]
            # This cast's towers came from a fetched file, or no tower file of this set is missing.
            if hits:
                complete = all(not event.get("replay") for event in hits)
            else:
                complete = all(guid in fetched for guid in needs.soak)
            at = min(event["timestamp"] for event in hits) if hits else first - round(needs.lag * 1000)
            soaked = {names_by_id.get(event.get("targetID")) for event in hits}
            if needs.stack:
                hits = []
            shared: dict[tuple, set[str]] = defaultdict(set)
            for event in hits:
                name = names_by_id.get(event.get("targetID"))
                # The replay's hit list has no tower instance, so it cannot show a shared tower.
                if name and event.get("sourceInstance") is not None:
                    shared[(event.get("sourceID"), event.get("sourceInstance"))].add(name)
            fact.doubled = [
                name for name in roster
                if any(name in group and len(group) > 1 for group in shared.values())
            ]
        died: dict[str, int] = {}
        for ts, other in timed:
            if ts is not None and ts < at:
                died[other.name] = max(died.get(other.name, ts), ts)
        needed = roster
        if needs.roles:
            needed = [name for name in needed if (roles or {}).get(name) in needs.roles]
        if needs.holders:
            needed = [name for name in needed if name in _holders(table, needs.holders, at, names_by_id)]
        if needs.marked_out:
            excused = _marker_holders(marker_casts or {}, fight_id, needs.marked_out, at, names_by_id)
            needed = [name for name in needed if name not in excused]
        # Just raised and still invulnerable counts as dead, the same as for the ice pairs.
        risen = _holders(table, [TRANSCENDENT], at, names_by_id) if table else set()
        fact.down = [
            name for name in needed
            if name in died and name not in victims
            and (name in risen or not any(died[name] < raised <= at for raised in raises.get(name, [])))
        ]
        if needs.soak and complete:
            fact.unsoaked = [name for name in needed if name not in soaked and name not in fact.down]
        elif needs.soak:
            gap = "ability " + "/".join(str(guid) for guid in needs.soak)
            if gap not in fact.missing:
                fact.missing.append(gap)


# How long before a stack its markers resolve, such as Skyward Leap just before Dragon's Rage.
MARKED_OUT_MS = 5000
# A stack's hits land on its players a few milliseconds apart, some after the first death.
STACK_SLACK_MS = 1000


def _marker_holders(
    marker_casts: dict[tuple, list[tuple]], fight_id: int, guids: list[int], at: int,
    names_by_id: dict[int, str],
) -> set[str]:
    """The holders of these markers that resolved just before `at`: each cast's first target."""
    found: set[str] = set()
    for (fight, _source), casts in marker_casts.items():
        if fight != fight_id:
            continue
        for first, guid, targets in casts:
            if guid in guids and at - MARKED_OUT_MS <= first <= at and targets:
                name = names_by_id.get(targets[0])
                if name:
                    found.add(name)
    return found


def _holders(table: dict | None, guids: list[int], at: int, names_by_id: dict[int, str]) -> set[str]:
    """Players who held one of these debuffs or buffs at this moment."""
    held: dict[str, bool] = {}
    for aura in sorted((table or {}).get("auras") or [], key=lambda row: row[0]):
        if aura[2] not in guids or aura[0] > at:
            continue
        name = names_by_id.get(aura[5])
        if not name:
            continue
        if aura[1] in ("applydebuff", "applybuff", "refreshbuff", "refreshdebuff"):
            held[name] = True
        elif aura[1] in ("removedebuff", "removebuff"):
            held[name] = False
    return {name for name, holding in held.items() if holding}


def _bearing(origin: tuple, point: tuple) -> float:
    """Compass degrees from one replay point to another: 0 is east, 90 south."""
    return math.degrees(math.atan2(point[1] - origin[1], point[0] - origin[0])) % 360


def _apart(left: float, right: float) -> float:
    return abs((left - right + 180) % 360 - 180)


def _sample(places: dict[int, list], actor: int, timestamp: int, slack_ms: int = 1500) -> tuple | None:
    """Where the actor was at this moment, between the samples either side of it.

    A player is sampled about once a second, so a player on the move is placed on
    the line between the two samples. With a sample on one side only, the nearest one.
    """
    rows = sorted(row for row in places.get(actor) or [] if abs(row[0] - timestamp) <= slack_ms)
    if not rows:
        return None
    before = [row for row in rows if row[0] <= timestamp]
    after = [row for row in rows if row[0] > timestamp]
    if before and after:
        left, right = before[-1], after[0]
        share = (timestamp - left[0]) / (right[0] - left[0])
        return left[1] + (right[1] - left[1]) * share, left[2] + (right[2] - left[2]) * share
    _ts, x, y, _facing = min(rows, key=lambda row: abs(row[0] - timestamp))
    return x, y


def _baited_by(
    baited,
    event: dict | None,
    snapshots: list[dict],
    places: dict[int, list],
    fight_id: int,
    target: int | None,
    timestamp: int | None,
    t: float,
    names_by_id: dict[int, str],
) -> list[str]:
    """Who baited the cone that hit this player from outside the stack.

    At the snapshot each cone faces the player it locked on. Most face the stack and
    one faces the front tank. A cone facing anywhere else was baited by the player
    standing in that direction when the cones locked. When this player died inside
    such a cone and it was not their own, its baiter shares the death.
    """
    if t > baited.until or event is None or target is None or timestamp is None:
        return []
    source = event.get("sourceID")
    rows = [
        row for row in snapshots
        if row.get("fight") == fight_id and row.get("targetID") == target and row.get("sourceID") == source
        and 0 <= timestamp - row["timestamp"] <= 2500
    ]
    snap = max((row["timestamp"] for row in rows), default=event["timestamp"])
    boss = [row for row in places.get(source) or [] if abs(row[0] - snap) <= 100 and row[3] is not None]
    if len(boss) < 3:
        return []
    origin = (boss[0][1], boss[0][2])
    facings = [math.degrees(row[3] / 100) % 360 for row in boss]
    stack = max(facings, key=lambda facing: sum(_apart(facing, other) <= 15 for other in facings))
    front = (stack + 180) % 360
    stray = sorted({round(facing, 1) for facing in facings if _apart(facing, stack) > 20 and _apart(facing, front) > 30})
    here = _sample(places, target, snap)
    if not stray or here is None:
        return []
    lock = snap - round(baited.lock * 1000)
    bearings = {}
    for actor, name in names_by_id.items():
        there = _sample(places, actor, lock)
        if there is not None:
            bearings[name] = _bearing(origin, there)
    owners: list[str] = []
    for facing in stray:
        if _apart(_bearing(origin, here), facing) > baited.width:
            continue
        aimed = sorted((_apart(bearing, facing), name) for name, bearing in bearings.items())
        if not aimed or aimed[0][0] > baited.aim:
            continue
        baiter = aimed[0][1]
        if baiter != names_by_id.get(target) and baiter not in owners:
            owners.append(baiter)
    return owners


# A deathwall death's time is only good to about a second, so a knockback is matched this far back.
KNOCKED_MS = 2500


def _knocked_by(
    pack: FightPack,
    snapshots: dict[int, list[dict]],
    by_guid: dict[int, list[dict]],
    fight_id: int,
    target: int | None,
    timestamp: int | None,
    names_by_id: dict[int, str],
) -> list[str]:
    """Whose landing knocked this player into the deathwall.

    A knockback landing hit them just before they died at the edge, and it was
    not their own: someone else was first in its hit list.
    """
    if target is None or timestamp is None:
        return []
    owners: list[str] = []
    for mechanic in pack.mechanics:
        if not mechanic.knockback:
            continue
        for guid in mechanic.guids:
            events = [*snapshots.get(guid, []), *by_guid.get(guid, [])]
            packets: dict[int, list[dict]] = defaultdict(list)
            for event in events:
                if event.get("fight") == fight_id and event.get("packetID") is not None:
                    packets[event["packetID"]].append(event)
            for rows in packets.values():
                rows.sort(key=lambda row: row["timestamp"])
                hit = [row for row in rows if row.get("targetID") == target]
                if not hit or not -KNOCKED_MS <= hit[0]["timestamp"] - timestamp <= 1000:
                    continue
                holder = names_by_id.get(rows[0].get("targetID"))
                if holder and rows[0].get("targetID") != target and holder not in owners:
                    owners.append(holder)
    return owners


def _stunned_by(
    stun,
    table: dict | None,
    snapshots: dict[int, list[dict]],
    by_guid: dict[int, list[dict]],
    positions: _Positions,
    fight_id: int,
    target: int | None,
    timestamp: int | None,
    names_by_id: dict[int, str],
) -> list[str]:
    """Who drew the hit that stunned this player, when it was aimed at someone else.

    The stun is still on them at the death. The players hit by `stun.casts` just
    before it are who drew it. With more than one, the one standing nearest the
    stunned player when it landed. Empty when the player drew it themselves, or
    when positions cannot tell who it was.
    """
    if target is None or timestamp is None or not table:
        return []
    applied = None
    for aura in sorted(table.get("auras") or [], key=lambda row: row[0]):
        if aura[2] != stun.debuff or aura[5] != target or aura[0] > timestamp:
            continue
        if aura[1] in ("applydebuff", "refreshdebuff"):
            applied = aura[0]
        elif aura[1] == "removedebuff" and aura[0] < timestamp - 500:
            applied = None
    if applied is None:
        return []
    drew: set[int] = set()
    for guid in stun.casts:
        for event in [*snapshots.get(guid, []), *by_guid.get(guid, [])]:
            if event.get("fight") != fight_id or event.get("targetID") not in names_by_id:
                continue
            if applied - stun.within * 1000 <= event["timestamp"] <= applied + 500:
                drew.add(event["targetID"])
    if not drew or target in drew:
        return []
    if len(drew) == 1:
        return [names_by_id[next(iter(drew))]]
    here = positions.at(fight_id, target, applied, 1500)
    if here is None:
        return []
    near = []
    for actor in drew:
        there = positions.at(fight_id, actor, applied, 1500)
        if there is not None:
            near.append((math.dist(here, there), names_by_id[actor]))
    return [min(near)[1]] if near else []


def _casts(events: list[dict], fight_id: int, names_by_id: dict[int, str]) -> list[tuple[int, list[str]]]:
    """Each cast of one ability in a pull, as its first hit and its targets, in order.

    A cast is one packet. The snapshot rows keep a target who died before the hit landed.
    """
    packets: dict[int, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("fight") == fight_id and event.get("packetID") is not None:
            packets[event["packetID"]].append(event)
    casts = []
    for rows in packets.values():
        rows.sort(key=lambda row: row["timestamp"])
        targets: list[str] = []
        for row in rows:
            name = names_by_id.get(row.get("targetID"))
            if name and name not in targets:
                targets.append(name)
        if targets:
            casts.append((rows[0]["timestamp"], targets))
    return sorted(casts)


@dataclass
class _Seats:
    """Each player's opposite number in a cast that alternates between two groups, and how
    often each two players shared a full cast over the report."""

    partners: dict[str, str]
    together: Counter
    # One of the two groups the players most often stack in.
    usual: frozenset[str] = frozenset()


def _seat_partners(
    pack: FightPack,
    snapshots: dict[int, list[dict]],
    by_guid: dict[int, list[dict]],
    names_by_id: dict[int, str],
) -> _Seats | None:
    """For a cast that alternates between two groups, each player's opposite number.

    Each group has one player of each seat, such as one tank, one healer, one melee,
    and one ranged, and a swap trades a player for their opposite number. So the two
    players of one seat are almost never in the same full cast. The seats are the
    pairing of the report's players that shares the fewest full casts. None when
    there are too few full casts, or two pairings fit as well.
    """
    together: Counter = Counter()
    players: set[str] = set()
    groups: Counter = Counter()
    full = 0
    for mechanic in pack.mechanics:
        if not mechanic.alternating or not mechanic.typical_targets:
            continue
        events = [event for guid in mechanic.guids for event in snapshots.get(guid, [])]
        events = events or [event for guid in mechanic.guids for event in by_guid.get(guid, [])]
        packets: dict[tuple, set[str]] = defaultdict(set)
        for event in events:
            name = names_by_id.get(event.get("targetID"))
            if name and event.get("packetID") is not None:
                packets[(event.get("fight"), event["packetID"])].add(name)
        for names in packets.values():
            if len(names) != mechanic.typical_targets:
                continue
            full += 1
            players |= names
            groups[frozenset(names)] += 1
            for left in names:
                for right in names:
                    if left != right:
                        together[(left, right)] += 1
    if full < 4 or len(players) % 2 or len(players) > 12:
        return None
    costs = sorted(
        (sum(together[pair] for pair in pairing), pairing)
        for pairing in _pairings(sorted(players))
    )
    if len(costs) > 1 and costs[0][0] == costs[1][0]:
        return None
    partners = {}
    for left, right in costs[0][1]:
        partners[left], partners[right] = right, left
    return _Seats(partners, together, groups.most_common(1)[0][0])


def _pairings(players: list[str]):
    """Every way to split these players into pairs."""
    if not players:
        yield []
        return
    first, rest = players[0], players[1:]
    for at, other in enumerate(rest):
        for pairing in _pairings(rest[:at] + rest[at + 1:]):
            yield [(first, other), *pairing]


def _cast_group(casts: list[tuple[int, list[str]]], index: int, roster: list[str]) -> list[str] | None:
    """Whoever took the cast two before this one, or for the first two casts, everyone
    the other group's cast did not hit."""
    if index >= 2:
        return list(casts[index - 2][1])
    if index + 2 < len(casts) and index == 0:
        return list(casts[index + 2][1])
    other = casts[index - 1][1] if index else (casts[index + 1][1] if index + 1 < len(casts) else None)
    if other is None:
        return None
    return [name for name in roster if name not in other]


def _seat_group(
    group: list[str], other: list[str], casts: list[tuple[int, list[str]]], index: int,
    seats: _Seats, roster: list[str], size: int,
) -> list[str]:
    """This cast's group from the hit lists, with each seat it has nobody in filled,
    while it has fewer than `size` players.

    A cast that hit three of its group says nothing of the fourth. The fourth is the
    player of the empty seat who is not in the other group. When both or neither
    are, the one a cast of the other group landed on first (its target) stays there,
    and otherwise the one whose usual group this is.
    """
    if any(seats.partners.get(name) not in roster for name in roster):
        return group
    targets_mine = {targets[0] for at, (_first, targets) in enumerate(casts) if at % 2 == index % 2}
    targets_theirs = {targets[0] for at, (_first, targets) in enumerate(casts) if at % 2 != index % 2}
    filled = list(group)
    for name in roster:
        partner = seats.partners[name]
        if len(filled) >= size:
            break
        if name > partner or name in group or partner in group:
            continue
        if (partner in other) != (name in other):
            filled.append(partner if name in other else name)
        elif (name in targets_theirs) != (partner in targets_theirs):
            filled.append(partner if name in targets_theirs else name)
        elif (name in targets_mine) != (partner in targets_mine):
            filled.append(name if name in targets_mine else partner)
        else:
            usual = seats.usual
            mine = sum(member in usual for member in group) - sum(member not in usual for member in group)
            if mine and (name in usual) != (partner in usual):
                filled.append(name if (name in usual) == (mine > 0) else partner)
            else:
                here = sum(seats.together[(name, member)] for member in group)
                there = sum(seats.together[(partner, member)] for member in group)
                filled.append(name if here >= there else partner)
    return [name for name in roster if name in filled]


def _alternating_groups(
    timed: list[tuple[int | None, DeathFact]],
    pack: FightPack,
    snapshots: dict[int, list[dict]],
    by_guid: dict[int, list[dict]],
    fight_id: int,
    roster: list[str],
    raises: dict[str, list[int]],
    names_by_id: dict[int, str],
    seats: _Seats | None = None,
) -> None:
    """Who should have taken a cast that alternates between two groups, and who was missing.

    The same players take every other cast, so the group for a cast is whoever took
    the one two casts earlier. The first two casts, with nothing that early, take
    everyone the other group's cast did not hit. With each player's opposite number
    known (`_seat_partners`), a seat that group has nobody in is filled
    (`_seat_group`). `group` is that group. `down` are its players already dead, and
    `unsoaked` are the ones alive and not in this cast.
    """
    for timestamp, fact in timed:
        mechanic = pack.mechanic_for(fact.guid, fact.phase)
        if timestamp is None or mechanic is None or not mechanic.alternating:
            continue
        events = [event for guid in mechanic.guids for event in snapshots.get(guid, [])]
        events = events or [event for guid in mechanic.guids for event in by_guid.get(guid, [])]
        casts = _casts(events, fight_id, names_by_id)
        landed = [index for index, (first, _targets) in enumerate(casts) if 0 <= timestamp - first <= 2500]
        if not landed:
            continue
        index = landed[-1]
        targets = casts[index][1]
        group = _cast_group(casts, index, roster)
        if group is None:
            continue
        if seats:
            beside = index + 1 if index % 2 == 0 and index + 1 < len(casts) else index - 1
            other = _cast_group(casts, beside, roster) if beside >= 0 else None
            group = _seat_group(group, other or [], casts, index, seats, roster, mechanic.typical_targets or 0)
        fact.group = group
        fact.down = [
            name for name in group
            if name not in targets and _still_dead(name, timed, timestamp, raises)
        ]
        fact.unsoaked = [
            name for name in group
            if name not in targets and name not in fact.down
        ]


TRANSCENDENT = 1000418
SUPPORT = {"tank", "healer"}


def _ice_pairs(
    timed: list[tuple[int | None, DeathFact]],
    pack: FightPack,
    snapshots: dict[int, list[dict]],
    fight_id: int,
    roles: dict[str, str],
    raises: dict[str, list[int]],
    table: dict | None,
    names_by_id: dict[int, str],
) -> None:
    """Who should have shared a pair circle with a player who was alone in it, or
    who left a pair with two circles on it.

    Each circle is one support and one DPS. A circle is one caster instance in the
    snapshot. For a player alone in one circle, the partner was a player of the
    other group who was dead (or raised and still Transcendent), alive and in no
    circle, or the extra body in a circle of three. `group` is the circle,
    `down`, `unsoaked`, and `doubled` are those partners.

    A dead holder's ice goes to a living player, so with someone dead a pair can
    take two circles. That surplus ice belongs to everyone missing from the
    circles: `group` is both circles, `down` the dead, `unsoaked` the living in none.
    """
    for timestamp, fact in timed:
        mechanic = pack.mechanic_for(fact.guid, fact.phase)
        if timestamp is None or mechanic is None or not mechanic.pairs:
            continue
        rows = [
            event for guid in mechanic.guids for event in snapshots.get(guid, [])
            if event.get("fight") == fight_id and abs(event["timestamp"] - timestamp) <= 2500
        ]
        if not rows:
            continue
        snap = min(event["timestamp"] for event in rows)
        circles: dict[tuple, list[str]] = defaultdict(list)
        for event in rows:
            name = names_by_id.get(event.get("targetID"))
            if name and name not in circles[(event.get("sourceID"), event.get("sourceInstance"))]:
                circles[(event.get("sourceID"), event.get("sourceInstance"))].append(name)
        mine = [members for members in circles.values() if fact.name in members]
        anywhere = {name for members in circles.values() for name in members}
        resting = _holders(table, [TRANSCENDENT], snap, names_by_id)
        if len(mine) >= 2:
            down = [
                name for name in roles
                if name not in anywhere and (_still_dead(name, timed, snap, raises) or name in resting)
            ]
            if down:
                fact.group = sorted({name for members in mine for name in members})
                fact.down = down
                fact.unsoaked = [name for name in roles if name not in anywhere and name not in down]
            continue
        if len(mine) != 1 or len(mine[0]) != 1:
            continue
        fact.group = [fact.name]
        side = roles.get(fact.name) in SUPPORT
        partners = [name for name, role in roles.items() if (role in SUPPORT) != side]
        fact.down = [
            name for name in partners
            if name not in anywhere and (_still_dead(name, timed, snap, raises) or name in resting)
        ]
        fact.unsoaked = [name for name in partners if name not in anywhere and name not in fact.down]
        fact.doubled = [
            name for name in partners
            if any(name in members and len(members) >= 3 for members in circles.values())
        ]


def _extra_hits(
    timed: list[tuple[int | None, DeathFact]],
    pack: FightPack,
    snapshots: dict[int, list[dict]],
    fight_id: int,
    roster: list[str],
    raises: dict[str, list[int]],
    table: dict | None,
    names_by_id: dict[int, str],
) -> None:
    """A hit that comes once for each player, which killed a player who took two.

    Neither of their hits fell on anyone else, so nobody clipped them: a dead
    player's hit went to them. `down` is who was dead (or raised and still
    Transcendent) at the cast.
    """
    for timestamp, fact in timed:
        mechanic = pack.mechanic_for(fact.guid, fact.phase)
        if timestamp is None or mechanic is None or not mechanic.one_each or len(fact.cohort) > 1:
            continue
        rows = [
            event for guid in mechanic.guids for event in snapshots.get(guid, [])
            if event.get("fight") == fight_id and abs(event["timestamp"] - timestamp) <= 2500
        ]
        if not rows:
            continue
        snap = min(event["timestamp"] for event in rows)
        hits: dict[tuple, set[str]] = defaultdict(set)
        for event in rows:
            name = names_by_id.get(event.get("targetID"))
            if name:
                hits[(event.get("sourceID"), event.get("sourceInstance"))].add(name)
        mine = [names for names in hits.values() if fact.name in names]
        if len(mine) < 2 or any(len(names) > 1 for names in mine):
            continue
        anywhere = {name for names in hits.values() for name in names}
        resting = _holders(table, [TRANSCENDENT], snap, names_by_id)
        fact.down = [
            name for name in roster
            if name not in anywhere and (_still_dead(name, timed, snap, raises) or name in resting)
        ]


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
    total, hp, unmit, mult, absorb, stack, buffs, boss_pct, max_hp, mitigations,
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
        max_hp=max_hp,
        unmitigated=int(unmit) if unmit is not None else None,
        multiplier=mult,
        absorb=absorb,
        stack=stack,
        buffs=buffs,
        boss_pct=boss_pct,
        pull_ms=fight["end_time"] - start,
        mitigations=mitigations,
    )


def _max_hp(
    base: dict[str, int], name: str, table: dict | None, target: int | None, timestamp: int | None, pack: FightPack,
) -> int | None:
    """Their max HP at this moment: the base, raised by any max-HP buff that was on."""
    if name not in base:
        return None
    return round(base[name] * _buff_factor(table, target, timestamp, pack.max_hp_buffs))


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
