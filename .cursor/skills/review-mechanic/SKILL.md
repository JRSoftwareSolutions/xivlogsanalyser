---
name: review-mechanic
description: >-
  Judge a Dragonsong's Reprise death: what happened, what the mechanic should
  have been, and whose fault it was. Use when analyzing a log, pull, death,
  killing blow, or mechanic, or when the user corrects a call (raw, fail, low,
  stack, tower, gaze, cone, ring, soak).
---

# Review a mechanic

Thordan (phase 2) is the fight these skills know. Caps and `should_have_been` live in `fights/dsr/mechanics.json`. How to tell the cases apart lives in the mechanic skill. `notes/classification.md` is why the settled calls look like this.

Read the mechanic skill for the killing blow before you assign fault. Setting or checking parameters uses `analyze-mechanic-parameters`, then that mechanic's Parameters section. Which casts belong together, and what each one does, is `mechanic-components`. The session line lists those clusters by `starts`. That file names the skill for the stop. The killing-blow index is below.

## Killing blow

The killing blow is the first ability in the deaths-table row before `last-three-events`. The last tooltip event is often reverse-chronological and is the wrong blow.

No ability on that row means there is no damage packet.

## Packet

Compare `unmitigatedAmount` to the role cap. `amount` is HP removed. `overkill` is the excess that killed. `absorbed` is the shield. Total hit is amount + overkill + absorbed. `multiplier` is the mit still on the hit: 1.00 is none, 0.90 is about 10%. HP at the killing blow is `amount` when `overkill` is set. Stack size is distinct targets in the same ~1.5s cluster.

Role comes from the job. Tanks: Paladin, Warrior, Gunbreaker, Dark Knight. Healers: Astrologian, Scholar, White Mage, Sage. Everyone else is DPS.

`low_hp` in `fights/dsr/fight.json` is 15,000.

## Outcome

Apply these in order:

1. No damage packet → **environment**. No mechanic fault. Usually the body after a raise, or a wipe tick. Weakness `1000043` is the raise debuff and does not increase damage taken.
2. Guid is not in `mechanics.json` for this phase → **unknown**. No fault. Ask what the hit should mean.
3. Magic Vulnerability Up `1002941`, Physical Vulnerability Up `1002940`, or Damage Down on the packet → **fail**. The amp is a failed mechanic. `buffs` is often empty on the damage packet even when a calculated-damage sibling had the aura. Check that sibling before calling a borderline hit raw.
4. `any_hit_is_fail` → **fail**. Use the mechanic skill for whose fault.
5. Unmitigated above `fail_above`, or above the role cap → **fail**. Use the mechanic skill. Overkill on a failed hit is still a fail.
6. Unmitigated at or under the role cap, and HP already under 15,000 → **low**. The hit is the normal one.
7. Unmitigated at or under the role cap → **raw**, unless that mechanic's skill says the hit is still a mistake. A short stack that still fits the cap is raw when the mechanic scales with stack. A tank death on Ascalon's Might, Heavenly Heel, or Holy Bladedance without the required personal mitigation is a fail. A Skyward Leap death on the real marker is a fail: short of full HP belongs to the healers, and full HP is missing mitigation.

## Say this

One block per death:

```
**Pull {id} · {player} · {mechanic}** — {raw|fail|low|environment|unknown}
Happened: {unmitigated, HP, mit, shield, stack if it scales}
Should have been: {from the mechanic entry}
Fault: {from the mechanic skill}
```

For a whole pull, add one line: how many raw, fail, low, and no-packet deaths.

Name the player. A raw hit on a full share is the resolve: shield, mit, and HP. A short stack that scales is the missing bodies. A failed shape is the player who took it, unless that mechanic's skill says the miss belongs to someone who was not in the tower.

## When a call is wrong

A correction ("X should be Y", "that is not a mistake", "that one is a fail") updates `fights/dsr/mechanics.json`, then:

```
python -m xivloganalyzer reanalyze
```

Update `tests/test_reference.py` only when the settled headline is meant to change. That headline is 183 raw deaths on report `XVz8bCqgPw1KRh9d`. Update `notes/classification.md` when the reason changes. Update the mechanic skill when the way you tell the cases apart changes. Leave `dashboard.html` and `session.html` alone; reanalyze rewrites them.

## Mechanic index

| Ability | Guids | Skill |
|---|---|---|
| Eternal Conviction | 25568 | `dsr-eternal-conviction` |
| Sacred Sever | 25571 | `dsr-sacred-sever` |
| Hiemal Storm | 25575 | `dsr-hiemal-storm` |
| Holy Impact | 25578 | `dsr-holy-impact` |
| Dragon's Rage | 25551 | `dsr-dragons-rage` |
| Skyward Leap | 25565 | `dsr-skyward-leap` |
| Heavenly Heel | 25543 | `dsr-heavenly-heel` |
| Holy Bladedance | 25299 | `dsr-holy-bladedance` |
| Lightning Storm | 25549 | `dsr-lightning-storm` |
| Bright Flare | 25295 | `dsr-bright-flare` |
| Ascalon's Might | 25541 | `dsr-ascalons-might` |
| Ascalon's Mercy Concealed | 25545 | `dsr-ascalons-mercy-concealed` |
| Heavy Impact | 25560, 25559 | `dsr-heavy-impact` |
| Dragon's Glory | 25554 | `dsr-dragons-glory` |
| Dragon's Gaze | 25553 | `dsr-dragons-gaze` |
| Holy Shield Bash | 25297 | `dsr-holy-shield-bash` |
| Shining Blade | 25570 | `dsr-shining-blade` |
| Heavens' Stake | 28591 | `dsr-heavens-stake` |
| Frostbite | 1002946 | `dsr-frostbite` |
| Dimensional Collapse | 25564 | `dsr-dimensional-collapse` |

Other phases need their own lived samples. Reuse these bands only for Thordan.
