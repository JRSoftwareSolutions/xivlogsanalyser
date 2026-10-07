"""Rules the pull-by-pull blame audit settled, pinned on the saved logs."""

import json
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

    def test_a_tower_with_no_hit_list_says_what_it_was_missing(self):
        # XVz has no file for the tower soak, so a tower with nobody dead is a missed soak on missing evidence.
        unnamed = [
            item for item in _judged("XVz8bCqgPw1KRh9d")[4]
            if item.mechanic_id == "eternal-conviction" and item.cause == "tower"
        ]
        self.assertTrue(unnamed)
        for item in unnamed:
            self.assertIn("ability 25567", item.fact.missing)
            self.assertEqual(_owners(item), [("Missed soak", 50)])


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
            self.assertEqual(item.went_wrong, f"{item.fact.name} got cleaved.")
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
                cleaved = item.went_wrong.endswith("got cleaved.")
                casts.setdefault((fact.fight, fact.guid, tuple(sorted(fact.cohort))), set()).add(cleaved)
            split = {key: seen for key, seen in casts.items() if len(seen) > 1}
            self.assertEqual(split, {}, code)


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

    def test_a_missing_ability_file_is_named(self):
        report = _judged("XVz8bCqgPw1KRh9d")[0]
        guids = {row["guid"] for row in read_inputs(report)["abilities"]}
        self.assertIn(25567, guids)


if __name__ == "__main__":
    unittest.main()
