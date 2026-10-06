"""Session pages: what happened, what it should have been, what went wrong.

Each dropped log is one session. The library page lists them by day and time.
"""

from __future__ import annotations

import base64
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from xivloganalyzer.catalog import FightPack, load_catalog, pack_for_zone
from xivloganalyzer.judge import Judgment

JOB = {
    "Paladin": "PLD",
    "Warrior": "WAR",
    "Gunbreaker": "GNB",
    "DarkKnight": "DRK",
    "Astrologian": "AST",
    "Scholar": "SCH",
    "WhiteMage": "WHM",
    "Sage": "SGE",
    "Ninja": "NIN",
    "Viper": "VPR",
    "BlackMage": "BLM",
    "Dancer": "DNC",
    "Samurai": "SAM",
    "Reaper": "RPR",
    "Monk": "MNK",
    "Dragoon": "DRG",
    "Bard": "BRD",
    "Machinist": "MCH",
    "RedMage": "RDM",
    "Summoner": "SMN",
    "Pictomancer": "PCT",
}


def _pull_clock(ms: int) -> str:
    seconds = int(round(ms / 1000))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _parse_started(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, timezone.utc)
    return datetime.fromisoformat(str(value))


def _day_label(moment: datetime) -> str:
    return f"{moment.strftime('%a')} {moment.day} {moment.strftime('%b %Y')}"


def _clock(moment: datetime) -> str:
    return moment.strftime("%H:%M")


def wall_clock(started: datetime | None, offset_ms: int) -> str:
    if started is None:
        return ""
    return _clock(started + timedelta(milliseconds=offset_ms))


def _friendly_phase(name: str) -> str:
    if "Rewind" in name:
        return "Rewind"
    if ":" not in name:
        return name
    left, right = [part.strip() for part in name.split(":", 1)]
    if right.startswith("King Thordan II"):
        return "Thordan II"
    if right.startswith("King Thordan"):
        return "Thordan"
    if "," in right:
        return left
    return right


def _phase_table(meta: dict) -> list[dict]:
    block = (meta.get("phases") or [{}])[0]
    names = block.get("phases") or []
    return [
        {"id": index, "name": name, "short": _friendly_phase(name)}
        for index, name in enumerate(names, start=1)
    ]


def _pack_for(meta: dict) -> FightPack | None:
    catalog = load_catalog()
    for fight in meta.get("fights") or []:
        pack = pack_for_zone(fight.get("zoneID"), catalog)
        if pack is not None:
            return pack
    return None


def _into_phase(fight: dict) -> tuple[int, float]:
    """Seconds into the phase the pull ended in. Cast time is from the pull start."""
    phase_id = int(fight.get("lastPhaseForPercentageDisplay") or 0)
    start = int(fight["start_time"])
    phase_start = start
    for phase in fight.get("phases") or []:
        if int(phase.get("id") or 0) == phase_id:
            phase_start = int(phase["startTime"])
    into = (int(fight.get("lastCastTime") or 0) - (phase_start - start)) / 1000
    return phase_id, max(0.0, into)


def _chart_marks(pack: FightPack | None) -> list[dict]:
    """Named mechanics, in fight order. `at` is seconds from a full pull's start."""
    if pack is None:
        return []
    rows = [
        {"name": marker.name, "phase": marker.phase, "starts": marker.starts}
        for marker in pack.markers
    ]
    rows.extend(
        {"name": cluster.name, "phase": cluster.phase, "starts": cluster.starts}
        for cluster in pack.clusters
    )
    marks = []
    for row in rows:
        at = pack.clock.get(row["phase"], 0) + row["starts"]
        marks.append({"name": row["name"], "phase": row["phase"], "at": at})
    marks.sort(key=lambda row: (row["at"], row["name"]))
    return marks


def _reached_name(marks: list[dict], phase_id: int, into: float, offset: float) -> str:
    name = ""
    latest = -1.0
    for mark in marks:
        if mark["phase"] != phase_id:
            continue
        starts = mark["at"] - offset
        if starts <= into and starts >= latest:
            latest = starts
            name = mark["name"]
    return name


