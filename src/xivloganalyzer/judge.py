"""Apply mechanic parameters to extracted facts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from xivloganalyzer.catalog import FightPack, Mechanic
from xivloganalyzer.extract import DeathFact


@dataclass
class Blame:
    """Who owns a death, and how sure that call is.

    100 means one owner. A shared death splits 100 across the people who
    could own it, so pointing at any one of them is a lower number.
    """

    who: str
    confidence: int

    def to_dict(self) -> dict:
        return {"who": self.who, "confidence": int(self.confidence)}


@dataclass
class Judgment:
    fact: DeathFact
    mechanic_id: str | None
    mechanic: str
    outcome: str
    happened: str
    should_have_been: str
    went_wrong: str
    cause: str = "none"
    blames: list[Blame] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self.fact)
        payload.update(
            {
                "mechanic_id": self.mechanic_id,
                "mechanic": self.mechanic,
                "outcome": self.outcome,
                "happened": self.happened,
                "should_have_been": self.should_have_been,
                "went_wrong": self.went_wrong,
                "blames": [blame.to_dict() for blame in self.blames],
            }
        )
        return payload


def _comma(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}"


def _mit(multiplier: float | None) -> str:
    if multiplier is None:
        return "mit unknown"
    if multiplier > 1.01:
        return f"{round((multiplier - 1) * 100)}% amp"
    if multiplier >= 0.995:
        return "no party mit"
    return f"{round((1 - multiplier) * 100)}% mit"


def _hp(fact: DeathFact) -> str:
    if fact.hp is None:
        return "HP unknown"
    if fact.max_hp:
        pct = round(100 * fact.hp / fact.max_hp)
        return f"HP {_comma(fact.hp)} ({pct}%)"
    return f"HP {_comma(fact.hp)}"


def _happened(fact: DeathFact, mechanic: Mechanic | None) -> str:
    if fact.guid == 0:
        return "No damage packet."
    hit = fact.unmitigated if fact.unmitigated is not None else fact.total
    parts = [f"{_comma(hit)} unmitigated", _hp(fact), _mit(fact.multiplier)]
    if fact.absorb >= 1000:
        parts.append(f"shield {_comma(fact.absorb)}")
    else:
        parts.append("no shield")
    if mechanic and mechanic.scales_with_stack and fact.stack and mechanic.typical_targets:
        parts.append(f"stack {fact.stack} of {mechanic.typical_targets}")
    owners = _mit_owners(fact)
    if owners:
        parts.append(owners)
    return " · ".join(parts)


def _mit_owners(fact: DeathFact) -> str:
    bits = []
    for mit in fact.mitigations:
        who = mit.get("by") or "unknown"
        label = f"{mit['name']} from {who}"
        via = mit.get("via")
        if via:
            label += f" ({via})"
        amount = mit.get("amount") or 0
        pct = mit.get("pct")
        if amount:
            label += f", shield {_comma(amount)}"
        elif pct is not None and pct != 100:
            delta = round(100 - pct)
            if delta > 0:
                label += f", {delta}%"
            elif delta < 0:
                label += f", {abs(delta)}% amp"
        bits.append(label)
    return "; ".join(bits)


def _vuln(fact: DeathFact) -> bool:
    for name in fact.buffs:
        lowered = name.lower()
        if "vulnerability" in lowered or "damage down" in lowered:
            return True
    return False


def _hit(fact: DeathFact) -> int:
    if fact.unmitigated is not None:
        return fact.unmitigated
    return fact.total


def judge_fact(fact: DeathFact, pack: FightPack) -> Judgment:
    happened = ""
    if fact.guid == 0:
        return Judgment(
            fact=fact,
            mechanic_id=None,
            mechanic="No damage packet",
            outcome="environment",
            happened="No damage packet.",
            should_have_been="A death with no hit is the body after a raise, or a wipe tick.",
            went_wrong="No hit.",
            cause="none",
        )
    mechanic = pack.mechanic_for(fact.guid, fact.phase)
    happened = _happened(fact, mechanic)
    if mechanic is None:
        return Judgment(
            fact=fact,
            mechanic_id=None,
            mechanic=fact.ability,
            outcome="unknown",
            happened=happened,
            should_have_been="This ability is not understood yet.",
            went_wrong=f"{fact.name} died to {fact.ability}.",
            cause="none",
        )
    if _vuln(fact):
        return _done(fact, mechanic, happened, "fail", _amp(fact, mechanic), "personal", pack)
    hit = _hit(fact)
    if mechanic.tanks_only and fact.role != "tank":
        return _done(fact, mechanic, happened, "fail", _not_a_tank(fact, mechanic), "personal", pack)
    if mechanic.off_tank and fact.name != mechanic.off_tank:
        return _done(
            fact, mechanic, happened, "fail",
            f"{fact.name} took {mechanic.name}.",
            "personal", pack,
        )
    if mechanic.one_target and fact.stack and fact.stack > 1:
        return _done(
            fact, mechanic, happened, "fail",
            f"{fact.name} ate an extra {mechanic.name}.",
            "personal", pack,
        )
    if mechanic.any_hit_is_fail:
        if mechanic.id == "bright-flare" and (fact.stack or 0) > 1:
            return _done(
                fact, mechanic, happened, "fail",
                f"{fact.name} got clipped by a Bright Flare.",
                "overlap", pack,
            )
        if mechanic.id == "holy-impact":
            return _done(
                fact, mechanic, happened, "fail",
                f"{fact.name} died to comets that were too close.",
                "prey", pack,
            )
        return _done(fact, mechanic, happened, "fail", _personal(fact, mechanic), "personal", pack)
    failed = _failed_moment(mechanic, fact, hit)
    if failed:
        return _done(
            fact, mechanic, happened, "fail",
            _moment_fault(fact, failed),
            failed.cause or "personal", pack,
        )
    if mechanic.fail_above is not None and hit > mechanic.fail_above:
        return _done(
            fact, mechanic, happened, "fail", _oversized(fact, mechanic),
            _oversized_cause(fact, mechanic), pack,
        )
    cap = mechanic.cap_for(fact.role)
    if cap is None:
        return _done(
            fact, mechanic, happened, "unknown",
            f"{fact.name} died to {mechanic.name}.",
            "none", pack,
        )
    if hit <= cap:
        if fact.hp is not None and fact.hp < pack.low_hp:
            return _done(
                fact, mechanic, happened, "low",
                f"{fact.name} was already low.",
                "low", pack,
            )
        if mechanic.requires_personal_mit and fact.role == "tank" and not _personal_mit(fact, pack):
            return _done(
                fact, mechanic, happened, "fail",
                f"{fact.name} died to {mechanic.name} without mitigation.",
                "personal", pack,
            )
        if mechanic.id == "skyward-leap":
            return _done(
                fact, mechanic, happened, "fail", _skyward_marker(fact), _skyward_cause(fact), pack,
            )
        return _done(
            fact, mechanic, happened, "raw", _raw_fault(fact, mechanic), _raw_cause(fact, mechanic), pack,
        )
    if mechanic.id == "skyward-leap":
        return _done(fact, mechanic, happened, "fail", _skyward_clip(fact), "clip", pack)
    return _done(
        fact, mechanic, happened, "fail", _oversized(fact, mechanic),
        _oversized_cause(fact, mechanic), pack,
    )


def _failed_moment(mechanic: Mechanic, fact: DeathFact, hit: int):
    for moment in mechanic.moments:
        if moment.fail and moment.matches(fact.t, hit):
            return moment
    return None


def _moment_fault(fact: DeathFact, moment) -> str:
    if moment.cause == "tower":
        return f"{fact.name} died to an empty tower."
    return f"{fact.name} got hit."


def _amp(fact: DeathFact, mechanic: Mechanic) -> str:
    if mechanic.id == "holy-shield-bash":
        return f"{fact.name} shorted the tether."
    return f"{fact.name} still had a damage amp."


def _not_a_tank(fact: DeathFact, mechanic: Mechanic) -> str:
    if mechanic.id == "holy-shield-bash":
        return f"{fact.name} took the tether."
    if mechanic.id == "holy-bladedance":
        return f"{fact.name} stood in the cone."
    return f"{fact.name} took {mechanic.name}."


def _personal_mit(fact: DeathFact, pack: FightPack) -> bool:
    if any(name in fact.buffs for name in pack.personal_mit):
        return True
    return fact.multiplier is not None and fact.multiplier <= 0.75


def _personal(fact: DeathFact, mechanic: Mechanic) -> str:
    name = fact.name
    if mechanic.id == "darkdragon-dive-debuff":
        return f"{name} soaked with the dive debuff."
    if mechanic.id in {"gnashing-wheel", "lashing-wheel"}:
        return f"{name} was on the wrong side."
    if mechanic.id == "geirskogul":
        return f"{name} stood in the line."
    if mechanic.id == "ascalons-mercy-concealed":
        return f"{name} got hit by the cone."
    if mechanic.id == "bright-flare":
        return f"{name} got hit by a Bright Flare."
    if mechanic.id == "heavy-impact":
        return f"{name} stood in the ring."
    if mechanic.id == "shining-blade":
        return f"{name} got cleaved."
    if mechanic.id == "heavens-stake":
        return f"{name} stood in the fire."
    if mechanic.id == "holy-shield-bash":
        return f"{name} shorted the tether."
    if mechanic.id == "frostbite":
        return f"{name} stood in the ice."
    if mechanic.id == "dimensional-collapse":
        return f"{name} stood in the puddle."
    if mechanic.category == "gaze":
        return f"{name} looked at the gaze."
    if mechanic.category == "tower":
        return f"{name} died to an empty tower."
    if mechanic.category == "puddle":
        return f"{name} stood in the puddle."
    return f"{name} got hit by {mechanic.name}."


def _short_stack(fact: DeathFact, mechanic: Mechanic) -> str:
    if fact.stack and mechanic.typical_targets:
        return f"The stack was {fact.stack} of {mechanic.typical_targets}."
    return "The stack was short."


def _oversized(fact: DeathFact, mechanic: Mechanic) -> str:
    name = fact.name
    if mechanic.id in {"dark-high-jump", "dark-elusive-jump"}:
        return f"{name} stood in the dive."
    if mechanic.id == "eye-of-the-tyrant":
        return _short_stack(fact, mechanic)
    if mechanic.id == "lightning-storm":
        return f"{name} got clipped by Lightning Storm."
    if mechanic.category == "tower":
        return f"{name} died to an empty tower."
    if mechanic.id == "dragons-rage":
        return f"{name} took a failed Dragon's Rage."
    if mechanic.category == "stack":
        return f"{name} got cleaved."
    if mechanic.id == "hiemal-storm":
        return f"{name} failed the ice soak."
    if mechanic.category == "puddle":
        return f"{name} stood in the puddle."
    return f"{name} took too much from {mechanic.name}."


def _skyward_marker(fact: DeathFact) -> str:
    if fact.max_hp and fact.hp is not None and fact.hp < fact.max_hp:
        return f"{fact.name} wasn't full for Skyward Leap."
    return f"{fact.name} died to Skyward Leap without mitigation."


def _skyward_clip(fact: DeathFact) -> str:
    return f"{fact.name} got clipped by a Skyward Leap."


def _skyward_cause(fact: DeathFact) -> str:
    if fact.max_hp and fact.hp is not None and fact.hp < fact.max_hp:
        return "healers"
    return "mitigation"


def _raw_cause(fact: DeathFact, mechanic: Mechanic) -> str:
    if (
        mechanic.scales_with_stack
        and fact.stack
        and mechanic.typical_targets
        and fact.stack < mechanic.typical_targets
    ):
        return "missing"
    return "resolve"


def _oversized_cause(fact: DeathFact, mechanic: Mechanic) -> str:
    if mechanic.id in {"dark-high-jump", "dark-elusive-jump"}:
        return "overlap"
    if mechanic.id == "eye-of-the-tyrant":
        return "missing"
    if mechanic.category == "tower" or mechanic.id == "skyward-leap":
        return "tower"
    if mechanic.id == "lightning-storm":
        return "overlap"
    if mechanic.id == "bright-flare" and (fact.stack or 0) > 1:
        return "overlap"
    return "personal"


def _raw_fault(fact: DeathFact, mechanic: Mechanic) -> str:
    if (
        mechanic.scales_with_stack
        and fact.stack
        and mechanic.typical_targets
        and fact.stack < mechanic.typical_targets
    ):
        return _short_stack(fact, mechanic)
    return f"{fact.name} died to the real hit."


def _should(fact: DeathFact, mechanic: Mechanic, pack: FightPack) -> str:
    """The correct play for this cast, not a later one of the same ability."""
    hit = _hit(fact)
    for moment in mechanic.moments:
        if moment.matches(fact.t, hit):
            return moment.should_have_been
    part = pack.part_for(mechanic.id, fact.t, fact.phase)
    if part and part.should_have_been:
        return part.should_have_been
    return mechanic.should_have_been


def _done(
    fact: DeathFact,
    mechanic: Mechanic,
    happened: str,
    outcome: str,
    wrong: str,
    cause: str,
    pack: FightPack,
) -> Judgment:
    return Judgment(
        fact=fact,
        mechanic_id=mechanic.id,
        mechanic=mechanic.name,
        outcome=outcome,
        happened=happened,
        should_have_been=_should(fact, mechanic, pack),
        went_wrong=wrong,
        cause=cause,
    )


def _shares(whos: list[str]) -> list[Blame]:
    """Equal share of 100. Two owners is 50 each. Three is 33."""
    count = len(whos)
    if count == 0:
        return []
    score = 100 if count == 1 else 100 // count
    return [Blame(who, score) for who in whos]


def _group(who: str, people: int) -> list[Blame]:
    """One label for a set of people the log cannot name."""
    size = max(int(people), 1)
    return [Blame(who, 100 if size == 1 else 100 // size)]


def _no_party_mit(fact: DeathFact) -> bool:
    return fact.multiplier is None or fact.multiplier >= 0.995


def _same_cast(left: Judgment, right: Judgment) -> bool:
    return (
        left.cause == right.cause
        and left.mechanic_id == right.mechanic_id
        and left.fact.fight == right.fact.fight
        and abs(left.fact.t - right.fact.t) <= 1.5
    )


def _overlap_names(item: Judgment, cohort: list[Judgment]) -> list[str]:
    ordered = sorted(cohort, key=lambda other: (other.fact.name != item.fact.name, other.fact.name))
    names: list[str] = []
    for other in ordered:
        if other.fact.name not in names:
            names.append(other.fact.name)
    stack = item.fact.stack or 0
    if item.mechanic_id == "bright-flare" and stack > len(names):
        names.extend("Another player" for _ in range(stack - len(names)))
    return names


def roster_from_meta(meta: dict, pack: FightPack) -> list[tuple[str, str]]:
    """Player name and role from the report's friendlies."""
    skip = {"LimitBreak", "NPC"}
    people = []
    for actor in meta.get("friendlies") or []:
        name = str(actor.get("name") or "").strip()
        job = actor.get("type") or ""
        if not name or job in skip:
            continue
        people.append((name, pack.role_of(job)))
    return people


