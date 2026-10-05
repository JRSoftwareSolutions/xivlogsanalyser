"""The saved Thordan review stays put until we deliberately change a call."""

import unittest
from collections import Counter
from pathlib import Path

from xivloganalyzer.catalog import load_catalog, pack_for_zone
from xivloganalyzer.extract import extract_report
from xivloganalyzer.judge import judge_report

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "XVz8bCqgPw1KRh9d"


class ReferenceReportTest(unittest.TestCase):
    def test_settled_thordan_counts(self):
        pack = pack_for_zone(968, load_catalog(ROOT))
        facts = extract_report(REPORT, pack)
        judgments = judge_report(facts, pack)
        counts = Counter(item.outcome for item in judgments)
        self.assertEqual(counts["raw"], 187)
        self.assertEqual(counts["fail"], 133)
        self.assertEqual(counts["low"], 11)
        self.assertEqual(counts["unknown"], 0)
        raw = Counter(item.mechanic for item in judgments if item.outcome == "raw")
        self.assertEqual(raw["Eternal Conviction"], 121)
        self.assertEqual(raw["Sacred Sever"], 36)
        self.assertEqual(raw["Holy Impact"], 21)
        self.assertEqual(raw["Dragon's Rage"], 5)
        self.assertEqual(raw["Skyward Leap"], 4)
        self.assertNotIn("Heavenly Heel", raw)
        heel = [
            item for item in judgments
            if item.fact.fight == 60 and item.fact.name == "Absolute Gigalad"
            and item.mechanic == "Heavenly Heel"
        ]
        self.assertEqual(len(heel), 1)
        self.assertEqual(heel[0].outcome, "fail")
        self.assertIn("Personal mitigation", heel[0].went_wrong)
        might = [
            item for item in judgments
            if item.fact.fight == 14 and item.mechanic == "Ascalon's Might"
        ]
        self.assertEqual(len(might), 1)
        self.assertEqual(might[0].outcome, "fail")
        self.assertIn("extra hit", might[0].went_wrong)
        dancer = [
            item for item in judgments
            if item.fact.fight == 18 and item.mechanic == "Heavenly Heel"
        ]
        self.assertEqual(len(dancer), 1)
        self.assertEqual(dancer[0].outcome, "fail")
        self.assertIn("Only a tank", dancer[0].went_wrong)
        pull_68 = [
            item for item in judgments
            if item.fact.fight == 68 and item.outcome == "raw"
        ]
        self.assertEqual(len(pull_68), 1)
        self.assertEqual(pull_68[0].fact.name, "Kitana Kahn")
        self.assertEqual(pull_68[0].mechanic, "Skyward Leap")
        self.assertIn("resolve was fine", pull_68[0].went_wrong)
        strength = pack.cluster_for("skyward-leap", 59.5, 2)
        self.assertEqual(strength.name, "Strength of the Ward")
        opener = pack.cluster_for("ascalons-might", 16.7, 2)
        swap = pack.cluster_for("ascalons-might", 84.7, 2)
        self.assertEqual(opener.name, "Ascalon's Might")
        self.assertEqual(swap.name, "Heavenly Heel")
        early = pack.cluster_for("eternal-conviction", 64.0, 2)
        late = pack.cluster_for("eternal-conviction", 136.5, 2)
        self.assertEqual(early.name, "Strength of the Ward")
        self.assertEqual(late.name, "Meteors")


if __name__ == "__main__":
    unittest.main()
