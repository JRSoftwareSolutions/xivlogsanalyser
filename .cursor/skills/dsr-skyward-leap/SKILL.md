---
name: dsr-skyward-leap
description: >-
  Identify Skyward Leap (guid 25565) deaths in Dragonsong's Reprise Thordan:
  the blue marker versus an empty-tower explosion, and whose fault it was.
  Use when the killing blow is Skyward Leap or 25565.
---

# Skyward Leap

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Entry `skyward-leap` in `fights/dsr/mechanics.json`. Guid `25565`. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

The blue marker is Skyward Leap. Three non-tanks have it. The one directly opposite Thordan stands as far away as possible. East and west are slightly offset toward the north, not too far. A real leap is 59–70k unmitigated, usually with 5–10% mit and a 13–39k shield. `fail_above` is 150,000.

A death on that leap is a mistake. It is not raw.

The six towers are a later soak. A soaked tower does not deal this much. An empty tower explodes for about 600–760k on this same guid and applies Damage Down and Paralysis to everyone.

## How to tell

Apply these to a Skyward Leap death in this order:

- Over 150,000, including 600–760k: a tower exploded. Pull 68, Kiara Blaiddyd, is that case.
- Above the role cap and at or under 150,000: clipped by another leap. This log has no hit in that gap.
- Already under 15,000 HP on a 59–70k hit: low. The leap was the normal one.
- HP below their max: not fully healed. The healers own it. Pull 13 Kiara Blaiddyd was at 36,457 of 68,662. Pull 18 Kiara was at 51,175. Pull 25 Speed Panda was at 48,117 of 68,259.
- At full HP: mitigation was not enough. The players who were supposed to mitigate this leap own it. Name the mit the packet is missing. Do not invent the cooldown plan. Pull 68 Kitana Kahn was at 61,737 of 61,737, multiplier 1.00, no shield.

## Fault

Not fully healed: the healers. `{player}` was short of full HP. That is a healer mistake even when the hit also had light mitigation.

Missing mitigation: `{player}` was fully healed and the leap still killed. Whoever was supposed to mitigate it, and did not, owns the death.

Clip: `{player}` was clipped by another Skyward Leap. The player who was out of the spot owns it. Opposite Thordan is as far away as possible. East and west are slightly toward the north, not too far. This log has no positions, so a death names the overlap and does not pick which of the three was east, west, or opposite.

Empty tower: `{player}` died to the explosion. The explosion applies Damage Down and Paralysis to everyone. The mistake is the missed soak.

## Parameters

One cast, about 59–60 seconds, with the stack and the tethers. 50 casts. 41 of them are three bodies, the non-tanks outside the Dragon's Rage stack. Those hits, when people live them, are 59–70k. That is the marker.

Clean casts do not store six tower soaks. A soaked tower is not this band. The explosions in this log are the same guid: pull 68 Kiara Blaiddyd at 713,570, and the other deaths from 655k to 762k. No Damage Down or Paralysis aura is on those packets. The person stated that effect. The damage is what the log shows.
