"""Dive from Grace baseline on the Nidhogg pulls in 8DYNHQx4C7ytdLb9."""

import json
import unittest
from collections import Counter
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.dashboard import attach_debuffs, session_clock, session_payload
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
        self.assertEqual(counts["fail"], 57)
        self.assertEqual(counts["raw"], 8)
        self.assertEqual(counts["low"], 0)
        self.assertEqual(counts["unknown"], 0)
        # Pull 33: Gigalad's circle landed in the north stack and knocked five players into the wall.
        self.assertEqual(counts["environment"], 0)
        walls = [item for item in self.phase3 if item.mechanic_id == "deathwall"]
        self.assertEqual(len(walls), 8)
        # Final Chorus is the opening raidwide. The first auto-attack is a frontal cleave.
        chorus = [item for item in self.phase3 if item.mechanic == "Final Chorus"]
        self.assertEqual({item.outcome for item in chorus}, {"raw"})
        autos = [item for item in self.phase3 if item.mechanic_id == "nidhogg-auto"]
        self.assertEqual({item.fact.name for item in autos}, {"Spring Nymphar", "Kiara Blaiddyd"})

    def test_short_stack_and_full_stack(self):
        # The 2s and 3s stack. Kite, Loki, and Kiara were already dead, and each gap
        # belongs to whoever owned that death: the healers for Final Chorus, Kiara for the auto.
        # Each dead player is one share, split the way their death was.
        short = self._one(16, "Kitana Kahn", 26388)
        self.assertEqual(short.outcome, "fail")
        self.assertEqual(short.fact.down, ["Kite Noodle", "Loki Doki", "Kiara Blaiddyd"])
        self.assertEqual(
            [blame.to_dict() for blame in short.blames],
            [
                {"who": "Loki Doki", "confidence": 25, "via": ["Kite Noodle"]},
                {"who": "Spring Nymphar", "confidence": 41, "via": ["Kite Noodle", "Loki Doki"]},
                {"who": "Kiara Blaiddyd", "confidence": 33},
            ],
        )
        self.assertEqual(short.basis, "hit-list")
        raw = self._one(26, "Loki Doki", 26388)
        self.assertEqual(raw.outcome, "raw")
        # The Eye of the Tyrant file says the hit had no party mitigation.
        self.assertEqual(raw.fact.multiplier, 1.0)
        self.assertEqual(raw.fact.missing, [])
        self.assertEqual([blame.who for blame in raw.blames], ["Loki Doki", "Spring Nymphar", "Party mitigation"])

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

    def test_first_mistake_is_the_arrow_holder_not_the_player_hit(self):
        loki = self._one(27, "Loki Doki", 26384)
        spring = self._one(27, "Spring Nymphar", 26384)
        self.assertTrue(loki.first)
        self.assertFalse(spring.first)
        self.assertEqual(
            spring.first_mistake,
            "Loki Doki dying to Dark Elusive Jump and Spring Nymphar dying to "
            "Loki Doki's Dark Elusive Jump at 30.9s into Nidhogg",
        )

    def test_card_lists_each_players_number_and_dive(self):
        when = session_clock(REPORT, self.meta)
        payload = session_payload(self.judgments, self.pack, REPORT.name, when, self.meta)
        attach_debuffs(REPORT, payload, self.pack, self.meta)
        pull = next(row for row in payload["pulls"] if row["id"] == 27)
        card = next(row for row in pull["cards"] if row["id"] == "dive-from-grace")
        self.assertEqual(card["debuffs"]["columns"], ["Number", "Dive"])
        rows = [(row["name"], *row["values"]) for row in card["debuffs"]["players"]]
        self.assertEqual(rows, [
            ("Spring Nymphar", "1", "up arrow"),
            ("Speed Panda", "1", "circle"),
            ("Loki Doki", "1", "down arrow"),
            ("Absolute Gigachad", "2", "up arrow"),
            ("Kite Noodle", "2", "down arrow"),
            ("Absolute Gigalad", "3", "circle"),
            ("Kiara Blaiddyd", "3", "circle"),
            ("Kitana Kahn", "3", "circle"),
        ])
        spring = card["debuffs"]["players"][0]
        self.assertEqual(spring["statuses"], [
            {"id": 1003004, "name": "First in Line"},
            {"id": 1002756, "name": "Spineshatter Dive Target"},
        ])

    def test_every_listed_debuff_has_its_game_icon(self):
        icons = ROOT / "src" / "xivloganalyzer" / "status_icons"
        for cluster in self.pack.clusters:
            for column in cluster.debuffs:
                for guid in column.labels:
                    self.assertTrue((icons / f"{guid}.png").is_file(), f"{cluster.id} {guid}")

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
        # 26395 is only ever the explosion of an unsoaked tower, about 2s after the soak, so every hit is a fail.
        for fight, name in ((27, "Kite Noodle"), (36, "Kitana Kahn"), (36, "Kite Noodle")):
            self.assertEqual(self._one(fight, name, 26395).outcome, "fail")
        # With the soak file, the 3s who were alive and not in a tower own it.
        tower = self._one(36, "Kitana Kahn", 26395)
        self.assertEqual(sorted(blame.who for blame in tower.blames), ["Absolute Gigachad", "Loki Doki", "Spring Nymphar"])

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
        # The two who died in the short stack were in place. The missing players' owners failed it.
        self.assertTrue(seats["Kitana Kahn"]["passed"])
        self.assertTrue(seats["Absolute Gigalad"]["passed"])
        self.assertFalse(seats["Loki Doki"]["passed"])
        self.assertFalse(seats["Kiara Blaiddyd"]["passed"])
