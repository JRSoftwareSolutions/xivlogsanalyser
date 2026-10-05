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

The swap is about 81–88 seconds after phase 2 starts. The session stop is Heavenly Heel (`heavenly-heel-swap`). Two components, in this order. The person stated the plan: Heavenly Heel, then the three Ascalon's Might hits, both properly mitigated, and a tank swap is necessary. Sanctity of the Ward is the next mechanic.

| Component | Guid | What it does |
|---|---|---|
| Heavenly Heel | 25543, about 81s | One tankbuster on one tank, with personal mitigation. It applies Slashing Resistance Down, so that tank cannot take the cleaves that follow. |
| Ascalon's Might | 25541, the cast about 85s | Three cleaves on the other tank, also with personal mitigation. The opener Might, about 16s, is `dsr-thordan-opener`, not this swap. |

Anyone who is not a tank getting either hit owns that mistake. The tank who took the heel does not take the three hits. A tank who dies on the real hit without personal mitigation owns that death.

## Parameters

Heavenly Heel is the first hit of the swap. The three Ascalon's Might hits follow it, about three seconds later. It is not the opener. The opener three-hit is `dsr-ascalons-might`. Sanctity of the Ward starts about 112 seconds, after this swap.

Correct cast:

- One tank takes Heavenly Heel, properly mitigated.
- The other tank takes the three hits that follow, properly mitigated.
- They do not both take the heel. The tank who took the heel does not stay for the three hits.
- Tanks who live the heel take about 159–174k unmitigated, median about 168k. The tank cap in `mechanics.json` is 190,000. In this log the paladin takes it, with Rampart, Holy Sheltron, and Knight's Resolve. Pull 11 lived it with Rampart and Holy Sheltron only. The multiplier on those hits is about 0.47–0.68.
- The three hits are the other tank's. In this log the warrior takes them with Vengeance, Bloodwhetting, and Stem the Flow. Those lived hits are about 59–86k, median about 79k. Pull 11's first cleave was 95,527 before Vengeance, with only Exaltation and a shield, and he still lived the three.
- A tank who dies on the real heel without personal mitigation owns the mistake. It is not raw. Pull 60 is the swap the other way: Absolute Gigalad took the heel at 165,404 unmitigated, 10% mit, a 15k shield, and only Desperate Measures. That 10% is not personal mitigation. Absolute Gigachad then took the three hits with Rampart and Holy Sheltron and lived.
- Anyone who is not a tank being hit is a mistake by that player. Pull 18 is Kiara Blaiddyd, about 250k.
- Pull 14 is the missed swap. Absolute Gigachad took the heel, then also took one of the three hits at 152,770 and died. Absolute Gigalad still took the three hits with Vengeance, Bloodwhetting, and Stem the Flow.

## How to tell

- One tank, unmitigated at or under the tank cap, with personal mitigation, and the other tank on the three hits: the swap was taken correctly.
- One tank, normal-sized heel, dead, and no personal mitigation: fail. Theirs.
- A non-tank, including a hit around 250k: fail. Theirs.
- A second tank also in the heel: fail. One tank takes Heavenly Heel.
- The tank who took the heel also in the three hits: fail. The swap gives those hits to the other tank. That death is on Ascalon's Might.

## Fault

`{player}` is a non-tank: they got Heavenly Heel. Only a tank takes this.

`{player}` is the tank and the unmitigated hit is the real one, but personal mitigation is missing: they died to the real Heavenly Heel. Personal mitigation was not enough.

A second tank in the heel: only one tank takes Heavenly Heel. `{player}` ate the extra hit.

The tank who already took the heel is in the three hits: the tanks had to swap. `{player}` ate the extra Ascalon's Might.

Low: the hit was the normal tankbuster and they were already under 15,000 HP.
