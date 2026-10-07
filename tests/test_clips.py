"""A Skyward Leap that clips the party is the marker holder's mistake."""

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
            self.assertEqual(item.went_wrong, f"{name} was clipped by Spring Nymphar's Skyward Leap.")
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
        clipped = [row for row in pull["deaths"] if row["culprits"]]
        self.assertEqual(len(clipped), 4)
        for row in clipped:
            self.assertEqual(row["componentId"], "skyward-leap")
            self.assertEqual(row["culprits"], ["Spring Nymphar"])
        self.assertEqual(
            sorted(row["cast"] for row in clipped),
            ["Dragon's Rage", "Dragon's Rage", "Dragon's Rage", "Holy Shield Bash"],
        )

    def test_a_marker_on_a_tank_after_deaths_still_names_that_tank(self):
        gigalad = next(item for item in self._deaths(15) if item.fact.name == "Absolute Gigalad")
        self.assertEqual(_owners(gigalad), [("Absolute Gigachad", 100)])

    def test_two_markers_that_overlap_share_the_blame(self):
        kiara = next(item for item in self._deaths(25) if item.fact.name == "Kiara Blaiddyd")
        self.assertEqual(kiara.went_wrong, "Kiara Blaiddyd's Skyward Leap overlapped Loki Doki's.")
        self.assertEqual(_owners(kiara), [("Kiara Blaiddyd", 50), ("Loki Doki", 50)])

    def test_a_marker_holder_with_their_own_vulnerability_keeps_it(self):
        _report, _pack, _meta, judgments = _judged("XVz8bCqgPw1KRh9d")
        kitana = next(
            item for item in judgments
            if item.fact.fight == 28 and item.fact.name == "Kitana Kahn" and item.mechanic == "Dragon's Rage"
        )
        self.assertEqual(kitana.fact.clipped_by, [])
        self.assertEqual(_owners(kitana), [("Kitana Kahn", 100)])
        others = [
            item for item in judgments
            if item.fact.fight == 28 and item.fact.name != "Kitana Kahn" and item.fact.t < 61
            and item.outcome == "fail"
        ]
        self.assertTrue(others)
        for item in others:
            self.assertEqual(_owners(item), [("Kitana Kahn", 100)])


if __name__ == "__main__":
    unittest.main()
