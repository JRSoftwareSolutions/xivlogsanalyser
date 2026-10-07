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

The death line is only this cast. A later cast of the same ability stays out of it. `should_have_been` on the mechanic is the default. A cluster part's own `should_have_been` is the line for deaths inside that part's `after` / `until` window. A `moments` row, with `above` set to an unmitigated hit, replaces the line when the hit is larger than that. Use it when one guid covers two resolutions at the same time, such as a Skyward Leap marker and a second leap on the same player.

Read the mechanic skill for the killing blow before you assign fault. Setting or checking parameters uses `analyze-mechanic-parameters`, then that mechanic's Parameters section. Which casts belong together, and what each one does, is `mechanic-components`. The session line lists those clusters by `starts`. That file names the skill for the stop. The killing-blow index is below.

## Killing blow

The killing blow is the first ability in the deaths-table row before `last-three-events`. The last tooltip event is often reverse-chronological and is the wrong blow.

No ability on that row means there is no damage packet. That is the deathwall. The only timestamp on that row is the last hit they lived, so the death is timed by the row's clock instead, moved back 1.5 seconds to match the hit timestamps.

## Packet

Compare `unmitigatedAmount` to the role cap. `amount` is HP removed. `overkill` is the excess that killed. `absorbed` is the shield. Total hit is amount + overkill + absorbed. `multiplier` is the mit still on the hit: 1.00 is none, 0.90 is about 10%. HP at the killing blow is `amount` when `overkill` is set. Stack size is distinct targets in the same ~1.5s cluster.

Role comes from the job. Tanks: Paladin, Warrior, Gunbreaker, Dark Knight. Healers: Astrologian, Scholar, White Mage, Sage. Everyone else is DPS.

`low_hp` in `fights/dsr/fight.json` is 15,000.

## Outcome

Apply these in order:

1. No damage packet → **fail**, Deathwall. They walked into the deathwall, and that is always a mistake. Before any other death, Damage Down, or Hysteria in the pull, it is their own mistake. With their own Hysteria still on, they looked at the gaze and it walked them in. Weakness `1000043` is the raise debuff and does not increase damage taken.
2. Guid is not in `mechanics.json` for this phase → **unknown**. No fault. Ask what the hit should mean.
3. Magic Vulnerability Up `1002941`, Physical Vulnerability Up `1002940`, or Damage Down on the packet → **fail**. The amp is a failed mechanic. `buffs` is often empty on the damage packet even when a calculated-damage sibling had the aura. Check that sibling before calling a borderline hit raw.
4. `any_hit_is_fail` → **fail**. Use the mechanic skill for whose fault. A Bright Flare overlap still splits across the players in the burst. Holy Impact is the two prey players.
5. A `moments` row with `fail` true, when the time matches → **fail**. Sanctity Eternal Conviction, after 100 seconds, is the empty tower. The Strength hit around 63 seconds stays the raidwide.
6. Unmitigated above `fail_above`, or above the role cap → **fail**. Use the mechanic skill. Overkill on a failed hit is still a fail.
7. Unmitigated at or under the role cap, and HP already under 15,000 → **low**. The hit is the normal one.
8. Unmitigated at or under the role cap → **raw**, unless that mechanic's skill says the hit is still a mistake. A short stack that still fits the cap is raw when the mechanic scales with stack. A tank death on Ascalon's Might, Heavenly Heel, or Holy Bladedance without the required personal mitigation is a fail. Heavenly Heel belongs to the off tank: the main tank taking it is a fail. A Skyward Leap death on the real marker is a fail: short of full HP belongs to the healers, and full HP is missing mitigation.

## Say this

One block per death. The sentence is what went wrong. Do not say what the mechanic should have been.

```
**Pull {id} · {player} · {mechanic}** — {raw|fail|low|unknown}
{one short sentence}
Fault: {who} {confidence}%
```

Name the player and the mistake. Leave out the damage, the shield, and who owns it. The blame line owns that.

- Kitana Kahn got clipped by a Bright Flare.
- Kite Noodle looked at the gaze.
- Kiara Blaiddyd wasn't full for Skyward Leap.
- The stack was 2 of 4.

