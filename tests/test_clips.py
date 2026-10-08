"""A Skyward Leap that hits anyone else is the mistake of whoever was out of position."""

import json
import unittest
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.dashboard import session_clock, session_payload
from xivloganalyzer.extract import extract_report
from xivloganalyzer.judge import judge_report, roster_from_meta

ROOT = Path(__file__).resolve().parents[1]


def _judged(code):
    report = ROOT / "data" / code
    pack = load_pack(ROOT / "fights" / "dsr")
    meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
    judgments = judge_report(extract_report(report, pack), pack, roster_from_meta(meta, pack))
    return report, pack, meta, judgments


def _owners(item):
    return [(blame.who, blame.confidence) for blame in item.blames]


class MarkerClipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.pack, cls.meta, cls.judgments = _judged("8DYNHQx4C7ytdLb9")

    def _deaths(self, fight):
        return [item for item in self.judgments if item.fact.fight == fight and item.fact.t < 61]

    def test_spring_owns_the_deaths_his_leap_caused(self):
        by_name = {item.fact.name: item for item in self._deaths(4)}
        spring = by_name["Spring Nymphar"]
        self.assertEqual(spring.mechanic, "Dimensional Collapse")
        self.assertEqual(_owners(spring), [("Spring Nymphar", 100)])
        for name in ("Speed Panda", "Kiara Blaiddyd", "Kitana Kahn", "Absolute Gigachad"):
            item = by_name[name]
            self.assertEqual(item.outcome, "fail")
            self.assertEqual(item.went_wrong, f"Spring Nymphar was out of position and clipped {name}.")
            self.assertEqual(_owners(item), [("Spring Nymphar", 100)])
        self.assertEqual(by_name["Absolute Gigachad"].mechanic, "Holy Shield Bash")

    def test_pull_card_fails_only_the_marker_holder(self):
        when = session_clock(self.report, self.meta)
        payload = session_payload(self.judgments, self.pack, self.report.name, when, self.meta)
        pull = next(pull for pull in payload["pulls"] if pull["id"] == 4)
        card = next(card for card in pull["cards"] if card["id"] == "strength-of-the-ward")
        failed = {
            part["id"]: sorted(seat["name"] for seat in part["seats"] if not seat["passed"])
            for part in card["parts"]
        }
        self.assertEqual(failed["dimensional-collapse"], ["Spring Nymphar"])
        self.assertEqual(failed["skyward-leap"], ["Spring Nymphar"])
        self.assertEqual(failed["dragons-rage"], [])
        self.assertEqual(failed["holy-shield-bash"], [])
        clipped = [row for row in pull["deaths"] if row["componentId"] == "skyward-leap"]
        self.assertEqual(len(clipped), 4)
        for row in clipped:
            self.assertEqual(row["culprits"], ["Spring Nymphar"])
        # The towers at 65s were empty because Kite Noodle and Spring Nymphar were dead.
        towers = [row for row in pull["deaths"] if row["componentId"] == "eternal-conviction"]
        self.assertEqual(sorted(row["name"] for row in towers), ["Absolute Gigalad", "Loki Doki"])
        for row in towers:
            self.assertEqual(row["culprits"], ["Kite Noodle", "Spring Nymphar"])
        self.assertEqual(
            sorted(row["cast"] for row in clipped),
            ["Dragon's Rage", "Dragon's Rage", "Dragon's Rage", "Holy Shield Bash"],
        )

    def test_a_leap_on_a_tank_belongs_to_the_dead_holders(self):
        # A tank never holds a marker. The leap fell on Gigachad because its holder walked
        # into the wall first: Speed and Kiara were dead at the two empty spots.
        gigalad = next(item for item in self._deaths(15) if item.fact.name == "Absolute Gigalad")
        self.assertEqual(gigalad.cause, "orphan")
        self.assertEqual(gigalad.basis, "position")
        self.assertEqual(_owners(gigalad), [("Speed Panda", 50), ("Kiara Blaiddyd", 50)])

    def test_the_holder_off_their_spot_owns_the_overlap(self):
        deaths = {item.fact.name: item for item in self._deaths(25)}
        kiara = deaths["Kiara Blaiddyd"]
        self.assertEqual(kiara.fact.in_spot, {"Kiara Blaiddyd": True, "Loki Doki": False})
        self.assertEqual(kiara.went_wrong, "Loki Doki was out of position and overlapped Kiara Blaiddyd.")
        self.assertEqual(_owners(kiara), [("Loki Doki", 100)])
        loki = deaths["Loki Doki"]
        self.assertEqual(loki.went_wrong, "Loki Doki was out of position and overlapped Kiara Blaiddyd.")
        self.assertEqual(_owners(loki), [("Loki Doki", 100)])

    def test_leaps_with_dead_holders_fall_on_the_survivors(self):
        # Every leap fell on Spring or Gigachad in the stack: their holders, Kite and Speed,
        # had walked into the wall on their spots before the leaps landed.
        deaths = {item.fact.name: item for item in self._deaths(51)}
        for name in ("Spring Nymphar", "Absolute Gigachad"):
            item = deaths[name]
            self.assertEqual(
                item.went_wrong,
                "Speed Panda and Kite Noodle died holding a marker, so its leap fell on someone else.",
            )
            self.assertEqual(_owners(item), [("Speed Panda", 50), ("Kite Noodle", 50)])

    def test_a_second_leap_is_not_an_empty_tower(self):
        for item in self.judgments:
            if item.mechanic == "Skyward Leap":
                self.assertNotIn("tower", item.went_wrong)
                self.assertNotIn("Missed soak", [blame.who for blame in item.blames])

    def test_a_leap_whose_holder_walked_into_the_wall_is_theirs(self):
        # Loki ran for the far spot and walked into the wall before the leaps. His leap fell
        # on Kitana in the stack, and everything it hit is his.
        _report, _pack, _meta, judgments = _judged("XVz8bCqgPw1KRh9d")
        hit = [
            item for item in judgments
            if item.fact.fight == 28 and 58 < item.fact.t < 61
            and item.outcome == "fail" and item.mechanic_id != "deathwall"
        ]
        self.assertEqual(
            sorted(item.fact.name for item in hit),
            ["Absolute Gigachad", "Absolute Gigalad", "Kiara Blaiddyd", "Kitana Kahn", "Kite Noodle"],
        )
        for item in hit:
            self.assertEqual((item.cause, _owners(item)), ("orphan", [("Loki Doki", 100)]))


class PositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.pack, cls.meta, cls.judgments = _judged("XVz8bCqgPw1KRh9d")

    def _one(self, fight, name, mechanic):
        found = [
            item for item in self.judgments
            if item.fact.fight == fight and item.fact.name == name and item.mechanic == mechanic
        ]
        self.assertEqual(len(found), 1, (fight, name, mechanic))
        return found[0]

    def test_a_holder_pulled_in_from_their_spot_owns_both_leaps(self):
        for name in ("Kiara Blaiddyd", "Kitana Kahn"):
            item = self._one(59, name, "Skyward Leap")
            self.assertEqual(item.outcome, "fail")
            self.assertEqual(_owners(item), [("Kitana Kahn", 100)])

    def test_a_holder_short_of_the_edge_owns_the_leaps_on_the_others(self):
        for name in ("Loki Doki", "Kitana Kahn", "Kite Noodle"):
            self.assertEqual(_owners(self._one(21, name, "Skyward Leap")), [("Loki Doki", 100)])

    def test_a_player_who_stands_in_a_placed_leap_owns_it(self):
        gigachad = self._one(59, "Absolute Gigachad", "Holy Shield Bash")
        self.assertEqual(gigachad.fact.in_spot, {"Spring Nymphar": True, "Absolute Gigachad": False})
        self.assertEqual(gigachad.went_wrong, "Absolute Gigachad stood in Spring Nymphar's Skyward Leap.")
        self.assertEqual(_owners(gigachad), [("Absolute Gigachad", 100)])

    def test_a_leap_with_no_living_holder_names_the_dead_holder(self):
        # Speed walked into the wall near the empty spot, so the second leap on Kiara was his.
        kiara = self._one(68, "Kiara Blaiddyd", "Skyward Leap")
        self.assertEqual(kiara.outcome, "fail")
        self.assertEqual(
            kiara.went_wrong,
            "Speed Panda died holding a marker, so its leap fell on someone else.",
        )
        self.assertEqual(_owners(kiara), [("Speed Panda", 100)])


if __name__ == "__main__":
    unittest.main()
