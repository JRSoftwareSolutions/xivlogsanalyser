"""A death caused by someone else's earlier mistake belongs to that mistake, named from the log."""

import json
import unittest
from pathlib import Path

from xivloganalyzer.catalog import load_pack
from xivloganalyzer.extract import extract_report
from xivloganalyzer.judge import judge_report, roster_from_meta

ROOT = Path(__file__).resolve().parents[1]
PACK = load_pack(ROOT / "fights" / "dsr")
_JUDGED: dict[str, list] = {}


def _judged(code):
    if code not in _JUDGED:
        report = ROOT / "data" / code
        meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
        _JUDGED[code] = judge_report(extract_report(report, PACK), PACK, roster_from_meta(meta, PACK))
    return _JUDGED[code]


def _owners(item):
    return [(blame.who, blame.confidence) for blame in item.blames]


def _deaths(code, fight, mechanic):
    return [
        item for item in _judged(code)
        if item.fact.fight == fight and item.mechanic == mechanic
    ]


def _one(code, fight, name, mechanic):
    found = [item for item in _deaths(code, fight, mechanic) if item.fact.name == name]
    assert len(found) == 1, (code, fight, name, mechanic, len(found))
    return found[0]


class OwnDamageTest(unittest.TestCase):
    def test_looking_at_the_gaze_then_dying_to_the_share_is_theirs(self):
        # Both looked at Dragon's Glory a second before the jump. Full HP would have lived the share.
        for name in ("Kitana Kahn", "Speed Panda"):
            item = _one("XVz8bCqgPw1KRh9d", 11, name, "Sacred Sever")
            self.assertEqual(item.outcome, "raw")
            self.assertEqual(item.cause, "self")
            self.assertEqual(item.went_wrong, f"{name} was still low from Dragon's Glory.")
            self.assertEqual(_owners(item), [(name, 100)])

    def test_a_puddle_before_the_cone_is_the_tanks_own(self):
        item = _one("3wzL6x4VHTmvNkhq", 6, "Absolute Gigachad", "Holy Bladedance")
        self.assertEqual(item.outcome, "low")
        self.assertEqual(item.went_wrong, "Absolute Gigachad was still low from Dimensional Collapse.")
        self.assertEqual(_owners(item), [("Absolute Gigachad", 100)])

    def test_a_hit_that_would_not_have_saved_them_stays_with_the_healers(self):
        # Gigalad lived a Bright Flare, but the lone share was more than full HP plus that hit.
        item = _one("XVz8bCqgPw1KRh9d", 34, "Absolute Gigalad", "Sacred Sever")
        self.assertNotEqual(item.cause, "self")

    def test_a_healthy_share_stays_with_the_healers(self):
        item = _one("XVz8bCqgPw1KRh9d", 17, "Kitana Kahn", "Sacred Sever")
        self.assertEqual(item.cause, "resolve")
        self.assertEqual(
            _owners(item), [("Loki Doki", 33), ("Spring Nymphar", 33), ("Party mitigation", 33)],
        )


