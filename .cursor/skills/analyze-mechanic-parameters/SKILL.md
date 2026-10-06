---
name: analyze-mechanic-parameters
description: >-
  Set a Dragonsong's Reprise mechanic's parameters from casts, not from the
  death list: when it happens, who may be hit, how many bodies, the lived
  damage band, and what mitigation is required. Use when refining mechanics
  one by one, defining parameters, or deciding what a correct cast looks like.
---

# Analyze a mechanic's parameters

Parameters answer what a correct cast looks like, so a later review can say what happened, what it should have been, and whose fault a miss was. Which casts are one mechanic, and what each component does, is `mechanic-components`. The person confirms that list. Caps already stored in `fights/dsr/mechanics.json` are the current numbers. This pass checks them against every cast, then adds the plan the damage numbers do not show.

Walk abilities in the order they hit during the phase. The death catalog is not that order. The first pass named Ascalon's Might, then Lightning Storm, then the Heavenly Heel tank swap with the second Might.

## Survey the casts

Phase 2 only. A pull counts when `lastPhaseForPercentageDisplay` is at least 2 and the phase lasts at least 20 seconds. Time zero is the phase 2 start.

Use damage events in `data/<report>/abilities/ab_<guid>.json`. Deaths are the failures. The lived band comes from hits people survived.

1. On one long pull, list damage bursts in order. A new burst starts when the guid changes or the gap is more than about 4 seconds. That places the ability and shows when the same guid comes back as a later assignment.
2. On every qualifying pull, cluster that guid into casts. Hits within about 8 seconds are one cast when the ability is multi-hit. Record, per cast: time in the phase, hit count, distinct people, jobs, unmitigated min / median / high / max, multiplier, shield, overkill.
3. Split those casts by time. An opener and a later cast of the same guid are different assignments until the plan says they are the same.
4. The tight cluster of hits people lived is the real band. A second body, a disallowed job, or an unmitigated amount far above that cluster is the fail shape. Quote the pull where the exception happened.

## Parameters to write down

Fill these on the mechanic skill, then on `fights/dsr/mechanics.json` where a field exists. The death's `should_have_been` line is that cast only. When a later cast is a different assignment, put its line on that cluster part. Do not describe the other cast in this one. Update `notes/classification.md` when the reason changes. Run `python -m xivloganalyzer reanalyze`. Touch `tests/test_reference.py` only when the 183 raw deaths on `XVz8bCqgPw1KRh9d` are meant to change.

| Parameter | What to record |
|---|---|
| When | Seconds after phase start, and whether a later cast is a separate assignment. If that moves the cast onto another session stop, move its `parts` window and the cluster `starts`. Edit the skill named on that cluster |
| Bodies | How many people a correct cast hits |
| Who | Which jobs may take it. A non-allowed player who is hit owns that mistake |
| Lived band | Unmitigated range of hits that were lived, by role. Deaths do not set this band |
| Mitigation | Invuln, personal mit, party mit, shield. Say which of these a correct take uses |
| Personal mit death | When a tank dies on a normal-sized hit without the required personal mit, that tank owns the mistake. It is not raw |
| Fail shape | Extra body, wrong job, or the oversized amount, and who owns it |

The plan (who is assigned, invuln, a tank swap) comes from the user when the log cannot show it. Do not invent an assignment from one party's habit. Do record what this log actually did, as evidence.

After the parameters are written, judge deaths with `review-mechanic` and that mechanic's skill. The mechanic skill wins when it says a normal-sized hit is still a mistake.