def build_timeline(meta: dict, when: dict, judged: set[int]) -> dict:
    """Every pull in the log, with how far it got. This is the session chart.

    Bar height is seconds along the fight script, so a mechanic line sits where
    that mechanic starts. Fight percentage stays flat while a boss is untargetable,
    which would stack Strength of the Ward and Sanctity of the Ward on top of each other.
    """
    started = when.get("started")
    if isinstance(started, str):
        started = _parse_started(started)
    phases = _phase_table(meta)
    by_id = {phase["id"]: phase for phase in phases}
    pack = _pack_for(meta)
    marks = _chart_marks(pack)
    clock = pack.clock if pack else {}
    rows = []
    for fight in meta.get("fights") or []:
        phase_id, into = _into_phase(fight)
        phase = by_id.get(phase_id) or {
            "id": phase_id,
            "name": f"Phase {phase_id}",
            "short": f"P{phase_id}",
        }
        offset = clock.get(phase_id, 0)
        duration = int(fight.get("combatTime") or (fight["end_time"] - fight["start_time"]))
        rows.append(
            {
                "id": int(fight["id"]),
                "phase": phase_id,
                "phaseName": phase["short"],
                "phaseFull": phase["name"],
                "bossPct": round(fight.get("bossPercentage", 0) / 100, 1),
                "progress": round(100 - fight.get("fightPercentage", 0) / 100, 1),
                "reached": round(offset + into, 1),
                "mechanic": _reached_name(marks, phase_id, into, offset),
                "clock": _pull_clock(duration),
                "when": wall_clock(started, int(fight["start_time"])),
                "kill": bool(fight.get("kill")),
                "judged": int(fight["id"]) in judged,
            }
        )
    best = max(rows, key=lambda row: (row["kill"], row["progress"])) if rows else None
    return {"phases": phases, "pulls": rows, "best": best, "markers": marks}


def session_clock(report: Path, meta: dict) -> dict:
    """Day and time for a dropped log.

    `session.json` may set `started` (ISO-8601, report time zero), `title`, and `owner`.
    A `start` unix timestamp on the fights file is used when the sidecar is absent.
    """
    extra = {}
    sidecar = report / "session.json"
    if sidecar.is_file():
        extra = json.loads(sidecar.read_text(encoding="utf-8"))
    started = _parse_started(extra.get("started", meta.get("start")))
    fights = meta.get("fights") or []
    starts = {int(fight["id"]): int(fight["start_time"]) for fight in fights}
    first_ms = min(starts.values()) if starts else 0
    last_ms = max((int(fight["end_time"]) for fight in fights), default=0)
    window_start = started + timedelta(milliseconds=first_ms) if started else None
    window_end = started + timedelta(milliseconds=last_ms) if started else None
    return {
        "title": extra.get("title") or meta.get("title") or "",
        "owner": extra.get("owner") or meta.get("owner") or "",
        "started": started,
        "starts": starts,
        "day": window_start.date().isoformat() if window_start else "",
        "dayLabel": _day_label(window_start) if window_start else "No date",
        "timeLabel": f"{_clock(window_start)}–{_clock(window_end)}" if window_start and window_end else "",
    }


def _cluster_of(item: Judgment, pack: FightPack):
    return pack.cluster_for(item.mechanic_id, item.fact.t, item.fact.phase)


_ROLE_RANK = {"tank": 0, "healer": 1, "dps": 2}
_REACH_SLACK = 1.0


def _fight_ids(raw: str) -> list[int]:
    return [int(piece) for piece in str(raw).split(".") if piece.isdigit()]


def _party(meta: dict, pack: FightPack) -> list[dict]:
    """Players in the log, tanks then healers then DPS."""
    rows = []
    for actor in meta.get("friendlies") or []:
        job = actor.get("type") or ""
        if not actor.get("server") or job in {"LimitBreak", "NPC", "Pet"}:
            continue
        rows.append(
            {
                "name": actor["name"],
                "job": JOB.get(job, job),
                "role": pack.role_of(job),
                "fights": _fight_ids(actor.get("fights") or ""),
            }
        )
    rows.sort(key=lambda row: (_ROLE_RANK.get(row["role"], 9), row["name"]))
    return rows


def _later_start(clusters, cluster) -> float | None:
    later = [
        other.starts
        for other in clusters
        if other.phase == cluster.phase and other.starts > cluster.starts
    ]
    return min(later) if later else None


