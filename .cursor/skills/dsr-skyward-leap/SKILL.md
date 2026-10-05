---
name: dsr-skyward-leap
description: >-
  Identify Skyward Leap (guid 25565) deaths in Dragonsong's Reprise Thordan:
  a real tower soak versus an empty tower, and whose fault it was. Use when
  the killing blow is Skyward Leap or 25565.
---

# Skyward Leap

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `skyward-leap` in `fights/dsr/mechanics.json`. Guid `25565`. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

This is a tower. A real soak is 59–70k unmitigated, usually with 5–10% mit and a 13–39k shield. `fail_above` is 150,000. An empty tower is about 600–760k.

## How to tell

- Healer or DPS at or under the role cap: a real soak. A death on that hit is raw, or low if they were already under 15,000 HP. Pull 68, Kitana Kahn, is the settled raw Skyward Leap. It is the only raw death on that pull.
- Over 150,000, including 600–760k: the tower exploded. That is a fail, not a soak with bad mit.

## Fault

Raw: the resolve. Name the shield, the mit, and the HP. The tower was soaked.

Fail: the tower was empty. `{player}` died to the explosion. The mistake is the missed soak. Pull 68, Kiara Blaiddyd, is that case, separate from Kitana's real soak.

## Parameters

Follow `analyze-mechanic-parameters`. One cast, about 59–60 seconds, with the stack and the tethers.

The person assigned the blue markers to three non-tanks. They stand opposite Thordan and to the left and right, away from him. The other three non-tanks are under him for Dragon's Rage. On a clean cast this guid hits three non-tanks, and those three are the ones outside the stack. Lived soaks are 59–70k unmitigated, usually with 5–10% mit and a 13–39k shield. 50 casts. 41 of them are three bodies.

After that wave, six towers spawn. Three near the spread, three near the stack. Each of the six non-tanks has to be inside one. An empty tower is a mistake. The player who dies to the explosion owns the missed soak. Pull 68, Kiara Blaiddyd, is that case. Kitana Kahn on the same pull is the 65k soak and stays raw.

Clean casts store three Skyward Leap hits, not six. The 59–70k band stays the real soak, and anything over 150,000 stays the empty tower, until the person says whether the 60k is the blue-marker hit or three of the six towers. Do not retune the caps or the 4 raw deaths on that guess.
