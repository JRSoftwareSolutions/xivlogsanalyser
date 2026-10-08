"""Load fight packs from fights/<id>/."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RoleBand:
    unmitigated_max: int
    lived: str


@dataclass
class Moment:
    """A different resolution of the same ability. `above` is an unmitigated hit.

    `fail` means a hit in this window is a mistake even when it fits the role cap.
    """

    should_have_been: str
    after: float | None = None
    until: float | None = None
    above: int | None = None
    fail: bool = False
    cause: str = ""

    def matches(self, t: float, hit: int) -> bool:
        if self.after is not None and t < self.after:
            return False
        if self.until is not None and t >= self.until:
            return False
        if self.above is not None and hit <= self.above:
            return False
        return True


@dataclass
class DiveMarker:
    """A debuff that marks who dives.

    `side` is the half of the arena it resolves on. `facing` is where the diver
    looks at the snapshot, which decides where the tower drops.
    """

    name: str
    side: str = ""
    facing: str = ""


@dataclass
class MarkerSpots:
    """Where marker holders stand, as seen from the arena center with the boss at 0 degrees.

    `angles` are the spots, mirrored left and right. `edge` is their distance
    from the center. A holder within `tolerance` yalms of a spot is in it. A
    player who is not a holder is in position when no leap from those spots
    reaches them, so farther than `radius` from every spot.
    """

    angles: list[float]
    edge: float
    tolerance: float
    radius: float
    boss: str


@dataclass
class NeedsEveryone:
    """A mechanic that fails when a player is missing from it.

    `soak` are the guids that hit everyone in place, such as towers. They land up to
    `lead` seconds before the first death. Without a soak, the cast lands `lead`
    seconds before the first death.

    `holders` narrows it to the players who held one of those debuffs when it
    landed, such as the Dive from Grace 3s for the first towers. `roles` narrows
    it to those roles, such as the non-tanks for the Strength towers. `after` and
    `until` are the phase times this set covers, when one ability explodes for
    more than one set of towers.

    `stack` is a soak that is one shared hit, such as a stack marker: everyone in it
    shares one instance, so nobody doubled up. `marked_out` are marker guids whose
    holders belong elsewhere, such as the three Skyward Leap holders for the
    Dragon's Rage stack: the first player each of those casts hit is not needed.
    """

    lead: float
    soak: list[int] = field(default_factory=list)
    # Seconds from the soak to the explosion, for a pull with no soak hit at all.
    lag: float = 2.0
    holders: list[int] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    after: float | None = None
    until: float | None = None
    stack: bool = False
    marked_out: list[int] = field(default_factory=list)

    def covers(self, t: float) -> bool:
        if self.after is not None and t < self.after:
            return False
        return self.until is None or t < self.until


@dataclass
class Drops:
    """Markers that drop something, which explodes when two drops land too close.

    `debuff` marks the holders, applied up to `within` seconds before the explosion.
    `actor` is what they drop. An explosion sits within `reach` yalms of each drop it came from.
    """

    debuff: int
    actor: str
    within: float
    reach: float


@dataclass
class Stun:
    """A status that stops the player from moving, put on them by a hit aimed at someone else.

    `debuff` is the stun. `casts` are the hits on the players who caused it, such as
    the Holy Shield Bash on a tether holder, landing up to `within` seconds before the stun.
    A player stunned this way could not dodge, so whoever drew that hit owns the death.
    """

    debuff: int
    casts: list[int]
    within: float


@dataclass
class Baited:
    """Cones each aimed at one player, who all stand together but one, such as the opener's
    Ascalon's Mercy Concealed: everyone stacks behind the boss and one tank in front.

    Up to `until` seconds into the phase. Each cone locks on its player `lock` seconds
    before it hits. A cone that points neither at the stack nor at the front was baited
    by the player standing within `aim` degrees of it, and a player who dies within
    `width` degrees of it was hit by that cone.
    """

    until: float
    lock: float
    aim: float
    width: float


@dataclass
class Mechanic:
    id: str
    name: str
    phase: int
    guids: list[int]
    category: str
    should_have_been: str
    any_hit_is_fail: bool = False
    scales_with_stack: bool = False
    typical_targets: int | None = None
    fail_above: int | None = None
    roles: dict[str, RoleBand] = field(default_factory=dict)
    tanks_only: bool = False
    one_target: bool = False
    requires_personal_mit: bool = False
    # Only the report's off tank takes it. Who that is comes from the log (`extract.off_tank`).
    off_tank: bool = False
    # Only the report's main tank takes it, the same way (`extract.main_tank`).
    main_tank: bool = False
    marker_owns_clip: bool = False
    spots: MarkerSpots | None = None
    moments: list[Moment] = field(default_factory=list)
    dive_markers: dict[int, DiveMarker] = field(default_factory=dict)
    needs_everyone: list[NeedsEveryone] = field(default_factory=list)
    drops: Drops | None = None
    # Casts alternate between two groups, so the same players take every other one.
    alternating: bool = False
    # Each circle is shared by one support and one DPS, such as Hiemal Storm's ice.
    pairs: bool = False
    # A player stunned by a hit aimed at someone else could not dodge this.
    stun: Stun | None = None
    # One hit for each player, such as Lightning Storm's bolts. A dead player's goes to
    # someone alive, who then takes two that hit nobody else.
    one_each: bool = False
    # The landing knocks back everyone it hits, so a player it hit who dies at the edge
    # right after was knocked into the deathwall by whoever it landed on.
    knockback: bool = False
    # A cone baited from outside the stack is also the baiter's mistake.
    baited: Baited | None = None
    # A tank's hit, such as a tether, that falls to someone else when a tank is dead.
    covers_dead_tanks: bool = False
    # What went wrong when a hit is bigger than the role takes, with {name}, such as
    # "{name} stood too close to Ser Zephirin's landing." Without it, the category's line.
    too_much: str = ""

    def cap_for_stack(self, role: str, stack: int | None) -> int | None:
        """The role cap for this many players in the stack. The caps are set for a full
        stack; the same cast split fewer ways is bigger per player, so the cap scales up."""
        cap = self.cap_for(role)
        if cap is None or not self.scales_with_stack or not self.typical_targets or not stack:
            return cap
        if stack >= self.typical_targets:
            return cap
        return round(cap * self.typical_targets / stack)

    def fail_above_for(self, stack: int | None) -> int | None:
        """The hit no share reaches, for this many players in the stack. Like the role cap,
        it is set for a full stack and scales up when the same cast splits fewer ways."""
        if self.fail_above is None or not self.scales_with_stack or not self.typical_targets or not stack:
            return self.fail_above
        if stack >= self.typical_targets:
            return self.fail_above
        return round(self.fail_above * self.typical_targets / stack)

    def cap_for(self, role: str) -> int | None:
        band = self.roles.get(role) or self.roles.get("dps")
        return band.unmitigated_max if band else None

    def lived_for(self, role: str) -> str:
        band = self.roles.get(role) or self.roles.get("dps")
        return band.lived if band else ""


@dataclass
class ClusterPart:
    mechanic_id: str
    after: float | None = None
    until: float | None = None
    should_have_been: str = ""
    at: float | None = None


@dataclass
class DebuffColumn:
    """Debuffs that hand out a role for a stop, such as a number or a dive marker.

    `labels` maps each debuff guid to what it means, in the order the list sorts by.
    """

    column: str
    labels: dict[int, str]


@dataclass
class Cluster:
    """One stop on the session line. `starts` is seconds into `phase`. `skill` explains the stop.

    `debuffs` are the role debuffs listed for every player on the pull's card.
    `lands` is when its first mechanic lands, the earliest seen in the logs: a
    player raised before it played the whole stop.
    """

    id: str
    name: str
    phase: int
    starts: float
    summary: str
    parts: list[ClusterPart]
    skill: str = ""
    debuffs: list[DebuffColumn] = field(default_factory=list)
    lands: float | None = None


@dataclass
class Phase:
    id: int
    name: str
    min_duration_ms: int


@dataclass
class Marker:
    """A named mechanic on the pull chart. `starts` is seconds into `phase`."""

    name: str
    phase: int
    starts: float


@dataclass
class FightPack:
    id: str
    name: str
    zone_id: int | None
    low_hp: int
    personal_mit: list[str]
    roles: dict[str, list[str]]
    phases: list[Phase]
    mechanics: list[Mechanic]
    clusters: list[Cluster] = field(default_factory=list)
    clock: dict[int, float] = field(default_factory=dict)
    markers: list[Marker] = field(default_factory=list)
    deathwall: Mechanic | None = None
    cascade_debuffs: list[str] = field(default_factory=list)
    # Buffs that raise max HP while they are on, such as Thrill of Battle, by name.
    max_hp_buffs: dict[str, float] = field(default_factory=dict)
    folder: Path | None = None

    def role_of(self, job: str) -> str:
        for role, jobs in self.roles.items():
            if job in jobs:
                return role
        return "dps"

    def mechanic_for(self, guid: int, phase: int) -> Mechanic | None:
        for mech in self.mechanics:
            if mech.phase == phase and guid in mech.guids:
                return mech
        return None

    def mechanic_named(self, name: str, phase: int | None = None) -> Mechanic | None:
        """The mechanic a status's source names, such as "the Dragon's Glory". Case and a leading "the " do not matter."""
        wanted = name.strip().casefold().removeprefix("the ")
        for mech in self.mechanics:
            if mech.name.casefold() == wanted and (phase is None or mech.phase == phase):
                return mech
        return None

    def cluster_for(self, mechanic_id: str | None, t: float, phase: int) -> Cluster | None:
        if not mechanic_id:
            return None
        for cluster in self.clusters:
            if cluster.phase != phase:
                continue
            for part in cluster.parts:
                if part.mechanic_id != mechanic_id:
                    continue
                if part.after is not None and t < part.after:
                    continue
                if part.until is not None and t >= part.until:
                    continue
                return cluster
        return None

    def part_for(self, mechanic_id: str | None, t: float, phase: int) -> ClusterPart | None:
        if not mechanic_id:
            return None
        for cluster in self.clusters:
            if cluster.phase != phase:
                continue
            for part in cluster.parts:
                if part.mechanic_id != mechanic_id:
                    continue
                if part.after is not None and t < part.after:
                    continue
                if part.until is not None and t >= part.until:
                    continue
                return part
        return None

    def phase(self, phase_id: int) -> Phase | None:
        for phase in self.phases:
            if phase.id == phase_id:
                return phase
        return None


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "fights").is_dir() and (candidate / "reports").is_dir():
            return candidate
    return Path.cwd()


