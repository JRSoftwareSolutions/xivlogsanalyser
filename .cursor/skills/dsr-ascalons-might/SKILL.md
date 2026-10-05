---
name: dsr-ascalons-might
description: >-
  Parameters and faults for Ascalon's Might (guid 25541) in Dragonsong's
  Reprise Thordan. One tank, three hits. A non-tank hit or a tank death
  without personal mitigation is their mistake. Use when refining or judging
  Ascalon's Might or 25541.
---

# Ascalon's Might

Follow `analyze-mechanic-parameters` when changing these parameters. Follow `review-mechanic` when judging a death. Entry `ascalons-might` in `fights/dsr/mechanics.json`. Guid `25541`. The cast about 16s is the opener (`dsr-thordan-opener`). The cast about 85s is the Heavenly Heel swap (`dsr-heavenly-heel`).

## Parameters

Two assignments of the same guid. Survey them separately.

**Opener, about 17 seconds.** Three physical hits on exactly one tank. In this log that tank is the warrior, Absolute Gigalad, on every opener. Lived hits are about 71–84k unmitigated, median about 80k. Nothing on the opener went over 85k, and nobody died to it. Many of those openers show no mitigation and he still lives, because the hit is about 80k on a warrior health pool. Correct play is still an invuln or heavy personal mitigation. A death without that is his.

**Second cast, about 85 seconds, after Heavenly Heel.** Three hits on the other tank. The person said these hits are properly mitigated and the tank swap is necessary. The tank who took Heavenly Heel does not take this. In this log the warrior's take uses Vengeance, Bloodwhetting, and Stem the Flow. Lived hits on that take are about 59–86k, median about 79k. Pull 11's first cleave was 95,527 before Vengeance, with only Exaltation and a shield, and he lived the three. Pull 60 is the swap the other way: after Absolute Gigalad died on the heel, Absolute Gigachad took the three hits with Rampart and Holy Sheltron.

Correct for either cast:

- Exactly one person is hit.
- That person is a tank.
- The three hits are properly mitigated. On the opener that is an invuln or heavy personal mitigation. On the swap it is personal mitigation on the tank who did not take Heavenly Heel.
- A tank who dies on the normal-sized hit without that personal mitigation owns the mistake. It is not raw.

Pull 14 is the fail shape for the second cast: the paladin had already taken Heavenly Heel and stayed in the three hits. Absolute Gigachad took about 153k and died. That hit is the cleave, above the lived band. The warrior still took the three hits with Vengeance, Bloodwhetting, and Stem the Flow.

## How to tell

- One tank, unmitigated in the lived band, and the required personal mit or invuln is present: the buster was taken correctly. A death is then low only if they were already under 15,000 HP before a normal hit. Do not call a missing-personal-mit death raw.
- A second body, the tank who already took Heavenly Heel, or anyone who is not a tank: fail.
- Unmitigated far above the lived band (the 153k cleave): fail.

## Fault

Non-tank: `{player}` got Ascalon's Might. Only a tank takes this.

Second body: only one tank takes Ascalon's Might. `{player}` ate the extra hit. On the swap, that includes the tank who already took Heavenly Heel. Pull 14 is Absolute Gigachad at about 153k, in it with the warrior.

Tank death on a normal-sized hit without invuln or heavy personal mit: `{player}` died to the real Ascalon's Might. Personal mitigation was not enough. That includes the warrior on the opener.

Low: the hit was the normal buster and they were already under 15,000 HP.
