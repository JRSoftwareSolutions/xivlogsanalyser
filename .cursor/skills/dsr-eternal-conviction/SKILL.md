---
name: dsr-eternal-conviction
description: >-
  Identify Eternal Conviction (guid 25568) deaths in Dragonsong's Reprise
  Thordan: real raidwide versus a failed hit, and whose fault it was. Use when
  the killing blow is Eternal Conviction or 25568.
---

# Eternal Conviction

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `eternal-conviction` in `fights/dsr/mechanics.json`. Guid `25568`. Hits around 63s are the Strength of the Ward stop. Hits around 130s are the Meteors stop, next to Conviction `29564`. Which tower each window is, the person confirms (`dsr-strength-of-the-ward`, `dsr-sanctity-of-the-ward`).

This is a raidwide. It does not scale with stack size. A full party of 8 still hits a DPS for about 97k of the same cast that hits a tank for about 64k.

## How to tell

- At or under the role cap: the real raidwide. Tanks who lived it sit around 61–67k. No healer or DPS lived it in the reference log. Healer and DPS deaths in the 90–108k band are that same cast, so they are raw when they fit the cap.
- Over the role cap: a failed hit. Missing bodies do not explain it.
- Vulnerability or Damage Down on the packet, or on the calculated-damage sibling when `buffs` is empty: fail, even inside the band. The death cluster is tight; a vuln amp would have broken it.

## Fault

Raw: the resolve. Name the shield, the mit, and the HP. The mechanic was the normal raidwide.

Fail over the cap: `{player}` took a hit that is not Eternal Conviction. Do not call it a short stack.

Low: the raidwide was normal and they were already under 15,000 HP.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Before changing the caps, survey every cast and record: time in the phase, bodies hit, unmitigated by role for hits people lived, and whether a full party of 8 still lands on the DPS band. The current parameter is that this raidwide does not scale with stack size. A larger hit is not missing bodies. The plan for who stands where is not confirmed beyond that.
