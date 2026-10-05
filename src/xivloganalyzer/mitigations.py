"""Who applied the mitigations on a hit.

Replay files in ``mitigations/fight-<id>.json`` keep the buff timeline, the
mitigations FFLogs attached to each player hit, and the shields that absorbed
it. ``source`` on those rows is the player who applied it.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_mitigations(report: Path) -> dict[int, dict]:
    folder = report / "mitigations"
    loaded: dict[int, dict] = {}
    if not folder.is_dir():
        return loaded
    guids: set[int] = set()
    for path in sorted(folder.glob("fight-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for hit in payload.get("hits") or []:
            for mit in hit[6]:
                if mit[0] is not None:
                    guids.add(int(mit[0]))
        for shield in payload.get("shields") or []:
            if shield[3] is not None:
                guids.add(int(shield[3]))
        payload["auras"] = sorted(payload.get("auras") or [], key=lambda row: row[0])
        loaded[int(payload["fight"])] = payload
    _credit_pet_owners(report, loaded)
    for payload in loaded.values():
        payload["mit_guids"] = guids
    return loaded


def _credit_pet_owners(report: Path, loaded: dict[int, dict]) -> None:
    meta_path = report / "fights.json"
    if not meta_path.is_file():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    names = {}
    owners = {}
    for group in ("friendlies", "enemies", "friendlyPets", "enemyPets"):
        for actor in meta.get(group) or []:
            names[actor["id"]] = actor.get("name")
            if actor.get("petOwner"):
                owners[actor["id"]] = actor["petOwner"]
    for payload in loaded.values():
        actors = payload.setdefault("actors", {})
        for pet_id, owner_id in owners.items():
            owner = names.get(owner_id)
            if not owner:
                continue
            info = actors.setdefault(str(pet_id), {"name": names.get(pet_id) or str(pet_id)})
            info["owner"] = owner


def mitigations_for(
    tables: dict[int, dict],
    fight: int,
    target: int | None,
    source: int | None,
    guid: int,
    timestamp: int | None,
) -> list[dict]:
    payload = tables.get(fight)
    if payload is None or timestamp is None:
        return []
    actors = payload.get("actors") or {}
    hit = _closest_hit(payload.get("hits") or [], target, guid, timestamp)
    when = hit[0] if hit is not None else timestamp
    active = _active(payload.get("auras") or [], when, payload.get("mit_guids") or set())
    rows: dict[tuple, dict] = {}
    watched = {actor for actor in (target, source) if actor is not None}
    for aura in active:
        if aura["target"] not in watched:
            continue
        _put(rows, actors, aura["guid"], aura["name"], aura["source"], aura["target"], None, None, aura["via"])
    if hit is not None:
        for mit in hit[6]:
            _put(rows, actors, mit[0], mit[1], mit[2], mit[3], mit[4], None, _via(active, mit[0], mit[3]))
    for shield in payload.get("shields") or []:
        if not _same_shield(shield, target, guid, when):
            continue
        _put(
            rows, actors, shield[3], shield[4], shield[2], shield[1],
            None, int(shield[5]), _via(active, shield[3], shield[1]),
        )
    ordered = sorted(rows.values(), key=_order)
    return ordered


def _closest_hit(hits: list, target: int | None, guid: int, timestamp: int) -> list | None:
    near = [
        hit for hit in hits
        if hit[3] == guid and (target is None or hit[1] == target) and abs(hit[0] - timestamp) <= 4000
    ]
    if not near:
        return None
    return min(near, key=lambda hit: abs(hit[0] - timestamp))


def _same_shield(shield: list, target: int | None, guid: int, when: int) -> bool:
    if target is not None and shield[1] != target:
        return False
    if abs(shield[0] - when) > 50:
        return False
    attack = shield[6]
    return attack is None or attack == guid


def _active(auras: list, timestamp: int, mit_guids: set[int]) -> list[dict]:
    state: dict[tuple, dict] = {}
    for aura in auras:
        if aura[0] > timestamp:
            break
        action = aura[1]
        key = (aura[5], aura[2])
        if action.startswith("remove") and not action.endswith("stack"):
            state.pop(key, None)
            continue
        if action.endswith("stack") and not action.startswith("apply"):
            continue
        duration = aura[6]
        state[key] = {
            "guid": aura[2],
            "name": aura[3],
            "source": aura[4],
            "target": aura[5],
            "until": aura[0] + duration if duration else None,
            "via": aura[8],
        }
    live = []
    for aura in state.values():
        if aura["guid"] not in mit_guids:
            continue
        if aura["until"] is not None and aura["until"] <= timestamp:
            continue
        live.append(aura)
    return live


def _via(active: list[dict], guid: int | None, target: int | None) -> str | None:
    for aura in active:
        if aura["guid"] == guid and aura["target"] == target and aura["via"]:
            return aura["via"]
    return None


def _put(rows, actors, guid, name, source, target, pct, amount, via) -> None:
    if not name:
        return
    key = (guid, target)
    row = rows.get(key)
    if row is None:
        row = {
            "name": name,
            "guid": guid,
            "by": _actor(actors, source),
            "by_id": source,
            "on": _actor(actors, target),
            "on_id": target,
            "pct": pct,
            "amount": amount,
            "via": via if via and via != name else None,
        }
        rows[key] = row
        return
    if source is not None and row["by_id"] is None:
        row["by"] = _actor(actors, source)
        row["by_id"] = source
    if pct is not None:
        row["pct"] = pct
        if source is not None:
            row["by"] = _actor(actors, source)
            row["by_id"] = source
    if amount:
        row["amount"] = (row["amount"] or 0) + int(amount)
    if via and via != name and not row["via"]:
        row["via"] = via


def _actor(actors: dict, actor_id: int | None) -> str:
    if actor_id is None:
        return "unknown"
    info = actors.get(str(actor_id))
    if not info:
        return str(actor_id)
    return info.get("owner") or info.get("name") or str(actor_id)


def _order(row: dict) -> tuple:
    pct = row.get("pct")
    if row.get("amount"):
        group = 1
    elif pct is not None and pct > 100:
        group = 2
    else:
        group = 0
    return (group, row["name"], row.get("by") or "")
