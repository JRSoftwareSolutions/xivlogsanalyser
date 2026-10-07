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
    first: bool = False
    first_mistake: str = ""
    # Who left an empty tower. Blame for cause "empty".
    owners: list[str] = field(default_factory=list)

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
                "cause": self.cause,
                "blames": [blame.to_dict() for blame in self.blames],
                "first": self.first,
                "first_mistake": self.first_mistake,
            }
        )
        return payload


# Yalms off the north-south line before a diver counts as west or east.
SIDE_MARGIN = 2.0
# A diver this close to the player who died was in the same landing.
LANDING_REACH = 6.0


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


def _everything(fact: DeathFact, mechanic: Mechanic | None) -> str:
    """Every number in the packet, for a death nobody understands yet."""
    if fact.unmitigated is not None:
        parts = [f"{_comma(fact.unmitigated)} unmitigated"]
    else:
        parts = [f"took {_comma(fact.total)}"]
    parts += [_hp(fact), _mit(fact.multiplier)]
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


_ROLE = {"tank": "tank", "healer": "healer", "dps": "DPS"}


def _known_hp(fact: DeathFact) -> bool:
    return fact.hp is not None and fact.hp > 0 and bool(fact.max_hp)


def _full(fact: DeathFact) -> bool:
    return _known_hp(fact) and fact.hp >= fact.max_hp


def _took(fact: DeathFact, exact: bool) -> str:
    """The hit and the HP it landed on. `exact` adds the HP numbers, for a heal check."""
    took = f"Took {_comma(fact.total)}"
    if not _known_hp(fact):
        return f"{took}."
    if _full(fact):
        return f"{took} at full HP."
    pct = round(100 * fact.hp / fact.max_hp)
    if exact:
        return f"{took} at {pct}% HP ({_comma(fact.hp)} of {_comma(fact.max_hp)})."
    return f"{took} at {pct}% HP."


def _landed(fact: DeathFact) -> int:
    """What reached their HP, after the shield."""
    return max(fact.total - fact.absorb, 0)


def _amped(fact: DeathFact) -> str:
    names = [
        name for name in fact.buffs
        if "vulnerability" in name.lower() or "damage down" in name.lower()
    ]
    amp = ""
    if fact.multiplier is not None and fact.multiplier > 1.01:
        amp = f"{round((fact.multiplier - 1) * 100)}%"
    if names and amp:
        return f"Had {_joined(names)} ({amp} amp)."
    if names:
        return f"Had {_joined(names)}."
    if amp:
        return f"The hit was amplified {amp}."
    return ""


def _band(lived: str) -> bool:
    """A lived band reads as a range of numbers, not a note that nobody lives it."""
    lowered = lived.lower()
    if not any(ch.isdigit() for ch in lowered):
        return False
    return not any(word in lowered for word in ("no ", "not ", "killed"))


def _beyond_role(fact: DeathFact, mechanic: Mechanic) -> str:
    """A hit bigger than this role takes from the real cast, against the band people live."""
    cap = mechanic.cap_for(fact.role)
    hit = _hit(fact)
    lived = mechanic.lived_for(fact.role)
    if cap is None or hit <= cap or not _band(lived):
        return ""
    role = _ROLE.get(fact.role, fact.role)
    if fact.unmitigated is not None and fact.unmitigated != fact.total:
        return f"The hit was {_comma(hit)} before mitigation. A {role} takes {lived}."
    return f"A {role} takes {lived}."


def _one_shot(fact: DeathFact) -> str:
    if not fact.max_hp or _landed(fact) < fact.max_hp:
        return ""
    if _full(fact):
        return "A one-shot."
    return "It would have killed them from full HP."


def _short(fact: DeathFact, mechanic: Mechanic) -> str:
    if (
        mechanic.scales_with_stack
        and fact.stack
        and mechanic.typical_targets
        and fact.stack < mechanic.typical_targets
    ):
        return f"Shared by {fact.stack} of {mechanic.typical_targets}."
    return ""