def _clusters(raw_clusters: list[dict]) -> list[Cluster]:
    clusters = []
    for raw in raw_clusters:
        parts = []
        for part in raw.get("parts") or []:
            parts.append(
                ClusterPart(
                    mechanic_id=part["id"],
                    after=part.get("after"),
                    until=part.get("until"),
                    should_have_been=part.get("should_have_been") or "",
                    at=part.get("at"),
                )
            )
        clusters.append(
            Cluster(
                id=raw["id"],
                name=raw["name"],
                phase=int(raw["phase"]),
                starts=float(raw.get("starts", 0)),
                lands=float(raw["lands"]) if raw.get("lands") is not None else None,
                summary=raw.get("summary", ""),
                parts=parts,
                skill=raw.get("skill", ""),
                debuffs=[
                    DebuffColumn(
                        column=row["column"],
                        labels={int(guid): label for guid, label in row["labels"].items()},
                    )
                    for row in raw.get("debuffs") or []
                ],
            )
        )
    return clusters


def _spots(raw: dict | None) -> MarkerSpots | None:
    if not raw:
        return None
    return MarkerSpots(
        angles=[float(angle) for angle in raw["angles"]],
        edge=float(raw["edge"]),
        tolerance=float(raw["tolerance"]),
        radius=float(raw["radius"]),
        boss=raw.get("boss") or "",
    )


