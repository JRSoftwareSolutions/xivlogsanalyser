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
        self.assertEqual(counts["raw"], 40)
        self.assertEqual(counts["fail"], 416)
        self.assertEqual(counts["low"], 2)
        self.assertEqual(counts["unknown"], 0)
        self.assertEqual(counts["environment"], 0)
        walls = [item for item in judgments if item.mechanic_id == "deathwall"]
        self.assertEqual(len(walls), 110)
        self.assertTrue(all(item.outcome == "fail" for item in walls))
        raw = Counter(item.mechanic for item in judgments if item.outcome == "raw")
        # The towers at 63s exploded because a tower was empty. None of those deaths is raw.
        self.assertNotIn("Eternal Conviction", raw)
        self.assertEqual(raw["Sacred Sever"], 35)
        self.assertNotIn("Holy Impact", raw)
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
        self.assertEqual(heel[0].went_wrong, "Absolute Gigalad took Heavenly Heel.")
        might = [
            item for item in judgments
            if item.fact.fight == 14 and item.mechanic == "Ascalon's Might"
        ]
        self.assertEqual(len(might), 1)
        self.assertEqual(might[0].outcome, "fail")
        self.assertEqual(might[0].went_wrong, "Absolute Gigachad ate an extra Ascalon's Might.")
        dancer = [
            item for item in judgments
            if item.fact.fight == 18 and item.mechanic == "Heavenly Heel"
        ]
        self.assertEqual(len(dancer), 1)
        self.assertEqual(dancer[0].outcome, "fail")
        self.assertEqual(dancer[0].went_wrong, "Kiara Blaiddyd took Heavenly Heel.")
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
        self.assertEqual(kitana[0].went_wrong, "Kitana Kahn died to Skyward Leap without mitigation.")
        kiara = [
            item for item in judgments
            if item.fact.fight == 13 and item.mechanic == "Skyward Leap"
        ]
        self.assertEqual(len(kiara), 1)
        self.assertEqual(kiara[0].outcome, "fail")
        self.assertEqual(kiara[0].went_wrong, "Kiara Blaiddyd wasn't full for Skyward Leap.")
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
        # Two orbs at once, one packet each: each player was hit by their own orb.
        orbs = [item for item in judgments if item.fact.fight == 39 and item.mechanic == "Bright Flare"]
        self.assertEqual({item.fact.name for item in orbs}, {"Kitana Kahn", "Speed Panda"})
        for item in orbs:
            self.assertEqual(item.went_wrong, f"{item.fact.name} got hit by a Bright Flare.")
            self.assertEqual(owners(item), [(item.fact.name, 100)])
        # One orb's packet hit Kite and Gigalad, who lived. He is named, not "Another player".
        self.assertEqual(
            owners(one(34, "Kite Noodle", "Bright Flare")),
            [("Kite Noodle", 50), ("Absolute Gigalad", 50)],
        )
        self.assertEqual(
            one(10, "Kitana Kahn", "Bright Flare").went_wrong,
            "Kitana Kahn got hit by a Bright Flare.",
        )
        self.assertEqual(
            one(11, "Kite Noodle", "Dragon's Gaze").went_wrong,
            "Kite Noodle looked at the gaze.",
        )
        self.assertEqual(owners(one(22, "Kitana Kahn", "Bright Flare")), [("Kitana Kahn", 100)])
        self.assertEqual(one(22, "Absolute Gigalad", "Bright Flare").outcome, "fail")
        self.assertEqual(owners(one(10, "Kitana Kahn", "Bright Flare")), [("Kitana Kahn", 100)])

        self.assertEqual(
            owners(one(13, "Kiara Blaiddyd", "Skyward Leap")),
            [("Loki Doki", 50), ("Spring Nymphar", 50)],
        )
        self.assertEqual(owners(one(68, "Kitana Kahn", "Skyward Leap")), [("Assigned mitigation", 50)])
        self.assertEqual(owners(one(21, "Loki Doki", "Skyward Leap")), [("Loki Doki", 100)])
        self.assertEqual(
            owners(one(25, "Speed Panda", "Skyward Leap")),
            [("Kiara Blaiddyd", 50), ("Speed Panda", 50)],
        )
        self.assertEqual(owners(one(25, "Loki Doki", "Skyward Leap")), [("Loki Doki", 100)])

        # Kitana took the double sword's second jump with them and was not in the fourth.
        self.assertEqual(owners(one(14, "Kite Noodle", "Sacred Sever")), [("Kitana Kahn", 100)])
        # His group died to the second jump, which landed on them because Spring and Kite were in the wall.
        self.assertEqual(
            owners(one(10, "Absolute Gigachad", "Sacred Sever")),
            [("Spring Nymphar", 50), ("Kite Noodle", 50)],
        )
        self.assertEqual(owners(one(12, "Loki Doki", "Dragon's Rage")), [("Missing bodies", 50)])

        # Spring died to the cone at 48s, so the tower Spring should have stood in was empty.
        self.assertEqual(
            owners(one(16, "Kiara Blaiddyd", "Eternal Conviction")),
            [("Spring Nymphar", 100)],
        )
        self.assertEqual(one(16, "Kiara Blaiddyd", "Eternal Conviction").outcome, "fail")
        self.assertEqual(one(14, "Kiara Blaiddyd", "Eternal Conviction").outcome, "fail")
        # Six players were dead before the towers. Each gap belongs to whoever owned that death:
        # Kite and Spring died to the short stack Kitana left, so theirs are Kitana's. Loki's ice
        # had no partner because Kite and Kitana were dead, so Loki's gap is Kitana's too.
        # Four of the six gaps are Kitana's.
        self.assertEqual(
            owners(one(14, "Kiara Blaiddyd", "Eternal Conviction")),
            [("Speed Panda", 16), ("Absolute Gigachad", 16), ("Kitana Kahn", 66)],
        )
        # Kitana and Spring died to a jump the healers did not heal them for, so their gaps are the healers'.
        # Speed's and Loki's gaps are their own; Kitana's and Spring's are split between the two healers.
        self.assertEqual(
            owners(one(26, "Kiara Blaiddyd", "Eternal Conviction")),
            [("Speed Panda", 25), ("Loki Doki", 50), ("Spring Nymphar", 25)],
        )
        # Kitana's ice had no partner because Gigalad and Loki doubled up in another one,
        # so the tower Kitana should have stood in is theirs. Gigachad's own gap is the other half.
        self.assertEqual(
            owners(one(15, "Kitana Kahn", "Hiemal Storm")),
            [("Absolute Gigalad", 50), ("Loki Doki", 50)],
        )
        self.assertEqual(
            owners(one(15, "Kiara Blaiddyd", "Eternal Conviction")),
            [("Absolute Gigachad", 50), ("Absolute Gigalad", 25), ("Loki Doki", 25)],
        )
        # Everyone was alive, and the one the towers missed owns it.
        self.assertEqual(
            owners(one(57, "Kiara Blaiddyd", "Eternal Conviction")),
            [("Kitana Kahn", 100)],
        )
        # The comets that exploded were both Gigachad's, though six players were already dead.
        self.assertEqual(one(41, "Absolute Gigachad", "Holy Impact").outcome, "fail")
        self.assertEqual(owners(one(41, "Absolute Gigachad", "Holy Impact")), [("Absolute Gigachad", 100)])
        # Kiara's first two comets landed 4.5 yalms apart.
        self.assertEqual(owners(one(67, "Absolute Gigachad", "Holy Impact")), [("Kiara Blaiddyd", 100)])
        self.assertEqual(
            one(67, "Absolute Gigachad", "Holy Impact").went_wrong,
            "Kiara Blaiddyd dropped two comets too close.",
        )
        # Loki Doki was already dead to a short Dragon's Rage, so his share passes on.
        self.assertEqual(
            owners(one(12, "Absolute Gigalad", "Holy Bladedance")),
            [("Missing bodies", 33), ("Spring Nymphar", 33), ("Earlier damage", 33)],
        )

        for item in judgments:
            text = item.went_wrong
            self.assertTrue(text.endswith("."), text)
            self.assertEqual(text.count("."), 1, text)
            self.assertLessEqual(len(text), 90, text)
            if item.outcome in {"environment", "unknown"}:
                self.assertEqual(item.blames, [])
                continue
            self.assertTrue(item.blames, (item.fact.fight, item.fact.name, item.mechanic))
            for blame in item.blames:
                self.assertGreaterEqual(blame.confidence, 1)
                self.assertLessEqual(blame.confidence, 100)
            if len(item.blames) > 1:
                # A share passed on through a dead player is split the way that death was,
                # so shares can differ. Rounded down, they add up to 100 less under one per owner.
                total = sum(blame.confidence for blame in item.blames)
                self.assertLessEqual(total, 100)
                self.assertGreater(total, 100 - len(item.blames))
                if item.cause not in {"empty", "redirected", "missing", "healers", "resolve", "low"}:
                    self.assertEqual(len({blame.confidence for blame in item.blames}), 1)
            elif item.blames[0].who == item.fact.name:
                self.assertEqual(item.blames[0].confidence, 100)


    def test_deathwall_and_first_mistake(self):
        pack = pack_for_zone(968, load_catalog(ROOT))
        meta = json.loads((REPORT / "fights.json").read_text(encoding="utf-8"))
        judgments = judge_report(extract_report(REPORT, pack), pack, roster_from_meta(meta, pack))

        def owners(item):
            return [(blame.who, blame.confidence) for blame in item.blames]

        # Pull 28: Loki Doki walks into the wall before anyone dies. That is the first mistake.
        pull_28 = sorted(
            (item for item in judgments if item.fact.fight == 28),
            key=lambda item: item.fact.t,
        )
        loki = pull_28[0]
        self.assertEqual((loki.fact.name, loki.mechanic), ("Loki Doki", "Deathwall"))
        self.assertEqual(loki.outcome, "fail")
        self.assertTrue(loki.first)
        self.assertEqual(loki.went_wrong, "Loki Doki walked into the deathwall.")
        self.assertEqual(owners(loki), [("Loki Doki", 100)])
        self.assertFalse(any(item.first for item in pull_28[1:]))
        self.assertTrue(all(item.first_mistake == loki.first_mistake for item in pull_28))
        self.assertTrue(loki.first_mistake.startswith("Loki Doki walking into the deathwall at "))

        # Pull 23: two cone deaths first, then the party walks into the wall.
        pull_23 = [item for item in judgments if item.fact.fight == 23]
        cones = [item for item in pull_23 if item.mechanic == "Ascalon's Mercy Concealed"]
        self.assertEqual(len(cones), 2)
        self.assertTrue(all(item.first for item in cones))
        walls = [item for item in pull_23 if item.mechanic_id == "deathwall"]
        self.assertTrue(walls)
        for item in walls:
            self.assertFalse(item.first)
            self.assertEqual(item.outcome, "fail")
            self.assertEqual(
                item.went_wrong, f"{item.fact.name} walked into the deathwall after the first mistake.",
            )
            self.assertEqual(owners(item), [(item.fact.name, 50), ("Earlier mistake", 50)])
            self.assertGreater(item.fact.t, cones[0].fact.t)

        # A deathwall death is timed by the clock, not by the last hit they lived.
        pull_25 = [item for item in judgments if item.fact.fight == 25 and item.mechanic_id == "deathwall"]
        self.assertTrue(pull_25)
        self.assertTrue(all(item.fact.t > 50 for item in pull_25))

        # Pull 10: the walls came with their own Hysteria from the gaze.
        hysteria = [
            item for item in judgments
            if item.fact.fight == 10 and item.mechanic_id == "deathwall"
        ]
        self.assertTrue(hysteria)
        for item in hysteria:
            self.assertIn("Hysteria", item.went_wrong)
            self.assertEqual(owners(item), [(item.fact.name, 100)])


if __name__ == "__main__":
    unittest.main()