def _mit_seen(fact: DeathFact) -> float | None:
    """The damage multiplier from mitigation, from the packet or the buffs on the hit."""
    if fact.multiplier is not None:
        return fact.multiplier
    found = None
    for mit in fact.mitigations:
        pct = mit.get("pct")
        if pct is None or mit.get("amount") or pct > 100:
            continue
        found = (found if found is not None else 1.0) * pct / 100
    return found


def _heal_check(fact: DeathFact) -> list[str]:
    """What would have kept them alive through a hit people live: HP, a shield, mitigation."""
    missing = []
    if _known_hp(fact) and not _full(fact):
        if _landed(fact) < fact.max_hp:
            missing.append("Full HP would have lived.")
        else:
            missing.append("Full HP would not have been enough.")
    if fact.absorb < 1000:
        missing.append("No shield.")
    seen = _mit_seen(fact)
    if seen is not None and seen >= 0.995:
        missing.append("No party mitigation.")
    if missing:
        return missing
    held = [f"a {_comma(fact.absorb)} shield"]
    if seen is not None:
        held.append(f"{round((1 - seen) * 100)}% mitigation")
    text = " and ".join(held)
    return [f"{text[0].upper()}{text[1:]} were not enough."]


def _happened(
    fact: DeathFact, mechanic: Mechanic, outcome: str, cause: str, pack: FightPack,
) -> str:
    """The facts behind the call, not every number in the packet.

    A fail says how hard the hit was and what made it worse. A raw death says
    what would have kept them alive: HP, a shield, mitigation, or a full stack.
    """
    if outcome == "unknown":
        return _everything(fact, mechanic)
    if outcome == "low":
        return _took(fact, exact=True)
    if outcome == "raw":
        short = _short(fact, mechanic)
        if short:
            return f"{_took(fact, exact=False)} {short}"
        return " ".join([_took(fact, exact=True), *_heal_check(fact)])
    if cause == "healers":
        return " ".join([_took(fact, exact=True), *_heal_check(fact)])
    if cause == "mitigation":
        seen = _mit_seen(fact)
        if seen is None:
            mit = ""
        elif seen >= 0.995:
            mit = "No mitigation."
        else:
            mit = f"Only {round((1 - seen) * 100)}% mitigation."
        shield = "No shield." if fact.absorb < 1000 else ""
        return " ".join(bit for bit in (_took(fact, exact=False), mit, shield) if bit)
    bits = [_took(fact, exact=False)]
    amped = _amped(fact)
    if amped:
        bits.append(amped)
    if mechanic.requires_personal_mit and fact.role == "tank" and not _personal_mit(fact, pack):
        bits.append("No personal mitigation.")
    beyond = "" if amped else _beyond_role(fact, mechanic)
    bits.append(beyond or _one_shot(fact))
    return " ".join(bit for bit in bits if bit)


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
    if fact.guid == 0 and pack.deathwall is not None:
        return _deathwall(fact, pack.deathwall)
    if fact.guid == 0:
        return Judgment(
            fact=fact,
            mechanic_id=None,
            mechanic="No damage packet",
            outcome="environment",
            happened="Nothing hit them.",
            should_have_been="A death with no hit is the body after a raise, or a wipe tick.",
            went_wrong="No hit.",
            cause="none",
        )
    mechanic = pack.mechanic_for(fact.guid, fact.phase)
    if mechanic is None:
        return Judgment(
            fact=fact,
            mechanic_id=None,
            mechanic=fact.ability,
            outcome="unknown",
            happened=_everything(fact, None),
            should_have_been="This ability is not understood yet.",
            went_wrong=f"{fact.name} died to {fact.ability}.",
            cause="none",
        )
    if fact.clipped_by and (_vuln(fact) or mechanic.marker_owns_clip):
        return _done(fact, mechanic, "fail", _marker_clip(fact, pack), "marker", pack)
    if _vuln(fact):
        return _done(fact, mechanic, "fail", _amp(fact, mechanic), "personal", pack)
    hit = _hit(fact)
    if mechanic.tanks_only and fact.role != "tank":
        return _done(fact, mechanic, "fail", _not_a_tank(fact, mechanic), "personal", pack)
    if mechanic.off_tank and fact.name != mechanic.off_tank:
        return _done(
            fact, mechanic, "fail",
            f"{fact.name} took {mechanic.name}.",
            "personal", pack,
        )
    if mechanic.one_target and fact.stack and fact.stack > 1:
        return _done(
            fact, mechanic, "fail",
            f"{fact.name} ate an extra {mechanic.name}.",
            "personal", pack,
        )
    if mechanic.any_hit_is_fail:
        if mechanic.id == "bright-flare" and (fact.stack or 0) > 1:
            return _done(
                fact, mechanic, "fail",
                f"{fact.name} got clipped by a Bright Flare.",
                "overlap", pack,
            )
        if mechanic.id == "holy-impact":
            return _done(
                fact, mechanic, "fail",
                f"{fact.name} died to comets that were too close.",
                "prey", pack,
            )
        return _done(fact, mechanic, "fail", _personal(fact, mechanic), "personal", pack)
    failed = _failed_moment(mechanic, fact, hit)
    if failed:
        return _done(
            fact, mechanic, "fail",
            _moment_fault(fact, failed),
            failed.cause or "personal", pack,
        )
    if mechanic.id == "skyward-leap" and mechanic.fail_above is not None and hit > mechanic.fail_above:
        return _done(
            fact, mechanic, "fail",
            f"{fact.name} took a second Skyward Leap whose marker holder was already dead.",
            "orphan", pack,
        )
    if mechanic.fail_above is not None and hit > mechanic.fail_above:
        if mechanic.dive_markers:
            wrong, cause = _landing(fact)
            return _done(fact, mechanic, "fail", wrong, cause, pack)
        return _done(
            fact, mechanic, "fail", _oversized(fact, mechanic),
            _oversized_cause(fact, mechanic), pack,
        )
    cap = mechanic.cap_for(fact.role)
    if cap is None:
        return _done(
            fact, mechanic, "unknown",
            f"{fact.name} died to {mechanic.name}.",
            "none", pack,
        )
    if hit <= cap:
        if fact.hp is not None and fact.hp < pack.low_hp:
            return _done(
                fact, mechanic, "low",
                f"{fact.name} was already low.",
                "low", pack,
            )
        if mechanic.requires_personal_mit and fact.role == "tank" and not _personal_mit(fact, pack):
            return _done(
                fact, mechanic, "fail",
                f"{fact.name} died to {mechanic.name} without mitigation.",
                "personal", pack,
            )
        if mechanic.id == "skyward-leap":
            return _done(
                fact, mechanic, "fail", _skyward_marker(fact), _skyward_cause(fact), pack,
            )
        return _done(
            fact, mechanic, "raw", _raw_fault(fact, mechanic), _raw_cause(fact, mechanic), pack,
        )
    if mechanic.id == "skyward-leap":
        return _done(fact, mechanic, "fail", _skyward_clip(fact), "clip", pack)
    return _done(
        fact, mechanic, "fail", _oversized(fact, mechanic),
        _oversized_cause(fact, mechanic), pack,
    )


