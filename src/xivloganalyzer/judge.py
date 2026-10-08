"""Apply mechanic parameters to extracted facts."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from xivloganalyzer.catalog import FightPack, Mechanic
from xivloganalyzer.extract import DeathFact
from xivloganalyzer.roster import players, pull_players


@dataclass
class Blame:
    """Who owns a death, and how sure that call is.

    100 means one owner. A shared death splits 100 across the people who
    could own it, so pointing at any one of them is a lower number.
    """

    who: str
    confidence: int
    # The dead players this share came through: they were missing, and their death was `who`'s.
    via: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = {"who": self.who, "confidence": int(self.confidence)}
        if self.via:
            payload["via"] = list(self.via)
        return payload


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
    # What decided the owner. See BASES.
    basis: str = ""
    # The pull's first mistake, per mechanic: [{"mechanic", "owners"}]. The same on every death of the pull.
    first_causes: list[dict] = field(default_factory=list)

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
                "basis": self.basis,
                "first": self.first,
                "first_mistake": self.first_mistake,
                "first_causes": [dict(cause) for cause in self.first_causes],
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
    """Full HP, allowing for rounding a max-HP buff."""
    return _known_hp(fact) and fact.hp >= fact.max_hp - max(1, round(fact.max_hp * 0.001))


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


def _beyond_role(fact: DeathFact, mechanic: Mechanic, cleave: bool = False) -> str:
    """A hit bigger than this role takes from the real cast, against the band people live.

    `cleave` is a cast judged a cleave as a whole, where this one hit can be under the cap.
    """
    cap = mechanic.cap_for_stack(fact.role, fact.stack)
    hit = _hit(fact)
    lived = mechanic.lived_for(fact.role)
    if cap is None or not _band(lived) or (hit <= cap and not cleave):
        return ""
    role = _ROLE.get(fact.role, fact.role)
    if hit <= cap:
        return f"The rest of the stack took more. A {role} takes {lived}."
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
    cleave: bool = False,
) -> str:
    """The facts behind the call, not every number in the packet.

    A fail says how hard the hit was and what made it worse. A raw death says
    what would have kept them alive: HP, a shield, mitigation, or a full stack.
    """
    if outcome == "unknown":
        return _everything(fact, mechanic)
    if cause == "self":
        own = _own_damage(fact)
        took = _took(fact, exact=True)
        if own is None:
            return took
        return f"{took} {own['ability']} had taken {_comma(own['amount'])} {own['ago']:g}s before."
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
    beyond = "" if amped else _beyond_role(fact, mechanic, cleave)
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


# A vulnerability this close before the hit, from the same mechanic, came with the hit's own snapshot.
_SAME_CAST_MS = 1500


def _expected_amp(fact: DeathFact, pack: FightPack, mechanic: Mechanic) -> bool:
    """The vulnerability is not a mistake of theirs: it came from a tower or soak they were
    meant to take, or from the killing cast's own snapshot. The hit is then judged on what
    actually went wrong."""
    source = pack.mechanic_named(fact.amp_via, fact.phase) if fact.amp_via else None
    if source is None:
        return False
    if source.category in {"soak", "tower"}:
        return True
    return source.name == mechanic.name and fact.amp_ms is not None and fact.amp_ms <= _SAME_CAST_MS


def _hit(fact: DeathFact) -> int:
    if fact.unmitigated is not None:
        return fact.unmitigated
    return fact.total


def judge_fact(fact: DeathFact, pack: FightPack, cleave: bool | None = None) -> Judgment:
    """One death. `cleave` is the verdict for the whole cast when it hit several
    players: True for a cleave, False for a real share, None to judge this hit alone."""
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
    if fact.orphan:
        return _done(
            fact, mechanic, "fail",
            f"{_people(fact.orphan)} died holding a marker, so its leap fell on someone else.",
            "orphan", pack,
        )
    if fact.clipped_by and (_vuln(fact) or mechanic.marker_owns_clip):
        return _done(fact, mechanic, "fail", _marker_clip(fact, pack), "marker", pack)
    if _vuln(fact) and _redirected(fact, mechanic):
        return _done(fact, mechanic, "fail", f"{fact.name} took the other group's jump.", "redirected", pack)
    if _vuln(fact) and not _expected_amp(fact, pack, mechanic):
        return _done(fact, mechanic, "fail", _amp(fact, mechanic), "personal", pack)
    hit = _hit(fact)
    if fact.stunned_by and fact.role != "tank":
        return _done(
            fact, mechanic, "fail",
            f"The bash on {_joined(fact.stunned_by)} stunned {fact.name} in the cone.",
            "stunned", pack,
        )
    if (
        mechanic.main_tank and fact.main_tank and fact.role == "tank"
        and fact.name != fact.main_tank and fact.main_tank in fact.dead
    ):
        # The main tank was dead, so the other tank had to take it.
        fact.down = [fact.main_tank]
        return _done(fact, mechanic, "fail", "", "redirected", pack)
    if mechanic.covers_dead_tanks and fact.role != "tank" and fact.down:
        # A tank was dead, so their tether fell to someone else.
        return _done(fact, mechanic, "fail", "", "redirected", pack)
    if mechanic.tanks_only and fact.role != "tank":
        return _done(fact, mechanic, "fail", _not_a_tank(fact, mechanic), "personal", pack)
    if mechanic.off_tank and fact.off_tank and fact.name != fact.off_tank:
        if fact.role == "tank" and fact.off_tank in fact.dead:
            # The off tank was dead, so the other tank had to take it.
            fact.down = [fact.off_tank]
            return _done(fact, mechanic, "fail", "", "redirected", pack)
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
        if mechanic.id == "bright-flare" and _flare_overlap(fact):
            return _done(
                fact, mechanic, "fail",
                f"{fact.name} got clipped by a Bright Flare.",
                "overlap", pack,
            )
        if mechanic.id == "holy-impact":
            return _done(fact, mechanic, "fail", *_comets(fact), pack)
        if fact.baited_by:
            return _done(
                fact, mechanic, "fail",
                f"{fact.name} was in the cone {_joined(fact.baited_by)} baited outside the stack.",
                "baited", pack,
            )
        return _done(fact, mechanic, "fail", _personal(fact, mechanic), "personal", pack)
    if mechanic.pairs and fact.group == [fact.name] and (fact.down or fact.unsoaked or fact.doubled):
        return _done(fact, mechanic, "fail", "The ice had no partner.", "missing", pack)
    if mechanic.pairs and len(fact.group) > 1 and fact.down:
        return _done(fact, mechanic, "fail", "The pair took a second ice.", "missing", pack)
    if mechanic.pairs and fact.stacked_by:
        return _done(
            fact, mechanic, "fail",
            f"{_joined(fact.stacked_by)} brought a second ice onto the pair.",
            "stacked", pack,
        )
    if mechanic.one_each and fact.down and len(fact.cohort) < 2:
        return _done(fact, mechanic, "fail", "They took two hits.", "missing", pack)
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
    above = mechanic.fail_above_for(fact.stack)
    if above is not None and hit > above:
        if mechanic.dive_markers:
            wrong, cause = _landing(fact)
            return _done(fact, mechanic, "fail", wrong, cause, pack)
        return _done(
            fact, mechanic, "fail", _oversized(fact, mechanic),
            _oversized_cause(fact, mechanic), pack,
        )
    cap = mechanic.cap_for_stack(fact.role, fact.stack)
    if cap is None:
        return _done(
            fact, mechanic, "unknown",
            f"{fact.name} died to {mechanic.name}.",
            "none", pack,
        )
    within = hit <= cap if cleave is None else not cleave
    if within:
        own = _own_damage(fact)
        if own and mechanic.id == "skyward-leap" and _skyward_cause(fact) == "healers":
            return _done(fact, mechanic, "fail", f"{fact.name} was still low from {own['ability']}.", "self", pack)
        if own and mechanic.id != "skyward-leap":
            return _done(
                fact, mechanic, "low" if fact.hp is not None and fact.hp < pack.low_hp else "raw",
                f"{fact.name} was still low from {own['ability']}.", "self", pack,
            )
        # A tank low from earlier hits of the same buster without mitigation is short the
        # mitigation, not the heals.
        if mechanic.requires_personal_mit and fact.role == "tank" and not _personal_mit(fact, pack):
            return _done(
                fact, mechanic, "fail",
                f"{fact.name} died to {mechanic.name} without mitigation.",
                "personal", pack,
            )
        if fact.hp is not None and fact.hp < pack.low_hp:
            return _done(
                fact, mechanic, "low",
                f"{fact.name} was already low.",
                "low", pack,
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
        _oversized_cause(fact, mechanic), pack, cleave=bool(cleave),
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
    if fact.knocked_by:
        return Judgment(
            fact=fact,
            mechanic_id=mechanic.id,
            mechanic=mechanic.name,
            outcome="fail",
            happened="A landing knocked them back just before they died at the edge.",
            should_have_been=mechanic.should_have_been,
            went_wrong=f"{_joined(fact.knocked_by)}'s landing knocked {fact.name} into the deathwall.",
            cause="knocked",
        )
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


def _cast_verdicts(facts: list[DeathFact], pack: FightPack) -> dict[int, bool]:
    """Share or cleave, once for every death in one stack packet.

    Victims of one packet land on both sides of a role cap through damage
    variance and different roles. The cast is a cleave when its middle victim is
    over their role cap, and every victim gets that verdict. A vulnerability, a
    marker clip, or a hit over `fail_above` is still judged on its own.
    """
    groups: dict[tuple, list[tuple[DeathFact, float]]] = defaultdict(list)
    for fact in facts:
        mechanic = pack.mechanic_for(fact.guid, fact.phase)
        if mechanic is None or not mechanic.scales_with_stack or len(fact.cohort) < 2:
            continue
        if _vuln(fact) or fact.clipped_by:
            continue
        cap = mechanic.cap_for_stack(fact.role, fact.stack)
        above = mechanic.fail_above_for(fact.stack)
        if not cap or (above is not None and _hit(fact) > above):
            continue
        groups[(fact.fight, fact.guid, tuple(sorted(fact.cohort)))].append((fact, _hit(fact) / cap))
    verdicts: dict[int, bool] = {}
    for rows in groups.values():
        if len(rows) < 2:
            continue
        ratios = sorted(ratio for _fact, ratio in rows)
        middle = len(ratios) // 2
        median = ratios[middle] if len(ratios) % 2 else (ratios[middle - 1] + ratios[middle]) / 2
        for fact, _ratio in rows:
            verdicts[id(fact)] = median > 1
    return verdicts


def _redirected(fact: DeathFact, mechanic: Mechanic) -> bool:
    """A cast that alternates groups landed on the group that took the last one.

    They still had the vulnerability from that cast, and they belong to the other
    group, so it was not their cast. Players of the right group were already dead.
    """
    return mechanic.alternating and bool(fact.group) and fact.name not in fact.group and bool(fact.down)


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


def _self_mits(fact: DeathFact) -> list[dict]:
    """Mitigation the player put on themselves, whatever the job: a % cut or a shield."""
    return [
        mit for mit in fact.mitigations
        if mit.get("by_id") is not None and mit.get("by_id") == mit.get("on_id") and mit.get("on") == fact.name
        and (mit.get("amount") or (mit.get("pct") is not None and mit["pct"] < 100))
    ]


def _personal_mit(fact: DeathFact, pack: FightPack) -> bool:
    """They used their own mitigation on this hit. The replay says so for any job.
    Without it, a known name on the packet or a heavily cut hit counts. With no
    multiplier, no buffs, and no replay rows, nothing says they had none, so it
    counts as had."""
    if _self_mits(fact):
        return True
    # With the replay, only what the tank put on themselves is theirs. A co-tank's or a
    # healer's cooldown counts only through the multiplier below.
    if not fact.mitigations and any(name in fact.buffs for name in pack.personal_mit):
        return True
    if fact.multiplier is None:
        return not fact.buffs and not fact.mitigations
    return fact.multiplier <= 0.75


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
    if mechanic.too_much:
        return mechanic.too_much.format(name=name)
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
    if _skyward_cause(fact) == "healers":
        return f"{fact.name} wasn't full for Skyward Leap."
    return f"{fact.name} died to Skyward Leap without mitigation."


def _skyward_clip(fact: DeathFact) -> str:
    return f"{fact.name} got clipped by a Skyward Leap."


def _skyward_cause(fact: DeathFact) -> str:
    """Short of full HP is the healers', when full HP would have lived. Otherwise it needed mitigation."""
    if _known_hp(fact) and not _full(fact) and _landed(fact) < fact.max_hp:
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
    if mechanic.id == "bright-flare" and _flare_overlap(fact):
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


