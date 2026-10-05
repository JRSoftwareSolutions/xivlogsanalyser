---
name: dsr-lightning-storm
description: >-
  Identify Lightning Storm (guid 25549) deaths in Dragonsong's Reprise
  Thordan: a clean spread versus an overlap, and whose fault it was. Use when
  the killing blow is Lightning Storm or 25549.
---

# Lightning Storm

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `lightning-storm` in `fights/dsr/mechanics.json`. Guid `25549`. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

This is a spread. A clean spread is about 40k. Role caps are tank 40,000, healer 55,000, DPS 60,000.

## How to tell

- At or under the role cap: the player was spread. A death is raw, or low if they were already under 15,000 HP. None of the reference deaths were inside the cap.
- The overlaps in the reference log are 430–470k, and anything over the role cap is an overlap.

## Fault

Fail: `{player}` overlapped Lightning Storm. They stood in someone else's spread.

Raw: the spread was clean and the resolve lost. Name the shield, the mit, and the HP.

## Parameters

Follow `analyze-mechanic-parameters`. The long-pull timeline places this next, about 43 seconds after the phase start, after the opener Ascalon's Might. The cast survey is not done, and the plan is not confirmed.

Survey every cast. Record people hit per burst, unmitigated on clean spreads (currently about 40k: tank cap 40,000, healer 55,000, DPS 60,000), and the overlap band (the reference deaths are 430–470k). A correct spread is one player per hit. An overlap is the mistake of each player who took the oversized hit. Who must stand where is not confirmed.
