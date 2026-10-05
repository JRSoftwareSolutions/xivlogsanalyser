"""Sessions are grouped by the day and time they were played."""

import json
import unittest
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.dashboard import build_timeline, library_payload, session_clock, wall_clock

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "XVz8bCqgPw1KRh9d"


def _session(code, started, day, label, clock):
    return {
        "code": code,
        "fight": "Dragonsong's Reprise",
        "title": "Ultimates (Legacy)",
        "owner": "Kite21",
        "started": started,
        "day": day,
        "dayLabel": label,
        "timeLabel": clock,
        "raw": 1,
        "fail": 0,
        "pulls": [],
    }


class SessionClockTest(unittest.TestCase):
    def test_known_log_is_the_oct_3_night(self):
        meta = json.loads((REPORT / "fights.json").read_text(encoding="utf-8"))
        when = session_clock(REPORT, meta)
        fight_68 = next(fight for fight in meta["fights"] if fight["id"] == 68)
        self.assertEqual(when["day"], "2026-10-03")
        self.assertEqual(when["dayLabel"], "Sat 3 Oct 2026")
        self.assertEqual(when["timeLabel"], "21:17–00:03")
        self.assertEqual(when["owner"], "Kite21")
        self.assertEqual(when["title"], "Ultimates (Legacy)")
        self.assertEqual(wall_clock(when["started"], fight_68["start_time"]), "00:02")

    def test_timeline_is_every_pull_and_the_best_is_thordan(self):
        meta = json.loads((REPORT / "fights.json").read_text(encoding="utf-8"))
        when = session_clock(REPORT, meta)
        overview = build_timeline(meta, when, judged=set())
        ended = {}
        for pull in overview["pulls"]:
            ended[pull["phase"]] = ended.get(pull["phase"], 0) + 1
        self.assertEqual(len(overview["pulls"]), 68)
        self.assertEqual(ended[1], 11)
        self.assertEqual(ended[2], 57)
        self.assertEqual(overview["best"]["id"], 49)
        self.assertEqual(overview["best"]["phaseName"], "Thordan")
        self.assertEqual(overview["best"]["bossPct"], 30.3)
        pull_68 = next(pull for pull in overview["pulls"] if pull["id"] == 68)
        self.assertEqual(pull_68["when"], "00:02")
        self.assertEqual(pull_68["bossPct"], 65.1)
        self.assertFalse(pull_68["judged"])
        by_id = {pull["id"]: pull for pull in overview["pulls"]}
        self.assertEqual(by_id[4]["mechanic"], "Empty Dimension")
        self.assertEqual(by_id[3]["mechanic"], "Hyperdimensional Slash")
        self.assertEqual(by_id[53]["mechanic"], "Faith Unmoving")
        self.assertEqual(by_id[7]["mechanic"], "Pure of Heart")
        self.assertEqual(by_id[9]["mechanic"], "Ascalon's Mercy Concealed")
        self.assertEqual(by_id[23]["mechanic"], "Ascalon's Might")
        self.assertEqual(by_id[68]["mechanic"], "Strength of the Ward")
        self.assertEqual(by_id[18]["mechanic"], "Heavenly Heel")
        self.assertEqual(by_id[49]["mechanic"], "Sanctity of the Ward")
        self.assertEqual(by_id[66]["mechanic"], "Meteors")
        marks = {mark["name"]: mark["at"] for mark in overview["markers"]}
        self.assertLess(marks["Strength of the Ward"], marks["Sanctity of the Ward"])
        self.assertLess(by_id[68]["reached"], marks["Sanctity of the Ward"])
        self.assertGreater(by_id[49]["reached"], marks["Sanctity of the Ward"])
        self.assertLess(by_id[49]["reached"], marks["Meteors"])
        self.assertGreater(by_id[66]["reached"], marks["Meteors"])


class ClusterTimelineTest(unittest.TestCase):
    def test_stops_follow_starts_and_each_names_a_skill(self):
        pack = load_pack(ROOT / "fights" / "dsr")
        starts = [cluster.starts for cluster in pack.clusters]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(
            [cluster.name for cluster in pack.clusters],
            [
                "Ascalon's Mercy Concealed",
                "Ascalon's Might",
                "Strength of the Ward",
                "Heavenly Heel",
                "Sanctity of the Ward",
                "Meteors",
            ],
        )
        known = {mechanic.id for mechanic in pack.mechanics}
        covered = set()
        for cluster in pack.clusters:
            skill = ROOT / ".cursor" / "skills" / cluster.skill / "SKILL.md"
            self.assertTrue(skill.is_file(), cluster.skill)
            self.assertTrue(cluster.parts, cluster.id)
            for part in cluster.parts:
                self.assertIn(part.mechanic_id, known)
                covered.add(part.mechanic_id)
        self.assertEqual(covered, known)


class SessionLibraryTest(unittest.TestCase):
    def test_newest_day_first_and_same_day_in_time_order(self):
        older = _session("aaa", "2026-10-01T18:00:00+02:00", "2026-10-01", "Thu 1 Oct 2026", "18:00–19:00")
        later = _session("bbb", "2026-10-03T22:00:00+02:00", "2026-10-03", "Sat 3 Oct 2026", "22:00–23:10")
        earlier = _session("ccc", "2026-10-03T20:00:00+02:00", "2026-10-03", "Sat 3 Oct 2026", "20:00–21:00")
        library = library_payload([older, later, earlier])
        self.assertEqual([day["day"] for day in library["days"]], ["2026-10-03", "2026-10-01"])
        self.assertEqual([item["code"] for item in library["days"][0]["sessions"]], ["ccc", "bbb"])
        self.assertEqual(library["days"][0]["sessions"][1]["timeLabel"], "22:00–23:10")


if __name__ == "__main__":
    unittest.main()
