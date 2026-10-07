"""Dive from Grace baseline on the Nidhogg pulls in 8DYNHQx4C7ytdLb9."""

import json
import unittest
from collections import Counter
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.dashboard import session_clock, session_payload
from xivloganalyzer.extract import extract_report
from xivloganalyzer.judge import judge_report, roster_from_meta

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "8DYNHQx4C7ytdLb9"


class DiveFromGraceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = load_pack(ROOT / "fights" / "dsr")
        cls.meta = json.loads((REPORT / "fights.json").read_text(encoding="utf-8"))
        facts = extract_report(REPORT, cls.pack)
        cls.judgments = judge_report(
            facts, cls.pack, roster_from_meta(cls.meta, cls.pack)
        )
        cls.phase3 = [item for item in cls.judgments if item.fact.phase == 3]

    def _one(self, fight, name, guid):
        rows = [
            item
            for item in self.phase3
            if item.fact.fight == fight
            and item.fact.name == name
            and item.fact.guid == guid
        ]
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_phase_three_counts(self):
        counts = Counter(item.outcome for item in self.phase3)
        self.assertEqual(counts["fail"], 42)
        self.assertEqual(counts["raw"], 15)
        self.assertEqual(counts["low"], 3)
        self.assertEqual(counts["unknown"], 5)
        self.assertEqual(counts["environment"], 0)
        walls = [item for item in self.phase3 if item.mechanic_id == "deathwall"]
        self.assertEqual(len(walls), 8)
        unknown = {item.mechanic for item in self.phase3 if item.outcome == "unknown"}
        self.assertEqual(unknown, {"Final Chorus", "attack"})

    def test_short_stack_and_full_stack(self):
        short = self._one(16, "Kitana Kahn", 26388)
        self.assertEqual(short.outcome, "fail")
        self.assertEqual(short.blames[0].who, "Missing bodies")
        self.assertEqual(short.blames[0].confidence, 50)
        raw = self._one(26, "Loki Doki", 26388)
        self.assertEqual(raw.outcome, "raw")
        self.assertEqual(
            [blame.who for blame in raw.blames],
            ["Loki Doki", "Spring Nymphar", "Party mitigation"],
        )

    def test_arrow_on_the_wrong_side_owns_the_landing(self):
        loki = self._one(27, "Loki Doki", 26384)
        self.assertEqual(loki.outcome, "fail")
        self.assertEqual(loki.cause, "arrow")
        self.assertEqual(loki.went_wrong, "Loki Doki took the down arrow west, facing west.")
        spring = self._one(27, "Spring Nymphar", 26384)
        self.assertEqual(spring.went_wrong, "Spring Nymphar got hit by Loki Doki's dive.")
        for item in (loki, spring):
            self.assertEqual([blame.to_dict() for blame in item.blames], [{"who": "Loki Doki", "confidence": 100}])
        divers = {diver["name"]: diver for diver in spring.fact.divers}
        self.assertEqual(divers["Spring Nymphar"]["marker"], "up arrow")
        self.assertEqual(divers["Spring Nymphar"]["facing"], "east")

    def test_arrow_holder_fails_the_card_not_the_player_hit(self):
        when = session_clock(REPORT, self.meta)
        payload = session_payload(self.judgments, self.pack, REPORT.name, when, self.meta)
        pull = next(row for row in payload["pulls"] if row["id"] == 27)
        card = next(row for row in pull["cards"] if row["id"] == "dive-from-grace")
        part = next(part for part in card["parts"] if part["id"] == "dark-elusive-jump")
        seats = {seat["name"]: seat for seat in part["seats"]}
        self.assertFalse(seats["Loki Doki"]["passed"])
        self.assertTrue(seats["Spring Nymphar"]["passed"])

    def test_circles_in_one_landing_are_a_miscommunication(self):
        jumps = [
            item for item in self.phase3 if item.fact.fight == 46 and item.fact.guid == 26382
        ]
        self.assertEqual(len(jumps), 4)
        self.assertTrue(all(item.cause == "miscommunication" for item in jumps))
        self.assertTrue(
            all(blame.to_dict() == {"who": "Miscommunication", "confidence": 25}
                for item in jumps for blame in item.blames)
        )

    def test_towers_split_debuff_soak_from_empty_tower(self):
        debuff = self._one(27, "Speed Panda", 26385)
        self.assertEqual(debuff.outcome, "fail")
        self.assertEqual(debuff.went_wrong, "Speed Panda soaked with the dive debuff.")
        self.assertEqual(debuff.blames[0].confidence, 100)
        low = self._one(27, "Kite Noodle", 26395)
        self.assertEqual(low.outcome, "low")
        tower = self._one(36, "Kitana Kahn", 26395)
        self.assertEqual(tower.outcome, "fail")
        self.assertEqual(tower.blames[0].who, "Missed soak")
        soak = self._one(36, "Kite Noodle", 26395)
        self.assertEqual(soak.outcome, "raw")

    def test_wheel_and_line_are_the_player_who_stood_there(self):
        wheel = self._one(30, "Loki Doki", 26390)
        self.assertEqual(wheel.outcome, "fail")
        self.assertEqual(wheel.went_wrong, "Loki Doki was on the wrong side.")
        line = self._one(46, "Kite Noodle", 26378)
        self.assertEqual(line.outcome, "fail")
        self.assertEqual(line.blames[0].who, "Kite Noodle")

    def test_went_wrong_is_one_short_sentence(self):
        for item in self.judgments:
            text = item.went_wrong
            self.assertTrue(text.endswith("."), text)
            self.assertEqual(text.count("."), 1, text)
            self.assertLessEqual(len(text), 90, text)

    def test_pull_card_shows_the_nidhogg_stop(self):
        when = session_clock(REPORT, self.meta)
        payload = session_payload(self.judgments, self.pack, REPORT.name, when, self.meta)
        pull = next(row for row in payload["pulls"] if row["id"] == 16)
        card = next(row for row in pull["cards"] if row["id"] == "dive-from-grace")
        eye = next(part for part in card["parts"] if part["id"] == "eye-of-the-tyrant")
        seats = {seat["name"]: seat for seat in eye["seats"]}
        self.assertFalse(seats["Kitana Kahn"]["passed"])
        self.assertFalse(seats["Absolute Gigalad"]["passed"])
        self.assertTrue(seats["Loki Doki"]["passed"])
