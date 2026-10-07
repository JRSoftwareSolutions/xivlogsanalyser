"""Sessions are grouped by the day and time they were played."""

import json
import unittest
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.dashboard import (
    build_timeline,
    library_payload,
    session_clock,
    session_payload,
    session_summary,
    wall_clock,
    write_library,
    write_session_page,
)
from xivloganalyzer.extract import read_facts
from xivloganalyzer.judge import judge_report

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
        self.assertGreater(marks["Dive from Grace"], marks["Meteors"])


class NidhoggChartTest(unittest.TestCase):
    def test_phase_three_bars_sit_above_thordan(self):
        report = ROOT / "data" / "8DYNHQx4C7ytdLb9"
        meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
        when = session_clock(report, meta)
        overview = build_timeline(meta, when, judged=set())
        by_phase = {}
        for pull in overview["pulls"]:
            by_phase.setdefault(pull["phase"], []).append(pull)
        thordan = by_phase[2]
        nidhogg = by_phase[3]
        self.assertEqual(len(nidhogg), 8)
        self.assertGreater(min(pull["reached"] for pull in nidhogg), max(pull["reached"] for pull in thordan))
        self.assertTrue(all(pull["phaseName"] == "Nidhogg" for pull in nidhogg))
        self.assertTrue(all(pull["mechanic"] == "Dive from Grace" for pull in nidhogg))
        marks = {mark["name"]: mark["at"] for mark in overview["markers"]}
        self.assertGreater(marks["Dive from Grace"], marks["Meteors"])
        self.assertGreater(min(pull["reached"] for pull in nidhogg), marks["Dive from Grace"])


class ClusterTimelineTest(unittest.TestCase):
    def test_stops_follow_starts_and_each_names_a_skill(self):
        pack = load_pack(ROOT / "fights" / "dsr")
        order = [(cluster.phase, cluster.starts) for cluster in pack.clusters]
        self.assertEqual(order, sorted(order))
        self.assertEqual(
            [cluster.name for cluster in pack.clusters],
            [
                "Ascalon's Mercy Concealed",
                "Ascalon's Might",
                "Strength of the Ward",
                "Heavenly Heel",
                "Sanctity of the Ward",
                "Meteors",
                "Dive from Grace",
            ],
        )
        known = {mechanic.id for mechanic in pack.mechanics}
        covered = set()
        for cluster in pack.clusters:
            skill = ROOT / ".claude" / "skills" / cluster.skill / "SKILL.md"
            self.assertTrue(skill.is_file(), cluster.skill)
            self.assertTrue(cluster.parts, cluster.id)
            for part in cluster.parts:
                self.assertIn(part.mechanic_id, known)
                covered.add(part.mechanic_id)
        self.assertEqual(covered, known)


def _payload():
    pack = load_pack(ROOT / "fights" / "dsr")
    meta = json.loads((REPORT / "fights.json").read_text(encoding="utf-8"))
    when = session_clock(REPORT, meta)
    judgments = judge_report(read_facts(REPORT), pack)
    return session_payload(judgments, pack, REPORT.name, when, meta)


def _seats(part):
    return {seat["name"]: seat for seat in part["seats"]}


class PullCardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = _payload()

    def _pull(self, pull_id):
        return next(pull for pull in self.payload["pulls"] if pull["id"] == pull_id)

    def _card(self, pull_id, card_id):
        return next(card for card in self._pull(pull_id)["cards"] if card["id"] == card_id)

    def test_concealed_opener_marks_the_player_who_was_hit(self):
        card = self._card(68, "ascalons-mercy-opener")
        self.assertEqual([part["name"] for part in card["parts"]], ["Ascalon's Mercy Concealed"])
        seats = _seats(card["parts"][0])
        self.assertEqual(len(seats), 8)
        self.assertFalse(seats["Loki Doki"]["passed"])
        self.assertEqual(seats["Loki Doki"]["job"], "AST")
        self.assertTrue(seats["Spring Nymphar"]["passed"])
        self.assertEqual(
            [seat["name"] for seat in card["parts"][0]["seats"][:2]],
            ["Absolute Gigachad", "Absolute Gigalad"],
        )

    def test_strength_cards_mark_each_component(self):
        card = self._card(68, "strength-of-the-ward")
        by_name = {part["name"]: part for part in card["parts"]}
        self.assertEqual(
            [part["name"] for part in card["parts"]],
            [
                "Lightning Storm",
                "Heavy Impact",
                "Ascalon's Mercy Concealed",
                "Dimensional Collapse",
                "Skyward Leap",
                "Dragon's Rage",
                "Holy Shield Bash",
                "Holy Bladedance",
                "Eternal Conviction",
            ],
        )
        self.assertTrue(all(seat["passed"] for seat in by_name["Lightning Storm"]["seats"]))
        self.assertFalse(_seats(by_name["Heavy Impact"])["Kite Noodle"]["passed"])
        self.assertTrue(_seats(by_name["Heavy Impact"])["Loki Doki"]["passed"])
        concealed = _seats(by_name["Ascalon's Mercy Concealed"])
        self.assertFalse(concealed["Spring Nymphar"]["passed"])
        self.assertTrue(concealed["Loki Doki"]["passed"])
        leap = _seats(by_name["Skyward Leap"])
        self.assertFalse(leap["Kitana Kahn"]["passed"])
        self.assertFalse(leap["Kiara Blaiddyd"]["passed"])
        self.assertTrue(leap["Spring Nymphar"]["passed"])
        names = {card["id"] for card in self._pull(68)["cards"]}
        self.assertNotIn("heavenly-heel-swap", names)
        self.assertNotIn("meteors", names)

    def test_a_raw_death_still_passes_the_component(self):
        card = self._card(12, "strength-of-the-ward")
        rage = next(part for part in card["parts"] if part["id"] == "dragons-rage")
        self.assertTrue(_seats(rage)["Loki Doki"]["passed"])
        opener = self._card(12, "ascalons-mercy-opener")
        hit = _seats(opener["parts"][0])
        self.assertFalse(hit["Kitana Kahn"]["passed"])
        self.assertFalse(hit["Spring Nymphar"]["passed"])

    def test_should_have_been_names_only_this_cast(self):
        pack = load_pack(ROOT / "fights" / "dsr")
        opener = pack.part_for("ascalons-might", 17, 2)
        swap = pack.part_for("ascalons-might", 85, 2)
        self.assertNotIn("Heavenly Heel", opener.should_have_been)
        self.assertNotIn("opener", swap.should_have_been.lower())
        self.assertNotIn("71", swap.should_have_been)
        for pull in self.payload["pulls"]:
            for row in pull["deaths"]:
                text = row["should"]
                cast = row["cast"]
                if cast == "Ascalon's Mercy Concealed" and row["t"] < 30:
                    self.assertIn("in front", text)
                    self.assertNotIn("4/4", text)
                    self.assertNotIn("Strength", text)
                if cast == "Ascalon's Mercy Concealed" and row["t"] >= 30:
                    self.assertIn("4/4", text)
                    self.assertNotIn("in front", text)
                    self.assertNotIn("baiter", text)
                if cast == "Ascalon's Might" and row["t"] >= 50:
                    self.assertNotIn("opener", text.lower())
                    self.assertNotIn("71", text)
                    self.assertIn("Heavenly Heel", text)
                if cast == "Heavenly Heel":
                    self.assertNotIn("Ascalon's Might", text)
                    self.assertNotIn("three hits", text)
                    self.assertNotIn("three-hit", text)
                if cast != "Skyward Leap":
                    continue
                head = row["happened"].split(" unmitigated", 1)[0].replace(",", "")
                if not head.isdigit():
                    continue
                hit = int(head)
                if hit > 150000:
                    self.assertIn("explodes", text)
                    self.assertNotIn("East and west", text)
                    self.assertNotIn("59", text)
                else:
                    self.assertIn("blue marker", text)
                    self.assertNotIn("explodes", text)
                    self.assertNotIn("600", text)

    def test_a_pull_that_wipes_in_the_opener_has_no_strength_card(self):
        names = [card["name"] for card in self._pull(23)["cards"]]
        self.assertEqual(names, ["Ascalon's Mercy Concealed", "Ascalon's Might"])
        might = self._card(23, "ascalons-might-opener")
        self.assertTrue(all(seat["passed"] for seat in might["parts"][0]["seats"]))

    def test_each_mechanic_counts_the_pulls_that_reached_it_and_had_a_mistake(self):
        by_id = {mech["id"]: mech for mech in self.payload["mechanics"]}
        strength = by_id["strength-of-the-ward"]
        cards = [
            card for pull in self.payload["pulls"] for card in pull["cards"]
            if card["id"] == "strength-of-the-ward"
        ]
        self.assertEqual(strength["reached"], len(cards))
        self.assertEqual((strength["reached"], strength["mistakes"]), (53, 20))
        self.assertEqual(by_id["dive-from-grace"]["reached"], 0)
        summary = session_summary(self.payload, "")
        self.assertEqual(
            next(row for row in summary["mechanics"] if row["id"] == "strength-of-the-ward")["mistakes"],
            20,
        )