For a whole pull, add one line: how many raw, fail, and low deaths, and the first mistake.

## First mistake

The first mistake of a pull matters most. It is the earliest death, Damage Down, or Hysteria in the pull, with anything else in the same second. Later deaths are often that mistake cascading: fewer bodies for a stack, a raise that leaves someone low, a group that gives up and walks into the wall. Name the first mistake before the rest. `first` and `first_mistake` on each judgment carry it.

## Blame confidence

Every blame has a percent. 100 means one owner. When several people made a mistake and the log cannot say who owns which part, each of them gets an equal share of 100, rounded down. Two owners is 50 each. Three is 33. An unnamed group is one chip at that same share.

A gaze, a ring, a cone, a puddle, a cleave, vulnerability, a non-tank on a tank hit, or a tank's own missing personal mitigation stays at 100 on that player. Another player dying to their own separate mistake on the same cast leaves that 100 in place.

These are the shared calls:

- Lightning Storm clip, and a Bright Flare overlap: each player in the overlap. A second body who lived is "Another player".
- Skyward Leap under full HP: the healers, named, split evenly.
- Skyward Leap at full HP: "Assigned mitigation" at 50. The plan is more than one player, and the log does not name them.
- Empty tower: "Missed soak" at 50. The player who died is the one the explosion hit. Sanctity Eternal Conviction after 100 seconds is this call.
- Holy Impact: "Prey markers" at 50. The two prey players dropped the comets too close.
- Someone else's Skyward Leap, by its vulnerability or by the leap itself: whoever was out of position, named. A holder off their spot owns it at 100. A player who stood in a holder's leap on its spot owns it at 100. Both off is 50 each. With no positions, the holder owns it. The death sits under Skyward Leap on the pull card, and only the owners fail it.
- A second Skyward Leap with nobody else's leap on the player: "Earlier deaths" at 100. That leap's holder was already dead.
- Dive from Grace landing: an arrow holder on the wrong side, named, at 100 on every death in that landing. Only that holder fails it on the pull card. With no arrow out of place, "Miscommunication" at the landing's share.
- Short stack: "Missing bodies" at 100 divided by the number missing. One missing body is 100. Three missing bodies is 33.
- Raw hit on a full share: the healers, 50 each. "Party mitigation" takes a third share, 33, when the packet has no party mit or the mit is unknown.
- Already under 15,000 HP: the healers and "Earlier damage", 33 each.
- Deathwall before anything else went wrong: that player at 100. With their own Hysteria from the gaze, still that player at 100.
- Deathwall after the first mistake: that player and "Earlier mistake", 50 each. It is still a mistake, but the first one usually caused it.

An ability that is not understood yet has no blame.

## When a call is wrong

A correction ("X should be Y", "that is not a mistake", "that one is a fail") updates `fights/dsr/mechanics.json`, then:

```
python -m xivloganalyzer reanalyze
```

Update `tests/test_reference.py` only when the settled headline is meant to change. That headline is 86 raw deaths on report `XVz8bCqgPw1KRh9d`. Update `notes/classification.md` when the reason changes. Update the mechanic skill when the way you tell the cases apart changes. Leave `dashboard.html`, `session.html`, and `analysis.json` alone; reanalyze rewrites them.

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
| Conviction | 29564, 28651 | `dsr-conviction` |
| Holy Comet | 25577 | `dsr-holy-comet` |
| Faith Unmoving | 25308 | `dsr-faith-unmoving` |
| Dark High Jump | 26382 | `dsr-dive-from-grace` |
| Dark Elusive Jump | 26384 | `dsr-dive-from-grace` |
| Eye of the Tyrant | 26388 | `dsr-dive-from-grace` |
| Gnashing Wheel | 26389 | `dsr-dive-from-grace` |
| Lashing Wheel | 26390 | `dsr-dive-from-grace` |
| Darkdragon Dive | 26385, 26395 | `dsr-dive-from-grace` |
| Geirskogul | 26378 | `dsr-dive-from-grace` |

Thordan bands stay on Thordan. Nidhogg uses `dsr-dive-from-grace`. Phase 4 and later need their own samples.
