---
name: dsr-holy-bladedance
description: >-
  Identify Holy Bladedance (guid 25299) deaths in Dragonsong's Reprise
  Thordan: the small tank hit versus the failed hits around 230k–370k, and
  whose fault it was. Use when the killing blow is Holy Bladedance or 25299.
---

# Holy Bladedance

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Entry `holy-bladedance` in `fights/dsr/mechanics.json`. Guid `25299`. `tanks_only` is true. `requires_personal_mit` is true. Part of Strength of the Ward (`dsr-strength-of-the-ward`), the cone after Holy Shield Bash.

## Parameters

About 62–64 seconds, after the tethers. Two cones, one after each bash. On a clean cast both tanks are hit, several times each. Lived tank hits are about 20–22k unmitigated, median about 21k. The tank cap is 55,000.

The tank who stretched that tether uses personal mitigation. A tank who dies on a normal-sized hit without it owns the death. It is not raw. The reference deaths on the small hit were already under 15,000 HP and had personal mitigation, so they stay low.

Anyone who is not a tank in the cone owns that hit. Pull 25, Kiara Blaiddyd, 372,472, with Physical Vulnerability Up.

## How to tell

- Tank, unmitigated at or under 55,000, with personal mitigation: the real cone. Under 15,000 HP is low.
- Tank, normal-sized hit, dead, no personal mitigation: fail. Theirs.
- Anyone who is not a tank, including a hit around 230k or 370k: fail. They stood in the cone.

## Fault

`{player}` is not a tank: they stood in Holy Bladedance. Only the tethered tank takes that cone.

`{player}` is the tank and the hit is the real one, but personal mitigation is missing: they died to the real Holy Bladedance. Personal mitigation was not enough.

Low: the hit was the normal cone and they were already under 15,000 HP.
