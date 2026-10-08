---
name: review-session
description: >-
  Process a whole FFLogs session with compact digests so the model reads less.
  Use when reviewing a log, night, session, report code, or "what happened this
  session", or when starting work on a dropped report before opening raw JSON.
---

# Review a session

Use scripts first. Do not load `judgments.json`, `facts.json`, `abilities/`, or
`positions/` into context unless a digests line forces a single-death follow-up.

## Steps

1. If `judgments.json` is missing in the report folder, run:

```
PYTHONPATH=src python3 -m xivloganalyzer analyze <code>
```

   Either way, check what the log is missing. Fetch the ability files it names before
   trusting the calls. A call made without some input lists it in `missing`.

```
PYTHONPATH=src python3 -m xivloganalyzer check <code>
```

2. Print a digest. For an overview ("how was the night"), start with counts only:

```
PYTHONPATH=src python3 -m xivloganalyzer brief <code> --detail none
```

For unknowns and raw death lines (default detail):

```
PYTHONPATH=src python3 -m xivloganalyzer brief <code>
```

Optional filters:

```
PYTHONPATH=src python3 -m xivloganalyzer brief <code> --pull 68
PYTHONPATH=src python3 -m xivloganalyzer brief <code> --mechanic "Skyward Leap"
PYTHONPATH=src python3 -m xivloganalyzer brief <code> --outcome unknown
PYTHONPATH=src python3 -m xivloganalyzer brief <code> --write
```

`--write` also saves `brief.txt` next to the judgments. Prefer the command
output; read `brief.txt` only when it is already current.

3. Answer from the digest. Default detail is **unknown** and **raw** only.
   Fail stays in the counts and pull index. A deathwall death is a fail. Do not
   paste the whole raw list into the reply unless the person asked for it. For
   a pull, lead with its first mistake; each death line says whether it was the
   first mistake or came after it.

4. Open a mechanic skill only when:
   - the digest lists an **unknown** (use the guid + `review-mechanic` index)
   - the person corrects a call
   - one death is disputed and the digest line is not enough

5. For a single death still unclear after the digest, filter first
   (`--pull` / `--mechanic` / `--outcome`). Only then open that death's packet
   fields or the ability file.

## Corrections

Same as `review-mechanic`: edit `fights/dsr/mechanics.json`, then:

```
PYTHONPATH=src python3 -m xivloganalyzer reanalyze
PYTHONPATH=src python3 -m xivloganalyzer brief <code>
```

Update `tests/test_reference.py` only when the settled headline is meant to
change. Leave `dashboard.html`, `session.html`, `analysis.json`, and `inputs.json` alone; reanalyze rewrites them.

## Do not

- Read full `judgments.json` or `facts.json` to overview a session
- Open every mechanic skill for a night review
- Re-judge deaths the digest already labels unless correcting parameters
