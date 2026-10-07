"""Fault goes to the player who broke the mechanic, named from the log."""

import json
import unittest
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.dashboard import session_clock, session_payload
from xivloganalyzer.extract import extract_report
from xivloganalyzer.judge import judge_report, roster_from_meta

ROOT = Path(__file__).resolve().parents[1]


def _owners(item):
    return [(blame.who, blame.confidence) for blame in item.blames]


class FaultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = ROOT / "data" / "8DYNHQx4C7ytdLb9"
        cls.pack = load_pack(ROOT / "fights" / "dsr")
        cls.meta = json.loads((cls.report / "fights.json").read_text(encoding="utf-8"))
        cls.judgments = judge_report(
            extract_report(cls.report, cls.pack), cls.pack, roster_from_meta(cls.meta, cls.pack),
        )

    def _pull(self, fight, mechanic=None):
        return sorted(
            (
                item for item in self.judgments
                if item.fact.fight == fight and (mechanic is None or item.mechanic == mechanic)
            ),
            key=lambda item: (item.fact.t, item.fact.name),
        )

    def test_a_frostbite_tick_is_not_the_deathwall(self):
        paladin = self._pull(53)[0]
        self.assertEqual((paladin.fact.name, paladin.mechanic), ("Absolute Gigachad", "Frostbite"))
        self.assertEqual(paladin.fact.guid, 1002946)
        self.assertEqual(paladin.outcome, "fail")
        self.assertEqual(paladin.went_wrong, "Absolute Gigachad stood in the ice.")
        self.assertTrue(paladin.first)

    def test_crossed_comets_name_both_prey_players(self):
        # Kite's last comet landed 3.6 yalms from Speed's first, before the outer towers.
        impact = self._pull(53, "Holy Impact")
        self.assertEqual(len(impact), 7)
        for item in impact:
            self.assertEqual(item.fact.marked, ["Kite Noodle", "Speed Panda"])
            self.assertEqual(_owners(item), [("Speed Panda", 50), ("Kite Noodle", 50)])
            self.assertFalse(item.first)

    def test_the_pull_card_fails_only_the_prey_players(self):
        when = session_clock(self.report, self.meta)
        payload = session_payload(self.judgments, self.pack, self.report.name, when, self.meta)
        pull = next(row for row in payload["pulls"] if row["id"] == 53)
        seats = [
            seat
            for card in pull["cards"]
            for part in card["parts"]
            if part["id"] == "holy-impact"
            for seat in part["seats"]
        ]
        self.assertTrue(seats)
        failed = sorted(seat["name"] for seat in seats if not seat["passed"])
        self.assertEqual(failed, ["Kite Noodle", "Speed Panda"])

    def test_one_players_comets_are_theirs(self):
        # Loki's fourth and fifth comets landed 4.7 yalms apart.
        for item in self._pull(24, "Holy Impact"):
            self.assertEqual(_owners(item), [("Loki Doki", 100)])
            self.assertEqual(item.went_wrong, "Loki Doki dropped two comets too close.")

    def test_a_dead_prey_player_passes_it_on(self):
        # Both prey players died to the empty tower, which Kiara left by standing in the ice.
        for item in self._pull(37, "Holy Impact"):
            self.assertEqual(_owners(item), [("Kiara Blaiddyd", 100)])

    def test_alive_outside_the_towers_is_named(self):
        towers = self._pull(37, "Eternal Conviction")
        self.assertTrue(towers)
        for item in towers:
            self.assertEqual(item.fact.unsoaked, ["Kiara Blaiddyd"])
            self.assertEqual(_owners(item), [("Kiara Blaiddyd", 100)])

    def test_two_in_one_tower_are_named(self):
        for pull, pair in ((19, ["Spring Nymphar", "Kiara Blaiddyd"]), (29, ["Loki Doki", "Speed Panda"])):
            towers = self._pull(pull, "Eternal Conviction")
            self.assertTrue(towers)
            for item in towers:
                self.assertEqual(sorted(_owners(item)), sorted((name, 50) for name in pair))


if __name__ == "__main__":
    unittest.main()
