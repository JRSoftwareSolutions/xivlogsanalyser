"""Fetch the ability files a log is missing from the official FFLogs API (v2).

`check` lists the ability files the reached phases need and do not have. This
fetches them: every damage-taken event of that ability in the report's pulls of
this encounter, written as `abilities/ab_<guid>.json` in the same shape as the
files fetched from the site, so `analyze` reads them unchanged.

It needs an FFLogs API client (made at https://www.fflogs.com/api/clients/). Its
id and secret are read from FFLOGS_CLIENT_ID and FFLOGS_CLIENT_SECRET. The
client-credentials flow reads public reports only.

    python -m xivloganalyzer fetch <code>              # everything check lists
    python -m xivloganalyzer fetch <code> --guid 25567 # one ability
"""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

from xivloganalyzer.inputs import read_inputs

TOKEN_URL = "https://www.fflogs.com/oauth/token"
API_URL = "https://www.fflogs.com/api/v2/client"
# Events per page. The API caps a page at 10,000.
PAGE = 10000

Post = Callable[[str, bytes, dict[str, str]], dict]


def _post(url: str, body: bytes, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


class Api:
    """A token and GraphQL queries against the FFLogs client endpoint."""

    def __init__(self, client_id: str, secret: str, post: Post = _post):
        self._post = post
        auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
        reply = post(
            TOKEN_URL,
            urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        self._token = reply["access_token"]

    def query(self, text: str) -> dict:
        reply = self._post(
            API_URL,
            json.dumps({"query": text}).encode(),
            {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
        )
        if reply.get("errors"):
            raise SystemExit(f"FFLogs API error: {reply['errors'][0].get('message')}")
        return reply["data"]


# The local file with the API client, kept out of git (.gitignore). The repository is public.
CLIENT_FILE = ".fflogs.json"


def _env(*names: str) -> str:
    """The first of these environment variables that is set, without surrounding spaces."""
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def client_credentials(root: Path | None = None) -> tuple[str, str] | None:
    """FFLOGS_CLIENT_ID and FFLOGS_CLIENT_SECRET (or fflogs_client and fflogs_secret, as the
    cloud environment's variables), or else `.fflogs.json` at the repo root
    ({"client_id": ..., "client_secret": ...})."""
    client_id = _env("FFLOGS_CLIENT_ID", "FFLOGS_CLIENT", "fflogs_client_id", "fflogs_client")
    secret = _env("FFLOGS_CLIENT_SECRET", "FFLOGS_SECRET", "fflogs_client_secret", "fflogs_secret")
    if client_id and secret:
        return client_id, secret
    path = (root or Path.cwd()) / CLIENT_FILE
    if path.is_file():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("client_id") and saved.get("client_secret"):
            return saved["client_id"], saved["client_secret"]
    return None


def api_from_env(post: Post = _post, root: Path | None = None) -> Api:
    found = client_credentials(root)
    if found is None:
        raise SystemExit(
            "No FFLogs API client. Set FFLOGS_CLIENT_ID and FFLOGS_CLIENT_SECRET, or put "
            f'{{"client_id": ..., "client_secret": ...}} in {CLIENT_FILE} at the repo root '
            "(https://www.fflogs.com/api/clients/)."
        )
    return Api(found[0], found[1], post)


def ability_names(api: Api, code: str) -> dict[int, dict]:
    data = api.query(
        f'{{ reportData {{ report(code: "{code}") {{ masterData {{ abilities {{ gameID name type }} }} }} }} }}'
    )
    abilities = data["reportData"]["report"]["masterData"]["abilities"] or []
    return {int(row["gameID"]): row for row in abilities}


def damage_taken(api: Api, code: str, guid: int, fights: list[int], start: int, end: int) -> list[dict]:
    """Every damage-taken event of this ability in these pulls, page by page."""
    events: list[dict] = []
    cursor = start
    while cursor is not None and cursor < end:
        data = api.query(
            f'{{ reportData {{ report(code: "{code}") {{ events(dataType: DamageTaken, abilityID: {guid}, '
            f"fightIDs: {json.dumps(fights)}, startTime: {cursor}, endTime: {end}, limit: {PAGE}) "
            f"{{ data nextPageTimestamp }} }} }} }}"
        )
        page = data["reportData"]["report"]["events"]
        events += page.get("data") or []
        cursor = page.get("nextPageTimestamp")
    return events


def site_shape(events: list[dict], names: dict[int, dict]) -> dict:
    """The API's events in the shape the site's files have: an `ability` object on each
    event, and the names of the buffs on them in `auraAbilities`."""
    out = []
    auras: set[int] = set()
    for event in events:
        row = dict(event)
        guid = row.pop("abilityGameID", None)
        if guid is not None and "ability" not in row:
            known = names.get(int(guid)) or {}
            kind = known.get("type") or 0
            row["ability"] = {"name": known.get("name") or "", "guid": int(guid), "type": int(kind) if str(kind).isdigit() else kind}
        for buff in str(row.get("buffs") or "").split("."):
            if buff.strip().isdigit():
                auras.add(int(buff))
        out.append(row)
    aura_rows = [
        {"name": names[guid]["name"], "guid": guid, "type": int(names[guid].get("type") or 0) if str(names[guid].get("type") or 0).isdigit() else names[guid]["type"]}
        for guid in sorted(auras) if guid in names and names[guid].get("name")
    ]
    return {"events": out, "count": len(out), "auraAbilities": aura_rows, "source": "fflogs api v2"}


def encounter_fights(meta: dict, zone_id: int | None) -> tuple[list[int], int, int]:
    fights = [fight for fight in meta.get("fights") or [] if zone_id is None or fight.get("zoneID") == zone_id]
    if not fights:
        return [], 0, 0
    return (
        [int(fight["id"]) for fight in fights],
        min(int(fight["start_time"]) for fight in fights),
        max(int(fight["end_time"]) for fight in fights),
    )


def fetch_missing(
    report: Path, api: Api, zone_id: int | None, guids: list[int] | None = None,
) -> list[tuple[int, int]]:
    """Fetch these ability files, or every one `check` lists. Returns (guid, events) per file written."""
    meta = json.loads((report / "fights.json").read_text(encoding="utf-8"))
    if guids is None:
        inputs = read_inputs(report) or {}
        guids = [int(row["guid"]) for row in inputs.get("abilities") or []]
    fights, start, end = encounter_fights(meta, zone_id)
    if not guids or not fights:
        return []
    names = ability_names(api, report.name)
    folder = report / "abilities"
    folder.mkdir(exist_ok=True)
    written = []
    for guid in guids:
        events = damage_taken(api, report.name, guid, fights, start, end)
        payload = site_shape(events, names)
        (folder / f"ab_{guid}.json").write_text(json.dumps(payload), encoding="utf-8")
        written.append((guid, len(events)))
    return written
