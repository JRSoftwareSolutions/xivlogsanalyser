"""Rules the pull-by-pull blame audit settled, pinned on the saved logs."""

import copy
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.extract import ROW_RE, _load_events, extract_report, off_tank
from xivloganalyzer.inputs import check_inputs, read_inputs
from xivloganalyzer.judge import judge_report, roster_from_meta

ROOT = Path(__file__).resolve().parents[1]
CODES = ("XVz8bCqgPw1KRh9d", "8DYNHQx4C7ytdLb9", "3wzL6x4VHTmvNkhq")
PACK = load_pack(ROOT / "fights" / "dsr")
_CACHE: dict[str, tuple] = {}


def _judged(code):
    if code not in _CACHE:
        report = ROOT / "data" / code
        meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
        skipped: list[dict] = []
        facts = extract_report(report, PACK, skipped)
        judgments = judge_report(facts, PACK, roster_from_meta(meta, PACK))
        _CACHE[code] = (report, meta, facts, skipped, judgments)
    return _CACHE[code]


def _one(code, fight, name, mechanic):
    found = [
        item for item in _judged(code)[4]
        if item.fact.fight == fight and item.fact.name == name and item.mechanic == mechanic
    ]
    assert len(found) == 1, (code, fight, name, mechanic, len(found))
    return found[0]


def _owners(item):
    return [(blame.who, blame.confidence) for blame in item.blames]


class StrengthTowersTest(unittest.TestCase):
    """The Eternal Conviction around 63s is the Strength towers going off. It is never raw."""

    def test_no_eternal_conviction_death_is_raw(self):
        for code in CODES:
            towers = [item for item in _judged(code)[4] if item.mechanic_id == "eternal-conviction"]
            self.assertTrue(towers, code)
            self.assertEqual(Counter(item.outcome for item in towers), {"fail": len(towers)}, code)

    def test_strength_towers_are_owned_by_whoever_left_a_tower_empty(self):
        for code in CODES:
            for item in _judged(code)[4]:
                if item.mechanic_id != "eternal-conviction" or item.fact.t >= 100:
                    continue
                self.assertIn(item.cause, {"empty", "tower"}, (code, item.fact.fight, item.fact.name))
                self.assertTrue(item.blames, (code, item.fact.fight, item.fact.name))

    def test_with_the_soak_file_every_strength_tower_names_its_owner(self):
        # The Conviction 25567 file was fetched from the FFLogs API. Pull 24: Spring was alive and not in a tower.
        for code in CODES:
            for item in _judged(code)[4]:
                if item.mechanic_id == "eternal-conviction":
                    self.assertNotIn("Missed soak", [blame.who for blame in item.blames], (code, item.fact.fight))
        tower = _one("XVz8bCqgPw1KRh9d", 24, "Kiara Blaiddyd", "Eternal Conviction")
        self.assertEqual(_owners(tower), [("Spring Nymphar", 100)])

    def test_a_tower_with_no_hit_list_says_what_it_was_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "XVz8bCqgPw1KRh9d"
            shutil.copytree(ROOT / "data" / "XVz8bCqgPw1KRh9d", report)
            (report / "abilities" / "ab_25567.json").unlink()
            meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
            skipped: list[dict] = []
            facts = extract_report(report, PACK, skipped)
            judgments = judge_report(facts, PACK, roster_from_meta(meta, PACK))
            unnamed = [item for item in judgments if item.mechanic_id == "eternal-conviction" and item.cause == "tower"]
            self.assertTrue(unnamed)
            for item in unnamed:
                self.assertIn("ability 25567", item.fact.missing)
                self.assertEqual(_owners(item), [("Missed soak", 50)])
            guids = {row["guid"] for row in check_inputs(report, PACK, meta, facts, skipped)["abilities"]}
            self.assertIn(25567, guids)


class CastVerdictTest(unittest.TestCase):
    """A stack packet is a share or a cleave once for the whole cast."""

    def test_every_victim_of_a_cleaved_cast_failed(self):
        cast = [
            item for item in _judged("XVz8bCqgPw1KRh9d")[4]
            if item.fact.fight == 35 and item.mechanic_id == "sacred-sever" and item.fact.t < 113
        ]
        self.assertEqual(sorted(item.fact.name for item in cast), ["Kiara Blaiddyd", "Kite Noodle", "Loki Doki"])
        for item in cast:
            self.assertEqual(item.outcome, "fail")
            # The jump was short: the group stood about 31 yalms from Ser Zephirin instead of 34-35.
            self.assertEqual(item.went_wrong, f"{item.fact.name} stood too close to Ser Zephirin's landing.")
            self.assertRegex(item.happened, r"A (tank|healer|DPS) takes about")
        kite = next(item for item in cast if item.fact.name == "Kite Noodle")
        self.assertIn("The rest of the stack took more.", kite.happened)

    def test_no_packet_is_split_between_a_share_and_a_cleave(self):
        for code in CODES:
            casts: dict[tuple, set[bool]] = {}
            for item in _judged(code)[4]:
                fact = item.fact
                mechanic = PACK.mechanic_for(fact.guid, fact.phase)
                if mechanic is None or not mechanic.scales_with_stack or len(fact.cohort) < 2:
                    continue
                if fact.clipped_by or any("Vulnerability" in buff for buff in fact.buffs):
                    continue
                if item.cause not in {"personal", "resolve", "missing"}:
                    continue
                cleaved = item.went_wrong.endswith(("got cleaved.", "stood too close to Ser Zephirin's landing."))
                casts.setdefault((fact.fight, fact.guid, tuple(sorted(fact.cohort))), set()).add(cleaved)
            split = {key: seen for key, seen in casts.items() if len(seen) > 1}
            self.assertEqual(split, {}, code)


