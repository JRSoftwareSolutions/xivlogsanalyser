# xivloganalyzer

Session reviews for FFLogs. Dragonsong's Reprise is the first fight. The dashboard says what happened, what the mechanic should have been, and whose fault the death was.

## Current session

[XVz8bCqgPw1KRh9d](https://www.fflogs.com/reports/XVz8bCqgPw1KRh9d), Kite21, Ultimates (Legacy). Played Sat 3 Oct 2026, 21:17–00:03 (pull 68 is the 12:02 AM label from the log). Thordan: **187 raw deaths** across 55 pulls. Pull 68 is Kitana Kahn on a real Skyward Leap.

Open [dashboard.html](dashboard.html) after an analysis run. Every log is a session, listed by the day and the time it was played. Each session opens on a pull chart (taller means further into the fight), then the pull count and the mechanics for each phase. Those mechanics are the `clusters` in `fights/dsr/mechanics.json`, in `starts` order, drawn as a line. `markers` in `fight.json` are chart labels only. The side panel keeps the session list, the pulls, and the mechanics. The main area changes in place.

## How a log gets in

Put a report folder in `reports/<code>/` (or `data/<code>/`) with:

- `fights.json` from `/reports/fights-and-participants/<code>/0`
- `deaths-html.json`, a list of `{id, html}` death tables
- `abilities/ab_<guid>.json` for damage-taken on the mechanics we already know
- `positions/fight-<id>.json` from `/reports/replaysegment/<code>/<boss>/<start>/<end>`. Each sample is `[timestamp, actorId, x, y, facing, friendly]`. `x` and `y` are the in-game coordinates times 100, and `facing` is the actor's facing on that sample. `actors` maps those ids to names.
- `mitigations/fight-<id>.json` from that same replay. `auras` is `[timestamp, action, guid, name, sourceId, targetId, duration, stacks, via]`. `sourceId` is who applied it. `hits` is `[timestamp, targetId, sourceId, abilityGuid, multiplier, absorbed, mits]`, and each mit is `[guid, name, sourceId, targetId, percent]` where 90 means the hit was multiplied by 0.90. `shields` is `[timestamp, targetId, sourceId, guid, name, amount, attackGuid, attackerId]`.
- `party.json` optional, name to max HP
- `aura_map.json` optional
- `session.json` optional, with `started` (ISO-8601 time of report zero), `title`, and `owner`. That is what places the log on a day and a clock. A `start` unix time on `fights.json` is used when the sidecar is missing.

Then:

```
python -m xivloganalyzer analyze <code>
```

That writes `facts.json`, `judgments.json`, and `session.html` in the report folder, and rebuilds `dashboard.html` for every saved log.

## When a call is wrong

Mechanic knowledge lives in `fights/dsr/mechanics.json`. A correction such as "that hit is not a mistake" or "this should count as a failed soak" is a change to that file, then:

```
python -m xivloganalyzer reanalyze
```

Every saved log is judged again. `notes/classification.md` is the write-up of why Thordan is called the way it is. `tests/test_reference.py` keeps the current 187 until we change a call on purpose.
