# xivloganalyzer

Session reviews for FFLogs. Dragonsong's Reprise is the first fight. The dashboard says what happened, and a short line for what went wrong. Each blame has a confidence: 100% when one person owns it, and a lower share when several people made a mistake.

## Reference log

[XVz8bCqgPw1KRh9d](https://www.fflogs.com/reports/XVz8bCqgPw1KRh9d), Kite21, Ultimates (Legacy). Played Sat 3 Oct 2026, 21:17–00:03 (pull 68 is the 12:02 AM label from the log). Thordan: **86 raw deaths** across 55 pulls. Pull 68 has no raw death. Kitana Kahn's Skyward Leap was full HP with no mitigation.

The other two nights are [8DYNHQx4C7ytdLb9](https://www.fflogs.com/reports/8DYNHQx4C7ytdLb9) (Mon 5 Oct 2026, 21:31–00:14) and [3wzL6x4VHTmvNkhq](https://www.fflogs.com/reports/3wzL6x4VHTmvNkhq) (Wed 30 Sep 2026, 21:44–00:03).

Open [dashboard.html](dashboard.html) after an analysis run. The side panel is the fight, then the sessions newest first. The main area starts as the sessions list: a general trend of how far each night got, then each night on its own row with its pull count and furthest mechanic. The trend fits every night in view and scrolls sideways only when the pulls would get too thin to read. Hover a bar for that pull. A row starts collapsed. Open it for that night's pulls. Open a session for its overview, pulls, and mechanics. Death reviews load when a pull or a mechanic is opened. Inside a session, the main area is the pull count, the furthest and the best pull, then a pull chart (taller means further into the fight, numbered by pull, with the furthest and best pull labelled), then the mechanics for each phase with how many pulls had a mistake there, drawn as a bar. Those mechanics are the `clusters` in `fights/dsr/mechanics.json`, in `starts` order, drawn as a line. `markers` in `fight.json` are chart labels only. A mechanic page lists who failed each part and how often, then one row per pull that reached it. Clear pulls are dimmed, and the list can show only the pulls with a mistake. A pull page, and a pull opened on a mechanic page, shows only the parts where someone failed or died, and only the players who failed them. Clear mechanics and passed players are left out.

## Setup

Python 3.10 or newer, and nothing else. Install the package once from the repo root:

```
python -m venv .venv
.venv\Scripts\activate          # macOS or Linux: source .venv/bin/activate
pip install -e .
```

Without installing, put `src` on the path instead, for example `PYTHONPATH=src python -m xivloganalyzer reanalyze`. The tests are `python -m unittest discover -s tests`.

## Working with an AI agent

The project instructions are in `AGENTS.md`. Cursor reads that file directly, and `CLAUDE.md` imports it for Claude Code. The skills (`review-session`, `review-mechanic`, one `dsr-*` skill per mechanic, and so on) are in `.claude/skills/`. Both Cursor and Claude Code load skills from there, so each skill exists only once.

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

That writes `facts.json`, `judgments.json`, `session.html`, and the `analysis.json` stamp in the report folder, and rebuilds `dashboard.html` for every saved log. The death reviews are inside `session.html`. The dashboard keeps every night's pull chart and loads that page when a review is opened. The same run draws an arena still for each mechanic the party failed, from `positions/`. A clear mechanic has no still. The cast time comes from the damage events. Faith Unmoving has no stored cast, so its part `at` in `mechanics.json` is the time, and only while that pull was still going and someone failed it. A Sanctity of the Ward empty tower is drawn when the towers resolved, about two seconds before Eternal Conviction: every tower to size, the empty ones filled, players who were already dead left out, and anyone outside a tower or sharing one ringed and named in the caption. A log with no positions keeps the text.

For a short text digest of one session (counts, pull index, unknown and raw death lines):

```
python -m xivloganalyzer brief <code>
python -m xivloganalyzer brief <code> --pull 68
python -m xivloganalyzer brief <code> --mechanic "Skyward Leap"
python -m xivloganalyzer brief <code> --write
```

`--write` also saves `brief.txt` in the report folder. The `review-session` skill uses this instead of loading full JSON.

## When a call is wrong

Mechanic knowledge lives in `fights/dsr/mechanics.json`. A correction such as "that hit is not a mistake" or "this should count as a failed soak" is a change to that file, then:

```
python -m xivloganalyzer reanalyze
```

Every saved log whose rules changed is judged again. `notes/classification.md` is the write-up of why Thordan is called the way it is. `tests/test_reference.py` keeps the current 86 raw deaths until we change a call on purpose.

## Which logs are up to date

Each report folder gets an `analysis.json` stamp when it is judged. It holds a fingerprint of the fight pack (`fights/dsr/fight.json` and `mechanics.json`), of the analyzer code, and of that log's own files (`session.json` included), plus a fingerprint of each page it wrote and the session's dashboard entry. Line endings and hidden files do not count, so the stamp reads the same on Windows, macOS, and CI.

```
python -m xivloganalyzer status            # which logs are out of date, and why; writes nothing
python -m xivloganalyzer reanalyze         # judge only those again, then rebuild the dashboard
python -m xivloganalyzer reanalyze --all   # judge every log again
```

`status` exits with 1 when any log is out of date. A changed rule in `fights/dsr/` makes every Dragonsong log out of date. A corrected `session.json` makes only that log out of date. `analyze <code>` always judges that log, and also any other log that is out of date. The stamps are committed with the pages. CI checks `status`, then runs `reanalyze --all` and fails when a page or stamp changes.
