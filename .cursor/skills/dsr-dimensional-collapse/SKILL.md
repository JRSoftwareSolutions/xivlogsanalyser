---
name: dsr-dimensional-collapse
description: >-
  Identify Dimensional Collapse (guid 25564) deaths in Dragonsong's Reprise
  Thordan. A hit applies Heavy and Damage Down, so any hit stays a fail.
  Use when the killing blow is Dimensional Collapse or 25564.
---

# Dimensional Collapse

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Entry `dimensional-collapse` in `fights/dsr/mechanics.json`. Guid `25564`. `any_hit_is_fail` is true. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

## Parameters

The puddles on the floor during the second wave, with the tethers, the blue markers, and the stack. The person described them there. A hit applies Heavy and Damage Down. That is a mistake.

No lived sample is stored. The reference log has one death, pull 29, Speed Panda, about 59 seconds, with no unmitigated amount. It stays out of the 86 raw deaths. Do not add a raw band from that death.

## Replay

In the replay the puddles are eight spots about 59 seconds in, at 9 and 18 yalms from center. Ser Grinnaux places them, and some pulls store them with no actor. The arena still draws them as shaded circles. They are not the towers. The Strength towers are Ser Hermenost's six spots in a ring at 12 yalms, from about 62.7 seconds.

## How to tell

Any hit is a fail. A hit near 50k is still a fail. Survivable-looking damage is not a raw call without a lived sample.

## Fault

`{player}` stood in Dimensional Collapse. The hit applies Heavy and Damage Down.
