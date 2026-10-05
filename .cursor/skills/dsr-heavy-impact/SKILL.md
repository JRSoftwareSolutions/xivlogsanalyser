---
name: dsr-heavy-impact
description: >-
  Identify Heavy Impact deaths in Dragonsong's Reprise Thordan. Guids 25560
  and 25559 are the same ring, and any hit is a fail. Use when the killing
  blow is Heavy Impact, 25560, or 25559.
---

# Heavy Impact

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `heavy-impact` in `fights/dsr/mechanics.json`. Guids `25560` and `25559`. `any_hit_is_fail` is true. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

These are rings. Both guids are this mechanic. A clean pull takes 0. A hit is about 51–57k.

## How to tell

Any damage from either guid is a fail. A 51–57k ring is not raw raid damage and not a second ability.

## Fault

`{player}` stood in the Heavy Impact ring.

Pull 68: Kite Noodle dies to Heavy Impact. That death is a fail.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey both guids together, `25560` and `25559`. Record time in the phase and unmitigated on hits (currently about 51–57k) versus pulls that took 0. The current parameter is that both ids are this ring and `any_hit_is_fail`. Confirm no lived band exists before keeping that. The player who is hit owns the mistake.
