"""The saved Thordan review stays put until we deliberately change a call."""

import json
import unittest
from collections import Counter
from pathlib import Path

from xivloganalyzer.catalog import load_catalog, pack_for_zone
from xivloganalyzer.extract import extract_report
from xivloganalyzer.judge import judge_report, roster_from_meta

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "XVz8bCqgPw1KRh9d"


class ReferenceReportTest(unittest.TestCase):
    def test_settled_thordan_counts(self):
        pack = pack_for_zone(968, load_catalog(ROOT))
        facts = extract_report(REPORT, pack)
        judgments = judge_report(facts, pack)
        counts = Counter(item.outcome for item in judgments)
        self.assertEqual(counts["raw"], 183)
        self.assertEqual(counts["fail"], 137)
        self.assertEqual(counts["low"], 11)
        self.assertEqual(counts["unknown"], 0)
        raw = Counter(item.mechanic for item in judgments if item.outcome == "raw")
        self.assertEqual(raw["Eternal Conviction"], 121)
        self.assertEqual(raw["Sacred Sever"], 36)
        self.assertEqual(raw["Holy Impact"], 21)
        self.assertEqual(raw["Dragon's Rage"], 5)
        self.assertNotIn("Skyward Leap", raw)
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
        self.assertEqual(len(pull_68), 0)
        kitana = [
            item for item in judgments
            if item.fact.fight == 68 and item.fact.name == "Kitana Kahn"
            and item.mechanic == "Skyward Leap"
        ]
        self.assertEqual(len(kitana), 1)
        self.assertEqual(kitana[0].outcome, "fail")
        self.assertIn("fully healed", kitana[0].went_wrong)
        self.assertIn("mitigate", kitana[0].went_wrong)
        kiara = [
            item for item in judgments
            if item.fact.fight == 13 and item.mechanic == "Skyward Leap"
        ]
        self.assertEqual(len(kiara), 1)
        self.assertEqual(kiara[0].outcome, "fail")
        self.assertIn("healers", kiara[0].went_wrong)
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

    def test_blame_confidence(self):
        pack = pack_for_zone(968, load_catalog(ROOT))
        meta = json.loads((REPORT / "fights.json").read_text(encoding="utf-8"))
        judgments = judge_report(extract_report(REPORT, pack), pack, roster_from_meta(meta, pack))

        def one(fight, name, mechanic):
            found = [
                item for item in judgments
                if item.fact.fight == fight and item.fact.name == name and item.mechanic == mechanic
            ]
            self.assertEqual(len(found), 1, (fight, name, mechanic))
            return found[0]

        def owners(item):
            return [(blame.who, blame.confidence) for blame in item.blames]

        self.assertEqual(owners(one(60, "Absolute Gigalad", "Heavenly Heel")), [("Absolute Gigalad", 100)])
        self.assertEqual(owners(one(14, "Absolute Gigachad", "Ascalon's Might")), [("Absolute Gigachad", 100)])
        self.assertEqual(owners(one(18, "Kiara Blaiddyd", "Heavenly Heel")), [("Kiara Blaiddyd", 100)])
        self.assertEqual(owners(one(11, "Kite Noodle", "Dragon's Gaze")), [("Kite Noodle", 100)])
        heavies = [item for item in judgments if item.fact.fight == 33 and item.mechanic == "Heavy Impact"]
        self.assertEqual(len(heavies), 2)
        for item in heavies:
            self.assertEqual(owners(item), [(item.fact.name, 100)])
        opener = [
            item for item in judgments
            if item.fact.fight == 12 and item.mechanic == "Ascalon's Mercy Concealed" and item.fact.t < 30
        ]
        self.assertEqual(len(opener), 2)
        for item in opener:
            self.assertEqual(owners(item), [(item.fact.name, 100)])

        bolts = [item for item in judgments if item.fact.fight == 31 and item.mechanic == "Lightning Storm"]
        self.assertEqual({item.fact.name for item in bolts}, {"Kite Noodle", "Spring Nymphar"})
        for item in bolts:
            self.assertEqual(item.blames[0].who, item.fact.name)
            self.assertEqual(
                sorted(owners(item)),
                [("Kite Noodle", 50), ("Spring Nymphar", 50)],
            )
        orbs = [item for item in judgments if item.fact.fight == 39 and item.mechanic == "Bright Flare"]
        self.assertEqual({item.fact.name for item in orbs}, {"Kitana Kahn", "Speed Panda"})
        for item in orbs:
            self.assertEqual(
                sorted(owners(item)),
                [("Kitana Kahn", 50), ("Speed Panda", 50)],
            )
        self.assertEqual(
            owners(one(22, "Kitana Kahn", "Bright Flare")),
            [("Kitana Kahn", 50), ("Another player", 50)],
        )
        self.assertEqual(owners(one(10, "Kitana Kahn", "Bright Flare")), [("Kitana Kahn", 100)])

        self.assertEqual(
            owners(one(13, "Kiara Blaiddyd", "Skyward Leap")),
            [("Loki Doki", 50), ("Spring Nymphar", 50)],
        )
        self.assertEqual(owners(one(68, "Kitana Kahn", "Skyward Leap")), [("Assigned mitigation", 50)])
        self.assertEqual(owners(one(21, "Loki Doki", "Skyward Leap")), [("Missed soak", 50)])
        self.assertEqual(
            owners(one(25, "Speed Panda", "Skyward Leap")),
            [("Loki Doki", 50), ("Spring Nymphar", 50)],
        )
        self.assertEqual(owners(one(25, "Loki Doki", "Skyward Leap")), [("Missed soak", 50)])

        self.assertEqual(owners(one(14, "Kite Noodle", "Sacred Sever")), [("Missing bodies", 100)])
        self.assertEqual(owners(one(10, "Absolute Gigachad", "Sacred Sever")), [("Missing bodies", 33)])
        self.assertEqual(owners(one(12, "Loki Doki", "Dragon's Rage")), [("Missing bodies", 50)])

        self.assertEqual(
            owners(one(14, "Kiara Blaiddyd", "Eternal Conviction")),
            [("Loki Doki", 33), ("Spring Nymphar", 33), ("Party mitigation", 33)],
        )
        self.assertEqual(
            owners(one(15, "Kiara Blaiddyd", "Eternal Conviction")),
            [("Loki Doki", 50), ("Spring Nymphar", 50)],
        )
        self.assertEqual(
            owners(one(12, "Absolute Gigalad", "Holy Bladedance")),
            [("Loki Doki", 33), ("Spring Nymphar", 33), ("Earlier damage", 33)],
        )

        for item in judgments:
            if item.outcome in {"environment", "unknown"}:
                self.assertEqual(item.blames, [])
                continue
            self.assertTrue(item.blames, (item.fact.fight, item.fact.name, item.mechanic))
            for blame in item.blames:
                self.assertGreaterEqual(blame.confidence, 1)
                self.assertLessEqual(blame.confidence, 100)
            if len(item.blames) > 1:
                self.assertEqual(len({blame.confidence for blame in item.blames}), 1)
                self.assertEqual(item.blames[0].confidence, 100 // len(item.blames))
            elif item.blames[0].who == item.fact.name:
                self.assertEqual(item.blames[0].confidence, 100)


if __name__ == "__main__":
    unittest.main()
