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
- A short share is the same cast split fewer ways: a non-tank takes about 43k in a 4, 57k in a 3, 81–91k in a 2, and 160–181k alone. The role cap scales with the stack (`cap_for_stack`: a share of 2 gets twice the cap of a 4), so those are missing bodies and stay raw.
- The damage falls the farther Ser Zephirin jumps, so each group waits across the arena from him. In all three logs a full group 34–35 yalms from him takes about 43k each before mitigation. On reference pull 35 the first group stood about 31 yalms away and took 82–99k; on pull 27 about 6 yalms and took about 400k. A hit over the role cap on a full stack with no vulnerability is the group standing too close: `{player} stood too close to Ser Zephirin's landing.` Each player in it owns their own death.
- Hits in the millions with Physical Vulnerability Up are a jump on the wrong group (`alternating`).
- Share or too close is decided once per cast. Every death in one packet gets the verdict of the middle victim's hit against their role cap. A vulnerability, a marker clip, or a hit over `fail_above` is still judged on its own. Reference pull 35: Kite Noodle's 81,519 was under the DPS cap, but the cast was too close, so all three failed it.

## Fault

Raw, full share: the resolve. Name the shield, the mit, and the HP.

Raw, short share: the missing bodies. Say the share was `{stack} of 4`. The player who died took a legal share. The jumps alternate (`alternating` in `mechanics.json`), so the group for a jump is whoever took the jump two before it, and for the first two jumps everyone the other group's jump missed. Its players who were dead own the gap, passed on to whoever owned those deaths, and its players alive and not in the stack own it themselves. When the group is all there, it stays "Missing bodies".

Fail with the last jump's Physical Vulnerability Up: each jump leaves that vuln on its stack. A player who is not in this jump's group took a jump that landed on the wrong group, because that group's players were already dead. The dead players own it, passed on. The right group's living players are not named: the knight follows the sword. `3wzL6x4VHTmvNkhq` pull 49: the four who looked at Dragon's Glory own the third jump that killed the other four. A player who is in the group and still had the vuln took both jumps, and owns it (`3wzL6x4VHTmvNkhq` pull 24, Kitana Kahn).

A raw share right after looking at a gaze, when full HP would have lived it, is the player's own (`review-mechanic`, own hit).

Fail: `{player}` took the cleave. They were not in the stack.

## Parameters

Follow `analyze-mechanic-parameters`. Walked on `8DYNHQx4C7ytdLb9`. Each jump is four players, about 1.8 seconds apart, from about 113 to 119 seconds. The same four take the first and third jumps. The other four take the second and fourth. Early jumps are often fully shielded, so unmitigated is missing on that damage packet and the later jumps carry the band above. A share of 1 or 2 is still this mechanic: the 181k on pull 36 is the normal cast taken alone, a short share. On pull 36 and on `3wzL6x4VHTmvNkhq` pull 28 the whole group drifted off its spot before the last jump, so the positions name nobody in particular, and the group's missing players own it. A hit bigger than the share for its stack is the group standing too close.