class UnscoredPullTest(unittest.TestCase):
    def test_a_pull_without_a_percentage_does_not_win(self):
        report = ROOT / "data" / "3wzL6x4VHTmvNkhq"
        meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
        when = session_clock(report, meta)
        overview = build_timeline(meta, when, judged=set())
        self.assertEqual(when["day"], "2026-09-30")
        self.assertEqual(when["timeLabel"], "21:44–00:03")
        self.assertEqual(len(overview["pulls"]), 66)
        self.assertEqual(overview["best"]["id"], 66)
        self.assertEqual(overview["best"]["phaseName"], "Thordan")
        self.assertEqual(overview["best"]["bossPct"], 32.6)


def _sample_payload():
    return {
        "code": "abc",
        "fight": "Dragonsong's Reprise",
        "title": "Ultimates (Legacy)",
        "owner": "Kite21",
        "started": "2026-10-03T19:17:00+00:00",
        "day": "2026-10-03",
        "dayLabel": "Sat 3 Oct 2026",
        "timeLabel": "21:17–00:03",
        "raw": 1,
        "fail": 2,
        "low": 0,
        "unknown": {},
        "totals": {"raw": 1},
        "mechanics": [
            {
                "id": "meteors",
                "name": "Meteors",
                "phase": 2,
                "starts": 100,
                "should": "UNIQUE_SHOULD_TEXT",
                "parts": [{"name": "Holy Comet"}],
            }
        ],
        "pulls": [
            {
                "id": 4,
                "bossPct": 30.0,
                "when": "22:00",
                "phase": "Thordan",
                "clock": "4:00",
                "deaths": [{"happened": "UNIQUE_HAPPENED_TEXT", "should": "stack"}],
                "cards": [{"name": "Meteors"}],
            }
        ],
        "overview": {
            "pulls": [{"id": 4, "reached": 120, "phase": 2, "phaseName": "Thordan"}],
            "markers": [{"name": "Meteors", "phase": 2, "at": 100}],
            "best": {"id": 4},
            "phases": [],
        },
    }


class SessionDetailTest(unittest.TestCase):
    def test_summary_keeps_the_chart_and_drops_the_death_review(self):
        summary = session_summary(_sample_payload(), "session.html?v=abc")
        self.assertEqual(summary["detail"], "session.html?v=abc")
        self.assertEqual(summary["overview"]["pulls"][0]["reached"], 120)
        self.assertEqual(summary["pulls"], [{
            "id": 4,
            "bossPct": 30.0,
            "when": "22:00",
            "phase": "Thordan",
            "clock": "4:00",
        }])
        self.assertEqual(summary["mechanics"], [{
            "id": "meteors",
            "name": "Meteors",
            "phase": 2,
            "starts": 100,
            "reached": 0,
            "mistakes": 0,
        }])
        blob = json.dumps(summary)
        self.assertNotIn("UNIQUE_HAPPENED_TEXT", blob)
        self.assertNotIn("UNIQUE_SHOULD_TEXT", blob)

    def test_library_page_loads_death_reviews_from_the_session_page(self):
        import tempfile

        payload = _sample_payload()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "data" / payload["code"]
            report.mkdir(parents=True)
            write_session_page(report, payload)
            page = write_library(root, [payload])
            dashboard = page.read_text(encoding="utf-8")
            session_page = (report / "session.html").read_text(encoding="utf-8")
        self.assertNotIn("UNIQUE_HAPPENED_TEXT", dashboard)
        self.assertNotIn("UNIQUE_SHOULD_TEXT", dashboard)
        self.assertIn("UNIQUE_HAPPENED_TEXT", session_page)
        self.assertIn("UNIQUE_SHOULD_TEXT", session_page)
        self.assertIn("General trend", dashboard)
        self.assertIn("session-preview", dashboard)
        self.assertIn("loadDetail", dashboard)
        self.assertIn('<script type="application/json" id="session-detail">', session_page)
        self.assertNotIn('<script type="application/json" id="session-detail">', dashboard)
        self.assertIn("data/abc/session.html?v=", dashboard)
        self.assertNotIn("detail.js", dashboard)
        self.assertNotIn("detail.js", session_page)
        self.assertFalse((report / "detail.js").exists())
        self.assertIn('location.protocol === "file:"', dashboard)
        self.assertIn("detailFromFrame", dashboard)
        self.assertIn("postDetailToParent()", session_page)
        marker = 'id="session-detail">'
        start = session_page.index(marker) + len(marker)
        end = session_page.index("</script>", start)
        body = json.loads(session_page[start:end])
        self.assertEqual(body["pulls"][0]["deaths"][0]["happened"], "UNIQUE_HAPPENED_TEXT")
        self.assertEqual(body["mechanics"][0]["should"], "UNIQUE_SHOULD_TEXT")


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