class JumpGroupTest(unittest.TestCase):
    def test_a_jump_on_the_wrong_group_belongs_to_the_dead_group(self):
        # All four of the first group looked at Dragon's Glory. The third jump found the second group,
        # still carrying the second jump's vulnerability.
        victims = _deaths("3wzL6x4VHTmvNkhq", 49, "Sacred Sever")
        self.assertEqual(len(victims), 4)
        for item in victims:
            self.assertEqual(item.cause, "redirected")
            self.assertEqual(item.went_wrong, "4 players were dead, so Sacred Sever hit the other group.")
            self.assertEqual(
                sorted(_owners(item)),
                [("Kiara Blaiddyd", 25), ("Kitana Kahn", 25), ("Loki Doki", 25), ("Speed Panda", 25)],
            )

    def test_the_living_players_of_the_missing_group_did_nothing_wrong(self):
        # Kiara walked into the wall with Hysteria. Speed, Gigalad, and Loki were alive and are not named.
        for item in _deaths("3wzL6x4VHTmvNkhq", 51, "Sacred Sever"):
            if item.cause == "redirected":
                self.assertEqual(_owners(item), [("Kiara Blaiddyd", 100)])
        lone = _one("3wzL6x4VHTmvNkhq", 51, "Absolute Gigalad", "Sacred Sever")
        self.assertEqual(lone.cause, "missing")
        self.assertEqual(_owners(lone), [("Kiara Blaiddyd", 100)])

    def test_a_player_who_took_both_jumps_owns_it(self):
        # Kitana stood in the first group's jump, then took her own group's.
        item = _one("3wzL6x4VHTmvNkhq", 24, "Kitana Kahn", "Sacred Sever")
        self.assertEqual(item.cause, "personal")
        self.assertEqual(_owners(item), [("Kitana Kahn", 100)])

    def test_a_short_stack_names_who_was_not_in_it(self):
        for name in ("Kiara Blaiddyd", "Kite Noodle"):
            item = _one("3wzL6x4VHTmvNkhq", 66, name, "Sacred Sever")
            self.assertEqual(item.outcome, "raw")
            self.assertEqual(
                item.went_wrong,
                "The stack was 2 of 4 because Spring Nymphar and Absolute Gigachad were not in it.",
            )
            self.assertEqual(_owners(item), [("Spring Nymphar", 50), ("Absolute Gigachad", 50)])

    def test_a_seat_no_jump_filled_goes_to_its_player(self):
        # Every jump hit three of Speed, Kitana and Gigachad's group. The healer seat was
        # empty: Spring was the other group's jump target, so it was Loki's, who stood in
        # the other group's stack twice and then walked into the wall.
        for item in _deaths("XVz8bCqgPw1KRh9d", 49, "Sacred Sever"):
            self.assertEqual(sorted(item.fact.group), ["Absolute Gigachad", "Kitana Kahn", "Loki Doki", "Speed Panda"])
            self.assertEqual(_owners(item), [("Loki Doki", 100)])


class PassedOnTest(unittest.TestCase):
    def test_an_empty_tower_left_by_a_killed_player_belongs_to_the_killer(self):
        # Kitana and Spring died to the same jump. Their deaths were the healers', so their towers are too.
        # Speed and Loki died to the surplus ice their dead pair left them, so theirs are the same healers'.
        item = _one("XVz8bCqgPw1KRh9d", 26, "Kite Noodle", "Eternal Conviction")
        self.assertEqual(item.fact.down, ["Speed Panda", "Spring Nymphar", "Kitana Kahn", "Loki Doki"])
        self.assertEqual(_owners(item), [("Loki Doki", 50), ("Spring Nymphar", 50)])

    def test_dead_threes_leave_the_first_dive_towers_empty(self):
        # Loki and Speed held the 3s and died to Eye of the Tyrant with no shield. Those were the healers'.
        for item in _deaths("8DYNHQx4C7ytdLb9", 26, "Darkdragon Dive"):
            if item.outcome != "fail":
                continue
            self.assertEqual(item.fact.down, ["Loki Doki", "Speed Panda"])
            # Gigalad, a 3, was alive and not in a tower. The soak file shows it.
            self.assertEqual(item.fact.unsoaked, ["Absolute Gigalad"])
            self.assertEqual(
                item.went_wrong,
                "Loki Doki and Speed Panda were dead and Absolute Gigalad was out of the towers.",
            )
            # Loki died first, so Speed's missed heal was more Spring's.
            self.assertEqual(_owners(item), [("Loki Doki", 24), ("Spring Nymphar", 41), ("Absolute Gigalad", 33)])

    def test_first_dive_towers_with_every_three_alive_name_who_was_not_in_one(self):
        towers = _deaths("8DYNHQx4C7ytdLb9", 36, "Darkdragon Dive")
        self.assertTrue(towers)
        for item in towers:
            self.assertEqual(item.fact.down, [])
            self.assertEqual(sorted(item.fact.unsoaked), ["Absolute Gigachad", "Loki Doki", "Spring Nymphar"])
            self.assertNotIn("Missed soak", [blame.who for blame in item.blames])

    def test_a_wall_after_only_your_own_mistake_is_yours(self):
        item = _one("8DYNHQx4C7ytdLb9", 18, "Absolute Gigalad", "Deathwall")
        self.assertEqual(item.cause, "personal")
        self.assertEqual(_owners(item), [("Absolute Gigalad", 100)])

    def test_a_wall_after_other_deaths_still_shares_it(self):
        item = _one("XVz8bCqgPw1KRh9d", 24, "Absolute Gigachad", "Deathwall")
        self.assertEqual(item.cause, "after")
        self.assertEqual(_owners(item), [("Absolute Gigachad", 50), ("Earlier mistake", 50)])


if __name__ == "__main__":
    unittest.main()
