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

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast, not only deaths. Record bodies and unmitigated on soaks people lived (the current lived band is 59–70k, usually 5–10% mit and a 13–39k shield) versus explosions over 150,000 (about 600–760k). Who is assigned to each tower is not confirmed. A real soak that kills is the resolve. An explosion means the tower was missed.
