"""Rules every saved call keeps, whatever the log. A new log is checked the moment it is analyzed."""

import json
import unittest
from collections import defaultdict
from pathlib import Path

from xivloganalyzer.calls import key
from xivloganalyzer.judge import BASES, CONTEXT_SHARES, GROUP_LABELS
from xivloganalyzer.pipeline import report_dirs
from xivloganalyzer.roster import pull_players

ROOT = Path(__file__).resolve().parents[1]


def _saved():
    for report in report_dirs(ROOT):
        meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
        rows = json.loads((report / "judgments.json").read_text(encoding="utf-8"))
        yield report, meta, rows


class InvariantTest(unittest.TestCase):
    def test_owners_played_the_pull_or_are_a_label(self):
        for report, meta, rows in _saved():
            rosters: dict[int, set[str]] = {}
            for row in rows:
                fight = row["fight"]
                if fight not in rosters:
                    rosters[fight] = {actor["name"] for actor in pull_players(meta, fight)}
                allowed = rosters[fight] | GROUP_LABELS | CONTEXT_SHARES
                for blame in row["blames"]:
                    self.assertIn(blame["who"], allowed, (report.name, fight, row["name"]))
                    for name in blame.get("via") or []:
                        self.assertIn(name, rosters[fight], (report.name, fight, row["name"]))
                for cause in row["first_causes"]:
                    for who in cause["owners"]:
                        self.assertIn(who, allowed, (report.name, fight, cause))

    def test_every_mistake_has_an_owner_and_a_basis(self):
        for report, _meta, rows in _saved():
            for row in rows:
                where = (report.name, row["fight"], row["time"], row["name"])
                if row["outcome"] in {"fail", "raw", "low"}:
                    self.assertTrue(row["blames"], where)
                    self.assertIn(row["basis"], BASES, where)
                names = [blame["who"] for blame in row["blames"]]
                self.assertEqual(len(names), len(set(names)), where)
                self.assertTrue(all(blame["confidence"] > 0 for blame in row["blames"]), where)
                self.assertLessEqual(sum(blame["confidence"] for blame in row["blames"]), 100, where)

    def test_one_line_says_what_went_wrong(self):
        for report, _meta, rows in _saved():
            for row in rows:
                text = row["went_wrong"]
                self.assertTrue(text.endswith("."), (report.name, text))
                self.assertLessEqual(len(text), 90, (report.name, text))

    def test_each_death_has_one_key_and_one_first_mistake_per_pull(self):
        for report, _meta, rows in _saved():
            keys = [key(row) for row in rows]
            self.assertEqual(len(keys), len(set(keys)), report.name)
            per_pull = defaultdict(set)
            for row in rows:
                per_pull[row["fight"]].add((row["first_mistake"], json.dumps(row["first_causes"], sort_keys=True)))
            for fight, seen in per_pull.items():
                self.assertEqual(len(seen), 1, (report.name, fight))

    def test_every_death_row_is_accounted_for(self):
        for report, _meta, rows in _saved():
            inputs = json.loads((report / "inputs.json").read_text(encoding="utf-8"))
            self.assertEqual(inputs["deaths"]["judged"], len(rows), report.name)
            self.assertEqual(inputs["deaths"]["not_judged"], len(inputs["skipped"]), report.name)


if __name__ == "__main__":
    unittest.main()
