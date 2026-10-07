"""Session digests stay short and filterable."""

import unittest
from pathlib import Path

from xivloganalyzer.brief import brief_text, filter_judgments, format_death, load_judgments

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "XVz8bCqgPw1KRh9d"
OTHER = ROOT / "data" / "8DYNHQx4C7ytdLb9"


class BriefTest(unittest.TestCase):
    def test_default_brief_has_counts_pulls_and_raw_not_full_json(self):
        text = brief_text(REPORT)
        self.assertIn("XVz8bCqgPw1KRh9d", text)
        self.assertIn("86 raw", text)
        self.assertIn("368 fail", text)
        self.assertIn("110 Deathwall", text)
        self.assertIn("28 r1 f7 · first: Loki Doki walking into the deathwall at ", text)
        self.assertIn("Raw by mechanic", text)
        self.assertIn("45 Eternal Conviction", text)
        self.assertIn("Pulls (55)", text)
        self.assertIn("68 ", text)
        self.assertNotIn('"unmitigated"', text)
        self.assertLess(len(text), 80_000)

    def test_default_detail_lists_raw_and_skips_environment(self):
        text = brief_text(REPORT)
        self.assertIn("Raw (86)", text)
        self.assertIn("Kitana Kahn", text)
        self.assertNotIn("No damage packet.", text)

    def test_pull_filter_shows_that_pulls_fails(self):
        text = brief_text(REPORT, pull=68)
        self.assertIn("filter: pull 68", text)
        self.assertIn("Kitana Kahn", text)
        self.assertIn("Skyward Leap", text)
        self.assertIn("fail", text)
        self.assertNotIn("Pull 10 ·", text)

    def test_mechanic_filter_and_outcome(self):
        text = brief_text(REPORT, mechanic="Skyward Leap", outcome="fail")
        self.assertIn("Skyward Leap", text)
        self.assertIn("filter: mechanic Skyward Leap", text)
        self.assertTrue(all("raw" not in line.lower() or "Skyward" in line for line in text.splitlines() if line.startswith("Pull ")))

    def test_unknowns_include_guid(self):
        text = brief_text(OTHER, outcome="unknown")
        self.assertIn("Unknown (", text)
        self.assertIn("(25579)", text)
        self.assertIn("Holy Shield Bash", text)

    def test_detail_none_is_counts_only(self):
        text = brief_text(REPORT, detail="none")
        self.assertIn("86 raw", text)
        self.assertIn("Pulls (55)", text)
        self.assertNotIn("Raw (86)", text)
        self.assertNotIn("Fault:", text)

    def test_format_death_matches_review_shape(self):
        rows = load_judgments(REPORT)
        kitana = next(
            row
            for row in rows
            if row["fight"] == 68
            and row["name"] == "Kitana Kahn"
            and row["mechanic"] == "Skyward Leap"
        )
        block = format_death(kitana)
        self.assertIn("Pull 68 · Kitana Kahn · Skyward Leap — fail", block)
        self.assertIn("without mitigation", block)
        self.assertIn("Fault:", block)

    def test_filter_by_guid(self):
        rows = load_judgments(REPORT)
        skyward = filter_judgments(rows, mechanic="25565")
        self.assertTrue(skyward)
        self.assertTrue(all(row["guid"] == 25565 for row in skyward))


if __name__ == "__main__":
    unittest.main()
