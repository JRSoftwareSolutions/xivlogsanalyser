"""Still frames of where people stood for a mechanic.

Coordinates are yalms relative to the arena center. Positive x is east and
positive y is south, matching the replay. Facing is a unit vector in that
same space: the stored value is hundredths of a radian, and at the start of
a pull the party stands south of Thordan with facing -158, which points north.

A failed death keeps a picture of that hit. A mechanic the party failed also
gets a picture at the cast. A clear mechanic does not. The cast time comes
from the damage events, and from deaths when a pull has no event of its own.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from xivloganalyzer.catalog import FightPack
from xivloganalyzer.dashboard import JOB
from xivloganalyzer.extract import _load_events, _qualifying_phases

CENTER = 100.0
ARENA = 20.0
SKIP_TYPES = {"Pet", "NPC", "Boss", "LimitBreak"}
TOWER_NAMES = {"King Thordan", "Holy Comet", "Brightsphere", "Haurchefant", "Spear of the Fury"}


@dataclass
class Sample:
    t: float
    ts: int
    actor: int | None
    x: float
    y: float
    face: tuple[float, float] | None
    name: str
    kind: str
    friendly: bool


@dataclass
class FightReplay:
    p2: int
    phase_starts: dict[int, int] = field(default_factory=dict)
    samples: list[Sample] = field(default_factory=list)
    by_actor: dict[int, list[Sample]] = field(default_factory=dict)
    players: dict[str, int] = field(default_factory=dict)
    hysteria: list[tuple[str, float, float]] = field(default_factory=list)
    prey: list[tuple[str, float, float]] = field(default_factory=list)


def _replay_seconds(replay: FightReplay, phase_id: int, when: float) -> float:
    """Phase seconds to the replay clock, which starts at phase 2."""
    start = replay.phase_starts.get(phase_id)
    if start is None:
        return when
    return when + (start - replay.p2) / 1000.0


def _clock_label(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 60}:{total % 60:02d}"


def _bursts(times: list[float], gap: float = 2.5) -> list[float]:
    """First timestamp of each cluster of hits."""
    groups: list[list[float]] = []
    for when in sorted(times):
        if not groups or when - groups[-1][-1] > gap:
            groups.append([when])
        else:
            groups[-1].append(when)
    return [group[0] for group in groups]


def _waves(burst_starts: list[float], gap: float = 8.0, limit: int = 4) -> list[float]:
    """Keep casts that are far enough apart to be a different picture."""
    kept: list[float] = []
    for when in burst_starts:
        if kept and when - kept[-1] < gap:
            continue
        kept.append(when)
        if len(kept) >= limit:
            break
    return kept


def facing_vector(raw: int | None) -> tuple[float, float] | None:
    """Unit vector for a replay facing. +x east, +y south."""
    if raw is None:
        return None
    theta = raw / 100.0
    return (math.cos(theta), math.sin(theta))


def _rel(x: float, y: float) -> tuple[float, float]:
    return (round(x - CENTER, 2), round(y - CENTER, 2))


def _radius(x: float, y: float) -> float:
    return math.hypot(x - CENTER, y - CENTER)


def _dedupe(samples: list[Sample], gap: float = 1.5) -> list[Sample]:
    chosen: list[Sample] = []
    for sample in samples:
        if any(math.hypot(sample.x - kept.x, sample.y - kept.y) < gap for kept in chosen):
            continue
        chosen.append(sample)
    return chosen


def _active(intervals: list[tuple[str, float, float]], name: str, t: float) -> bool:
    for owner, start, end in intervals:
        if owner == name and start - 0.4 <= t <= end + 0.4:
            return True
    return False


def _intervals(auras: list, actors: dict, p2: int, debuff: str) -> list[tuple[str, float, float]]:
    pending: dict[str, list[float]] = {}
    ranges: list[tuple[str, float, float]] = []
    for row in auras:
        if row[3] != debuff:
            continue
        name = (actors.get(str(row[5])) or {}).get("name")
        if not name:
            continue
        when = (row[0] - p2) / 1000
        if row[1] == "applydebuff":
            pending.setdefault(name, []).append(when)
        elif row[1] == "removedebuff" and pending.get(name):
            ranges.append((name, pending[name].pop(0), when))
    for name, starts in pending.items():
        for start in starts:
            ranges.append((name, start, start + 15))
    return ranges


class FrameBook:
    """Replay snapshots for one dropped report. Fights load the first time they are asked for."""

    def __init__(self, report: Path):
        self.report = report
        meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
        self.fights = {fight["id"]: fight for fight in meta["fights"]}
        self._loaded: dict[int, FightReplay | None] = {}

    def frame(self, death: dict, pack: FightPack) -> dict | None:
        if death.get("outcome") != "fail":
            return None
        replay = self._replay(int(death["fight"]))
        if replay is None:
            return None
        mechanic_id = death.get("componentId") or death.get("mechanic_id")
        mechanic = next((item for item in pack.mechanics if item.id == mechanic_id), None)
        category = mechanic.category if mechanic else ""
        phase_id = int(death.get("phaseId") or death.get("phase") or 2)
        if phase_id != 2 and phase_id not in replay.phase_starts:
            return None
        when = _replay_seconds(replay, phase_id, float(death["t"]))
        victim = death["name"]
        gaze_death = category == "gaze" or mechanic_id in {"dragons-gaze", "dragons-glory"}
        hysteria_names = {
            name for name, start, end in replay.hysteria if start - 0.4 <= when <= end + 0.4
        }
        if gaze_death:
            hysteria_names.add(victim)
        show_gaze = gaze_death or victim in hysteria_names

        players = self._players(
            replay, when, victim, hysteria_names, replay.prey, mechanic_id == "holy-impact",
        )
        if not players:
            return None
        victim_row = next((row for row in players if row["name"] == victim), None)
        if victim_row is None:
            return None

        marks: list[dict] = []
        if show_gaze:
            gaze_at = when
            applied = [
                start for name, start, end in replay.hysteria
                if name == victim and start - 0.4 <= when <= end + 0.4
            ]
            if applied and when - applied[0] > 1.5:
                gaze_at = applied[0]
            for sample in self._burst(
                replay, _is_gaze, gaze_at, back=2.0, forward=1.5, min_count=1, prefer_pair=True,
            ):
                x, y = _rel(sample.x, sample.y)
                marks.append({"kind": "gaze", "x": x, "y": y, "name": "Gaze"})

        show_towers = category == "tower" or (
            mechanic_id == "eternal-conviction" and when >= 100
        ) or "tower was empty" in (death.get("wrong") or "").lower()
        if show_towers:
            for sample in self._burst(
                replay, _is_tower, when, back=4.0, forward=1.0, min_count=5,
            ):
                x, y = _rel(sample.x, sample.y)
                marks.append({"kind": "tower", "x": x, "y": y, "name": "Tower"})

        if mechanic_id == "holy-impact":
            for sample in self._burst(
                replay, _is_comet, when, back=2.5, forward=1.0, min_count=1,
            ):
                x, y = _rel(sample.x, sample.y)
                marks.append({"kind": "comet", "x": x, "y": y, "name": "Comet"})

        if mechanic_id == "bright-flare":
            for sample in self._burst(
                replay, _is_orb, when, back=2.0, forward=1.0, min_count=1,
            ):
                x, y = _rel(sample.x, sample.y)
                marks.append({"kind": "orb", "x": x, "y": y, "name": "Orb"})

        boss = self._boss(replay, when)
        gaze_drawn = any(mark["kind"] == "gaze" for mark in marks)
        if boss is not None and not gaze_drawn:
            x, y = _rel(boss.x, boss.y)
            face = [round(boss.face[0], 3), round(boss.face[1], 3)] if boss.face else None
            marks.append({"kind": "boss", "x": x, "y": y, "face": face, "name": "Thordan"})
            if mechanic_id == "ascalons-mercy-concealed":
                marks.append({
                    "kind": "hit",
                    "x": x,
                    "y": y,
                    "x2": victim_row["x"],
                    "y2": victim_row["y"],
                    "name": death.get("cast") or "Cone",
                })

        killed = death.get("cast") or (mechanic.name if mechanic else death.get("ability") or "the hit")
        carried = victim in hysteria_names and not gaze_death
        return {
            "killedBy": killed,
            "caption": _caption(victim, killed, marks, players, carried),
            "players": players,
            "marks": marks,
        }

    def mechanic_frame(
        self,
        fight_id: int,
        phase_id: int,
        when: float,
        mechanic_id: str,
        name: str,
        failed: list[str],
        pack: FightPack,
    ) -> dict | None:
        """Where the party stood when this mechanic resolved. No death required."""
        replay = self._replay(int(fight_id))
        if replay is None:
            return None
        phase_id = int(phase_id)
        if phase_id != 2 and phase_id not in replay.phase_starts:
            return None
        replay_when = _replay_seconds(replay, phase_id, float(when))
        mechanic = next((item for item in pack.mechanics if item.id == mechanic_id), None)
        category = mechanic.category if mechanic else ""
        gaze = category == "gaze" or mechanic_id in {"dragons-gaze", "dragons-glory"}
        hysteria_names = {
            owner for owner, start, end in replay.hysteria
            if start - 0.4 <= replay_when <= end + 0.4
        }
        players = self._players(
            replay,
            replay_when,
            None,
            hysteria_names,
            replay.prey,
            mechanic_id == "holy-impact",
            set(replay.players) if gaze else None,
        )
        if not players:
            return None
        failed_names = [person for person in failed if any(row["name"] == person for row in players)]
        for row in players:
            if row["name"] in failed_names:
                row["failed"] = True

        marks: list[dict] = []
        if gaze:
            for sample in self._burst(
                replay, _is_gaze, replay_when, back=2.0, forward=1.5, min_count=1, prefer_pair=True,
            ):
                x, y = _rel(sample.x, sample.y)
                marks.append({"kind": "gaze", "x": x, "y": y, "name": "Gaze"})

        show_towers = category == "tower" or (
            mechanic_id == "eternal-conviction" and float(when) >= 100
        )
        if show_towers:
            for sample in self._burst(
                replay, _is_tower, replay_when, back=4.0, forward=1.0, min_count=5,
            ):
                x, y = _rel(sample.x, sample.y)
                marks.append({"kind": "tower", "x": x, "y": y, "name": "Tower"})

        if mechanic_id == "holy-impact":
            for sample in self._burst(
                replay, _is_comet, replay_when, back=2.5, forward=1.0, min_count=1,
            ):
                x, y = _rel(sample.x, sample.y)
                marks.append({"kind": "comet", "x": x, "y": y, "name": "Comet"})

        if mechanic_id == "bright-flare":
            for sample in self._burst(
                replay, _is_orb, replay_when, back=2.0, forward=1.0, min_count=1,
            ):
                x, y = _rel(sample.x, sample.y)
                marks.append({"kind": "orb", "x": x, "y": y, "name": "Orb"})

        boss = self._boss(replay, replay_when)
        if boss is None and phase_id != 2:
            boss = self._boss(replay, replay_when, "Nidhogg")
        gaze_drawn = any(mark["kind"] == "gaze" for mark in marks)
        if boss is not None and not gaze_drawn:
            x, y = _rel(boss.x, boss.y)
            face = [round(boss.face[0], 3), round(boss.face[1], 3)] if boss.face else None
            label = "Thordan" if boss.name == "King Thordan" else boss.name
            marks.append({"kind": "boss", "x": x, "y": y, "face": face, "name": label})
            if mechanic_id == "ascalons-mercy-concealed":
                for row in players:
                    if not row.get("failed"):
                        continue
                    marks.append({
                        "kind": "hit",
                        "x": x,
                        "y": y,
                        "x2": row["x"],
                        "y2": row["y"],
                        "name": name,
                    })

        return {
            "title": f"{name} · {_clock_label(when)}",
            "caption": _mechanic_caption(name, failed_names, marks, players, gaze),
            "players": players,
            "marks": marks,
        }

    def phase_length(self, fight_id: int, phase_id: int) -> float | None:
        """Seconds from the start of that phase to the end of the pull."""
        fight = self.fights.get(int(fight_id))
        if not fight:
            return None
        for phase in fight.get("phases") or []:
            if phase.get("id") == int(phase_id) and phase.get("startTime") is not None:
                return (int(fight["end_time"]) - int(phase["startTime"])) / 1000
        return None

    def _replay(self, fight_id: int) -> FightReplay | None:
        if fight_id in self._loaded:
            return self._loaded[fight_id]
        fight = self.fights.get(fight_id)
        path = self.report / "positions" / f"fight-{fight_id:02d}.json"
        p2 = None
        if fight:
            for phase in fight.get("phases") or []:
                if phase.get("id") == 2:
                    p2 = phase.get("startTime")
        if p2 is None or not path.is_file():
            self._loaded[fight_id] = None
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        actors = payload.get("actors") or {}
        phase_starts = {}
        for phase in (fight or {}).get("phases") or []:
            if phase.get("id") is None or phase.get("startTime") is None:
                continue
            phase_starts[int(phase["id"])] = int(phase["startTime"])
        replay = FightReplay(p2=int(p2), phase_starts=phase_starts)
        counted: dict[tuple[str, int], int] = {}
        for row in payload.get("samples") or []:
            ts, actor, x, y, facing, _friendly = row
            info = actors.get(str(actor), {}) if actor is not None else {}
            name = info.get("name") or ""
            kind = info.get("type") or ""
            friendly = bool(info.get("friendly"))
            sample = Sample(
                t=(ts - p2) / 1000,
                ts=int(ts),
                actor=actor,
                x=x / 100,
                y=y / 100,
                face=facing_vector(facing),
                name=name,
                kind=kind,
                friendly=friendly,
            )
            replay.samples.append(sample)
            if actor is not None:
                replay.by_actor.setdefault(actor, []).append(sample)
            if friendly and kind not in SKIP_TYPES and name and actor is not None:
                key = (name, actor)
                counted[key] = counted.get(key, 0) + 1
        best: dict[str, tuple[int, int]] = {}
        for (name, actor), count in counted.items():
            if name not in best or count > best[name][0]:
                best[name] = (count, actor)
        replay.players = {name: actor for name, (_count, actor) in best.items()}
        mit_path = self.report / "mitigations" / f"fight-{fight_id:02d}.json"
        if mit_path.is_file():
            mit = json.loads(mit_path.read_text(encoding="utf-8"))
            mit_actors = mit.get("actors") or {}
            auras = mit.get("auras") or []
            replay.hysteria = _intervals(auras, mit_actors, int(p2), "Hysteria")
            replay.prey = _intervals(auras, mit_actors, int(p2), "Prey")
        self._loaded[fight_id] = replay
        return replay

    def _players(self, replay, when, victim, hysteria, prey, tag_prey, faces=None) -> list[dict]:
        rows = []
        for name, actor in sorted(replay.players.items()):
            samples = replay.by_actor.get(actor) or []
            sample = _nearest(samples, when)
            if sample is None:
                continue
            x, y = _rel(sample.x, sample.y)
            looked = name in hysteria
            row = {
                "name": name,
                "job": JOB.get(sample.kind, sample.kind),
                "x": x,
                "y": y,
                "dead": name == victim,
                "hysteria": looked,
                "prey": tag_prey and _active(prey, name, when),
                "stale": _mid_move(samples, when, sample),
            }
            if (looked or (faces and name in faces)) and sample.face:
                row["face"] = [round(sample.face[0], 3), round(sample.face[1], 3)]
            rows.append(row)
        rows.sort(key=lambda row: (not row["dead"], row["name"]))
        return rows

    def _boss(self, replay: FightReplay, when: float, name: str = "King Thordan") -> Sample | None:
        best = None
        best_age = None
        for samples in replay.by_actor.values():
            if not samples or samples[0].name != name or samples[0].kind != "Boss":
                continue
            sample = _nearest(samples, when)
            if sample is None:
                continue
            age = abs(sample.t - when)
            if best_age is None or age < best_age:
                best = sample
                best_age = age
        if best is None or best_age is None or best_age > 2 or _radius(best.x, best.y) > 30:
            return None
        return best

    def _burst(self, replay, predicate, center, back, forward, min_count, prefer_pair=False):
        buckets: dict[tuple, list[Sample]] = {}
        for sample in replay.samples:
            if sample.t < center - back or sample.t > center + forward:
                continue
            if not predicate(sample):
                continue
            buckets.setdefault((sample.actor, sample.ts), []).append(sample)
        best = None
        best_rank = None
        for (_actor, ts), group in buckets.items():
            uniq = _dedupe(group)
            if len(uniq) < min_count:
                continue
            when = (ts - replay.p2) / 1000
            pair = 0 if len(uniq) >= 2 else 1
            rank = (pair, abs(when - center), -len(uniq)) if prefer_pair else (abs(when - center), -len(uniq))
            if best_rank is None or rank < best_rank:
                best_rank = rank
                best = uniq
        return best or []


def _mid_move(samples: list[Sample], when: float, nearest: Sample) -> bool:
    """A dot is stale only when the player was moving and the replay skipped the hit.

    A long gap with no other position means they were standing still. That spot is still good.
    """
    if abs(nearest.t - when) <= 0.8:
        return False
    before = None
    after = None
    for sample in samples:
        if sample.t <= when and (before is None or sample.t > before.t):
            before = sample
        if sample.t >= when and (after is None or sample.t < after.t):
            after = sample
    if before is None or after is None or before is after:
        return False
    if abs(after.t - before.t) > 3:
        return False
    return math.hypot(after.x - before.x, after.y - before.y) > 4


def _nearest(samples: list[Sample], when: float) -> Sample | None:
    best = None
    best_age = None
    for sample in samples:
        age = abs(sample.t - when)
        if best_age is None or age < best_age:
            best = sample
            best_age = age
    return best


def _is_gaze(sample: Sample) -> bool:
    return sample.name == "King Thordan" and _radius(sample.x, sample.y) >= 18


def _is_tower(sample: Sample) -> bool:
    if sample.friendly or sample.kind == "Pet" or sample.name in TOWER_NAMES:
        return False
    radius = _radius(sample.x, sample.y)
    return 5 <= radius <= 19


def _is_comet(sample: Sample) -> bool:
    return sample.name == "Holy Comet"


def _is_orb(sample: Sample) -> bool:
    return sample.name == "Brightsphere"


def _mark_sentences(marks: list[dict], players: list[dict], carried: bool, arrows_are_hysteria: bool = True) -> list[str]:
    kinds = {mark["kind"] for mark in marks}
    sentences = []
    if carried:
        sentences.append("Hysteria from the gazes was still on them.")
    arrows = [row for row in players if row.get("face")]
    if arrows:
        if len(arrows) == 1:
            sentences.append("The arrow is the way they were facing.")
        elif arrows_are_hysteria:
            sentences.append("Arrows are the way the players with Hysteria were facing.")
        else:
            sentences.append("Arrows are the way they were facing.")
    gazes = sum(mark["kind"] == "gaze" for mark in marks)
    if gazes >= 2:
        sentences.append("The two marks outside the floor are the enemies casting the gazes.")
    elif gazes == 1:
        sentences.append("One gaze enemy was in the replay.")
    if "tower" in kinds:
        sentences.append("The squares are the towers.")
    if "comet" in kinds:
        sentences.append("The rings are the comets.")
    if any(row.get("prey") for row in players):
        sentences.append("Prey is tagged on the players who had it.")
    if "orb" in kinds:
        sentences.append("The circles are the orbs.")
    hits = sum(mark["kind"] == "hit" for mark in marks)
    if hits == 1:
        sentences.append("The line runs from Thordan to the player the cone hit.")
    elif hits > 1:
        sentences.append("Lines run from Thordan to the players the cone hit.")
    return sentences


def _caption(victim: str, killed: str, marks: list[dict], players: list[dict], carried: bool) -> str:
    opening = f"{victim} was killed by {killed}."
    return " ".join([opening, *_mark_sentences(marks, players, carried)])


def _mechanic_caption(name: str, failed: list[str], marks: list[dict], players: list[dict], gaze: bool) -> str:
    if failed:
        opening = f"{', '.join(failed)} failed {name}."
    else:
        opening = f"{name}."
    carried = any(row.get("hysteria") for row in players) and not gaze
    return " ".join([opening, *_mark_sentences(marks, players, carried, arrows_are_hysteria=not gaze)])


class CastClock:
    """When each mechanic resolved on each pull.

    Damage events supply the cast. A death does too, for a guid the log did not
    download. A pull that dodged uses the usual time from the pulls that were hit.
    """

    def __init__(self, report: Path, pack: FightPack, pulls: list[dict]):
        self.pack = pack
        meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
        self.fights = {int(fight["id"]): fight for fight in meta.get("fights") or []}
        self._hits: dict[tuple[int, str, str], list[float]] = defaultdict(list)
        for fight_id, guid, when, phase_id in self._events(report):
            self._note(fight_id, phase_id, when, guid)
        for pull in pulls:
            for death in pull.get("deaths") or []:
                if death.get("outcome") == "environment":
                    continue
                component = death.get("componentId") or death.get("mechanic_id")
                phase_id = death.get("phaseId") if death.get("phaseId") is not None else death.get("phase")
                if component is None or phase_id is None or death.get("t") is None:
                    continue
                cluster_id = death.get("mechanicId")
                if not cluster_id:
                    cluster = pack.cluster_for(component, float(death["t"]), int(phase_id))
                    cluster_id = cluster.id if cluster else None
                if cluster_id:
                    self._hits[(int(pull["id"]), cluster_id, component)].append(float(death["t"]))
        self._typical: dict[tuple[str, str], float] = {}
        grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
        for (fight_id, cluster_id, part_id), times in self._hits.items():
            bursts = _bursts(times)
            if bursts:
                grouped[(cluster_id, part_id)].append(bursts[0])
        for key, values in grouped.items():
            self._typical[key] = float(statistics.median(values))

    def times(self, fight_id: int, cluster_id: str, part_id: str) -> list[float]:
        raw = self._hits.get((int(fight_id), cluster_id, part_id)) or []
        if raw:
            return _waves(_bursts(raw))
        typical = self._typical.get((cluster_id, part_id))
        if typical is None:
            return []
        return [typical]

    def _events(self, report: Path):
        by_guid = _load_events(report)
        for guid, events in by_guid.items():
            for event in events:
                fight = self.fights.get(int(event.get("fight") or 0))
                timestamp = event.get("timestamp")
                if fight is None or timestamp is None:
                    continue
                placed = _place(fight, self.pack, int(timestamp))
                if placed is None:
                    continue
                phase_id, when = placed
                yield int(fight["id"]), int(guid), when, phase_id

    def _note(self, fight_id: int, phase_id: int, when: float, guid: int) -> None:
        mechanic = self.pack.mechanic_for(guid, phase_id)
        if mechanic is None:
            return
        cluster = self.pack.cluster_for(mechanic.id, when, phase_id)
        if cluster is None:
            return
        self._hits[(fight_id, cluster.id, mechanic.id)].append(when)


def _place(fight: dict, pack: FightPack, timestamp: int) -> tuple[int, float] | None:
    for phase, start, end in _qualifying_phases(fight, pack):
        if start - 500 <= timestamp < end:
            return phase.id, (timestamp - start) / 1000
    return None


def attach_frames(report: Path, payload: dict, pack: FightPack) -> None:
    """Add a still to each failed death, and to each mechanic the party failed."""
    book = FrameBook(report)
    clock = CastClock(report, pack, payload.get("pulls") or [])
    mechanics = {item["id"]: item for item in payload.get("mechanics") or []}
    for pull in payload.get("pulls") or []:
        for death in pull.get("deaths") or []:
            death["fight"] = pull["id"]
            frame = book.frame(death, pack)
            if frame:
                death["frame"] = frame
        for card in pull.get("cards") or []:
            mech = mechanics.get(card["id"])
            if mech is None:
                continue
            for part in card.get("parts") or []:
                failed = [
                    seat["name"]
                    for seat in part.get("seats") or []
                    if not seat.get("passed")
                ]
                if not failed:
                    continue
                frames = []
                moments = clock.times(pull["id"], card["id"], part["id"])
                if not moments:
                    scheduled = _scheduled(pack, card["id"], part["id"])
                    if scheduled is not None:
                        moments = [scheduled]
                end = _phase_end(pull, mech["phase"])
                length = book.phase_length(pull["id"], mech["phase"])
                if length is not None:
                    end = length if end is None else min(end, length)
                for when in moments:
                    if end is not None and when > end:
                        continue
                    shot = book.mechanic_frame(
                        pull["id"], mech["phase"], when, part["id"], part["name"], failed, pack,
                    )
                    if shot:
                        frames.append(shot)
                if frames:
                    part["frames"] = frames


def _scheduled(pack: FightPack, cluster_id: str, part_id: str) -> float | None:
    """A cast time from the mechanic list, for a hit the log did not store."""
    for cluster in pack.clusters:
        if cluster.id != cluster_id:
            continue
        for part in cluster.parts:
            if part.mechanic_id == part_id and part.at is not None:
                return float(part.at)
    return None


def _phase_end(pull: dict, phase_id: int) -> float | None:
    """A few seconds after the last death. Later casts had not happened yet."""
    times = []
    for death in pull.get("deaths") or []:
        death_phase = death.get("phaseId")
        if death_phase is None:
            death_phase = death.get("phase")
        if death_phase != phase_id or death.get("t") is None:
            continue
        times.append(float(death["t"]))
    if not times:
        return None
    return max(times) + 5
