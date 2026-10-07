"""Still frames use the replay, not a guessed formation."""

import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.frames import (
    CastClock,
    FrameBook,
    _bursts,
    _waves,
    attach_frames,
    facing_vector,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "XVz8bCqgPw1KRh9d"
PACK = load_pack(ROOT / "fights" / "dsr")


def _report_without_replay() -> Path:
    """A saved log's fight list, with no replay files beside it."""
    report = Path(tempfile.mkdtemp())
    source = ROOT / "data" / "8DYNHQx4C7ytdLb9"
    shutil.copy(source / "fights.json", report / "fights.json")
    return report


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
        conviction = self._frame(11, "Absolute Gigalad", "eternal-conviction", 136.7)
        self.assertGreaterEqual(sum(mark["kind"] == "tower" for mark in conviction["marks"]), 5)
        self.assertEqual(sum(mark["kind"] == "collapse" for mark in conviction["marks"]), 0)
        self.assertIn("towers", conviction["caption"])

    def test_skyward_leap_floor_is_dimensional_collapse_not_towers(self):
        leap = self._frame(21, "Loki Doki", "skyward-leap", 59.5)
        self.assertEqual(sum(mark["kind"] == "tower" for mark in leap["marks"]), 0)
        self.assertEqual(sum(mark["kind"] == "collapse" for mark in leap["marks"]), 8)
        self.assertNotIn("towers", leap["caption"])
        self.assertIn("Dimensional Collapse", leap["caption"])

    def test_unnamed_collapse_spots_are_not_towers(self):
        leap = self.book.mechanic_frame(
            10, 2, 59.3, "skyward-leap", "Skyward Leap", ["Kite Noodle"], PACK,
        )
        self.assertEqual(sum(mark["kind"] == "tower" for mark in leap["marks"]), 0)
        self.assertEqual(sum(mark["kind"] == "collapse" for mark in leap["marks"]), 8)

    def test_strength_towers_are_the_ring_after_the_leap(self):
        frame = self.book.mechanic_frame(
            21, 2, 63.0, "skyward-leap", "Skyward Leap", ["Loki Doki"], PACK,
        )
        towers = [mark for mark in frame["marks"] if mark["kind"] == "tower"]
        self.assertEqual(len(towers), 6)
        for mark in towers:
            self.assertAlmostEqual(math.hypot(mark["x"], mark["y"]), 12, delta=0.5)

    def test_cone_line_runs_from_thordan_to_the_player(self):
        frame = self._frame(68, "Loki Doki", "ascalons-mercy-concealed", 14.5)
        bosses = [mark for mark in frame["marks"] if mark["kind"] == "boss"]
        hits = [mark for mark in frame["marks"] if mark["kind"] == "hit"]
        self.assertEqual(len(bosses), 1)
        self.assertEqual(len(hits), 1)
        victim = next(player for player in frame["players"] if player["dead"])
        self.assertEqual(hits[0]["x2"], victim["x"])
        self.assertEqual(hits[0]["y2"], victim["y"])

    def test_heavy_impact_marks_where_the_pulses_start(self):
        frame = self._frame(42, "Spring Nymphar", "heavy-impact", 45.2)
        impacts = [mark for mark in frame["marks"] if mark["kind"] == "impact"]
        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0]["name"], "Ser Guerrique")
        self.assertAlmostEqual(impacts[0]["x"], 0, delta=0.5)
        self.assertAlmostEqual(impacts[0]["y"], -7, delta=0.5)
        self.assertIn("Heavy Impact starts at Ser Guerrique", frame["caption"])

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
        report = _report_without_replay()
        self.addCleanup(shutil.rmtree, report)
        book = FrameBook(report)
        rows = json.loads((ROOT / "data" / "8DYNHQx4C7ytdLb9" / "judgments.json").read_text(encoding="utf-8"))
        fail = next(row for row in rows if row["outcome"] == "fail" and row["phase"] == 2)
        self.assertIsNone(book.frame(_death(fail), PACK))


class MechanicStillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = FrameBook(REPORT)
        cls.rows = json.loads((REPORT / "judgments.json").read_text(encoding="utf-8"))
        cls.clock = CastClock(REPORT, PACK, _pulls(cls.rows))

    def test_far_apart_casts_keep_two_stills(self):
        self.assertEqual(_waves(_bursts([135.0, 135.2, 148.0, 148.4])), [135.0, 148.0])
        self.assertEqual(len(_waves(_bursts([113.0, 114.8, 116.6, 118.4]))), 1)

    def test_a_clear_gaze_shows_the_party_and_both_eyes(self):
        times = self.clock.times(14, "sanctity-of-the-ward", "dragons-gaze")
        self.assertTrue(times)
        self.assertAlmostEqual(times[0], 112.6, delta=2)
        frame = self.book.mechanic_frame(
            14, 2, times[0], "dragons-gaze", "Dragon's Gaze", [], PACK,
        )
        self.assertIsNotNone(frame)
        self.assertIn("Dragon's Gaze", frame["title"])
        self.assertGreaterEqual(sum(mark["kind"] == "gaze" for mark in frame["marks"]), 2)
        self.assertGreaterEqual(len(frame["players"]), 8)
        self.assertTrue(all(player.get("face") for player in frame["players"]))
        self.assertNotIn("killed", frame["caption"].lower())
        self.assertIn("two marks", frame["caption"])

    def test_a_dodged_cone_uses_the_usual_cast(self):
        times = self.clock.times(11, "ascalons-mercy-opener", "ascalons-mercy-concealed")
        self.assertTrue(times)
        self.assertAlmostEqual(times[0], 14.5, delta=1)
        frame = self.book.mechanic_frame(
            11, 2, times[0], "ascalons-mercy-concealed", "Ascalon's Mercy Concealed", [], PACK,
        )
        self.assertEqual(sum(mark["kind"] == "boss" for mark in frame["marks"]), 1)
        self.assertEqual(sum(mark["kind"] == "hit" for mark in frame["marks"]), 0)
        self.assertFalse(any(player.get("failed") for player in frame["players"]))

    def test_a_failed_cone_draws_a_line_to_that_player(self):
        frame = self.book.mechanic_frame(
            68, 2, 14.5, "ascalons-mercy-concealed", "Ascalon's Mercy Concealed",
            ["Loki Doki"], PACK,
        )
        victim = next(player for player in frame["players"] if player["name"] == "Loki Doki")
        self.assertTrue(victim["failed"])
        hits = [mark for mark in frame["marks"] if mark["kind"] == "hit"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["x2"], victim["x"])
        self.assertIn("Loki Doki failed", frame["caption"])

    def test_a_failed_heavy_impact_still_marks_ser_guerrique(self):
        frame = self.book.mechanic_frame(
            42, 2, 45.2, "heavy-impact", "Heavy Impact", ["Spring Nymphar"], PACK,
        )
        impacts = [mark for mark in frame["marks"] if mark["kind"] == "impact"]
        self.assertEqual(len(impacts), 1)
        self.assertAlmostEqual(impacts[0]["y"], -7, delta=0.5)

    def test_attach_frames_puts_a_still_on_the_mechanic(self):
        row = next(
            item for item in self.rows
            if item["fight"] == 11 and item["name"] == "Kite Noodle" and item["mechanic_id"] == "dragons-gaze"
        )
        payload = {
            "mechanics": [{
                "id": "sanctity-of-the-ward",
                "phase": 2,
                "parts": [{"id": "dragons-gaze"}],
            }],
            "pulls": [{
                "id": 11,
                "deaths": [_death(row)],
                "cards": [{
                    "id": "sanctity-of-the-ward",
                    "name": "Sanctity of the Ward",
                    "parts": [{
                        "id": "dragons-gaze",
                        "name": "Dragon's Gaze",
                        "seats": [
                            {"name": "Kite Noodle", "passed": False},
                            {"name": "Loki Doki", "passed": True},
                        ],
                    }],
                }],
            }],
        }
        attach_frames(REPORT, payload, PACK)
        frames = payload["pulls"][0]["cards"][0]["parts"][0]["frames"]
        self.assertTrue(frames)
        self.assertIn("Dragon's Gaze", frames[0]["title"])
        failed = [player["name"] for player in frames[0]["players"] if player.get("failed")]
        self.assertEqual(failed, ["Kite Noodle"])
        self.assertEqual(payload["pulls"][0]["deaths"][0]["frame"]["killedBy"], "Dragon's Gaze")

    def test_a_clear_mechanic_is_left_without_a_still(self):
        payload = {
            "mechanics": [{
                "id": "sanctity-of-the-ward",
                "phase": 2,
                "parts": [{"id": "dragons-gaze"}],
            }],
            "pulls": [{
                "id": 14,
                "deaths": [],
                "cards": [{
                    "id": "sanctity-of-the-ward",
                    "parts": [{
                        "id": "dragons-gaze",
                        "name": "Dragon's Gaze",
                        "seats": [{"name": "Kite Noodle", "passed": True}],
                    }],
                }],
            }],
        }
        attach_frames(REPORT, payload, PACK)
        self.assertNotIn("frames", payload["pulls"][0]["cards"][0]["parts"][0])

    def test_faith_uses_its_known_time_once_the_pull_is_still_going(self):
        early = _faith_payload(11, 136.7, passed=False)
        attach_frames(REPORT, early, PACK)
        self.assertNotIn("frames", early["pulls"][0]["cards"][0]["parts"][0])
        clear = _faith_payload(41, 147.0, passed=True)
        attach_frames(REPORT, clear, PACK)
        self.assertNotIn("frames", clear["pulls"][0]["cards"][0]["parts"][0])
        late = _faith_payload(41, 147.0, passed=False)
        attach_frames(REPORT, late, PACK)
        frames = late["pulls"][0]["cards"][0]["parts"][0]["frames"]
        self.assertEqual(len(frames), 1)
        self.assertIn("2:26", frames[0]["title"])
        self.assertGreaterEqual(len(frames[0]["players"]), 8)

    def test_a_log_without_a_replay_has_no_mechanic_still(self):
        other = _report_without_replay()
        self.addCleanup(shutil.rmtree, other)
        rows = json.loads((ROOT / "data" / "8DYNHQx4C7ytdLb9" / "judgments.json").read_text(encoding="utf-8"))
        fail = next(row for row in rows if row["outcome"] == "fail" and row["phase"] == 2)
        payload = {
            "mechanics": [{"id": "ascalons-mercy-opener", "phase": 2, "parts": [{"id": fail["mechanic_id"]}]}],
            "pulls": [{
                "id": fail["fight"],
                "deaths": [_death(fail)],
                "cards": [{
                    "id": "ascalons-mercy-opener",
                    "parts": [{
                        "id": fail["mechanic_id"],
                        "name": fail["mechanic"],
                        "seats": [{"name": fail["name"], "passed": False}],
                    }],
                }],
            }],
        }
        attach_frames(other, payload, PACK)
        self.assertNotIn("frame", payload["pulls"][0]["deaths"][0])
        self.assertNotIn("frames", payload["pulls"][0]["cards"][0]["parts"][0])


def _faith_payload(fight_id, died_at, passed=True):
    return {
        "mechanics": [{"id": "meteors", "phase": 2, "parts": [{"id": "faith-unmoving"}]}],
        "pulls": [{
            "id": fight_id,
            "deaths": [{
                "outcome": "raw",
                "t": died_at,
                "phaseId": 2,
                "name": "Kite Noodle",
                "componentId": "eternal-conviction",
                "mechanicId": "meteors",
            }],
            "cards": [{
                "id": "meteors",
                "parts": [{
                    "id": "faith-unmoving",
                    "name": "Faith Unmoving",
                    "seats": [{"name": "Kite Noodle", "passed": passed}],
                }],
            }],
        }],
    }


def _pulls(rows):
    pulls = {}
    for row in rows:
        pull = pulls.setdefault(row["fight"], {"id": row["fight"], "deaths": []})
        cluster = PACK.cluster_for(row["mechanic_id"], row["t"], row["phase"])
        pull["deaths"].append({
            "outcome": row["outcome"],
            "t": row["t"],
            "phaseId": row["phase"],
            "componentId": row["mechanic_id"],
            "mechanicId": cluster.id if cluster else row["mechanic_id"],
        })
    return list(pulls.values())
