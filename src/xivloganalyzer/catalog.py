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
    off_tank: str = ""
    marker_owns_clip: bool = False
    spots: MarkerSpots | None = None
    moments: list[Moment] = field(default_factory=list)
    dive_markers: dict[int, DiveMarker] = field(default_factory=dict)

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
class Cluster:
    """One stop on the session line. `starts` is seconds into `phase`. `skill` explains the stop."""

    id: str
    name: str
    phase: int
    starts: float
    summary: str
    parts: list[ClusterPart]
    skill: str = ""


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
                summary=raw.get("summary", ""),
                parts=parts,
                skill=raw.get("skill", ""),
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
                off_tank=raw.get("off_tank") or "",
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
