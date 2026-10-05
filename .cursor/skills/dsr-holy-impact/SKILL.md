---
name: dsr-holy-impact
description: >-
  Identify Holy Impact (guid 25578) deaths in Dragonsong's Reprise Thordan:
  real raidwide versus a failed hit, and whose fault it was. Use when the
  killing blow is Holy Impact or 25578.
---

# Holy Impact

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `holy-impact` in `fights/dsr/mechanics.json`. Guid `25578`. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). The session stop is Meteors. The wiki calls this the meteor-overlap explosion. The death rule below still treats a hit inside the role cap as raw until the person says otherwise.

Same shape as Eternal Conviction. It does not scale with stack size. Tanks take about 63k. Everyone else takes about 95–103k, including in a full party of 8.

## How to tell

- At or under the role cap: the real raidwide. Pulls 66 and 67 are the whole party with no shield and multiplier 1.00, and they are still the real hit when the unmitigated amount is inside the cap.
- Over the role cap: a failed hit. Missing bodies do not explain it.
- Vulnerability or Damage Down on the packet, or on the calculated-damage sibling when `buffs` is empty: fail, even inside the band.

## Fault

Raw: the resolve. Name the shield, the mit, and the HP.

Fail over the cap: `{player}` took a hit that is not Holy Impact. Do not call it a short stack.

Low: the raidwide was normal and they were already under 15,000 HP.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast: time in the phase, bodies hit, unmitigated by role on hits people lived. The current parameter is the same shape as Eternal Conviction: it does not scale with stack size, including on pulls where the whole party is hit with no shield and multiplier 1.00. Confirm that from lived hits before treating a death cluster as the band.
