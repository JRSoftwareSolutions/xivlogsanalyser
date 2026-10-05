---
name: dsr-heavy-impact
description: >-
  Identify Heavy Impact deaths in Dragonsong's Reprise Thordan. Guids 25560
  and 25559 are the same ring, and any hit is a fail. Use when the killing
  blow is Heavy Impact, 25560, or 25559.
---

# Heavy Impact

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Entry `heavy-impact` in `fights/dsr/mechanics.json`. Guids `25560` and `25559`. `any_hit_is_fail` is true. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

## Parameters

The knight's pulses, after Lightning Storm and while Thordan casts Ascalon's Mercy Concealed from the middle. The person described an earthquake that pulses outward. These two guids are that cast. Deaths land about 45–47 seconds into phase 2. `25559` is the earlier pulse in this log (pull 42, 45.2 seconds). `25560` is the later one (about 46.8 seconds).

A correct pull takes 0. There is no lived band. A hit is about 51–57k where an amount is stored. It stuns and applies Damage Down. The player who is hit owns it.

This log has no ability file for either guid, so the survey is the deaths, not every cast. Clean pulls are the ones with no death on these ids.

## How to tell

Any damage from either guid is a fail. A 51–57k ring is not raw raid damage and not a second ability.

## Fault

`{player}` stood in the Heavy Impact pulse. It stuns and applies Damage Down.

Pull 68: Kite Noodle dies to Heavy Impact. That death is a fail.
