---
name: assign-fault
description: >-
  The one process for deciding who messed up in a Dragonsong's Reprise pull,
  and why. Use when a blame looks wrong, when the person says "that wasn't
  them" or "this is not 8 people failing", when checking a session's blame,
  when a call names a group instead of a player, or before changing how any
  mechanic assigns fault.
---

# Assign fault

`review-mechanic` says what a hit was. This skill says whose fault it was, the same way for every mechanic. The mechanic skill holds the facts for that mechanic: what a correct resolve looks like, and which debuffs and hits show who had which job.

## The rule

Fault belongs to the player whose action broke what the mechanic needed. A player who did their part is never at fault, even when they died.

When a player was missing from their part because they were already dead, the gap is theirs. When that death was itself someone else's fault, the gap passes on to that owner. The first mistake of the pull is usually where the chain starts.

## Steps

Do these in order for every disputed death. Write down what each step found.

1. **Killing blow.** Read it the way `review-mechanic` says. A status link, such as Frostbite `#status/2946`, is a real killing blow. Only a row with no ability at all is the deathwall.
2. **What the mechanic needed.** From the mechanic skill: who takes it, how many bodies, where they stand, which debuff or marker gives the job, what mitigation and HP a lived hit needs.
3. **Party state at the cast.** From the log, never from memory:
   - Who played the pull. `src/xivloganalyzer/roster.py` reads it per pull, so a substitute or a job swap counts only where they played.
   - Who was alive. A death before the cast, with no Weakness `1000043` after it, is still dead.
   - Who held which job. Debuffs in `mitigations/fight-NN.json` auras, such as Prey `1000562`, the Dive from Grace numbers, and the resistance-down debuffs from an ice or lightning hit.
   - Who was hit, and by what. The cast's own hit list, and any soak that must hit everyone in place, from `abilities/ab_<guid>.json`. Survivors are in there too.
   - Which hit was which. `packetID` is one hit, such as one orb. `sourceInstance` is one copy of the caster, such as one tower. Two targets on one tower's instance shared it.
   - The snapshot. `calculateddamage` rows list everyone the hit snapped, including a player who died before the damage landed. Count a stack from the snapshot, not the damage rows.
   - Where people stood. `positions/fight-NN.json` samples players every few seconds. An NPC such as a Holy Comet is sampled at each of its own hits, so its spots are exact.
4. **The deviation.** Compare what was needed with what happened. Name who was not where the mechanic needed them, or who took what was not theirs.
5. **Owner.** The player who deviated owns it at 100. Several players who each deviated split it evenly. A player who was missing because they died earlier passes it on to whoever owned that death, when that death was a cascade.
6. **Group label only as a last resort.** Use a group label such as Prey markers, Missed soak, or Missing bodies only when steps 3 and 4 cannot name anyone. Say which evidence was missing. `audit` lists every such call.
7. **Sentence.** Name the player and the deviation: "Absolute Gigachad was already dead, so a tower was empty." Do not name the victims' damage.

## Evidence order

When two kinds of evidence disagree, trust them in this order:

1. The hit list of the cast and of its soak: who was hit, and who was not.
2. Debuffs: who held which marker or number, and when it came off.
3. Deaths and raises: who was alive.
4. Positions: sparse, so a position near the cast is only a hint.
5. Timing alone.

A call that rests only on positions or timing says so in its confidence, and gets a test that pins the pull.

## Prove it before changing a call

A story that fits one pull is not evidence. Pull 53 of `8DYNHQx4C7ytdLb9` looked like seven players in their towers dying because the paladin was dead. The log showed Holy Impact landing before the towers, and its two source spots sitting on Kite Noodle's last comet and Speed Panda's first. Check the timing and the hit list before the story.

- Check the cause lands before the effect.
- Check the same rule on clean pulls. The cause should be absent there.
- Check the pulls where the rule would name someone else. Each one is a counterexample until explained.

## Shapes

Most mechanics are one of these shapes. The question to ask is the same for each shape.

