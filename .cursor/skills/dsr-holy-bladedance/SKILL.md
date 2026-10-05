---
name: dsr-holy-bladedance
description: >-
  Identify Holy Bladedance (guid 25299) deaths in Dragonsong's Reprise
  Thordan: the small tank hit versus the failed hits around 230k–370k, and
  whose fault it was. Use when the killing blow is Holy Bladedance or 25299.
---

# Holy Bladedance

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `holy-bladedance` in `fights/dsr/mechanics.json`. Guid `25299`. Part of Strength of the Ward (`dsr-strength-of-the-ward`), the cone after Holy Shield Bash.

The tank hit people live is about 12–22k. The tank cap is 55,000.

## How to tell

- Tank at or under the cap: the real buster. If they were already under 15,000 HP, the outcome is low, not raw.
- Hits around 230k and 370k, or anything over the role cap: the failed version.

## Fault

Low or raw inside the cap: the buster was normal. Low means they were already under 15,000. Raw means the resolve (shield, mit, HP) lost to the normal hit.

Fail: `{player}` took the failed Holy Bladedance, not the 12–22k tank hit.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast. Record who is hit, hits per cast, and the unmitigated band of hits tanks lived (currently about 12–22k, cap 55,000) versus the failed hits around 230k and 370k. Whether a tank death on the small hit without personal mitigation is their mistake is not confirmed. Until it is, a normal hit on someone already under 15,000 HP is low.
