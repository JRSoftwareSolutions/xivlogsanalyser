---
name: dsr-ascalons-mercy-concealed
description: >-
  Parameters and faults for Ascalon's Mercy Concealed (guid 25545) in
  Dragonsong's Reprise Thordan. One tank in front, everyone else stacked
  behind, then dodge. Any hit is a mistake. Use when refining or judging
  Ascalon's Mercy Concealed or 25545.
---

# Ascalon's Mercy Concealed

Follow `analyze-mechanic-parameters` when changing these parameters. Follow `review-mechanic` when judging a death. Entry `ascalons-mercy-concealed` in `fights/dsr/mechanics.json`. Guid `25545`. `any_hit_is_fail` is true. The cones about 14 seconds in are the opener (`dsr-thordan-opener`). The cones about 50 seconds in are Strength of the Ward (`dsr-strength-of-the-ward`). Same cones both times.

## Parameters

Cones. A correct cast hits nobody. There is no raw band. Hits in this log are about 190–220k.

**Opener, about 14 seconds.** One tank stands in front of the boss. Everyone else stacks tight behind the boss, then dodges together. The death line for this cast is that stack and the dodge. It does not describe the Strength cast.

**Second cast, about 50 seconds, inside Strength of the Ward.** The party is walking toward the middle while dodging the Heavy Impact pulses. Thordan is in the middle. This cast is a 4/4 split. The opener's one-in-front, seven-behind stack does not apply here. Nobody is hit. The out-of-stack baiter rule is the opener only. The death line for this cast is the 4/4 split. It does not describe the opener.

## How to tell

- No damage from this guid: the dodge was clean.
- Any hit: fail. The player who took it owns that mistake.
- There is no lived band and no short-stack reading.

## Fault

`{player}` got hit by Ascalon's Mercy Concealed. Nobody should be hit.

Opener only: someone stood out of the stack, so their cone was baited away from the group. On the dodge, that cone hits someone else. The player who was hit still owns being in the cone. The player who baited from outside the stack shares the blame, even when that baiter took no damage. The Strength cast is a 4/4 split, so that baiter rule does not apply there.

Positions for this log are in `data/<code>/positions/fight-<id>.json`. A sample is `[timestamp, actorId, x, y, facing, friendly]`, with `x` and `y` stored as in-game coordinates times 100. A death names the player who was hit. Do not pick a loose baiter from a second death on the same cast. Two players hit means both of them were in a cone. Pulls 12, 23, and 45 each have two opener deaths at the same timestamp. Those are two hits, not a named baiter.

Pull 68: Loki Doki on the opener, Spring Nymphar during Strength. Both fails.