| Shape | Needed | Who owns a failure |
|---|---|---|
| Soak or tower | One player in each tower | Whoever was not hit by the soak: dead, or alive and elsewhere. Everyone in place is not at fault. The Strength towers are healers and DPS only (`roles`). |
| Stack | N bodies in each share | The players who should have been in the share: dead, or alive and in another share or none. A packet is a share or a cleave once, from its middle victim's hit against their role cap. |
| Alternating stack | Two groups take turns, such as Sacred Sever | The group is whoever took the cast two before. A cast that landed on the other group, still carrying the last cast's vulnerability, belongs to the right group's dead players. |
| Pairs | One support and one DPS in each circle, such as Hiemal Storm (`pairs`) | For a lone ice, the partners who were dead, in no circle, or doubled up in another circle. Transcendent `1000418` counts as dead. |
| Spread or overlap | Nobody shares a circle | Every player in the overlap. A survivor in the burst is named from the hit list. |
| Marker | The marked player in their spot | The marked player off their spot, or the player who stood in the marked player's spot. |
| Drops | Each marked player's drops land apart | Whoever dropped the two that landed too close: one player's own pair, or both players at 50. A dead holder passes it on. |
| Tankbuster | The right tank, with personal mitigation | A non-tank who took it, the wrong tank, or a tank without mitigation. When the right tank was dead, such as Heavenly Heel's off tank, that tank owns it, passed on. |
| Dodge, gaze, cone, puddle | Nobody hit | The player who was hit. |
| Raidwide | Everyone lives with mitigation and HP | The healers and the party's mitigation, unless the party was short or already low. Then pass it on to whoever made it short or low. Low from their own gaze, dodge, puddle, or orb a few seconds before is that player's own. |
| No packet | Nobody touches the wall | The player, alone before the first mistake, shared with "Earlier mistake" after it. |

## Checking a session

```
PYTHONPATH=src python -m xivloganalyzer check <code>
PYTHONPATH=src python -m xivloganalyzer audit <code>
PYTHONPATH=src python -m xivloganalyzer audit <code> --flag unnamed
```

`check` lists the inputs the log is missing. A call made without one names it in its `missing` list, such as `ability 25567`. Fetch those before trusting the call.

Each flag is an open question, not a verdict:

- `unknown`: the hit is not understood.
- `unnamed`: the blame is a group label. Can the log name the player?
- `mass-self`: three or more players died to one cast, each blamed on themselves. Did one earlier action cause all of them?
- `raw-after-death`: a raw death after someone already died. Was the party short?
- `thin-split`: three or more players share it. Is one of them the real cause?
- `degraded`: the call was made without an input it reads. Fetch it (`check`) and reanalyze.
- `mass-wall`: the pull's first mistake is three or more players dying with no packet at once. Was it the deathwall, or a hit the log did not record (8DYNHQx4C7ytdLb9 pull 33, right after Eye of the Tyrant)?

`python -m xivloganalyzer evidence <code> --pull N` prints the pull's hits, markers, and deaths in time order, then each call with its `basis`: what decided the owner (their own hit, a debuff, positions, who the cast hit, a role rule, no packet, or a label). A `role` or `label` basis, or a call with `missing` inputs, is the weakest. Record each call you checked with `confirm` (`review-new-log`).

Work one flag and one mechanic at a time. For each, follow the steps above on two or three pulls, including a clean pull for contrast.

## Changing a rule

1. Show the rule holds on every pull it touches, not just the reported one. Look for counterexamples: a clean pull, a pull with the same shape and a different cause.
2. Put mechanic facts in `fights/dsr/mechanics.json` (for example `needs_everyone`, a list of rows with the soak, `roles`, `until` or `after`, and `holders`) and the mechanic's skill. Put shared logic in `src/xivloganalyzer/judge.py` and `extract.py`.
3. Add a test that names the pull and the owner, in `tests/test_audit_rules.py`, or `tests/test_reference.py` for the reference log.
4. Run the tests, then `python -m xivloganalyzer reanalyze`. Read `python -m xivloganalyzer changes --since HEAD`: every call the rule moved, on every log. A moved call you did not expect is a counterexample. Run `verify`, and compare `audit` before and after.
5. Update `notes/classification.md` with the reason, and `review-mechanic` when the blame list changes.
6. Ask the person when the data cannot decide. Do not guess a mechanic's plan.
