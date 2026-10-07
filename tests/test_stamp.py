"""A saved report is judged again only when its rules, the code, or its log changed."""

import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from xivloganalyzer.pipeline import reanalyze, status
from xivloganalyzer.stamp import STAMP, check, read_stamp, write_stamp

ROOT = Path(__file__).resolve().parents[1]


class StampTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.pack = self.tmp / "fights" / "dsr"
        self.pack.mkdir(parents=True)
        (self.pack / "mechanics.json").write_text('{"mechanics": []}\n', encoding="utf-8")
        self.report = self.tmp / "data" / "abc"
        (self.report / "positions").mkdir(parents=True)
        (self.report / "fights.json").write_text('{"fights": []}\n', encoding="utf-8")
        (self.report / "positions" / "fight-1.json").write_text("[1, 2]\n", encoding="utf-8")
        for name in ("facts.json", "judgments.json", "session.html"):
            (self.report / name).write_text("out\n", encoding="utf-8")

    def stamp(self):
        write_stamp(self.report, self.pack, Counter(raw=2), {"code": "abc"})

    def test_never_analyzed(self):
        self.assertEqual(check(self.report, self.pack).reason, "never analyzed")

    def test_current_after_stamp(self):
        self.stamp()
        self.assertTrue(check(self.report, self.pack).current)
        self.assertEqual(read_stamp(self.report)["counts"]["raw"], 2)
        self.assertEqual(read_stamp(self.report)["counts"]["unknown"], 0)

    def test_rule_change(self):
        self.stamp()
        (self.pack / "mechanics.json").write_text('{"mechanics": [1]}\n', encoding="utf-8")
        self.assertEqual(check(self.report, self.pack).reason, "rules changed (fights/dsr)")

    def test_log_change(self):
        self.stamp()
        (self.report / "positions" / "fight-1.json").write_text("[1, 3]\n", encoding="utf-8")
        self.assertEqual(check(self.report, self.pack).reason, "log files changed")

    def test_new_log_file(self):
        self.stamp()
        (self.report / "session.json").write_text("{}\n", encoding="utf-8")
        self.assertEqual(check(self.report, self.pack).reason, "log files changed")

    def test_edited_page(self):
        self.stamp()
        (self.report / "session.html").write_text("edited\n", encoding="utf-8")
        self.assertEqual(check(self.report, self.pack).reason, "saved pages missing or edited")

    def test_brief_is_not_part_of_the_log(self):
        self.stamp()
        (self.report / "brief.txt").write_text("digest\n", encoding="utf-8")
        self.assertTrue(check(self.report, self.pack).current)

    def test_line_endings_do_not_matter(self):
        self.stamp()
        for path in (self.pack / "mechanics.json", self.report / "fights.json"):
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertTrue(check(self.report, self.pack).current)


class ReanalyzeSkipsCurrentReportsTest(unittest.TestCase):
    def test_only_stale_reports_are_judged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "fights", root / "fights")
            (root / "reports").mkdir()
            shutil.copytree(ROOT / "data" / "XVz8bCqgPw1KRh9d", root / "data" / "XVz8bCqgPw1KRh9d")
            (root / "data" / "XVz8bCqgPw1KRh9d" / STAMP).unlink(missing_ok=True)

            first = reanalyze(root)
            self.assertTrue(first[0].judged)
            self.assertEqual(first[0].counts["raw"], 86)
            fresh_dashboard = (root / "dashboard.html").read_text(encoding="utf-8")
            self.assertEqual(status(root), [("XVz8bCqgPw1KRh9d", "")])

            second = reanalyze(root)
            self.assertFalse(second[0].judged)
            self.assertEqual(second[0].counts["raw"], 86)
            self.assertEqual((root / "dashboard.html").read_text(encoding="utf-8"), fresh_dashboard)

            mechanics = root / "fights" / "dsr" / "mechanics.json"
            mechanics.write_text(mechanics.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertEqual(status(root), [("XVz8bCqgPw1KRh9d", "rules changed (fights/dsr)")])
            third = reanalyze(root)
            self.assertTrue(third[0].judged)
            self.assertTrue(reanalyze(root, everything=True)[0].judged)


if __name__ == "__main__":
    unittest.main()
