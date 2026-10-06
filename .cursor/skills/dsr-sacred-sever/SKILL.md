---
name: dsr-sacred-sever
description: >-
  Identify Sacred Sever (guid 25571) deaths in Dragonsong's Reprise Thordan:
  a real stack share, a short stack, or a cleave, and whose fault it was. Use
  when the killing blow is Sacred Sever or 25571.
---

# Sacred Sever

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `sacred-sever` in `fights/dsr/mechanics.json`. Guid `25571`. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). The dark knight jumps the single sword, then the double sword, then those two jumps again. Four players share each jump.

This is a stack and it scales. The usual share is 4. A lived share of 4 is tanks about 24–48k, healers about 43–67k, and DPS about 40–64k. DPS median is about 43k. Who runs which way is in `dsr-sanctity-of-the-ward`.

## How to tell

- At or under the role cap on a share of 4: the real stack.
- A share of 1 or 2 around 85–104k, still at or under the role cap: the same mechanic with missing bodies. It stays raw.
- Cleaves in the millions, or any hit over the role cap: the failed cleave, not a short share.

## Fault

Raw, full share: the resolve. Name the shield, the mit, and the HP.

Raw, short share: the missing bodies. Say the share was `{stack} of 4`. The player who died took a legal share.

Fail: `{player}` took the cleave. They were not in the stack.

## Parameters

Follow `analyze-mechanic-parameters`. Walked on `8DYNHQx4C7ytdLb9`. Each jump is four players, about 1.8 seconds apart, from about 113 to 119 seconds. The same four take the first and third jumps. The other four take the second and fourth. Early jumps are often fully shielded, so unmitigated is missing on that damage packet and the later jumps carry the band above. A share of 1 or 2 under the role cap is still this mechanic. Cleaves, such as the 181k hit on pull 36, are the fail shape. The marked player who runs the wrong way owns that mistake. When they run correctly and the role partner does not swap, the partner owns it. Missing bodies own a short share. The player who took the cleave owns that hit.