# A deathwall time is only good to about a second, so Hysteria is matched with this much slack.
_MOMENT_S = 1.5
# Deaths and debuffs this close to the first one are the same first mistake.
_FIRST_S = 1.0


def _own_hysteria(fact: DeathFact) -> bool:
    """They still had Hysteria from the gaze, so they were walked into the wall."""
    for debuff in fact.prior_debuffs:
        if debuff["name"] != fact.name or debuff["debuff"] != "Hysteria":
            continue
        if debuff["phase"] != fact.phase or debuff["t"] > fact.t + _MOMENT_S:
            continue
        until = debuff.get("until")
        if until is None or until >= fact.t - _MOMENT_S:
            return True
    return False


def _deathwall(fact: DeathFact, mechanic: Mechanic) -> Judgment:
    """No killing blow is the arena edge. It is always a mistake."""
    happened = "Nothing hit them."
    if _own_hysteria(fact):
        wrong = f"{fact.name} looked at the gaze and walked into the deathwall with Hysteria."
        happened = "Nothing hit them. They still had Hysteria from the gaze."
    else:
        wrong = f"{fact.name} walked into the deathwall."
    return Judgment(
        fact=fact,
        mechanic_id=mechanic.id,
        mechanic=mechanic.name,
        outcome="fail",
        happened=happened,
        should_have_been=mechanic.should_have_been,
        went_wrong=wrong,
        cause="personal",
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


def clip_mechanic(fact: DeathFact, pack: FightPack) -> Mechanic | None:
    """The marker cast that clipped this player, when the vulnerability came from one."""
    if not fact.clipped_by or fact.clip_guid is None:
        return None
    return pack.mechanic_for(fact.clip_guid, fact.phase)


def marker_owners(fact: DeathFact) -> list[str]:
    """Who owns a marker clip: whoever was out of position.

    A holder belongs on their spot. Anyone else belongs out of reach of every
    spot. With no positions, or when nobody looks out of place, the holders own it.
    """
    holders = list(fact.clipped_by)
    people = holders if fact.name in holders else [*holders, fact.name]
    if all(name in fact.in_spot for name in people):
        out = [name for name in people if not fact.in_spot[name]]
        if out:
            return out
    return holders


def _joined(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _marker_clip(fact: DeathFact, pack: FightPack) -> str:
    source = clip_mechanic(fact, pack)
    cast = source.name if source else "marker"
    holders = list(fact.clipped_by)
    overlap = fact.name in holders
    others = [holder for holder in holders if holder != fact.name]
    people = holders if overlap else [*holders, fact.name]
    out = [name for name in people if fact.in_spot.get(name) is False]
    if out and all(name in fact.in_spot for name in people):
        return _out_of_position(fact.name, others, out, overlap, cast)
    if overlap:
        return f"{fact.name}'s {cast} overlapped {' and '.join(others)}'s."
    plural = "s" if len(holders) > 1 else ""
    return f"{fact.name} was clipped by {_joined(holders)}'s {cast}{plural}."


def _out_of_position(victim: str, others: list[str], out: list[str], overlap: bool, cast: str) -> str:
    """One sentence naming who was out of position, from the victim's side."""
    verb = "overlapped" if overlap else "clipped"
    blamed = [name for name in out if name != victim]
    if victim not in out:
        be = "were" if len(blamed) > 1 else "was"
        return f"{_joined(blamed)} {be} out of position and {verb} {victim}."
    if not blamed:
        if overlap:
            return f"{victim} was out of position and overlapped {_joined(others)}."
        plural = "s" if len(others) > 1 else ""
        return f"{victim} stood in {_joined(others)}'s {cast}{plural}."
    both = " both" if len(blamed) == 1 else ""
    tail = " and overlapped" if overlap else ""
    return f"{victim} and {_joined(blamed)} were{both} out of position{tail}."


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
    if mechanic.id == "burns":
        return f"{name} stood in the fire."
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


def _side(diver: dict) -> str:
    """The half of the arena a diver stood on. Facing east, west is in front of an up arrow."""
    if diver["x"] <= -SIDE_MARGIN:
        return "west"
    if diver["x"] >= SIDE_MARGIN:
        return "east"
    return "north" if diver["y"] < 0 else "south"


def _wrong_arrows(fact: DeathFact) -> list[dict]:
    """Arrow divers in this landing who stood on the other side from their arrow."""
    wrong = []
    for diver in fact.divers:
        if not diver.get("side") or diver.get("x") is None:
            continue
        if diver.get("apart") is None or diver["apart"] > LANDING_REACH:
            continue
        if _side(diver) != diver["side"]:
            wrong.append(diver)
    return wrong


def _sides_known(fact: DeathFact) -> bool:
    if not fact.divers:
        return False
    return all(diver.get("apart") is not None for diver in fact.divers if diver.get("side"))


def _landing(fact: DeathFact) -> tuple[str, str]:
    """Whose dive landing this was.

    Easthogg resolves arrows facing east: an up arrow goes west, a down arrow
    east, and a 2 goes northwest or northeast. An arrow on the wrong side owns
    the landing, and its facing says where that tower went. With no arrow out
    of place, the overlap is a miscommunication.
    """
    name = fact.name
    wrong = _wrong_arrows(fact)
    if wrong:
        mine = next((diver for diver in wrong if diver["name"] == name), None)
        if mine:
            facing = mine.get("facing")
            if facing:
                return f"{name} took the {mine['marker']} {_side(mine)}, facing {facing}.", "arrow"
            return f"{name} took the {mine['marker']} to the {_side(mine)} side.", "arrow"
        owners = " and ".join(diver["name"] for diver in wrong)
        return f"{name} got hit by {owners}'s dive.", "arrow"
    if _sides_known(fact):
        return f"{name} stood in the dive, a miscommunication.", "miscommunication"
    return f"{name} stood in the dive.", "overlap"


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
    if mechanic.id == "eye-of-the-tyrant":
        return "missing"
    if mechanic.category == "tower":
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
        happened=_happened(fact, mechanic, outcome, cause, pack),
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


def _people(names: list[str]) -> str:
    if len(names) > 2:
        return f"{len(names)} players"
    return " and ".join(names)


def empty_owners(item: Judgment) -> list[str]:
    """The players named for an empty tower, without an unnamed group."""
    if item.cause != "empty":
        return []
    return [who for who in item.owners if who not in _EMPTY_GROUPS.values()]


def _hit_by_others(item: Judgment) -> list[str]:
    """Other players who own this death, when the player who died made no mistake.

    A player in the landing of an arrow taken to the wrong side was hit by that diver.
    A player in place for an empty tower was hit by whoever was missing from it.
    """
    if item.cause == "empty":
        owners = empty_owners(item)
    elif item.cause == "arrow":
        owners = [diver["name"] for diver in _wrong_arrows(item.fact)]
    else:
        return []
    if item.fact.name in owners:
        return []
    return owners


def _moment_text(deaths: list[Judgment], debuffs: list[dict], wall_id: str) -> str:
    groups: dict[str, list[str]] = {}
    for item in deaths:
        others = _hit_by_others(item)
        if item.mechanic_id == wall_id:
            verb = "walking into the deathwall"
        elif others:
            verb = f"dying to {' and '.join(others)}'s {item.mechanic}"
        else:
            verb = f"dying to {item.mechanic}"
        names = groups.setdefault(verb, [])
        if item.fact.name not in names:
            names.append(item.fact.name)
    bits = [f"{_people(names)} {verb}" for verb, names in groups.items()]
    by_debuff: dict[str, list[str]] = {}
    for debuff in debuffs:
        names = by_debuff.setdefault(debuff["debuff"], [])
        if debuff["name"] not in names:
            names.append(debuff["name"])
    bits += [f"{name} on {_people(names)}" for name, names in by_debuff.items()]
    if len(bits) == 1:
        return bits[0]
    return ", ".join(bits[:-1]) + f" and {bits[-1]}"


def _mark_first_mistakes(judgments: list[Judgment], pack: FightPack) -> None:
    """The first death, Damage Down, or Hysteria of a pull. Later deaths often cascade from it.

    A deathwall walk after the first mistake is still a mistake, shared with that earlier one.
    A player killed by someone else's mistake is not marked first. The text names whose it was.
    """
    wall_id = pack.deathwall.id if pack.deathwall else "deathwall"
    pulls: dict[int, list[Judgment]] = {}
    for item in judgments:
        pulls.setdefault(item.fact.fight, []).append(item)
    for rows in pulls.values():
        seen: set[tuple] = set()
        debuffs: list[dict] = []
        for item in rows:
            for debuff in item.fact.prior_debuffs:
                key = (debuff["name"], debuff["debuff"], debuff["phase"], debuff["t"])
                if key not in seen:
                    seen.add(key)
                    debuffs.append(debuff)
        moments = [(item.fact.phase, item.fact.t) for item in rows]
        moments += [(debuff["phase"], debuff["t"]) for debuff in debuffs]
        phase, start = min(moments)

        def at_first(where: int, t: float) -> bool:
            return where == phase and t <= start + _FIRST_S

        first_deaths = sorted(
            (item for item in rows if at_first(item.fact.phase, item.fact.t)),
            key=lambda item: (item.fact.t, item.fact.name),
        )
        first_debuffs = sorted(
            (debuff for debuff in debuffs if at_first(debuff["phase"], debuff["t"])),
            key=lambda debuff: (debuff["t"], debuff["name"]),
        )
        phase_name = rows[0].fact.phase_name
        for item in rows:
            if item.fact.phase == phase:
                phase_name = item.fact.phase_name
                break
        text = _moment_text(first_deaths, first_debuffs, wall_id)
        text = f"{text} at {start:.1f}s into {phase_name}"
        for item in rows:
            at_start = at_first(item.fact.phase, item.fact.t)
            item.first = at_start and not _hit_by_others(item)
            item.first_mistake = text
            if at_start or item.mechanic_id != wall_id or _own_hysteria(item.fact):
                continue
            item.went_wrong = f"{item.fact.name} walked into the deathwall after the first mistake."
            item.cause = "after"


def _was(names: list[str]) -> str:
    return f"{_people(names)} {'was' if len(names) == 1 else 'were'}"


# The unnamed owners of an explosion that needs every player.
_EMPTY_GROUPS = {"tower": "Missed soak", "prey": "Prey markers"}


def _mark_empty_soaks(judgments: list[Judgment]) -> None:
    """An explosion that needs every player, where someone was missing.

    A player already dead, or alive and outside every tower, left the soak empty.
    They own the explosion, not the players who were in place. A player who died
    to an earlier empty tower passes it on to whoever left that one empty.
    """
    latest: dict[tuple[int, str], Judgment] = {}
    for item in sorted(judgments, key=lambda row: (row.fact.fight, row.fact.phase, row.fact.t)):
        down, out = item.fact.down, item.fact.unsoaked
        if item.cause in {"tower", "prey"} and (down or out):
            owners: list[str] = []
            for name in down:
                earlier = latest.get((item.fact.fight, name))
                passed = [name]
                if earlier and earlier.cause == "empty":
                    passed = earlier.owners
                elif earlier and earlier.cause in _EMPTY_GROUPS:
                    passed = [_EMPTY_GROUPS[earlier.cause]]
                owners += [who for who in passed if who not in owners]
            owners += [name for name in out if name not in owners]
            item.owners = owners
            _empty_text(item, down, out)
        latest[(item.fact.fight, item.fact.name)] = item


def _empty_text(item: Judgment, down: list[str], out: list[str]) -> None:
    if down and out:
        item.went_wrong = f"{_was(down)} dead and {_was(out)} not in a tower."
    elif down:
        item.went_wrong = f"{_was(down)} already dead, so a tower was empty."
    else:
        item.went_wrong = f"{_was(out)} not in a tower, so it was empty."
    item.cause = "empty"


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
        elif item.cause == "after":
            item.blames = _shares([item.fact.name, "Earlier mistake"])
        elif item.cause == "marker":
            item.blames = _shares(marker_owners(item.fact))
        elif item.cause == "empty":
            if len(item.owners) == 1 and item.owners[0] in _EMPTY_GROUPS.values():
                item.blames = _group(item.owners[0], 2)
            else:
                item.blames = _shares(item.owners)
        elif item.cause == "orphan":
            item.blames = _group("Earlier deaths", 1)
        elif item.cause == "overlap":
            cohort = [other for other in judgments if _same_cast(item, other)]
            item.blames = _shares(_overlap_names(item, cohort))
        elif item.cause == "arrow":
            item.blames = _shares([diver["name"] for diver in _wrong_arrows(item.fact)])
        elif item.cause == "miscommunication":
            cohort = [other for other in judgments if _same_cast(item, other)]
            item.blames = _group("Miscommunication", len(_overlap_names(item, cohort)))
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
    _mark_empty_soaks(judgments)
    _mark_first_mistakes(judgments, pack)
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