def _needs_everyone(raw: dict | list | None) -> list[NeedsEveryone]:
    """One set, or a list of sets told apart by `after` and `until`."""
    if not raw:
        return []
    rows = raw if isinstance(raw, list) else [raw]
    return [
        NeedsEveryone(
            lead=float(row["lead"]),
            soak=[int(guid) for guid in row.get("soak") or []],
            lag=float(row.get("lag", 2.0)),
            holders=[int(guid) for guid in row.get("holders") or []],
            roles=list(row.get("roles") or []),
            after=float(row["after"]) if row.get("after") is not None else None,
            until=float(row["until"]) if row.get("until") is not None else None,
            stack=bool(row.get("stack", False)),
            marked_out=[int(guid) for guid in row.get("marked_out") or []],
        )
        for row in rows
    ]


def _drops(raw: dict | None) -> Drops | None:
    if not raw:
        return None
    return Drops(
        debuff=int(raw["debuff"]),
        actor=raw["actor"],
        within=float(raw["within"]),
        reach=float(raw["reach"]),
    )


def _baited(raw: dict | None) -> Baited | None:
    if not raw:
        return None
    return Baited(
        until=float(raw["until"]),
        lock=float(raw.get("lock", 1.2)),
        aim=float(raw.get("aim", 10)),
        width=float(raw.get("width", 20)),
    )


def _stun(raw: dict | None) -> Stun | None:
    if not raw:
        return None
    return Stun(
        debuff=int(raw["debuff"]),
        casts=[int(guid) for guid in raw["casts"]],
        within=float(raw.get("within", 3)),
    )


