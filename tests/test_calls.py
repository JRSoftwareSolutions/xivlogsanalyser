"""Every call is one line in calls.tsv, and checked calls are compared with the judge."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from xivloganalyzer.calls import (
    calls_text,
    diff_calls,
    key,
    owners_text,
    parse_owners,
    read_calls,
    saved_calls,
)
from xivloganalyzer.pipeline import report_dirs
from xivloganalyzer.verified import check_report, differences, failures, load_verified, record

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "XVz8bCqgPw1KRh9d"


class CallsFileTest(unittest.TestCase):
    def test_calls_file_matches_the_saved_judgments(self):
        for report in report_dirs(ROOT):
            judgments = json.loads((report / "judgments.json").read_text(encoding="utf-8"))
            self.assertEqual((report / "calls.tsv").read_text(encoding="utf-8"), calls_text(judgments), report.name)

    def test_each_death_has_one_key(self):
        for report in report_dirs(ROOT):
            rows = read_calls((report / "calls.tsv").read_text(encoding="utf-8"))
            keys = [key(row) for row in rows]
            self.assertEqual(len(keys), len(set(keys)), report.name)

    def test_owners_read_back(self):
        blames = [
            {"who": "Loki Doki", "confidence": 33, "via": ["Kite Noodle"]},
            {"who": "Spring Nymphar", "confidence": 33, "via": ["Kite Noodle", "Loki Doki"]},
            {"who": "Party mitigation", "confidence": 33},
        ]
        self.assertEqual(parse_owners(owners_text(blames)), blames)

    def test_a_changed_owner_or_outcome_is_listed(self):
        before = saved_calls(REPORT)
        after = [dict(row) for row in before]
        after[0]["owners"] = "Somebody Else 100"
        after[1]["outcome"] = "raw"
        after[2]["happened"] = "different words"
        changes = diff_calls(before, after)
        self.assertEqual([change.kind for change in changes], ["owners", "outcome"])
        self.assertEqual(diff_calls(before, before), [])


class VerifiedCallsTest(unittest.TestCase):
    def test_every_call_the_user_made_still_holds(self):
        checks = [item for report in report_dirs(ROOT) for item in check_report(ROOT, report)]
        self.assertTrue(any(item.call.get("by") == "user" for item in checks))
        self.assertEqual([item.found for item in failures(checks)], [])

    def test_context_shares_do_not_count_as_owners(self):
        call = {"outcome": "raw", "owners": ["Loki Doki", "Spring Nymphar"]}
        self.assertEqual(differences(call, {"outcome": "raw", "owners": ["Spring Nymphar", "Loki Doki"]}), [])
        self.assertEqual(len(differences(call, {"outcome": "fail", "owners": ["Loki Doki"]})), 2)
        self.assertEqual(differences({"outcome": "fail"}, {"outcome": "fail", "owners": ["Anyone"]}), [])

    def test_recording_a_call_keeps_what_the_judge_said_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            call = record(root, REPORT, 16, "Kiara Blaiddyd", outcome="raw", owners=["Loki Doki"], by="user", why="test")
            self.assertEqual(call["first_pass"], {"outcome": "fail", "owners": ["Spring Nymphar"]})
            self.assertEqual(len(load_verified(root, REPORT.name)), 1)
            checks = check_report(root, REPORT)
            self.assertEqual(len(failures(checks)), 1)
            self.assertFalse(checks[0].first_pass_agrees)
            # Recording it again keeps the first pass and replaces the call.
            again = record(root, REPORT, 16, "Kiara Blaiddyd", by="user")
            self.assertEqual(again["first_pass"], call["first_pass"])
            self.assertEqual(again["outcome"], "fail")
            self.assertEqual(len(load_verified(root, REPORT.name)), 1)
            shutil.rmtree(root / "reviews")


if __name__ == "__main__":
    unittest.main()
