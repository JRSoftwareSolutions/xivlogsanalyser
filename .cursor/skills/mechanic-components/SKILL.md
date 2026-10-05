---
name: mechanic-components
description: >-
  Group Dragonsong's Reprise casts into mechanics and say what each component
  does. Use when a death is listed as a bare ability, when clustering
  Strength of the Ward, Sanctity of the Ward, or any Thordan mechanic, or
  when the user says a cast belongs to a mechanic or does not.
---

# Mechanic components

A mechanic is several casts and effects that resolve together or in a short sequence. A component is one of those casts: its name, its guid when this log has one, what it does, and what a hit means.

Death review can still name the killing blow. The mechanic skill says which other components were part of the same moment.

## Where the draft comes from

The FFXIV wiki page for Dragonsong's Reprise is the published list of what each cast does. Report `XVz8bCqgPw1KRh9d` is where those guids actually land in phase 2. Time zero is the phase 2 start. A guid that only appears inside one time window belongs to the mechanic that occupies that window.

Guides disagree with each other on movement. They are not this party's positions. Clock spots, light parties, and who stands where stay out of these skills until the person states them.

## The person refines

Online text is a draft. The person decides what belongs and what a component does. A correction ("X belongs to Y", "Z is not part of this", "that hit means this") updates the mechanic skill, then the `clusters` entry in `fights/dsr/mechanics.json` if the dashboard groups by that entry.

Do not retune role caps or the 183 raw deaths while only regrouping components. Fault for a single killing blow stays in that ability's skill. If the guide and that skill disagree about what a hit means, say so and wait for the person.

Do not invent a guid for a cast this log has not stored. Spiral Thrust, Ancient Quaga, Faith Unmoving, Ultimate End, Broad Swing, and Aetheric Burst are in the phase write-up and are not studied components yet.

## Where a stop is drawn

The session line for a phase is `clusters` in `fights/dsr/mechanics.json`, top to bottom by `starts` (seconds into that phase). `skill` on a cluster is the skill for that stop. A new stop is a cluster with `phase`, `starts`, `summary`, `skill`, and `parts`. The page sorts by `starts`. Do not hardcode the order in the template.

`markers` in `fights/dsr/fight.json` are names on the pull chart for moments with no death review. Phase 1 uses markers only. They are not stops on the line.

## Phase 2 stops this log draws

| Stop | Cluster | About | Skill |
|---|---|---|---|
| Ascalon's Mercy Concealed | `ascalons-mercy-opener` | cones, about 14s | `dsr-thordan-opener` |
| Ascalon's Might | `ascalons-might-opener` | three-hit, about 17s | `dsr-thordan-opener` |
| Strength of the Ward | `strength-of-the-ward` | about 43–65s | `dsr-strength-of-the-ward` |
| Heavenly Heel | `heavenly-heel-swap` | heel, then three mitigated cleaves, about 81s | `dsr-heavenly-heel` |
| Sanctity of the Ward | `sanctity-of-the-ward` | gazes and jumps, about 112s | `dsr-sanctity-of-the-ward` |
| Meteors | `meteors` | ice, fire, towers, meteors, about 130s | `dsr-sanctity-of-the-ward` |

The opener is two stops. Sanctity is two stops: Meteors is the second wave, and `dsr-sanctity-of-the-ward` still explains it. Fault for a killing blow stays in that ability's skill.

Phase 3 and later stay out until the person is on them.
