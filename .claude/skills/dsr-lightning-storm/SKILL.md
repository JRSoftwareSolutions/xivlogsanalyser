---
name: dsr-lightning-storm
description: >-
  Identify Lightning Storm (guid 25549) deaths in Dragonsong's Reprise
  Thordan: a clean spread versus an overlap, and whose fault it was. Use when
  the killing blow is Lightning Storm or 25549.
---

# Lightning Storm

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Entry `lightning-storm` in `fights/dsr/mechanics.json`. Guid `25549`. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

## Parameters

One cast, about 43 seconds after phase 2 starts, inside the two safe triangles left by the knight dashes. 53 of 55 qualifying pulls store it. Pulls 23 and 45 wipe before it, at 25 and 29 seconds. There is no later cast.

A correct triangle is four players:

- Healer in front
- Melee on the left
- Ranged on the right
- Tank at the back

One healer, one melee, one ranged, and one tank on each side. This party is two of each, so the split is one and one.

Correct damage is one hit on each player. Hits people lived, unmitigated:

- Tanks: 26–29k, median about 27k
- Healers: 38–42k, median about 40k
- DPS: 38–45k, median about 42k

The multiplier on those hits is 1.00. Some carry a shield of about 5–24k. Most have none. No personal mitigation is required. Nobody died on a hit in that band.

## How to tell

- One hit in the lived band: the spread connected. A death is raw, or low if they were already under 15,000 HP. None of the reference deaths were inside the cap.
- Two players caught by the same bolts, with a second hit around 430–470k: they clipped. Each of them owns it.
- Two melees, two healers, or two ranged on the same side: a mistake. This log has no positions, so a normal-sized hit does not show it.
- A player standing anywhere other than the spot above: a mistake. Same limit. The damage does not show the spot.
- A Spiral Thrust hit: a mistake. No guid is stored. Do not invent one.

## Fault

Clip: `{player}` clipped Lightning Storm. The other player in the pair owns it too.

Pull 31, at 43.1 seconds, is the clip. Kite Noodle took 467,734 and died from full HP. Spring Nymphar took a lived 42,175, then 431,068, and died. Both bolts hit both of them.

Raw: the spread was the normal hit and the resolve lost. Name the shield, the mit, and the HP.

Wrong side or wrong spot, when positions are known: `{player}` was out of the Lightning Storm spot. Healer front, melee left, ranged right, tank back, one of each on a side.
