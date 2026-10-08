"""The FFLogs API fetcher writes ability files in the shape the site's files have."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from xivloganalyzer.fetch import TOKEN_URL, Api, fetch_missing, site_shape

ROOT = Path(__file__).resolve().parents[1]


class FakeApi:
    """Answers the token request and the queries the fetcher sends, two pages of events."""

    def __init__(self):
        self.queries = []

    def __call__(self, url, body, headers):
        if url == TOKEN_URL:
            self.auth = headers["Authorization"]
            return {"access_token": "token"}
        text = json.loads(body)["query"]
        self.queries.append(text)
        if "masterData" in text:
            return {"data": {"reportData": {"report": {"masterData": {"abilities": [
                {"gameID": 25567, "name": "Conviction", "type": 1024},
                {"gameID": 1001191, "name": "Rampart", "type": 1},
            ]}}}}}
        first = sum("events(" in query for query in self.queries) == 1
        events = [{"timestamp": 100 if first else 200, "type": "damage", "fight": 4, "sourceID": 33,
                   "targetID": 7, "abilityGameID": 25567, "amount": 5000, "buffs": "1001191."}]
        return {"data": {"reportData": {"report": {"events": {
            "data": events, "nextPageTimestamp": 150000 if first else None}}}}}


class FetchTest(unittest.TestCase):
    def test_events_get_an_ability_and_the_buff_names(self):
        shaped = site_shape(
            [{"abilityGameID": 25567, "buffs": "1001191.", "type": "damage"}],
            {25567: {"name": "Conviction", "type": 1024}, 1001191: {"name": "Rampart", "type": 1}},
        )
        self.assertEqual(shaped["events"][0]["ability"], {"name": "Conviction", "guid": 25567, "type": 1024})
        self.assertNotIn("abilityGameID", shaped["events"][0])
        self.assertEqual(shaped["auraAbilities"], [{"name": "Rampart", "guid": 1001191, "type": 1}])

    def test_fetch_writes_every_page_of_a_missing_ability(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "8DYNHQx4C7ytdLb9"
            report.mkdir()
            shutil.copy(ROOT / "data" / "8DYNHQx4C7ytdLb9" / "fights.json", report / "fights.json")
            fake = FakeApi()
            meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
            zone = meta["fights"][0]["zoneID"]
            written = fetch_missing(report, Api("id", "secret", fake), zone, [25567])
            self.assertEqual(written, [(25567, 2)])
            saved = json.loads((report / "abilities" / "ab_25567.json").read_text(encoding="utf-8"))
            self.assertEqual([event["timestamp"] for event in saved["events"]], [100, 200])
            self.assertEqual(saved["events"][0]["ability"]["name"], "Conviction")
            self.assertTrue(fake.auth.startswith("Basic "))
            self.assertIn("dataType: DamageTaken", fake.queries[1])
            self.assertIn("startTime: 150000", fake.queries[2])


if __name__ == "__main__":
    unittest.main()
