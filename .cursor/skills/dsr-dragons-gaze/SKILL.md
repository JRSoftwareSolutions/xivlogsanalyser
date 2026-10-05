---
name: dsr-dragons-gaze
description: >-
  Identify Dragon's Gaze (guid 25553) deaths in Dragonsong's Reprise Thordan.
  A successful gaze deals 0; any hit means they looked. Use when the killing
  blow is Dragon's Gaze or 25553. Dragon's Glory 25554 is a different cast.
---

# Dragon's Gaze

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `dragons-gaze` in `fights/dsr/mechanics.json`. Guid `25553`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). It resolves together with Dragon's Glory and inflicts Hysteria.

A successful gaze deals 0. Looking deals about 44–45k.

## Parameters

Follow `analyze-mechanic-parameters`. One cast, about 112 seconds after phase 2 starts. 30 of 55 qualifying pulls reach it. The other 25 end by 86 seconds, before Sanctity. There is no later cast. Survey this guid on its own. Dragon's Glory `25554` resolves at the same timestamp and is a different cast (`dsr-dragons-glory`).

The cast checks all eight players. A correct resolve stores amount 0 and no unmitigated amount. 28 of the 30 casts are that shape.

Looking is one player, about 43,749–45,156 unmitigated, multiplier 1.00. That is the fail. It is not a share, and the eight check-packets are not a stack. No personal mitigation is required. The correct play is to look away.

Pull 50 is the lived fail: Kite Noodle, 43,749 unmitigated, amount 21,684, a 22,065 shield, multiplier 1.00. He lived it. The shield does not make the look correct.

Pull 11 is the death: Kite Noodle, 45,156 unmitigated, HP 19,763 of 68,218, no shield, multiplier 1.00, overkill 25,393. On that same timestamp Dragon's Glory hits Kitana Kahn and Speed Panda, not Kite. A player can look at one gaze and not the other.

No aura is stored on these packets. `any_hit_is_fail` stays. Do not add a raw cap from the 44k look.

## How to tell

Any damage from this guid is a fail. Name this cast Dragon's Gaze. Dragon's Glory is guid `25554` and is a different cast (`dsr-dragons-glory`).

- Amount 0: they looked away.
- Any unmitigated amount, including 43,749–45,156: they looked. Theirs, whether they lived it or died.

## Fault

`{player}` looked at Dragon's Gaze.
