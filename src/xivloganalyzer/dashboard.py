"""Session pages: what happened, and a short line for what went wrong.

Each dropped log is one session. The library page lists them by day and time.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from xivloganalyzer.catalog import FightPack, load_catalog, pack_for_zone
from xivloganalyzer.judge import Judgment, clip_mechanic, marker_owners

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


def _fight_ms(fight: dict) -> int:
    """How long the pull lasted, from its first phase."""
    return int(fight.get("combatTime") or (fight["end_time"] - fight["start_time"]))


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


def _percent_left(raw) -> float:
    """Boss HP remaining, in percent. A pull FFLogs did not score left the boss untouched."""
    if raw is None:
        return 100.0
    return round(raw / 100, 1)


def _progress(raw) -> float:
    """How far the pull got. Missing fight percentage is an unscored pull, not a clear."""
    if raw is None:
        return 0.0
    return round(100 - raw / 100, 1)


def _into_phase(fight: dict) -> tuple[int, float]:
    """Seconds into the phase the pull ended in. Cast time is from the pull start.

    A pull reset before FFLogs placed it in a phase ended in the first one.
    """
    phase_id = int(fight.get("lastPhaseForPercentageDisplay") or 1)
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


def build_timeline(meta: dict, when: dict, judged: set[int], pack: FightPack | None = None) -> dict:
    """Every pull in the log, with how far it got. This is the session chart.

    Bar height is seconds along the fight script, so a mechanic line sits where
    that mechanic starts. Fight percentage stays flat while a boss is untargetable,
    which would stack Strength of the Ward and Sanctity of the Ward on top of each other.
    Each phase needs a clock in fight.json. Nidhogg is 350: Thordan's 153, plus
    about 197 seconds until that phase starts. Without it, a phase 3 wipe is only
    the seconds into Nidhogg and draws shorter than Thordan.
    """
    started = when.get("started")
    if isinstance(started, str):
        started = _parse_started(started)
    phases = _phase_table(meta)
    by_id = {phase["id"]: phase for phase in phases}
    pack = pack or _pack_for(meta)
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
        duration = _fight_ms(fight)
        rows.append(
            {
                "id": int(fight["id"]),
                "phase": phase_id,
                "phaseName": phase["short"],
                "phaseFull": phase["name"],
                "bossPct": _percent_left(fight.get("bossPercentage")),
                "progress": _progress(fight.get("fightPercentage")),
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


def _pull_cards(
    pull: dict,
    mechanics: list[dict],
    party: list[dict],
    durations: dict[int, float] | None = None,
) -> list[dict]:
    """Mechanic cards for one pull.

    A component is on the card once the pull lasted until that component resolves,
    or someone died to it. A player failed it when a death there was judged a fail.
    A death clipped by someone's marker sits under that marker, and the marker
    holder failed it, not the player who died. A dive landing caused by an arrow on
    the wrong side is failed by that arrow holder. Everyone else in the party passed.
    A pull that dies in a later phase still shows the earlier phase, and the later
    phase gets its own cards.
    """
    roster = [player for player in party if pull["id"] in player["fights"]]
    durations = durations or {}
    phases = set(durations) or {pull.get("phaseId")}
    cards = []
    for mech in mechanics:
        if mech["phase"] not in phases:
            continue
        duration = float(durations.get(mech["phase"], pull.get("duration") or 0))
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
            failed: dict[str, str] = {}
            for row in rows:
                if row["outcome"] != "fail":
                    continue
                for name in row.get("culprits") or [row["name"]]:
                    failed.setdefault(name, row["job"] if name == row["name"] else "")
            seats = [
                {"name": player["name"], "job": player["job"], "passed": player["name"] not in failed}
                for player in roster
            ]
            known = {seat["name"] for seat in seats}
            for name, job in failed.items():
                if name not in known:
                    seats.append({"name": name, "job": job, "passed": False})
                    known.add(name)
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
    fights = {int(fight["id"]): fight for fight in (meta or {}).get("fights") or []}
    pulls: dict[int, dict] = {}
    phase_durations: dict[int, dict[int, float]] = {}
    for item in judgments:
        fight = fights.get(item.fact.fight)
        pull = pulls.setdefault(
            item.fact.fight,
            {
                "id": item.fact.fight,
                "bossPct": item.fact.boss_pct,
                "phase": item.fact.phase_name,
                "phaseId": item.fact.phase,
                "clock": _pull_clock(_fight_ms(fight) if fight else item.fact.pull_ms),
                "duration": item.fact.pull_ms / 1000,
                "when": wall_clock(started, starts.get(item.fact.fight, 0)),
                "deaths": [],
            },
        )
        if item.fact.phase > pull["phaseId"]:
            pull["phase"] = item.fact.phase_name
            pull["phaseId"] = item.fact.phase
            pull["duration"] = item.fact.pull_ms / 1000
        phase_durations.setdefault(item.fact.fight, {})[item.fact.phase] = (
            item.fact.pull_ms / 1000
        )
        component = item.mechanic_id
        culprits: list[str] = []
        clip = clip_mechanic(item.fact, pack) if item.cause == "marker" else None
        if clip is not None:
            component = clip.id
            culprits = marker_owners(item.fact)
        if item.cause == "arrow":
            culprits = [blame.who for blame in item.blames]
        cluster = pack.cluster_for(component, item.fact.t, item.fact.phase) or _cluster_of(item, pack)
        pull["deaths"].append(
            {
                "time": item.fact.time,
                "t": item.fact.t,
                "phaseId": item.fact.phase,
                "name": item.fact.name,
                "job": JOB.get(item.fact.job, item.fact.job),
                "mechanicId": cluster.id if cluster else item.mechanic_id,
                "mechanic": cluster.name if cluster else item.mechanic,
                "componentId": component,
                "cast": item.mechanic,
                "outcome": item.outcome,
                "happened": item.happened,
                "should": item.should_have_been,
                "wrong": item.went_wrong,
                "blames": [blame.to_dict() for blame in item.blames],
                "culprits": culprits,
                "first": item.first,
            }
        )
        pull["firstMistake"] = item.first_mistake
    roster = _party(meta or {}, pack)
    for pull in pulls.values():
        pull["deaths"].sort(key=lambda row: (row["phaseId"], row["t"], row["name"]))
        pull["counts"] = Counter(row["outcome"] for row in pull["deaths"])
        pull["cards"] = _pull_cards(pull, mechanics, roster, phase_durations.get(pull["id"]))
    for mech in mechanics:
        cards = [card for pull in pulls.values() for card in pull["cards"] if card["id"] == mech["id"]]
        mech["reached"] = len(cards)
        mech["mistakes"] = sum(1 for card in cards if _card_failed(card))
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


def _pull_index(pull: dict) -> dict:
    """Pull list fields. Death reviews stay in the detail script."""
    return {
        "id": pull.get("id"),
        "bossPct": pull.get("bossPct"),
        "when": pull.get("when") or "",
        "phase": pull.get("phase") or "",
        "clock": pull.get("clock") or "",
    }


def _card_failed(card: dict) -> bool:
    return any(not seat["passed"] for part in card["parts"] for seat in part["seats"])


def _mechanic_index(mech: dict) -> dict:
    """Navigation for one mechanic, and how many pulls reached it and had a mistake there."""
    return {
        "id": mech.get("id"),
        "name": mech.get("name") or "",
        "phase": mech.get("phase"),
        "starts": mech.get("starts") or 0,
        "reached": mech.get("reached", 0),
        "mistakes": mech.get("mistakes", 0),
    }


def _jsonable(value):
    if isinstance(value, Counter):
        return dict(value)
    return value


def session_summary(payload: dict, detail_href: str) -> dict:
    """Chart and navigation for one session, without the death reviews.

    The reviews are embedded in that session's ``session.html`` and load when a
    pull or mechanic is opened. The library page fetches that HTML file.
    """
    overview = payload.get("overview") or {
        "phases": [],
        "pulls": [],
        "best": None,
        "markers": [],
    }
    return {
        "code": payload["code"],
        "fight": payload.get("fight") or "",
        "title": payload.get("title") or "",
        "owner": payload.get("owner") or "",
        "started": payload.get("started") or "",
        "day": payload.get("day") or "",
        "dayLabel": payload.get("dayLabel") or "No date",
        "timeLabel": payload.get("timeLabel") or "",
        "raw": payload.get("raw", 0),
        "fail": payload.get("fail", 0),
        "low": payload.get("low", 0),
        "detail": detail_href,
        "overview": overview,
        "pulls": [_pull_index(pull) for pull in payload.get("pulls") or []],
        "mechanics": [_mechanic_index(mech) for mech in payload.get("mechanics") or []],
    }


def detail_body(payload: dict) -> dict:
    """Death reviews and mechanic write-ups for one session."""
    return {
        "pulls": payload.get("pulls") or [],
        "mechanics": payload.get("mechanics") or [],
        "unknown": _jsonable(payload.get("unknown") or {}),
        "totals": _jsonable(payload.get("totals") or {}),
        "raw": payload.get("raw", 0),
        "fail": payload.get("fail", 0),
        "low": payload.get("low", 0),
    }


def _js_json(value) -> str:
    text = json.dumps(value, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def _versioned(href: str, path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return f"{href}?v={digest}"


def library_detail_href(root: Path, code: str) -> str:
    """Path from the library page to the session page that holds the reviews."""
    for folder in ("reports", "data"):
        path = root / folder / code / "session.html"
        if path.is_file():
            return _versioned(f"{folder}/{code}/session.html", path)
    return f"{code}/session.html"


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
    """One session. The death reviews are in the page, so a pull does not fetch another file."""
    path = report / "session.html"
    summary = session_summary(payload, "")
    path.write_text(_page([summary], _session_title(payload), detail=payload), encoding="utf-8")
    stale = report / "detail.js"
    if stale.is_file():
        stale.unlink()
    return path


def write_library(root: Path, payloads: list[dict]) -> Path:
    """Library page. Each session page should already be written."""
    return write_dashboard(root, [session_summary(payload, "") for payload in payloads])


def write_dashboard(root: Path, summaries: list[dict]) -> Path:
    """Library page from each session's `session_summary`, as saved in its stamp."""
    summaries = [
        {**summary, "detail": library_detail_href(root, summary["code"])}
        for summary in summaries
    ]
    path = root / "dashboard.html"
    title = "Sessions" if len(summaries) != 1 else _session_title(summaries[0])
    path.write_text(_page(summaries, title), encoding="utf-8")
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


def _detail_block(payload: dict | None) -> str:
    if not payload:
        return ""
    body = _js_json(detail_body(payload))
    return f'<script type="application/json" id="session-detail">{body}</script>\n'


def _page(payloads: list[dict], title: str, detail: dict | None = None) -> str:
    data = _js_json(library_payload(payloads))
    icons = json.dumps(_job_icons(), separators=(",", ":"))
    template = (Path(__file__).parent / "session_template.html").read_text(encoding="utf-8")
    html = template.replace("__DATA__", data)
    html = html.replace("__JOB_ICONS__", icons)
    html = html.replace("__TITLE__", title)
    return html.replace("__DETAIL__", _detail_block(detail))