def _resolves(part, cluster, later: float | None, judgments: list[Judgment]) -> float | None:
    """Earliest judged hit of this component inside its window, in phase seconds."""
    start = part.after if part.after is not None else cluster.starts
    end = part.until if part.until is not None else later
    times = []
    for item in judgments:
        if item.mechanic_id != part.mechanic_id or item.fact.phase != cluster.phase:
            continue
        if item.outcome == "environment" or item.fact.t < start:
            continue
        if end is not None and item.fact.t >= end:
            continue
        times.append(item.fact.t)
    return min(times) if times else None


def _part_gate(mech: dict, part: dict) -> float:
    if part["resolves"] is not None:
        return float(part["resolves"])
    if part["after"] is not None:
        return float(part["after"])
    return float(mech["starts"])


def _pull_cards(pull: dict, mechanics: list[dict], party: list[dict]) -> list[dict]:
    """Mechanic cards for one pull.

    A component is on the card once the pull lasted until that component resolves,
    or someone died to it. A player failed it when a death there was judged a fail.
    Everyone else in the party passed.
    """
    roster = [player for player in party if pull["id"] in player["fights"]]
    duration = float(pull["duration"] or 0)
    cards = []
    for mech in mechanics:
        if mech["phase"] != pull.get("phaseId"):
            continue
        parts_out = []
        for part in mech["parts"]:
            rows = [
                row
                for row in pull["deaths"]
                if row["outcome"] != "environment"
                and row["mechanicId"] == mech["id"]
                and row["componentId"] == part["id"]
            ]
            if not rows and duration + _REACH_SLACK < _part_gate(mech, part):
                continue
            failed = {row["name"] for row in rows if row["outcome"] == "fail"}
            seats = [
                {"name": player["name"], "job": player["job"], "passed": player["name"] not in failed}
                for player in roster
            ]
            known = {seat["name"] for seat in seats}
            for row in rows:
                if row["outcome"] == "fail" and row["name"] not in known:
                    seats.append({"name": row["name"], "job": row["job"], "passed": False})
                    known.add(row["name"])
            parts_out.append({"id": part["id"], "name": part["name"], "seats": seats})
        if parts_out:
            cards.append({"id": mech["id"], "name": mech["name"], "parts": parts_out})
    return cards


def session_payload(
    judgments: list[Judgment],
    pack: FightPack,
    code: str,
    when: dict | None = None,
    meta: dict | None = None,
) -> dict:
    grouped: dict[str, list[Judgment]] = {cluster.id: [] for cluster in pack.clusters}
    for item in judgments:
        cluster = _cluster_of(item, pack)
        if cluster is not None:
            grouped[cluster.id].append(item)
    names = {mechanic.id: mechanic.name for mechanic in pack.mechanics}
    mechanics = []
    ordered = sorted(pack.clusters, key=lambda cluster: (cluster.phase, cluster.starts, cluster.name))
    for cluster in ordered:
        rows = grouped[cluster.id]
        counts = Counter(item.outcome for item in rows)
        later = _later_start(pack.clusters, cluster)
        parts = []
        for part in cluster.parts:
            parts.append(
                {
                    "id": part.mechanic_id,
                    "name": names.get(part.mechanic_id, part.mechanic_id),
                    "after": part.after,
                    "until": part.until,
                    "resolves": _resolves(part, cluster, later, judgments),
                }
            )
        mechanics.append(
            {
                "id": cluster.id,
                "name": cluster.name,
                "phase": cluster.phase,
                "starts": cluster.starts,
                "should": cluster.summary,
                "raw": counts["raw"],
                "fail": counts["fail"],
                "low": counts["low"],
                "parts": parts,
            }
        )
    when = when or {}
    started = when.get("started")
    if isinstance(started, str):
        started = _parse_started(started)
    starts = when.get("starts") or {}
    pulls: dict[int, dict] = {}
    for item in judgments:
        pull = pulls.setdefault(
            item.fact.fight,
            {
                "id": item.fact.fight,
                "bossPct": item.fact.boss_pct,
                "phase": item.fact.phase_name,
                "phaseId": item.fact.phase,
                "clock": _pull_clock(item.fact.pull_ms),
                "duration": item.fact.pull_ms / 1000,
                "when": wall_clock(started, starts.get(item.fact.fight, 0)),
                "deaths": [],
            },
        )
        cluster = _cluster_of(item, pack)
        pull["deaths"].append(
            {
                "time": item.fact.time,
                "t": item.fact.t,
                "name": item.fact.name,
                "job": JOB.get(item.fact.job, item.fact.job),
                "mechanicId": cluster.id if cluster else item.mechanic_id,
                "mechanic": cluster.name if cluster else item.mechanic,
                "componentId": item.mechanic_id,
                "cast": item.mechanic,
                "outcome": item.outcome,
                "happened": item.happened,
                "should": item.should_have_been,
                "wrong": item.went_wrong,
            }
        )
    roster = _party(meta or {}, pack)
    for pull in pulls.values():
        pull["deaths"].sort(key=lambda row: (row["t"], row["name"]))
        pull["counts"] = Counter(row["outcome"] for row in pull["deaths"])
        pull["cards"] = _pull_cards(pull, mechanics, roster)
    unknown = [
        item.mechanic
        for item in judgments
        if item.outcome == "unknown"
    ]
    counts = Counter(item.outcome for item in judgments)
    return {
        "code": code,
        "fight": pack.name,
        "title": when.get("title") or "",
        "owner": when.get("owner") or "",
        "started": started.isoformat() if isinstance(started, datetime) else "",
        "day": when.get("day") or "",
        "dayLabel": when.get("dayLabel") or "No date",
        "timeLabel": when.get("timeLabel") or "",
        "mechanics": mechanics,
        "pulls": [pulls[key] for key in sorted(pulls)],
        "unknown": Counter(unknown),
        "totals": counts,
        "raw": counts["raw"],
        "fail": counts["fail"],
        "low": counts["low"],
    }


