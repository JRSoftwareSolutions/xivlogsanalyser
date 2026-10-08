---
name: dsr-heavenly-heel
description: >-
  Parameters and faults for Heavenly Heel (guid 25543) in Dragonsong's
  Reprise Thordan. The off tank always takes it. A non-tank hit, the main
  tank taking it while the off tank lives, or an off-tank death without
  personal mitigation is their mistake. Use when refining or judging Heavenly Heel or 25543.
---

# Heavenly Heel

Follow `analyze-mechanic-parameters` when changing these parameters. Follow `review-mechanic` when judging a death. Follow `mechanic-components` for what else is in this swap. Entry `heavenly-heel` in `fights/dsr/mechanics.json`. Guid `25543`. `off_tank` is true. The off tank is `assignments.off_tank` in `<report>/session.json`, or else the tank Heavenly Heel landed on in the most pulls. That is Absolute Gigachad in all three logs.

## Components

The swap is about 81–88 seconds after phase 2 starts. The session stop is Heavenly Heel (`heavenly-heel-swap`). Two components, in this order. The person stated the plan: the off tank always takes Heavenly Heel, then the main tank takes the three Ascalon's Might hits, both properly mitigated. Sanctity of the Ward is the next mechanic.

| Component | Guid | What it does |
|---|---|---|
| Heavenly Heel | 25543, about 81s | One tankbuster on the off tank, with personal mitigation. It applies Slashing Resistance Down, so that tank cannot take the cleaves that follow. The death line for a heel is only this hit. The three Ascalon's Might hits have their own line. |
| Ascalon's Might | 25541, the cast about 85s | Three cleaves on the main tank, also with personal mitigation. The opener Might, about 16s, is `dsr-thordan-opener`, not this swap. |

Anyone who is not a tank getting either hit owns that mistake. The main tank taking the heel owns that mistake, unless the off tank was dead. Then the dead off tank owns it, passed on to whoever owned that death. The off tank does not take the three hits. The off tank who dies on the real heel without personal mitigation owns that death.

## Parameters

Heavenly Heel is the first hit of the swap. The three Ascalon's Might hits follow it, about three seconds later. It is not the opener. The opener three-hit is `dsr-ascalons-might`. Sanctity of the Ward starts about 112 seconds, after this swap.

The off tank always takes Heavenly Heel. In this log the off tank is the paladin, Absolute Gigachad. He takes it on the lived pulls, with Rampart, Holy Sheltron, and Knight's Resolve. The main tank is the warrior, Absolute Gigalad. He takes the opener on every pull, and the three hits after the heel. No name is stored on the mechanic. Absolute Gigachad is the off tank because the heel landed on him in the most pulls.

Correct cast:

- The off tank takes Heavenly Heel, properly mitigated.
- The main tank takes the three hits that follow, properly mitigated.
- They do not both take the heel. The off tank does not stay for the three hits. The main tank does not take the heel.
- Tanks who live the heel take about 159–174k unmitigated, median about 168k. The tank cap in `mechanics.json` is 190,000. Pull 11 lived it with Rampart and Holy Sheltron only. The multiplier on those hits is about 0.47–0.68.
- The three hits are the main tank's. In this log the warrior's take uses Vengeance, Bloodwhetting, and Stem the Flow. Those lived hits are about 59–86k, median about 79k. Pull 11's first cleave was 95,527 before Vengeance, with only Exaltation and a shield, and he still lived the three.
- The off tank who dies on the real heel without personal mitigation owns the mistake. It is not raw.
- The main tank taking the heel is a mistake, mitigated or not. Pull 60 is Absolute Gigalad at 165,404 unmitigated, 10% mit, a 15k shield, and only Desperate Measures. The off tank takes this. That 10% is also not personal mitigation. Absolute Gigachad then took the three hits with Rampart and Holy Sheltron and lived.
- Anyone who is not a tank being hit is a mistake by that player. Pull 18 is Kiara Blaiddyd, about 250k.
- Pull 14 is the off tank staying in the cleaves. Absolute Gigachad took the heel, then also took one of the three hits at 152,770 and died. Absolute Gigalad still took the three hits with Vengeance, Bloodwhetting, and Stem the Flow.

## How to tell

- The off tank, unmitigated at or under the tank cap, with personal mitigation, and the main tank on the three hits: the heel was taken correctly.
- The main tank on the heel: fail. The off tank takes Heavenly Heel. Pull 60 is Absolute Gigalad. Missing personal mitigation is part of that same death when it is also missing.
- The main tank on the heel while the off tank was dead: fail, owned by the dead off tank, passed on. `3wzL6x4VHTmvNkhq` pull 20 is Absolute Gigalad taking it because Absolute Gigachad was dead.
- The off tank, normal-sized heel, dead, and no personal mitigation: fail. Theirs.
- A non-tank, including a hit around 250k: fail. Theirs.
- A second tank also in the heel: fail. The off tank takes Heavenly Heel.
- The off tank also in the three hits: fail. Those hits belong to the main tank. That death is on Ascalon's Might.

## Fault

`{player}` is a non-tank: they got Heavenly Heel. Only a tank takes this.

`{player}` is the main tank: the off tank takes Heavenly Heel. `{player}` took it. When personal mitigation is also missing, say that too.

`{player}` is the main tank and the off tank was dead: `{off tank}` was dead, so `{player}` had to take Heavenly Heel. The off tank owns it.

`{player}` is the off tank and the unmitigated hit is the real one, but personal mitigation is missing: they died to the real Heavenly Heel. Personal mitigation was not enough.

A second tank in the heel: the off tank takes Heavenly Heel. `{player}` ate the extra hit.

The off tank who already took the heel is in the three hits: the main tank takes those. `{player}` ate the extra Ascalon's Might.

Low: the hit was the normal tankbuster and the off tank was already under 15,000 HP.

Personal mitigation is the tank's own cooldowns: what the replay shows they put on themselves (by and on are the same player). A co-tank's or a healer's single-target cooldown on them (Intervention, The Blackest Night, Heart of Corundum, Exaltation, Aquaveil) is not personal; it counts only through the hit's multiplier, where 0.75 or less is mitigated. The names in `personal_mit` in `fights/dsr/fight.json` are used only when a pull has no replay. In all three logs no tank death to Ascalon's Might or Heavenly Heel had a co-tank cooldown on it.
