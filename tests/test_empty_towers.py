"""A player missing from a mechanic that needs everyone owns the explosion."""

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


class EmptyTowerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = ROOT / "data" / "8DYNHQx4C7ytdLb9"
        cls.pack = load_pack(ROOT / "fights" / "dsr")
        cls.meta = json.loads((cls.report / "fights.json").read_text(encoding="utf-8"))
        cls.judgments = judge_report(
            extract_report(cls.report, cls.pack), cls.pack, roster_from_meta(cls.meta, cls.pack),
        )

    def _pull(self, fight):
        return sorted(
            (item for item in self.judgments if item.fact.fight == fight),
            key=lambda item: (item.fact.t, item.fact.name),
        )

    def test_a_frostbite_tick_is_not_the_deathwall(self):
        paladin = self._pull(53)[0]
        self.assertEqual((paladin.fact.name, paladin.mechanic), ("Absolute Gigachad", "Frostbite"))
        self.assertEqual(paladin.fact.guid, 1002946)
        self.assertEqual(paladin.outcome, "fail")
        self.assertEqual(paladin.went_wrong, "Absolute Gigachad stood in the ice.")
        self.assertTrue(paladin.first)
        self.assertTrue(paladin.first_mistake.startswith("Absolute Gigachad dying to Frostbite at "))

    def test_the_dead_player_owns_the_holy_impact(self):
        impact = [item for item in self._pull(53) if item.mechanic == "Holy Impact"]
        self.assertEqual(len(impact), 7)
        for item in impact:
            self.assertFalse(item.first)
            self.assertEqual(item.fact.down, ["Absolute Gigachad"])
            self.assertEqual(
                item.went_wrong, "Absolute Gigachad was already dead, so a tower was empty.",
            )
            self.assertEqual(_owners(item), [("Absolute Gigachad", 100)])

    def test_the_pull_card_fails_only_the_dead_player(self):
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
        self.assertEqual(failed, ["Absolute Gigachad"])

    def test_alive_outside_the_towers_is_named(self):
        towers = [item for item in self._pull(37) if item.mechanic == "Eternal Conviction"]
        self.assertTrue(towers)
        for item in towers:
            self.assertEqual(item.fact.unsoaked, ["Kiara Blaiddyd"])
            self.assertEqual(_owners(item), [("Kiara Blaiddyd", 100)])

    def test_a_full_party_keeps_the_prey_markers(self):
        impact = [item for item in self._pull(24) if item.mechanic == "Holy Impact"]
        self.assertEqual(len(impact), 8)
        for item in impact:
            self.assertEqual(_owners(item), [("Prey markers", 50)])

    def test_deaths_to_an_unnamed_tower_pass_on_the_group(self):
        towers = [item for item in self._pull(19) if item.mechanic == "Eternal Conviction"]
        self.assertTrue(all(_owners(item) == [("Missed soak", 50)] for item in towers))
        impact = [item for item in self._pull(19) if item.mechanic == "Holy Impact"]
        self.assertEqual(len(impact), 1)
        # The tower victims pass on Missed soak. The paladin walked into the wall after it.
        self.assertEqual(_owners(impact[0]), [("Missed soak", 50), ("Absolute Gigachad", 50)])


if __name__ == "__main__":
    unittest.main()
