"""Who played which pull, on which job. One place, so extract, judge, and the pages agree.

A report lists each player once per job they played. `fights` on that entry is the
pulls they played on it, written ".10.11.12.". A player who swapped jobs, or a
substitute who joined later, is only in the pulls their entry lists.
"""

from __future__ import annotations

SKIP = frozenset({"LimitBreak", "NPC", "Pet"})


def players(meta: dict) -> list[dict]:
    """Every player entry in the report, one per name and job."""
    return [
        actor for actor in meta.get("friendlies") or []
        if actor.get("type") not in SKIP and str(actor.get("name") or "").strip()
    ]


def in_pull(actor: dict, fight_id: int) -> bool:
    """The entry played this pull. An entry with no pull list counts for every pull."""
    fights = str(actor.get("fights") or "")
    if not fights.strip("."):
        return True
    return f".{fight_id}." in fights


def pull_players(meta: dict, fight_id: int) -> list[dict]:
    return [actor for actor in players(meta) if in_pull(actor, fight_id)]


def actor_for(meta: dict, name: str, fight_id: int, job: str = "") -> dict | None:
    """The entry for this name in this pull. When a name has several, the one that
    played the pull wins, then the one on this job."""
    found = [actor for actor in players(meta) if actor.get("name") == name]
    if not found:
        return None
    playing = [actor for actor in found if in_pull(actor, fight_id)] or found
    if job:
        same = [actor for actor in playing if actor.get("type") == job or actor.get("icon") == job]
        if same:
            return same[0]
    return playing[0]
