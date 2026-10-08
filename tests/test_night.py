"""Each pull names what its first mistake was and who owns it, and the night adds them up."""

import unittest
from pathlib import Path

from test_audit_rules import PACK, _judged

from xivloganalyzer.brief import brief_text
from xivloganalyzer.evidence import evidence_text
from xivloganalyzer.night import night_tally

ROOT = Path(__file__).resolve().parents[1]
CODE = "XVz8bCqgPw1KRh9d"


def _causes(fight):
    rows = [item for item in _judged(CODE)[4] if item.fact.fight == fight]
    return rows[0].first_causes


class FirstCausesTest(unittest.TestCase):
    def test_a_debuff_names_where_it_came_from(self):
        self.assertEqual(_causes(24), [{"mechanic": "Dimensional Collapse", "owners": ["Absolute Gigachad"]}])
        item = next(item for item in _judged(CODE)[4] if item.fact.fight == 24)
        self.assertIn("Damage Down on Absolute Gigachad from Dimensional Collapse", item.first_mistake)

    def test_a_debuff_from_the_cast_that_killed_is_not_named_again(self):
        self.assertEqual(_causes(57), [{"mechanic": "Eternal Conviction", "owners": ["Kitana Kahn"]}])
        item = next(item for item in _judged(CODE)[4] if item.fact.fight == 57)
        self.assertNotIn("Damage Down", item.first_mistake)

    def test_a_shared_tower_names_who_left_it(self):
        # With the soak file, pull 47's Strength towers name Spring, who was alive and not in one.
        self.assertEqual(_causes(47), [{"mechanic": "Eternal Conviction", "owners": ["Spring Nymphar"]}])

    def test_a_gaze_debuff_is_the_holder_s(self):
        owners = {cause["mechanic"]: cause["owners"] for cause in _causes(11)}
        self.assertEqual(owners["Dragon's Gaze"], ["Kite Noodle"])
        self.assertEqual(sorted(owners["Dragon's Glory"]), ["Kitana Kahn", "Speed Panda"])


class NightTest(unittest.TestCase):
    def test_every_pull_has_a_first_mistake_and_the_tally_counts_pulls(self):
        rows = [item.to_dict() for item in _judged(CODE)[4]]
        tally = night_tally(rows)
        self.assertEqual(tally["pulls"], 55)
        self.assertGreaterEqual(sum(row["pulls"] for row in tally["started"]), 55)
        self.assertEqual(tally["started"][0]["mechanic"], "Ascalon's Mercy Concealed")
        self.assertIn("Missing bodies", tally["labels"])
        owned = dict(tally["owned"])
        self.assertNotIn("Party mitigation", owned)

    def test_the_brief_leads_with_the_night(self):
        text = brief_text(ROOT / "data" / CODE)
        self.assertIn("What started each pull (55 pulls", text)
        self.assertIn("Who started pulls", text)
        self.assertLess(text.index("Who started pulls"), text.index("Raw by mechanic"))


class EvidenceTest(unittest.TestCase):
    def test_evidence_shows_each_circle_and_the_calls(self):
        text = evidence_text(ROOT / "data" / CODE, PACK, 15)
        self.assertIn("HIT Hiemal Storm (source 176/3, 3): Kiara Blaiddyd", text)
        self.assertIn("DEATH Kitana Kahn (2:12)", text)
        self.assertIn("The judge's calls", text)

    def test_blind_evidence_has_no_calls(self):
        text = evidence_text(ROOT / "data" / CODE, PACK, 15, blind=True)
        self.assertNotIn("The judge's calls", text)
        self.assertNotIn("[hit-list]", text)


if __name__ == "__main__":
    unittest.main()