class DragonsRageStackTest(unittest.TestCase):
    """Everyone without a Skyward Leap marker stacks, both tanks too. A short stack names who was not in it."""

    def test_own_puddle_that_ate_the_shield_comes_before_the_missing_player(self):
        # Gigachad stood in a Dimensional Collapse puddle instead of the stack, but Spring
        # stood in one too. It ate her 17k shield at full HP; with it she would have lived.
        spring = _one("3wzL6x4VHTmvNkhq", 33, "Spring Nymphar", "Dragon's Rage")
        self.assertEqual(spring.fact.unsoaked, ["Absolute Gigachad"])
        self.assertEqual(spring.fact.self_hits[0]["shield"], 17074)
        self.assertEqual((spring.outcome, spring.cause), ("raw", "self"))
        self.assertEqual(_owners(spring), [("Spring Nymphar", 100)])

    def test_a_living_player_away_from_the_stack_owns_it(self):
        for code in CODES:
            for item in _judged(code)[4]:
                if item.mechanic_id == "dragons-rage" and item.cause == "missing" and item.fact.unsoaked and not item.fact.down:
                    self.assertEqual([who for who, _share in _owners(item)], item.fact.unsoaked, (code, item.fact.fight))

    def test_a_dead_player_passes_it_on(self):
        loki = _one("3wzL6x4VHTmvNkhq", 17, "Loki Doki", "Dragon's Rage")
        self.assertEqual(loki.fact.down, ["Spring Nymphar"])
        self.assertEqual(_owners(loki), [("Spring Nymphar", 100)])

    def test_marker_holders_are_not_missing(self):
        for code in CODES:
            for item in _judged(code)[4]:
                if item.mechanic_id == "dragons-rage" and item.cause == "missing":
                    self.assertNotIn("Missing bodies", [blame.who for blame in item.blames], (code, item.fact.fight))


class ShortStackTest(unittest.TestCase):
    """The role cap is for a full stack. The same cast split fewer ways is a short stack, owned by who was missing."""

    def test_a_lone_jump_at_the_normal_total_is_a_short_share(self):
        kite = _one("8DYNHQx4C7ytdLb9", 36, "Kite Noodle", "Sacred Sever")
        self.assertEqual(kite.fact.stack, 1)
        self.assertEqual((kite.outcome, kite.cause), ("raw", "missing"))
        self.assertEqual(sorted(blame.who for blame in kite.blames), ["Absolute Gigalad", "Kitana Kahn", "Spring Nymphar"])

    def test_a_dragons_rage_pair_is_a_short_stack(self):
        for name in ("Kite Noodle", "Spring Nymphar"):
            item = _one("3wzL6x4VHTmvNkhq", 38, name, "Dragon's Rage")
            self.assertEqual((item.outcome, item.cause), ("raw", "missing"))
            # Loki was just raised (Transcendent), so his gap passes on to his own Heavy Impact death.
            self.assertIn("Loki Doki", item.fact.down)

    def test_a_full_stack_far_over_the_share_is_still_too_close(self):
        for name in ("Kite Noodle", "Spring Nymphar", "Absolute Gigachad"):
            item = _one("3wzL6x4VHTmvNkhq", 50, name, "Sacred Sever")
            self.assertEqual(item.outcome, "fail")