def _deathwall(raw: dict | None) -> Mechanic | None:
    """The arena edge. It has no phase and no packet, so it is not in `mechanics`."""
    if not raw:
        return None
    return Mechanic(
        id=raw.get("id", "deathwall"),
        name=raw.get("name", "Deathwall"),
        phase=0,
        guids=[0],
        category=raw.get("category", "wall"),
        should_have_been=raw.get("should_have_been", ""),
    )


def load_pack(fight_dir: Path) -> FightPack:
    fight = json.loads((fight_dir / "fight.json").read_text(encoding="utf-8"))
    mechanics_doc = json.loads((fight_dir / "mechanics.json").read_text(encoding="utf-8"))
    mechanics = []
    for raw in mechanics_doc["mechanics"]:
        roles = {
            name: RoleBand(unmitigated_max=int(band["unmitigated_max"]), lived=band.get("lived", ""))
            for name, band in (raw.get("roles") or {}).items()
        }
        mechanics.append(
            Mechanic(
                id=raw["id"],
                name=raw["name"],
                phase=int(raw["phase"]),
                guids=[int(g) for g in raw["guids"]],
                category=raw.get("category", "unknown"),
                should_have_been=raw.get("should_have_been", ""),
                any_hit_is_fail=bool(raw.get("any_hit_is_fail", False)),
                scales_with_stack=bool(raw.get("scales_with_stack", False)),
                typical_targets=raw.get("typical_targets"),
                fail_above=raw.get("fail_above"),
                roles=roles,
                tanks_only=bool(raw.get("tanks_only", False)),
                one_target=bool(raw.get("one_target", False)),
                requires_personal_mit=bool(raw.get("requires_personal_mit", False)),
                off_tank=bool(raw.get("off_tank")),
                main_tank=bool(raw.get("main_tank")),
                marker_owns_clip=bool(raw.get("marker_owns_clip", False)),
                spots=_spots(raw.get("spots")),
                moments=[
                    Moment(
                        should_have_been=row.get("should_have_been") or "",
                        after=row.get("after"),
                        until=row.get("until"),
                        above=row.get("above"),
                        fail=bool(row.get("fail", False)),
                        cause=row.get("cause") or "",
                    )
                    for row in raw.get("moments") or []
                ],
                dive_markers={
                    int(guid): DiveMarker(
                        name=row["name"], side=row.get("side") or "", facing=row.get("facing") or "",
                    )
                    for guid, row in (raw.get("dive_markers") or {}).items()
                },
                needs_everyone=_needs_everyone(raw.get("needs_everyone")),
                drops=_drops(raw.get("drops")),
                alternating=bool(raw.get("alternating", False)),
                pairs=bool(raw.get("pairs", False)),
                stun=_stun(raw.get("stun")),
                one_each=bool(raw.get("one_each", False)),
                knockback=bool(raw.get("knockback", False)),
                baited=_baited(raw.get("baited")),
                covers_dead_tanks=bool(raw.get("covers_dead_tanks", False)),
                too_much=str(raw.get("too_much") or ""),
            )
        )
    return FightPack(
        id=fight["id"],
        name=fight["name"],
        zone_id=fight.get("zone_id"),
        low_hp=int(fight.get("low_hp", 15000)),
        personal_mit=list(fight.get("personal_mit") or []),
        roles=fight.get("roles") or {},
        phases=[
            Phase(id=int(p["id"]), name=p["name"], min_duration_ms=int(p.get("min_duration_ms", 0)))
            for p in fight.get("phases") or []
        ],
        mechanics=mechanics,
        clusters=_clusters(mechanics_doc.get("clusters") or []),
        clock={int(row["phase"]): float(row["at"]) for row in fight.get("clock") or []},
        markers=[
            Marker(name=row["name"], phase=int(row["phase"]), starts=float(row["starts"]))
            for row in fight.get("markers") or []
        ],
        deathwall=_deathwall(mechanics_doc.get("deathwall")),
        cascade_debuffs=list(fight.get("cascade_debuffs") or []),
        max_hp_buffs={name: float(factor) for name, factor in (fight.get("max_hp_buffs") or {}).items()},
        folder=fight_dir,
    )


def load_catalog(root: Path | None = None) -> list[FightPack]:
    root = root or repo_root()
    packs = []
    for fight_json in sorted((root / "fights").glob("*/fight.json")):
        packs.append(load_pack(fight_json.parent))
    return packs


def pack_for_zone(zone_id: int, catalog: list[FightPack]) -> FightPack | None:
    for pack in catalog:
        if pack.zone_id == zone_id:
            return pack
    return None