def library_payload(payloads: list[dict]) -> dict:
    """Newest day first. Sessions on the same day stay in time order."""
    ordered = sorted(payloads, key=lambda item: (item.get("started") or "", item["code"]))
    days: list[dict] = []
    index: dict[str, dict] = {}
    for item in ordered:
        key = item.get("day") or ""
        bucket = index.get(key)
        if bucket is None:
            bucket = {"day": key, "label": item.get("dayLabel") or "No date", "sessions": []}
            index[key] = bucket
            days.append(bucket)
        bucket["sessions"].append(
            {
                "code": item["code"],
                "fight": item["fight"],
                "title": item.get("title") or "",
                "owner": item.get("owner") or "",
                "timeLabel": item.get("timeLabel") or "",
                "raw": item.get("raw", 0),
                "fail": item.get("fail", 0),
                "pulls": len(item.get("pulls") or []),
            }
        )
    dated = [day for day in days if day["day"]]
    undated = [day for day in days if not day["day"]]
    dated.reverse()
    return {"sessions": payloads, "days": dated + undated}


def write_session_page(report: Path, payload: dict) -> Path:
    path = report / "session.html"
    title = _session_title(payload)
    path.write_text(_page([payload], title), encoding="utf-8")
    return path


def write_library(root: Path, payloads: list[dict]) -> Path:
    path = root / "dashboard.html"
    title = "Sessions" if len(payloads) != 1 else _session_title(payloads[0])
    path.write_text(_page(payloads, title), encoding="utf-8")
    return path


def _session_title(payload: dict) -> str:
    when = payload.get("dayLabel") or ""
    clock = payload.get("timeLabel") or ""
    stamp = " · ".join(part for part in (when, clock) if part and when != "No date")
    if stamp:
        return f"{payload['fight']} · {stamp}"
    return f"{payload['fight']} · {payload['code']}"


def _job_icons() -> dict[str, str]:
    """Set 11 job icons from the GamerEscape dictionary, keyed by abbreviation."""
    icons = {}
    folder = Path(__file__).parent / "job_icons"
    for path in sorted(folder.glob("*.png")):
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        icons[path.stem] = f"data:image/png;base64,{encoded}"
    return icons


def _page(payloads: list[dict], title: str) -> str:
    data = json.dumps(library_payload(payloads)).replace("<", "\\u003c")
    icons = json.dumps(_job_icons())
    template = (Path(__file__).parent / "session_template.html").read_text(encoding="utf-8")
    html = template.replace("__DATA__", data)
    html = html.replace("__JOB_ICONS__", icons)
    return html.replace("__TITLE__", title)