def _own_damage(fact: DeathFact) -> dict | None:
    """The player's own mistake that left them too low for this hit.

    They lived a hit that is always a mistake, such as looking at a gaze or standing
    in a puddle, and without it they would have had the HP to live this one.
    """
    if not fact.self_hits or not _known_hp(fact):
        return None
    hp = sum(hit.get("hp", hit["amount"]) for hit in fact.self_hits)
    shield = sum(hit.get("shield", 0) for hit in fact.self_hits)
    # They could not have had more than full HP back, but the shield their own hit
    # ate would have met this hit on top of that.
    if min(fact.hp + hp, fact.max_hp) + shield < _landed(fact):
        return None
    return max(fact.self_hits, key=lambda hit: hit["amount"])


def _done(
    fact: DeathFact,
    mechanic: Mechanic,
    outcome: str,
    wrong: str,
    cause: str,
    pack: FightPack,
    cleave: bool = False,
) -> Judgment:
    return Judgment(
        fact=fact,
        mechanic_id=mechanic.id,
        mechanic=mechanic.name,
        outcome=outcome,
        happened=_happened(fact, mechanic, outcome, cause, pack, cleave),
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
    """No party mitigation on the hit. Their own cooldowns are taken out first, so a
    tank who used Rampart is not counted as covered by the party. An unknown
    multiplier says nothing, so it adds no share."""
    if fact.multiplier is None:
        return False
    own = 1.0
    for mit in _self_mits(fact):
        if mit.get("pct") is not None and mit["pct"] < 100:
            own *= mit["pct"] / 100
    return fact.multiplier / own >= 0.995


def _people(names: list[str]) -> str:
    if len(names) > 2:
        return f"{len(names)} players"
    return " and ".join(names)


def passes_on(item: Judgment) -> bool:
    """The death belongs to other players: the ones missing from the mechanic, whose drops
    it was, or whose hit stunned them."""
    return item.cause in {"dropped", "marked", "stunned", "knocked", "orphan", "stacked", *_PASSED_ON}


def empty_owners(item: Judgment) -> list[str]:
    """The players named for a mechanic someone else broke, without an unnamed group."""
    if item.cause == "dropped":
        return list(item.fact.dropped_by)
    if item.cause == "marked":
        return list(item.fact.marked)
    if item.cause == "stunned":
        return list(item.fact.stunned_by)
    if item.cause == "knocked":
        return list(item.fact.knocked_by)
    if item.cause == "stacked":
        return list(item.fact.stacked_by)
    if item.cause == "orphan":
        return [who for who in item.owners if who not in GROUP_LABELS]
    if item.cause not in _PASSED_ON:
        return []
    return [who for who in item.owners if who not in GROUP_LABELS]


def _hit_by_others(item: Judgment) -> list[str]:
    """Other players who own this death, when the player who died made no mistake.

    A player in the landing of an arrow taken to the wrong side was hit by that diver.
    A player in place for an empty tower was hit by whoever was missing from it.
    """
    if passes_on(item):
        owners = empty_owners(item)
    elif item.cause == "arrow":
        owners = [diver["name"] for diver in _wrong_arrows(item.fact)]
    else:
        return []
    if item.fact.name in owners:
        return []
    return owners


def _debuff_source(debuff: dict) -> str:
    return str(debuff.get("via") or "").strip().removeprefix("the ")


def _debuff_owner(debuff: dict, pack: FightPack) -> str:
    """Who owns a Damage Down or Hysteria nobody died to: the player it landed on, unless it
    came from a mechanic the party shares, where the debuff does not say who broke it."""
    mechanic = pack.mechanic_named(_debuff_source(debuff), debuff.get("phase"))
    if mechanic is None:
        return debuff["name"]
    if mechanic.scales_with_stack:
        return "Missing bodies"
    if mechanic.needs_everyone:
        return "Missed soak"
    if mechanic.drops is not None:
        return "Prey markers"
    return debuff["name"]


def _moment_debuffs(deaths: list[Judgment], debuffs: list[dict]) -> list[dict]:
    """The debuffs worth naming: not the ones the same cast gave while it killed someone."""
    killed = {item.mechanic.casefold() for item in deaths}
    return [debuff for debuff in debuffs if _debuff_source(debuff).casefold() not in killed]


def _moment_causes(deaths: list[Judgment], debuffs: list[dict], pack: FightPack) -> list[dict]:
    """What the first mistake was, per mechanic, and who owns it."""
    causes: dict[str, list[str]] = {}
    for item in deaths:
        if item.cause == "reset":
            owners = causes.setdefault("Group reset", [])
            if "Group reset" not in owners:
                owners.append("Group reset")
            continue
        named = [blame.who for blame in item.blames if blame.who not in CONTEXT_SHARES]
        owners = causes.setdefault(item.mechanic, [])
        owners += [who for who in named or [item.fact.name] if who not in owners]
    for debuff in _moment_debuffs(deaths, debuffs):
        owners = causes.setdefault(_debuff_source(debuff) or debuff["debuff"], [])
        who = _debuff_owner(debuff, pack)
        if who not in owners:
            owners.append(who)
    return [{"mechanic": mechanic, "owners": owners} for mechanic, owners in causes.items()]


def _moment_text(deaths: list[Judgment], debuffs: list[dict], wall_id: str) -> str:
    groups: dict[str, list[str]] = {}
    for item in deaths:
        others = _hit_by_others(item)
        if item.cause == "reset":
            verb = "walking into the deathwall together to reset"
        elif item.cause == "knocked":
            verb = f"knocked into the deathwall by {' and '.join(others)}'s landing"
        elif item.mechanic_id == wall_id:
            verb = "walking into the deathwall"
        elif others:
            verb = f"dying to {' and '.join(others)}'s {item.mechanic}"
        else:
            verb = f"dying to {item.mechanic}"
        names = groups.setdefault(verb, [])
        if item.fact.name not in names:
            names.append(item.fact.name)
    bits = [f"{_people(names)} {verb}" for verb, names in groups.items()]
    # Each player's debuffs from one source, then players with the same ones together.
    held: dict[tuple[str, str], list[str]] = {}
    for debuff in _moment_debuffs(deaths, debuffs):
        kinds = held.setdefault((_debuff_source(debuff), debuff["name"]), [])
        if debuff["debuff"] not in kinds:
            kinds.append(debuff["debuff"])
    by_debuff: dict[tuple[str, str], list[str]] = {}
    for (source, name), kinds in held.items():
        by_debuff.setdefault((source, " and ".join(kinds)), []).append(name)
    for (source, kinds), names in by_debuff.items():
        bits.append(f"{kinds} on {_people(names)}" + (f" from {source}" if source else ""))
    if len(bits) == 1:
        return bits[0]
    return ", ".join(bits[:-1]) + f" and {bits[-1]}"


@dataclass
class _FirstMoment:
    """The first death, Damage Down, or Hysteria of one pull, plus anything within a second."""

    phase: int
    start: float
    phase_name: str
    deaths: list[Judgment]
    debuffs: list[dict]

    def holds(self, phase: int, t: float) -> bool:
        return phase == self.phase and t <= self.start + _FIRST_S

    def people(self) -> set[str]:
        return {item.fact.name for item in self.deaths} | {debuff["name"] for debuff in self.debuffs}


def _first_moments(judgments: list[Judgment], pack: FightPack) -> dict[int, _FirstMoment]:
    pulls: dict[int, list[Judgment]] = {}
    for item in judgments:
        pulls.setdefault(item.fact.fight, []).append(item)
    found = {}
    for fight, rows in pulls.items():
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
        known = pack.phase(phase)
        phase_name = known.name if known else rows[0].fact.phase_name
        for item in rows:
            if item.fact.phase == phase:
                phase_name = item.fact.phase_name
                break
        moment = _FirstMoment(phase, start, phase_name, [], [])
        moment.deaths = sorted(
            (item for item in rows if moment.holds(item.fact.phase, item.fact.t)),
            key=lambda item: (item.fact.t, item.fact.name),
        )
        moment.debuffs = sorted(
            (debuff for debuff in debuffs if moment.holds(debuff["phase"], debuff["t"])),
            key=lambda debuff: (debuff["t"], debuff["name"]),
        )
        found[fight] = moment
    return found


# Three or more players with no packet this close together, starting the pull, walked in on purpose.
RESET_PLAYERS = 3
RESET_S = 3.0


def _mark_resets(judgments: list[Judgment], firsts: dict[int, "_FirstMoment"], pack: FightPack) -> None:
    """Several players walking into the deathwall together as the pull's first event is an
    agreed reset after something the log does not show, such as a bad opener or a spilled
    drink. It is nobody's mistake, so it has no owner. A later death it left short passes
    on to "Group reset"."""
    wall_id = pack.deathwall.id if pack.deathwall else "deathwall"
    pulls: dict[int, list[Judgment]] = defaultdict(list)
    for item in judgments:
        pulls[item.fact.fight].append(item)
    for fight, rows in pulls.items():
        moment = firsts.get(fight)
        if moment is None or moment.debuffs:
            continue
        walls = [
            item for item in rows
            if item.mechanic_id == wall_id and item.fact.phase == moment.phase
            and moment.start <= item.fact.t <= moment.start + RESET_S and item.cause != "knocked"
        ]
        if len(walls) < RESET_PLAYERS or any(
            item.mechanic_id != wall_id or item.cause == "knocked" for item in moment.deaths
        ):
            continue
        for item in walls:
            item.outcome = "environment"
            item.cause = "reset"
            item.went_wrong = "The party walked into the deathwall together to reset."
            item.happened = "Nothing hit them. Several players walked in at once."
            item.blames = []


def _mark_after_walls(
    judgments: list[Judgment], firsts: dict[int, _FirstMoment], pack: FightPack,
) -> None:
    """A deathwall walk after the first mistake is still a mistake, shared with that earlier one.

    When the first mistake was the walker's own, such as their own Hysteria or Damage
    Down, nobody else shares it.
    """
    wall_id = pack.deathwall.id if pack.deathwall else "deathwall"
    for item in judgments:
        moment = firsts[item.fact.fight]
        if item.mechanic_id != wall_id or item.cause in {"reset", "knocked"} or moment.holds(item.fact.phase, item.fact.t):
            continue
        if _own_hysteria(item.fact) or _only_own_before(item, judgments):
            continue
        item.went_wrong = f"{item.fact.name} walked into the deathwall after the first mistake."
        item.cause = "after"


def _only_own_before(item: Judgment, judgments: list[Judgment]) -> bool:
    """Every death and cascade debuff earlier in the pull was this player's own."""
    when = (item.fact.phase, item.fact.t)
    names = {
        other.fact.name for other in judgments
        if other.fact.fight == item.fact.fight and (other.fact.phase, other.fact.t) < when
    }
    names |= {
        debuff["name"] for debuff in item.fact.prior_debuffs
        if (debuff["phase"], debuff["t"]) < when
    }
    return names == {item.fact.name}


def _mark_first_mistakes(
    judgments: list[Judgment], firsts: dict[int, _FirstMoment], pack: FightPack,
) -> None:
    """The first death, Damage Down, or Hysteria of a pull. Later deaths often cascade from it.

    A player killed by someone else's mistake is not marked first. The text names whose it was.
    """
    wall_id = pack.deathwall.id if pack.deathwall else "deathwall"
    texts = {
        fight: f"{_moment_text(moment.deaths, moment.debuffs, wall_id)} "
        f"at {moment.start:.1f}s into {moment.phase_name}"
        for fight, moment in firsts.items()
    }
    causes = {fight: _moment_causes(moment.deaths, moment.debuffs, pack) for fight, moment in firsts.items()}
    for item in judgments:
        moment = firsts[item.fact.fight]
        item.first = moment.holds(item.fact.phase, item.fact.t) and not _hit_by_others(item) and item.cause != "reset"
        item.first_mistake = texts[item.fact.fight]
        item.first_causes = causes[item.fact.fight]


def _was(names: list[str]) -> str:
    return f"{_people(names)} {'was' if len(names) == 1 else 'were'}"


# The unnamed owners of an explosion that needs every player.
_EMPTY_GROUPS = {"tower": "Missed soak", "prey": "Prey markers"}
# Labels that stand in for players the log did not name.
GROUP_LABELS = frozenset({
    *_EMPTY_GROUPS.values(),
    "Group reset",
    "Missing bodies",
    "Miscommunication",
    "Out of position",
    "Another player",
    "Assigned mitigation",
    "Earlier deaths",
    "Healers",
})
# Causes whose owners are the players who were missing, or whoever owned their deaths.
_PASSED_ON = frozenset({"empty", "redirected", "missing"})


def _mark_empty_soaks(judgments: list[Judgment]) -> None:
    """A mechanic that needs certain players, where someone was missing.

    A player already dead, or alive and outside every tower, left the soak empty.
    They own the explosion, not the players who were in place. Who owns each dead
    player's gap is settled with the blame, in time order (`_missing_owners`).
    """
    for item in judgments:
        down, out, doubled = item.fact.down, item.fact.unsoaked, item.fact.doubled
        if item.cause in {"tower", "prey"} and (down or out or doubled):
            _empty_text(item, down, out, doubled)
        elif item.cause == "missing" and (down or out or doubled):
            item.went_wrong = _missing_text(item, down, out, doubled)
        elif item.cause == "redirected" and item.fact.group:
            item.went_wrong = f"{_was(down)} dead, so {item.mechanic} hit the other group."
        elif item.cause == "redirected":
            took = "had to take" if len(down) == 1 else "took"
            item.went_wrong = f"{_was(down)} dead, so {item.fact.name} {took} {item.mechanic}."


def _missing_text(item: Judgment, down: list[str], out: list[str], doubled: list[str] = ()) -> str:
    """One sentence: how short the stack was, and who was missing from it."""
    stack = item.went_wrong if item.went_wrong.startswith(("The ", "They ")) else "The stack was short."
    stack = stack.rstrip(".")
    if sum(map(bool, (down, out, doubled))) > 1:
        why = f"{_people([*down, *out, *doubled])} were missing"
    elif down:
        why = f"{_was(down)} already dead"
    elif out:
        why = f"{_was(out)} not in it"
    else:
        why = f"{_was(doubled)} in another one"
    return f"{stack} because {why}."


def _empty_text(item: Judgment, down: list[str], out: list[str], doubled: list[str]) -> None:
    if item.fact.marked:
        item.went_wrong = f"{_was(down)} dead with Prey, so the comets piled up."
    elif sum(map(bool, (down, out, doubled))) > 1:
        bits = []
        if down:
            bits.append(f"{_was(down)} dead")
        if out:
            bits.append(f"{_was(out)} out of the towers")
        if doubled:
            bits.append(f"{_people(doubled)} shared one")
        item.went_wrong = f"{_joined(bits)}."
    elif down:
        item.went_wrong = f"{_was(down)} already dead, so a tower was empty."
    elif out:
        item.went_wrong = f"{_was(out)} not in a tower, so it was empty."
    else:
        item.went_wrong = f"{_people(doubled)} took one tower, so another was empty."
    item.cause = "empty"


def _comets(fact: DeathFact) -> tuple[str, str]:
    """Whose comets exploded. A prey player already dead is passed on by `_mark_empty_soaks`."""
    owners = fact.dropped_by
    if len(owners) == 1:
        return f"{owners[0]} dropped two comets too close.", "dropped"
    if owners:
        return f"{_joined(owners)} dropped their comets too close.", "dropped"
    if fact.marked and not fact.down:
        return f"{_joined(fact.marked)} had Prey, and the comets landed too close.", "marked"
    return f"{fact.name} died to comets that were too close.", "prey"


def _same_cast(left: Judgment, right: Judgment) -> bool:
    return (
        left.cause == right.cause
        and left.mechanic_id == right.mechanic_id
        and left.fact.fight == right.fact.fight
        and abs(left.fact.t - right.fact.t) <= 1.5
    )


def _flare_overlap(fact: DeathFact) -> bool:
    """One orb hit more than one player. Without the packet, several hits at once."""
    if fact.cohort:
        return len(fact.cohort) > 1
    return (fact.stack or 0) > 1


def _overlap_names(item: Judgment, cohort: list[Judgment]) -> list[str]:
    if item.mechanic_id == "bright-flare" and item.fact.cohort:
        return [item.fact.name] + [name for name in item.fact.cohort if name != item.fact.name]
    if item.mechanic_id == "lightning-storm" and len(item.fact.cohort) > 1:
        # One bolt on two players: both of them, whoever lived.
        return [item.fact.name] + [name for name in item.fact.cohort if name != item.fact.name]
    ordered = sorted(cohort, key=lambda other: (other.fact.name != item.fact.name, other.fact.name))
    names: list[str] = []
    for other in ordered:
        if other.fact.name not in names:
            names.append(other.fact.name)
    stack = item.fact.stack or 0
    if item.mechanic_id == "bright-flare" and stack > len(names):
        names.extend("Another player" for _ in range(stack - len(names)))
    return names


class Roster(list):
    """The report's players as (name, role) pairs, and who played each pull.

    A substitute, or a player who swapped jobs, has a role only in the pulls
    they played on that job, so a healer is only blamed for pulls they healed.
    """

    def __init__(self, rows: list[tuple[str, str]], pulls: dict[int, list[tuple[str, str]]] | None = None):
        super().__init__(rows)
        self.pulls = pulls or {}

    def for_pull(self, fight: int) -> list[tuple[str, str]]:
        return self.pulls.get(fight) or list(self)


def roster_from_meta(meta: dict, pack: FightPack) -> Roster:
    """Player name and role from the report's friendlies, per pull."""
    rows: list[tuple[str, str]] = []
    for actor in players(meta):
        row = (actor["name"].strip(), pack.role_of(actor.get("type") or ""))
        if row not in rows:
            rows.append(row)
    pulls: dict[int, list[tuple[str, str]]] = {}
    for fight in meta.get("fights") or []:
        fight_id = int(fight["id"])
        pulls[fight_id] = [
            (actor["name"].strip(), pack.role_of(actor.get("type") or ""))
            for actor in pull_players(meta, fight_id)
        ]
    return Roster(rows, pulls)


def _roster_from_facts(facts: list[DeathFact]) -> Roster:
    seen: dict[str, str] = {}
    for fact in facts:
        seen.setdefault(fact.name, fact.role)
    return Roster(list(seen.items()))


def _healers(roster: list[tuple[str, str]]) -> list[str]:
    return sorted({name for name, role in roster if role == "healer"})


def _death_owners(item: Judgment) -> list[str]:
    """Who owns this death, without the shares that only sit beside an owner."""
    return list(_death_shares(item))


def _death_shares(item: Judgment) -> dict[str, float]:
    """Who owns this death and how much of it, without the shares that only sit beside an owner."""
    if item.cause == "reset":
        return {"Group reset": 1.0}
    named = [(blame.who, blame.confidence) for blame in item.blames if blame.who not in CONTEXT_SHARES]
    if not named:
        return {item.fact.name: 1.0}
    total = sum(share for _who, share in named) or len(named)
    return {who: (share or 1) / total for who, share in named}


Weights = dict[str, float]


def _add(weights: Weights, who: str, part: float) -> None:
    weights[who] = weights.get(who, 0.0) + part


def _passed_on(
    item: Judgment, names: list[str], latest: dict[tuple[int, str], Judgment],
    via: dict[str, list[str]] | None = None,
) -> Weights:
    """Players who were missing because they were dead, each replaced by whoever owned that death.

    Each missing player is one share. A player who died to their own mistake keeps
    it. A player killed by someone else's mistake, a healer's missed heal included,
    passes it on to that death's owners, split the way that death was.
    `via` collects, for each owner, the dead players it came through.
    """
    weights: Weights = {}
    for name in names:
        earlier = latest.get((item.fact.fight, name))
        passed = _death_shares(earlier) if earlier is not None else {name: 1.0}
        for who, part in passed.items():
            _add(weights, who, part)
            if via is not None and who != name:
                came = via.setdefault(who, [])
                if name not in came:
                    came.append(name)
    return weights


def _missing_owners(
    item: Judgment, latest: dict[tuple[int, str], Judgment], via: dict[str, list[str]] | None = None,
) -> Weights:
    """Who left a mechanic short: the dead, passed on to their owners, then the living who were elsewhere."""
    weights = _passed_on(item, item.fact.down, latest, via)
    for name in [*item.fact.unsoaked, *item.fact.doubled]:
        _add(weights, name, 1.0)
    return weights


def _healers_at(
    item: Judgment, healers: list[str], latest: dict[tuple[int, str], Judgment],
    via: dict[str, list[str]] | None = None,
) -> Weights:
    """The healers who could heal this hit. A healer already dead passes their share
    on to whoever owned that healer's death."""
    weights: Weights = {}
    for healer in healers:
        if healer in item.fact.dead:
            for who, part in _passed_on(item, [healer], latest, via).items():
                _add(weights, who, part)
        else:
            _add(weights, healer, 1.0)
    return weights


def _weighted(weights: Weights) -> list[Blame]:
    """Shares of 100 in proportion to each owner's weight, rounded down."""
    total = sum(weights.values())
    if not total:
        return []
    return [Blame(who, max(1, int(100 * part / total + 1e-9))) for who, part in weights.items()]


# Shares that sit beside an owner rather than owning a death.
CONTEXT_SHARES = frozenset({"Party mitigation", "Earlier damage", "Earlier mistake"})


def _order(item: Judgment) -> tuple:
    """Time order inside a pull, to the millisecond when the log has it."""
    fact = item.fact
    return (fact.fight, fact.phase, fact.t if fact.ts is None else fact.ts / 1000, fact.t, fact.name)


def _assign_blame(
    judgments: list[Judgment], pack: FightPack, roster: Roster,
) -> None:
    latest: dict[tuple[int, str], Judgment] = {}
    for item in sorted(judgments, key=_order):
        healers = _healers(roster.for_pull(item.fact.fight))
        _blame(item, judgments, pack, healers, latest)
        latest[(item.fact.fight, item.fact.name)] = item


def _blame(
    item: Judgment,
    judgments: list[Judgment],
    pack: FightPack,
    healers: list[str],
    latest: dict[tuple[int, str], Judgment],
) -> None:
    """Who owns this death, from the rule that judged it, and what decided it."""
    via: dict[str, list[str]] = {}
    _owners_for(item, judgments, pack, healers, latest, via)
    for blame in item.blames:
        blame.via = via.get(blame.who, [])
    item.basis = _basis(item)


def _owners_for(
    item: Judgment,
    judgments: list[Judgment],
    pack: FightPack,
    healers: list[str],
    latest: dict[tuple[int, str], Judgment],
    via: dict[str, list[str]],
) -> None:
    if item.cause == "none":
        item.blames = []
    elif item.cause in {"personal", "self"}:
        item.blames = _shares([item.fact.name])
    elif item.cause == "after":
        item.blames = _shares([item.fact.name, "Earlier mistake"])
    elif item.cause == "marker":
        item.blames = _shares(marker_owners(item.fact))
    elif item.cause in {"dropped", "marked"}:
        item.blames = _shares(empty_owners(item))
    elif item.cause in {"empty", "redirected"}:
        # A redirected jump follows the marker, so the living players of that group did nothing wrong.
        if item.cause == "redirected":
            weights = _passed_on(item, item.fact.down, latest, via)
        else:
            weights = _missing_owners(item, latest, via)
        item.owners = list(weights)
        if len(item.owners) == 1 and item.owners[0] in GROUP_LABELS:
            item.blames = _group(item.owners[0], 2)
        else:
            item.blames = _weighted(weights)
    elif item.cause == "orphan" and item.fact.orphan:
        weights = _passed_on(item, item.fact.orphan, latest, via)
        item.owners = list(weights)
        item.blames = _weighted(weights)
    elif item.cause == "orphan":
        item.blames = _group("Earlier deaths", 1)
    elif item.cause == "stunned":
        item.blames = _shares(list(item.fact.stunned_by))
    elif item.cause == "knocked":
        item.blames = _shares(list(item.fact.knocked_by))
    elif item.cause == "stacked":
        item.blames = _shares(list(item.fact.stacked_by))
    elif item.cause == "baited":
        item.blames = _shares([item.fact.name, *item.fact.baited_by])
    elif item.cause == "overlap":
        cohort = [other for other in judgments if _same_cast(item, other)]
        item.blames = _shares(_overlap_names(item, cohort))
    elif item.cause == "arrow":
        item.blames = _shares([diver["name"] for diver in _wrong_arrows(item.fact)])
    elif item.cause == "miscommunication":
        cohort = [other for other in judgments if _same_cast(item, other)]
        item.blames = _group("Miscommunication", len(_overlap_names(item, cohort)))
    elif item.cause == "healers":
        item.blames = _weighted(_healers_at(item, healers, latest, via) or {"Healers": 1.0})
    elif item.cause == "mitigation":
        item.blames = _group("Assigned mitigation", 2)
    elif item.cause == "tower":
        item.blames = _group("Missed soak", 2)
    elif item.cause == "prey":
        item.blames = _group("Prey markers", 2)
    elif item.cause == "clip":
        item.blames = _group("Out of position", 3)
    elif item.cause == "missing" and (item.fact.down or item.fact.unsoaked or item.fact.doubled):
        weights = _missing_owners(item, latest, via)
        item.owners = list(weights)
        item.blames = _weighted(weights)
    elif item.cause == "missing":
        if not item.fact.stack:
            item.blames = _group("Missing bodies", 2)
        else:
            mechanic = pack.mechanic_for(item.fact.guid, item.fact.phase)
            typical = mechanic.typical_targets if mechanic and mechanic.typical_targets else 0
            missing = max(typical - (item.fact.stack or 0), 1)
            item.blames = _group("Missing bodies", missing)
    elif item.cause == "resolve":
        weights = _healers_at(item, healers, latest, via) or {"Healers": 1.0}
        if _no_party_mit(item.fact):
            _add(weights, "Party mitigation", 1.0)
        item.blames = _weighted(weights)
    elif item.cause == "low":
        weights = _healers_at(item, healers, latest, via) or {"Healers": 1.0}
        _add(weights, "Earlier damage", 1.0)
        item.blames = _weighted(weights)
    else:
        item.blames = []


# What decided who owns a death, from strongest to weakest evidence.
BASES = {
    "hit": "their own damage packet: its size, the HP and mitigation behind it",
    "debuff": "a status: a marker, a number, or a damage amp",
    "position": "where people stood when it resolved",
    "hit-list": "who the cast hit, and who it should have hit",
    "role": "a role rule: the healers or the party's mitigation, with nobody else to name",
    "no-packet": "no damage packet: the deathwall",
    "label": "nobody could be named, so a group label holds it",
}


def _basis(item: Judgment) -> str:
    """What decided the owner. A call whose owners are all group labels is `label`."""
    cause = item.cause
    named = [blame.who for blame in item.blames if blame.who not in CONTEXT_SHARES | GROUP_LABELS]
    if cause == "none" or not item.blames:
        return ""
    if not named:
        return "label"
    if cause == "knocked":
        return "hit-list"
    if item.fact.guid == 0 or cause == "after":
        return "no-packet"
    if cause in {"personal", "self"}:
        return "debuff" if _vuln(item.fact) or item.went_wrong.endswith("damage amp.") else "hit"
    if cause == "marker":
        people = [*item.fact.clipped_by, item.fact.name]
        return "position" if all(name in item.fact.in_spot for name in people) else "debuff"
    if cause in {"dropped", "overlap", "arrow", "baited", "stacked"}:
        return "position"
    if cause == "stunned":
        return "debuff"
    if cause in {"marked"}:
        return "debuff"
    if cause in {"empty", "redirected", "missing"}:
        return "hit-list"
    if cause == "orphan":
        return "position"
    if cause in {"healers", "resolve", "low"}:
        return "role"
    return "label"


def judge_report(
    facts: list[DeathFact],
    pack: FightPack,
    roster: list[tuple[str, str]] | None = None,
) -> list[Judgment]:
    verdicts = _cast_verdicts(facts, pack)
    judgments = [judge_fact(fact, pack, verdicts.get(id(fact))) for fact in facts]
    if not judgments:
        return judgments
    _mark_empty_soaks(judgments)
    firsts = _first_moments(judgments, pack)
    _mark_resets(judgments, firsts, pack)
    _mark_after_walls(judgments, firsts, pack)
    if roster is None or not len(roster):
        people = _roster_from_facts(facts)
    elif isinstance(roster, Roster):
        people = roster
    else:
        people = Roster(list(roster))
    _assign_blame(judgments, pack, people)
    _mark_first_mistakes(judgments, firsts, pack)
    return judgments


def write_judgments(report: Path, judgments: list[Judgment]) -> Path:
    path = report / "judgments.json"
    path.write_text(
        json.dumps([item.to_dict() for item in judgments], indent=2),
        encoding="utf-8",
    )
    return path
