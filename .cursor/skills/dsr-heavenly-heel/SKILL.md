---
name: dsr-heavenly-heel
description: >-
  Parameters and faults for Heavenly Heel (guid 25543) in Dragonsong's
  Reprise Thordan. Tank swap with the second Ascalon's Might. A non-tank hit
  or a tank death without personal mitigation is their mistake. Use when
  refining or judging Heavenly Heel or 25543.
---

# Heavenly Heel

Follow `analyze-mechanic-parameters` when changing these parameters. Follow `review-mechanic` when judging a death. Follow `mechanic-components` for what else is in this swap. Entry `heavenly-heel` in `fights/dsr/mechanics.json`. Guid `25543`.

## Components

The swap is about 81–88 seconds after phase 2 starts. The session stop is Heavenly Heel (`heavenly-heel-swap`). Two components. The person already stated the assignment.

| Component | Guid | What it does |
|---|---|---|
| Heavenly Heel | 25543, about 81s | One tankbuster. It applies Slashing Resistance Down, so the same tank cannot take the next cleaves. |
| Ascalon's Might | 25541, the cast about 85s | Three cleaves on the other tank. The opener Might, about 16s, is `dsr-thordan-opener`, not this swap. |

Anyone who is not a tank getting either hit owns that mistake. A tank who dies on the real hit without personal mitigation owns that death.

## Parameters

Heavenly Heel is the later tankbuster in the swap, around the same part of the phase as the second Ascalon's Might (about 85 seconds). It is not the opener. The opener three-hit is `dsr-ascalons-might`.

Correct cast:

- Exactly one tank is hit.
- The other tank takes the three-hit Ascalon's Might. They do not both take the heel, and they do not both take the three-hit.
- Tanks who live the heel take about 159–174k unmitigated, median about 168k. The tank cap in `mechanics.json` is 190,000. In this log the paladin lives it with Rampart, Holy Sheltron, and Knight's Resolve. The multiplier on those hits is about 0.47–0.68.
- The tank uses personal mitigation. A tank who dies on that normal-sized hit without personal mitigation owns the mistake. It is not raw. Pull 60 is Absolute Gigalad: 165,404 unmitigated, 10% mit, a 15k shield, and only Desperate Measures. That 10% is not personal mitigation.
- Anyone who is not a tank being hit is a mistake by that player. The cleave on a non-tank in this log is about 250k.

## How to tell

- One tank, unmitigated at or under the tank cap, with personal mitigation: the heel was taken correctly.
- One tank, normal-sized hit, dead, and no personal mitigation: fail. Theirs.
- A non-tank, including a hit around 250k: fail. Theirs.
- A second tank also in the heel: fail. The swap gives this hit to one tank only.

## Fault

`{player}` is a non-tank: they got Heavenly Heel. Only a tank takes this.

`{player}` is the tank and the unmitigated hit is the real one, but personal mitigation is missing: they died to the real Heavenly Heel. Personal mitigation was not enough.

A second tank in the heel: only one tank takes Heavenly Heel. `{player}` ate the extra hit.

Low: the hit was the normal tankbuster and they were already under 15,000 HP.
