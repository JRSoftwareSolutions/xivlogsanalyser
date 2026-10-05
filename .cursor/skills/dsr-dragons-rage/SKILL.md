---
name: dsr-dragons-rage
description: >-
  Identify Dragon's Rage (guid 25551) deaths in Dragonsong's Reprise Thordan:
  a real stack share, a short stack, or a failed hit, and whose fault it was.
  Use when the killing blow is Dragon's Rage or 25551.
---

# Dragon's Rage

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `dragons-rage` in `fights/dsr/mechanics.json`. Guid `25551`. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

This is a stack and it scales. The usual share is 5. A lived share is about 60–80k. `fail_above` is 200,000.

## How to tell

- At or under the role cap, including a share of 5: the real stack.
- A share of 3 around 102–113k, still at or under the role cap and at or under 200,000: the 5-share with two bodies missing. It stays raw.
- Over 200,000, or over the role cap: the failed hit, not a short share.

## Fault

Raw, full share: the resolve. Name the shield, the mit, and the HP.

Raw, short share: the missing bodies. Say the share was `{stack} of 5`.

Fail: `{player}` took the failed Dragon's Rage hit. Missing bodies do not explain a hit over 200,000.

## Parameters

Follow `analyze-mechanic-parameters`. One cast, about 59–60 seconds, under Thordan, with the tethers and the blue markers.

The person assigned the stack to the three non-tanks who do not have the blue marker. They stand under Thordan. The tanks are stretching tethers at the same time.

45 casts. Lived shares are usually 5 bodies: those three non-tanks plus both tanks, about 60–80k on a non-tank and about 26k on a tank. A share of 3 lands around 102–113k. Body counts in this log: 5 on 19 casts, 4 on 14, 3 on 9, and 1 or 2 on the failed cleaves.

The current reading stays until the person says whether the tanks belong in the stack. A share of 5 is the lived share. A share of 3 under the role cap and under 200,000 is two bodies missing and stays raw. The five raw deaths are that short share. Anything over 200,000, or Magic Vulnerability Up, is the failed cleave. Do not change `typical_targets` on a guess. The five raw deaths would still be raw either way. The fault sentence would change.
