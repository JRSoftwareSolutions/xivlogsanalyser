---
name: review-new-log
description: >-
  The repeatable intake for a new FFLogs report: drop it in, check its inputs,
  read what went wrong, check the weak calls against the evidence, and record
  every checked call so accuracy is measured. Use when a new log or report code
  arrives, when the person says "here's tonight's log", or before trusting the
  blame on a log nobody has reviewed yet.
---

# Review a new log

Every step is a command. Run them from the repo root, with `PYTHONPATH=src` when the package is not installed. Do not open `judgments.json`, `facts.json`, or the raw files until a step below points at one death.

## 1. Drop it in and judge it

Put the folder in `reports/<code>/`: `fights.json`, `deaths-html.json`, `abilities/ab_<guid>.json`, `positions/fight-NN.json`, `mitigations/fight-NN.json`, and `session.json` with `started`, `title`, and `owner` (README.md, "How a log gets in"). Then:

```
python -m xivloganalyzer analyze <code>
```

## 2. Make the inputs complete

```
python -m xivloganalyzer check <code>
```

It lists the ability files the reached phases need and do not have, pulls with no positions or mitigation replay, players with no max HP, buff ids with no name, how many calls were made without some input, and every death row that was not judged, with why. Fetch the ability files it names from the official FFLogs API, then run `analyze` again:

```
python -m xivloganalyzer fetch <code>
python -m xivloganalyzer analyze <code>
```

`fetch` needs FFLOGS_CLIENT_ID and FFLOGS_CLIENT_SECRET (an API client from https://www.fflogs.com/api/clients/) in the environment. Positions and the mitigation replay come from the site, which sits behind a human check; fetch those in a browser session a person can click through. Repeat until it is clean, or until the person agrees to the gaps that are left. A call made without an input lists it in `missing`; that call is weaker, whatever it says.

Then run the tests. `tests/test_invariants.py` checks every saved log, the new one included: every owner played the pull or is a label, every mistake has an owner and a basis, every death row is accounted for.

```
python -m unittest discover -s tests
```

## 3. Read what went wrong

```
python -m xivloganalyzer brief <code> --detail none
```

The brief opens with what lost each pull, who lost pulls, and each player's share of the night's deaths. That is the answer to "what went wrong tonight". The pull lines say the mistake each pull was lost to; a death the party recovered from does not count. Lead with those, not with the death totals: most deaths cascade from the mistake that lost the pull.

## 4. Check the weak calls

```
python -m xivloganalyzer audit <code>
```

It lists the calls on weak evidence: unknown hits, group labels where a player might be named, mass self-blame, raw deaths after a death, thin splits, and calls made without an input. For each one:

```
python -m xivloganalyzer evidence <code> --pull N
```

That prints the pull's hits, markers, debuffs, and deaths in time order, then the judge's calls, each with its `basis` (what decided the owner) and the inputs it was made without. Decide with `assign-fault` and the mechanic's skill.

- The judge is right: record it, so a later rule change cannot quietly undo it.
- The judge is wrong and the rule is clear: record the right call, fix the rule (`review-mechanic`, `assign-fault`), and go to step 6.
- It is a judgment call the rules do not settle: ask the person. Their answer is a `--by user` call.

```
python -m xivloganalyzer confirm <code> --pull N --name "<player>" [--time M:SS] [--outcome fail] [--owners "A,B"] --by review --why "<the evidence>"
```

Without `--outcome` and `--owners`, `confirm` records what the judge says now. With them, it records the call you checked and keeps the judge's call as `first_pass`. Record before changing any rule.

## 5. Spot-check calls nobody flagged

The audit only sees the calls it knows to doubt. Pick at least five pulls spread over the night and the mechanics, and read each one blind first:

```
python -m xivloganalyzer evidence <code> --pull N --blind
```

Make your own call for each death, then compare with the judge (`evidence` without `--blind`) and record each checked death with `confirm`. A log from a new party gets 20 to 30 checked calls across mechanics before its blame is trusted.

## 6. After any rule change

```
python -m xivloganalyzer reanalyze
python -m xivloganalyzer changes --since HEAD
python -m xivloganalyzer verify
```

`reanalyze` judges every saved log again and lists the calls it changed. Read the `changes` list: every moved call should be one you meant to move. A call that moved and is marked `[checked by ...]` needs a second look. `verify` must pass: it fails when a call the person made no longer holds. It also reports how often the judge agreed with the checked calls before they were checked, by mechanic. That is the judge's accuracy on a new log.

## 7. Commit

Commit the report folder (pages, `analysis.json`, `calls.tsv`, `inputs.json`), `reviews/<code>/verified.json`, and any rule and test changes together. CI runs the tests, `status`, `verify`, and lists the calls a pull request moves.
