"""Apply mechanic parameters to extracted facts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from xivloganalyzer.catalog import FightPack, Mechanic
from xivloganalyzer.extract import DeathFact


@dataclass
class Judgment:
    fact: DeathFact
    mechanic_id: str | None
    mechanic: str
    outcome: str
    happened: str
    should_have_been: str
    went_wrong: str

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
            went_wrong="No fault on a mechanic. There is no hit to assign.",
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
            went_wrong="No fault assigned. Say what this hit should mean and it can be judged.",
        )
    if _vuln(fact):
        return _done(
            fact, mechanic, happened, "fail",
            f"{fact.name} had vulnerability or damage down. The amp is from a failed mechanic.",
        )
    hit = _hit(fact)
    if mechanic.tanks_only and fact.role != "tank":
        return _done(
            fact, mechanic, happened, "fail",
            f"{fact.name} got {mechanic.name}. Only a tank takes this.",
        )
    if mechanic.off_tank and fact.name != mechanic.off_tank:
        wrong = f"The off tank takes {mechanic.name}. {fact.name} took it."
        if mechanic.requires_personal_mit and not _personal_mit(fact, pack):
            wrong += " Personal mitigation was not enough."
        return _done(fact, mechanic, happened, "fail", wrong)
    if mechanic.one_target and fact.stack and fact.stack > 1:
        return _done(
            fact, mechanic, happened, "fail",
            f"Only one tank takes {mechanic.name}. {fact.name} ate the extra hit ({_comma(hit)}).",
        )
    if mechanic.any_hit_is_fail:
        return _done(fact, mechanic, happened, "fail", _personal(fact, mechanic))
    if mechanic.fail_above is not None and hit > mechanic.fail_above:
        return _done(fact, mechanic, happened, "fail", _oversized(fact, mechanic, hit))
    cap = mechanic.cap_for(fact.role)
    if cap is None:
        return _done(fact, mechanic, happened, "unknown", "No fault assigned. This role is not covered yet.")
    if hit <= cap:
        if fact.hp is not None and fact.hp < pack.low_hp:
            return _done(
                fact, mechanic, happened, "low",
                f"{fact.name} was already at {_comma(fact.hp)}. The hit itself is the normal one.",
            )
        if mechanic.requires_personal_mit and fact.role == "tank" and not _personal_mit(fact, pack):
            return _done(
                fact, mechanic, happened, "fail",
                f"{fact.name} died to the real {mechanic.name}. Personal mitigation was not enough.",
            )
        if mechanic.id == "skyward-leap":
            return _done(fact, mechanic, happened, "fail", _skyward_marker(fact))
        return _done(fact, mechanic, happened, "raw", _raw_fault(fact, mechanic))
    if mechanic.id == "skyward-leap":
        return _done(fact, mechanic, happened, "fail", _skyward_clip(fact, hit))
    return _done(fact, mechanic, happened, "fail", _oversized(fact, mechanic, hit))


def _personal_mit(fact: DeathFact, pack: FightPack) -> bool:
    if any(name in fact.buffs for name in pack.personal_mit):
        return True
    return fact.multiplier is not None and fact.multiplier <= 0.75


def _personal(fact: DeathFact, mechanic: Mechanic) -> str:
    if mechanic.category == "tower":
        return f"A {mechanic.name} was missed. {fact.name} died to the failed version, not a real soak."
    if mechanic.id == "ascalons-mercy-concealed":
        return (
            f"{fact.name} got hit by Ascalon's Mercy Concealed. "
            "Nobody should be hit."
        )
    if mechanic.category in {"dodge", "gaze", "spread"}:
        return f"{fact.name} failed {mechanic.name}."
    if mechanic.category == "puddle":
        return f"{fact.name} failed the {mechanic.name} soak."
    return f"{fact.name} got the failed version of {mechanic.name}."


def _oversized(fact: DeathFact, mechanic: Mechanic, hit: int) -> str:
    if mechanic.category == "tower":
        return f"A tower was empty. {fact.name} died to the explosion ({_comma(hit)}), not a real soak."
    if mechanic.category == "stack":
        return f"{fact.name} took the failed cleave of {mechanic.name} ({_comma(hit)}), not the share."
    if mechanic.category == "puddle":
        return f"{fact.name} failed {mechanic.name}. {_comma(hit)} is well above a placed hit."
    return f"{fact.name} took {_comma(hit)}, which is not the real {mechanic.name}."


def _skyward_marker(fact: DeathFact) -> str:
    if fact.max_hp and fact.hp is not None and fact.hp < fact.max_hp:
        return (
            f"{fact.name} was at {_comma(fact.hp)} of {_comma(fact.max_hp)}. "
            "The healers did not fully heal them."
        )
    shield = "no shield" if fact.absorb < 1000 else f"a {_comma(fact.absorb)} shield"
    return (
        f"{fact.name} was fully healed. Skyward Leap had {_mit(fact.multiplier)} and {shield}. "
        "The players who were supposed to mitigate it own that death."
    )


def _skyward_clip(fact: DeathFact, hit: int) -> str:
    return (
        f"{fact.name} was clipped by another Skyward Leap ({_comma(hit)}). "
        "The player who was out of the spot owns it."
    )


def _raw_fault(fact: DeathFact, mechanic: Mechanic) -> str:
    if (
        mechanic.scales_with_stack
        and fact.stack
        and mechanic.typical_targets
        and fact.stack < mechanic.typical_targets
    ):
        return (
            f"The {mechanic.name} share was {fact.stack} of {mechanic.typical_targets}. "
            "Missing bodies raised the hit."
        )
    shield = "no shield" if fact.absorb < 1000 else f"a {_comma(fact.absorb)} shield"
    mit = _mit(fact.multiplier)
    return (
        f"The resolve was fine. {fact.name} died to the real {mechanic.name} "
        f"with {shield} and {mit}."
    )


def _done(fact: DeathFact, mechanic: Mechanic, happened: str, outcome: str, wrong: str) -> Judgment:
    return Judgment(
        fact=fact,
        mechanic_id=mechanic.id,
        mechanic=mechanic.name,
        outcome=outcome,
        happened=happened,
        should_have_been=mechanic.should_have_been,
        went_wrong=wrong,
    )


def judge_report(facts: list[DeathFact], pack: FightPack) -> list[Judgment]:
    return [judge_fact(fact, pack) for fact in facts]


def write_judgments(report: Path, judgments: list[Judgment]) -> Path:
    path = report / "judgments.json"
    path.write_text(
        json.dumps([item.to_dict() for item in judgments], indent=2),
        encoding="utf-8",
    )
    return path