class GroupResetTest(unittest.TestCase):
    """Several players walking into the wall together as the pull's first event agreed to reset."""

    def test_a_group_walk_first_is_nobodys_mistake(self):
        # Pull 33's five wall deaths without the landing that knocked them there: a group walk.
        facts = [copy.deepcopy(fact) for fact in _judged("8DYNHQx4C7ytdLb9")[2] if fact.fight == 33]
        for fact in facts:
            fact.knocked_by = []
        rows = judge_report(facts, PACK, roster_from_meta(_judged("8DYNHQx4C7ytdLb9")[1], PACK))
        resets = [item for item in rows if item.cause == "reset"]
        self.assertEqual(len(resets), 5)
        for item in resets:
            self.assertEqual(item.outcome, "environment")
            self.assertEqual(item.blames, [])
            self.assertFalse(item.first)
        self.assertEqual(rows[0].first_causes, [{"mechanic": "Group reset", "owners": ["Group reset"]}])

    def test_a_knockback_into_the_wall_is_not_a_reset(self):
        # Gigalad's circle landed in the north stack and knocked five players into the wall.
        rows = [item for item in _judged("8DYNHQx4C7ytdLb9")[4] if item.fact.fight == 33 and item.fact.t < 40]
        walls = [item for item in rows if item.mechanic_id == "deathwall"]
        self.assertEqual(len(walls), 5)
        for item in walls:
            self.assertEqual((item.outcome, item.cause, item.basis), ("fail", "knocked", "hit-list"))
            self.assertEqual(_owners(item), [("Absolute Gigalad", 100)])
            self.assertEqual(item.went_wrong, f"Absolute Gigalad's landing knocked {item.fact.name} into the deathwall.")

    def test_a_wall_after_a_mistake_is_still_a_fail(self):
        walls = [
            item for item in _judged("8DYNHQx4C7ytdLb9")[4]
            if item.fact.fight == 7 and item.mechanic_id == "deathwall"
        ]
        self.assertTrue(walls)
        self.assertTrue(all(item.outcome == "fail" for item in walls))


class OffTankTest(unittest.TestCase):
    def test_the_off_tank_is_the_tank_heel_lands_on(self):
        for code in CODES:
            report, meta = _judged(code)[:2]
            self.assertEqual(off_tank(report, meta, PACK, _load_events(report)), "Absolute Gigachad", code)

    def test_heel_on_the_main_tank_belongs_to_the_dead_off_tank(self):
        heel = _one("3wzL6x4VHTmvNkhq", 20, "Absolute Gigalad", "Heavenly Heel")
        self.assertEqual(heel.outcome, "fail")
        self.assertEqual(heel.cause, "redirected")
        self.assertEqual(heel.went_wrong, "Absolute Gigachad was dead, so Absolute Gigalad had to take Heavenly Heel.")
        self.assertEqual(_owners(heel), [("Absolute Gigachad", 100)])


class IcePairsTest(unittest.TestCase):
    def test_a_lone_ice_belongs_to_the_partners_who_doubled_up(self):
        kitana = _one("8DYNHQx4C7ytdLb9", 9, "Kitana Kahn", "Hiemal Storm")
        self.assertEqual(kitana.cause, "missing")
        self.assertEqual(kitana.fact.doubled, ["Loki Doki", "Spring Nymphar"])
        self.assertEqual(_owners(kitana), [("Loki Doki", 50), ("Spring Nymphar", 50)])

    def test_a_lone_ice_after_a_partner_died_passes_to_that_death(self):
        loki = _one("8DYNHQx4C7ytdLb9", 5, "Loki Doki", "Hiemal Storm")
        self.assertEqual(loki.cause, "missing")
        self.assertEqual(loki.fact.down, ["Speed Panda"])
        self.assertNotIn("Loki Doki", [blame.who for blame in loki.blames])


class MaxHpTest(unittest.TestCase):
    def test_max_hp_comes_from_the_killing_hits_and_scales_with_buffs(self):
        _report, _meta, facts, _skipped, _judgments = _judged("8DYNHQx4C7ytdLb9")
        seen = {(fact.name, fact.max_hp) for fact in facts}
        self.assertIn(("Speed Panda", 68259), seen)
        self.assertNotIn(("Speed Panda", 32112), seen)
        # Gigalad's max HP is 99,223, and 119,068 under Thrill of Battle.
        self.assertEqual({hp for name, hp in seen if name == "Absolute Gigalad"}, {99223, 119068})


class InputsTest(unittest.TestCase):
    def test_every_death_row_is_judged_or_skipped_with_a_reason(self):
        for code in CODES:
            report, _meta, facts, skipped, _judgments = _judged(code)
            rows = sum(
                len(ROW_RE.findall(item.get("html") or ""))
                for item in json.loads((report / "deaths-html.json").read_text(encoding="utf-8"))
            )
            self.assertEqual(len(facts) + len(skipped), rows, code)
            self.assertTrue(all(row["reason"] for row in skipped), code)

    def test_pulls_missing_from_the_fight_list_are_reported(self):
        _report, _meta, _facts, skipped, _judgments = _judged("8DYNHQx4C7ytdLb9")
        missing = [row for row in skipped if row["reason"] == "the pull is not in fights.json"]
        self.assertEqual(len(missing), 24)
        self.assertEqual(sorted({row["fight"] for row in missing}), [8, 32, 47])

    def test_saved_inputs_match_a_fresh_check(self):
        for code in CODES:
            report, meta, facts, skipped, _judgments = _judged(code)
            self.assertEqual(read_inputs(report), check_inputs(report, PACK, meta, facts, list(skipped)), code)

    def test_every_saved_log_has_every_ability_file(self):
        for code in CODES:
            self.assertEqual(read_inputs(_judged(code)[0])["abilities"], [], code)


