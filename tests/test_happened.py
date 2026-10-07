"""What happened names only what explains the death, not every number in the packet."""

import unittest
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.extract import read_facts
from xivloganalyzer.judge import judge_report

ROOT = Path(__file__).resolve().parents[1]


def _judged(code):
    pack = load_pack(ROOT / "fights" / "dsr")
    return judge_report(read_facts(ROOT / "data" / code), pack)


class HappenedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nidhogg = _judged("8DYNHQx4C7ytdLb9")
        cls.thordan = _judged("XVz8bCqgPw1KRh9d")

    def test_a_raw_death_says_what_would_have_kept_them_alive(self):
        item = next(
            item for item in self.nidhogg
            if item.fact.name == "Spring Nymphar" and item.fact.total == 59402
        )
        self.assertEqual(item.outcome, "raw")
        self.assertEqual(
            item.happened,
            "Took 59,402 at 82% HP (50,595 of 61,615). Full HP would have lived. No shield.",
        )

    def test_mitigation_that_was_there_is_not_listed(self):
        for item in self.nidhogg + self.thordan:
            if item.outcome == "unknown":
                continue
            self.assertNotRegex(item.happened, r" from [A-Z]")
            self.assertNotIn("mit unknown", item.happened)
            self.assertNotIn("·", item.happened)

    def test_a_short_stack_names_only_the_stack(self):
        for item in self.thordan:
            if item.outcome == "raw" and item.cause == "missing":
                self.assertIn(" of ", item.happened.split(". ", 1)[1])
                self.assertNotIn("shield", item.happened)

    def test_a_cleave_compares_the_hit_to_what_the_role_takes(self):
        cleaves = [
            item for item in self.thordan
            if item.mechanic_id == "sacred-sever" and item.went_wrong.endswith("got cleaved.")
        ]
        self.assertTrue(cleaves)
        for item in cleaves:
            self.assertRegex(item.happened, r"A (tank|healer|DPS) takes about")

    def test_an_amp_is_named(self):
        amped = [item for item in self.thordan if item.went_wrong.endswith("still had a damage amp.")]
        self.assertTrue(amped)
        for item in amped:
            self.assertIn("Vulnerability Up", item.happened)

    def test_the_deathwall_says_nothing_hit_them(self):
        walls = [item for item in self.thordan if item.mechanic_id == "deathwall"]
        self.assertTrue(walls)
        for item in walls:
            self.assertTrue(item.happened.startswith("Nothing hit them."))


if __name__ == "__main__":
    unittest.main()
