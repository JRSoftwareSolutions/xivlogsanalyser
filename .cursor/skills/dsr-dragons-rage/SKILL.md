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

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast. Record bodies per cast and unmitigated by stack size on hits people lived. The current parameters: usual share 5, a share of 3 around 102–113k under the role cap and under 200,000 is two missing bodies, anything over 200,000 is the fail shape. Who is assigned to the stack is not confirmed.
