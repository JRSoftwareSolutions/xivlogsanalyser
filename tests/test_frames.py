"""Still frames use the replay, not a guessed formation."""

import json
import math
import unittest
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.frames import FrameBook, attach_frames, facing_vector

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "XVz8bCqgPw1KRh9d"
PACK = load_pack(ROOT / "fights" / "dsr")


def _death(row: dict) -> dict:
    return {
        "outcome": row["outcome"],
        "t": row["t"],
        "name": row["name"],
        "fight": row["fight"],
        "componentId": row["mechanic_id"],
        "cast": row["mechanic"],
        "wrong": row["went_wrong"],
    }


def _load():
    rows = json.loads((REPORT / "judgments.json").read_text(encoding="utf-8"))
    return {(row["fight"], row["name"], row["mechanic_id"], round(row["t"], 1)): row for row in rows}


class FacingTest(unittest.TestCase):
    def test_south_party_facing_points_north(self):
        face = facing_vector(-158)
        self.assertIsNotNone(face)
        self.assertAlmostEqual(face[0], 0, delta=0.05)
        self.assertAlmostEqual(face[1], -1, delta=0.05)


class StillFrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = FrameBook(REPORT)
        cls.rows = _load()

    def _frame(self, fight, name, mechanic, t):
        row = self.rows[(fight, name, mechanic, t)]
        return self.book.frame(_death(row), PACK)

    def test_gaze_shows_facing_and_both_enemies(self):
        frame = self._frame(11, "Kite Noodle", "dragons-gaze", 112.6)
        self.assertEqual(frame["killedBy"], "Dragon's Gaze")
        gazes = [mark for mark in frame["marks"] if mark["kind"] == "gaze"]
        self.assertEqual(len(gazes), 2)
        for mark in gazes:
            self.assertGreater(math.hypot(mark["x"], mark["y"]), 18)
        victim = next(player for player in frame["players"] if player["dead"])
        self.assertEqual(victim["name"], "Kite Noodle")
        self.assertIn("face", victim)
        best = 0
        for mark in gazes:
            dx = mark["x"] - victim["x"]
            dy = mark["y"] - victim["y"]
            reach = math.hypot(dx, dy)
            best = max(best, (victim["face"][0] * dx + victim["face"][1] * dy) / reach)
        self.assertGreater(best, 0.7)
        self.assertIn("two marks", frame["caption"])

    def test_hysteria_into_a_later_hit_keeps_the_gazes(self):
        frame = self._frame(10, "Kitana Kahn", "bright-flare", 115.0)
        self.assertEqual(frame["killedBy"], "Bright Flare")
        victim = next(player for player in frame["players"] if player["dead"])
        self.assertTrue(victim["hysteria"])
        self.assertIn("face", victim)
        self.assertEqual(sum(mark["kind"] == "gaze" for mark in frame["marks"]), 2)
        self.assertGreaterEqual(sum(mark["kind"] == "orb" for mark in frame["marks"]), 2)
        self.assertIn("Hysteria", frame["caption"])
        self.assertIn("orbs", frame["caption"])

    def test_comet_overlap_tags_prey(self):
        frame = self._frame(41, "Absolute Gigachad", "holy-impact", 142.8)
        self.assertEqual(frame["killedBy"], "Holy Impact")
        self.assertGreaterEqual(sum(mark["kind"] == "comet" for mark in frame["marks"]), 2)
        prey = sorted(player["name"] for player in frame["players"] if player["prey"])
        self.assertEqual(prey, ["Absolute Gigachad", "Absolute Gigalad"])
        self.assertIn("Prey", frame["caption"])

    def test_empty_tower_draws_the_tower_ring(self):
        leap = self._frame(21, "Loki Doki", "skyward-leap", 59.5)
        self.assertGreaterEqual(sum(mark["kind"] == "tower" for mark in leap["marks"]), 5)
        conviction = self._frame(11, "Absolute Gigalad", "eternal-conviction", 136.7)
        self.assertGreaterEqual(sum(mark["kind"] == "tower" for mark in conviction["marks"]), 5)
        self.assertIn("towers", conviction["caption"])

    def test_cone_line_runs_from_thordan_to_the_player(self):
        frame = self._frame(68, "Loki Doki", "ascalons-mercy-concealed", 14.5)
        bosses = [mark for mark in frame["marks"] if mark["kind"] == "boss"]
        hits = [mark for mark in frame["marks"] if mark["kind"] == "hit"]
        self.assertEqual(len(bosses), 1)
        self.assertEqual(len(hits), 1)
        victim = next(player for player in frame["players"] if player["dead"])
        self.assertEqual(hits[0]["x2"], victim["x"])
        self.assertEqual(hits[0]["y2"], victim["y"])

    def test_a_raw_death_has_no_frame(self):
        row = next(
            item for item in json.loads((REPORT / "judgments.json").read_text(encoding="utf-8"))
            if item["outcome"] == "raw"
        )
        self.assertIsNone(self.book.frame(_death(row), PACK))

    def test_attach_frames_keeps_the_picture_on_the_death(self):
        row = self.rows[(11, "Kite Noodle", "dragons-gaze", 112.6)]
        payload = {"pulls": [{"id": 11, "phaseId": 2, "deaths": [_death(row)]}]}
        attach_frames(REPORT, payload, PACK)
        self.assertEqual(payload["pulls"][0]["deaths"][0]["frame"]["killedBy"], "Dragon's Gaze")

    def test_a_log_without_a_replay_has_no_frame(self):
        other = ROOT / "data" / "8DYNHQx4C7ytdLb9"
        book = FrameBook(other)
        rows = json.loads((other / "judgments.json").read_text(encoding="utf-8"))
        fail = next(row for row in rows if row["outcome"] == "fail" and row["phase"] == 2)
        self.assertIsNone(book.frame(_death(fail), PACK))