if __name__ == "__main__":
    unittest.main()


class AdjudicatedTest(unittest.TestCase):
    """Calls a blind review, an adjudicator, and a skeptic settled against the judge's first pass."""

    def test_a_pair_hit_by_two_ices_while_someone_was_dead_passes_it_on(self):
        # Spring was dead, so her ice went to Kiara, who was already with Gigalad.
        for name in ("Absolute Gigalad", "Kiara Blaiddyd"):
            item = _one("3wzL6x4VHTmvNkhq", 31, name, "Hiemal Storm")
            self.assertEqual((item.cause, _owners(item)), ("missing", [("Spring Nymphar", 100)]))

    def test_the_holder_who_came_last_owns_a_doubled_ice_with_nobody_dead(self):
        for name in ("Loki Doki", "Spring Nymphar", "Kite Noodle"):
            item = _one("8DYNHQx4C7ytdLb9", 39, name, "Hiemal Storm")
            self.assertEqual((item.cause, _owners(item)), ("stacked", [("Loki Doki", 100)]))

    def test_two_bolts_that_hit_nobody_else_are_a_dead_players_bolt(self):
        gigalad = _one("8DYNHQx4C7ytdLb9", 31, "Absolute Gigalad", "Lightning Storm")
        self.assertEqual(gigalad.fact.down, ["Kitana Kahn"])
        self.assertEqual(_owners(gigalad), [("Kitana Kahn", 100)])

    def test_the_other_tank_taking_might_for_a_dead_main_tank(self):
        gigachad = _one("3wzL6x4VHTmvNkhq", 30, "Absolute Gigachad", "Ascalon's Might")
        self.assertEqual((gigachad.cause, _owners(gigachad)), ("redirected", [("Absolute Gigalad", 100)]))
        # A non-tank in the cone still owns it.
        spring = _one("3wzL6x4VHTmvNkhq", 30, "Spring Nymphar", "Ascalon's Might")
        self.assertEqual(_owners(spring), [("Spring Nymphar", 100)])

    def test_a_cone_on_a_player_stunned_by_someone_elses_bash(self):
        for name in ("Kiara Blaiddyd", "Spring Nymphar"):
            item = _one("8DYNHQx4C7ytdLb9", 12, name, "Holy Bladedance")
            self.assertEqual(item.fact.stunned_by, ["Kitana Kahn"])
            self.assertEqual((item.cause, _owners(item)), ("stunned", [("Kitana Kahn", 100)]))

    def test_an_opener_cone_baited_from_outside_the_stack_is_shared(self):
        spring = _one("8DYNHQx4C7ytdLb9", 21, "Spring Nymphar", "Ascalon's Mercy Concealed")
        self.assertEqual(_owners(spring), [("Spring Nymphar", 50), ("Kitana Kahn", 50)])
        for name in ("Loki Doki", "Kitana Kahn"):
            item = _one("3wzL6x4VHTmvNkhq", 3, name, "Ascalon's Mercy Concealed")
            self.assertEqual(_owners(item), [(name, 50), ("Absolute Gigachad", 50)])

    def test_a_tether_taken_for_a_dead_tank_is_that_tanks(self):
        kitana = _one("XVz8bCqgPw1KRh9d", 30, "Kitana Kahn", "Holy Shield Bash")
        self.assertEqual(_owners(kitana), [("Absolute Gigachad", 100)])

    def test_a_sacred_sever_group_is_filled_from_the_empty_seat(self):
        # Jump 3's group hit Kite and Loki. Gigalad was alive elsewhere, and the ranged seat
        # was Kitana's: Kiara was the other group's.
        for name in ("Kite Noodle", "Loki Doki"):
            item = _one("3wzL6x4VHTmvNkhq", 43, name, "Sacred Sever")
            self.assertEqual(sorted(item.fact.group), ["Absolute Gigalad", "Kitana Kahn", "Kite Noodle", "Loki Doki"])
            self.assertEqual(sorted(_owners(item)), [("Absolute Gigalad", 50), ("Kitana Kahn", 50)])

    def test_a_stack_snapshot_counts_a_player_who_died_before_the_damage(self):
        kite = _one("8DYNHQx4C7ytdLb9", 34, "Kite Noodle", "Dragon's Rage")
        self.assertNotIn("Kitana Kahn", kite.fact.down)
        self.assertEqual(sorted(_owners(kite)), [("Absolute Gigachad", 50), ("Absolute Gigalad", 50)])