def _roster_from_facts(facts: list[DeathFact]) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for fact in facts:
        seen.setdefault(fact.name, fact.role)
    return list(seen.items())


def _healers(roster: list[tuple[str, str]]) -> list[str]:
    return sorted(name for name, role in roster if role == "healer")


def _assign_blame(
    judgments: list[Judgment], pack: FightPack, roster: list[tuple[str, str]],
) -> None:
    healers = _healers(roster)
    for item in judgments:
        if item.cause == "none":
            item.blames = []
        elif item.cause == "personal":
            item.blames = _shares([item.fact.name])
        elif item.cause == "overlap":
            cohort = [other for other in judgments if _same_cast(item, other)]
            item.blames = _shares(_overlap_names(item, cohort))
        elif item.cause == "healers":
            item.blames = _shares(healers or ["Healers"])
        elif item.cause == "mitigation":
            item.blames = _group("Assigned mitigation", 2)
        elif item.cause == "tower":
            item.blames = _group("Missed soak", 2)
        elif item.cause == "prey":
            item.blames = _group("Prey markers", 2)
        elif item.cause == "clip":
            item.blames = _group("Out of position", 3)
        elif item.cause == "missing":
            if not item.fact.stack:
                item.blames = _group("Missing bodies", 2)
            else:
                mechanic = pack.mechanic_for(item.fact.guid, item.fact.phase)
                typical = mechanic.typical_targets if mechanic and mechanic.typical_targets else 0
                missing = max(typical - (item.fact.stack or 0), 1)
                item.blames = _group("Missing bodies", missing)
        elif item.cause == "resolve":
            owners = list(healers) or ["Healers"]
            if _no_party_mit(item.fact):
                owners.append("Party mitigation")
            item.blames = _shares(owners)
        elif item.cause == "low":
            owners = list(healers) or ["Healers"]
            owners.append("Earlier damage")
            item.blames = _shares(owners)
        else:
            item.blames = []


def judge_report(
    facts: list[DeathFact],
    pack: FightPack,
    roster: list[tuple[str, str]] | None = None,
) -> list[Judgment]:
    judgments = [judge_fact(fact, pack) for fact in facts]
    people = list(roster) if roster else _roster_from_facts(facts)
    _assign_blame(judgments, pack, people)
    return judgments


def write_judgments(report: Path, judgments: list[Judgment]) -> Path:
    path = report / "judgments.json"
    path.write_text(
        json.dumps([item.to_dict() for item in judgments], indent=2),
        encoding="utf-8",
    )
    return path
