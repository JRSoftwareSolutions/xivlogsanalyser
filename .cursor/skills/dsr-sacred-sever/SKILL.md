---
name: dsr-sacred-sever
description: >-
  Identify Sacred Sever (guid 25571) deaths in Dragonsong's Reprise Thordan:
  a real stack share, a short stack, or a cleave, and whose fault it was. Use
  when the killing blow is Sacred Sever or 25571.
---

# Sacred Sever

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `sacred-sever` in `fights/dsr/mechanics.json`. Guid `25571`. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). Ser Zephirin jumps the sword markers; four players share each jump, and a longer jump hits for less.

This is a stack and it scales. The usual share is 4. A full share people live is about 35–63k, DPS median about 43k.

## How to tell

- At or under the role cap on a share of 4: the real stack.
- A share of 1 or 2 around 85–104k, still at or under the role cap: the same mechanic with missing bodies. It stays raw.
- Cleaves in the millions, or any hit over the role cap: the failed cleave, not a short share.

## Fault

Raw, full share: the resolve. Name the shield, the mit, and the HP.

Raw, short share: the missing bodies. Say the share was `{stack} of 4`. The player who died took a legal share.

Fail: `{player}` took the cleave. They were not in the stack.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast, not only deaths. Record bodies per cast, unmitigated by stack size on hits people lived, and the cleave amounts. The current parameters: usual share 4, a share of 1 or 2 under the role cap is still this mechanic, cleaves in the millions are the fail shape. Who is assigned to the stack is not confirmed. Missing bodies own a short share. The player who took the cleave owns that hit.
