---
name: dsr-skyward-leap
description: >-
  Identify Skyward Leap (guid 25565) deaths in Dragonsong's Reprise Thordan:
  the blue marker versus an empty-tower explosion, and whose fault it was.
  Use when the killing blow is Skyward Leap or 25565.
---

# Skyward Leap

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Entry `skyward-leap` in `fights/dsr/mechanics.json`. Guid `25565`. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

The blue marker is Skyward Leap. Three non-tanks have it. They stand opposite Thordan and to the left and right, away from him. A real leap is 59–70k unmitigated, usually with 5–10% mit and a 13–39k shield. `fail_above` is 150,000.

The six towers are a later soak. A soaked tower does not deal this much. An empty tower explodes for about 600–760k on this same guid and applies Damage Down and Paralysis to everyone.

## How to tell

- Healer or DPS at or under the role cap: the blue marker. A death on that hit is raw, or low if they were already under 15,000 HP. Pull 68, Kitana Kahn, is the settled raw Skyward Leap. It is the only raw death on that pull.
- Over 150,000, including 600–760k: a tower exploded. That is a fail. It is not a marker with bad mit.

## Fault

Raw: the resolve. Name the shield, the mit, and the HP. The blue marker was the real Skyward Leap.

Fail: a tower was empty. `{player}` died to the explosion. The explosion applies Damage Down and Paralysis to everyone. The mistake is the missed soak. Pull 68, Kiara Blaiddyd, is that case, separate from Kitana's marker.

## Parameters

One cast, about 59–60 seconds, with the stack and the tethers. 50 casts. 41 of them are three bodies, the non-tanks outside the Dragon's Rage stack. Those hits, when people live them, are 59–70k. That is the marker.

Clean casts do not store six tower soaks. A soaked tower is not this band. The explosions in this log are the same guid: pull 68 Kiara Blaiddyd at 713,570, and the other deaths from 655k to 762k. No Damage Down or Paralysis aura is on those packets. The person stated that effect. The damage is what the log shows.
