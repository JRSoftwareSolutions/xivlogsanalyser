# Thordan classification

Report `XVz8bCqgPw1KRh9d`. Phase 2 only. This is the rule set behind the 86 raw deaths. Sanctity parameters were checked against the successful resolves in `8DYNHQx4C7ytdLb9`.

## What counts

A death is **raw** when the killing blow's unmitigated damage is in the same band as hits of that ability on that role that were lived. A short stack counts when the share is smaller than usual and the hit scales with the missing bodies (Sacred Sever, Dragon's Rage).

A death is a **failed mechanic** when it is a cone, ring, gaze, empty tower, ice fail, or a hit several times larger than anything lived. Vulnerability Up or Damage Down on the packet is a fail. Overkill from a failed mechanic is not raw.

**Low** means the hit was normal-sized and they were already under 15,000 HP. Those 4 are not in the 86. An empty Sanctity tower or a comet overlap is a fail even when they were already that low.

**Deathwall** means the deaths table has no damage packet. The player walked into the deathwall, and that is always a mistake. The page reports 110. A damage-over-time kill, such as Frostbite `1002946` or Burns `1002945`, links its status (`#status/2946`) instead of an action. That is a real killing blow, not the deathwall. Reading only action links had 17 of those as deathwall. The only timestamp in those rows is the last hit they lived, often several seconds earlier. The death is timed by the row's clock instead. That clock reads 1–2 seconds after the killing hit on rows that have one, so a deathwall death is moved back 1.5 seconds. Weakness (`1000043`) is the raise debuff. It does not increase damage taken.

**First mistake** is the earliest death, Damage Down, or Hysteria in the pull, plus anything within the next second. It matters most. Later deaths often cascade from it. A deathwall walk before it, or as part of it, is that player's own mistake at 100. With their own Hysteria from the gaze still on, it is still theirs: they looked. A deathwall walk after it is still a mistake, shared 50 with "Earlier mistake". Pull 28 is Loki Doki walking into the wall at 0:59, before anyone died. Pull 23 is two cone deaths at 14.9 seconds, then the rest of the party in the wall over the next six seconds.

## Which pulls

55 pulls: `lastPhaseForPercentageDisplay >= 2` and at least 20 seconds after the phase 2 start. Deaths before the phase 2 start are skipped. Fights 9 and 56 only touch phase 2 for the Pure of Heart / Brightwing transition and are out. None of the 55 pulls reached phase 3.

Killing blow is the first ability in the deaths-table row before `last-three-events`. The last tooltip event is often reverse-chronological and is the wrong blow.

## Party

| Player | Job | Max HP used |
|---|---|---|
| Loki Doki | AST | 62,101 |
| Kite Noodle | NIN | 68,218 |
| Spring Nymphar | SCH | 61,615 |
| Absolute Gigachad | PLD | 99,211 |
| Absolute Gigalad | WAR | 118,362 |
| Speed Panda | VPR | 68,259 |
| Kitana Kahn | BLM | 61,737 |
| Kiara Blaiddyd | DNC | 68,662 |

Gigalad's 118,362 is the largest hit amount seen and is treated as full HP. A weakness HP of 88,843 was also seen.

## Result

| Kind | Deaths |
|---|---|
| Raw | 86 |
| Failed mechanic | 258 |
| Deathwall, also a fail | 110 |
| Already under 15k | 4 |

Raw by killing blow: Eternal Conviction 45, all of them the Strength raidwide around 63 seconds. Sacred Sever 36. Dragon's Rage 5. Holy Impact is no longer raw. Sanctity Eternal Conviction, around 137 seconds, is the empty tower.

Pull 68, wiped at 65.1%: no raw death. Kitana Kahn was at full HP with no mitigation on Skyward Leap, so that death is a mitigation fail. Loki and Spring ate Ascalon's Mercy Concealed, Kite ate Heavy Impact, Kiara took a second Skyward Leap whose holder was already dead. Gigachad, Gigalad, Speed, and the second Loki death walked into the deathwall after those.

## Ability bands

Unmitigated amounts. A hit at or under the cap for that role is raw. Far above it is a fail. Ascalon's Might, Heavenly Heel, and Holy Bladedance are the exception: a tank death on the real hit without personal mitigation is a fail. Heavenly Heel belongs to the off tank. The main tank taking it is a fail.

| Guid | Ability | Lived | Fatal that still counts | Fail |
|---|---|---|---|---|
| 25568 | Eternal Conviction | Strength, around 63s: tanks 61–67k (39 lived). No healer or DPS lived it. Sanctity stores none of this guid on a soaked tower. | Strength: tanks ≤75k, healers and DPS ≤115k (the 90–108k band). Sanctity, after 100s: any hit is the empty tower. | Strength does not scale with stack size. A full party of 8 still does ~97k to a DPS. The Sanctity explosion is the same size and is a mistake. |
| 25571 | Sacred Sever | DPS share about 35–63k, median ~43k, usual stack 4. | DPS ≤85k, healer ≤90k, tank ≤120k. Short stacks of 1–2 around 85–104k. | Cleaves in the millions (21 deaths). |
| 25578 | Holy Impact | No lived hit. Clean comet drops store none. | Any hit. The explosion is tanks about 57–66k and everyone else about 91–106k. | Comets too close. The two prey players own it. |
| 25551 | Dragon's Rage | About 60–80k, usual stack 5: the three unmarked non-tanks plus both tanks. Whether the tanks are supposed to share it is not known, so 5 stays the full share. | ≤140k. Stack of 3 at 102–113k matches a 5-share with two missing. | Over 200k. |
| 25565 | Skyward Leap | The blue marker. 59–70k on three non-tanks, usually 5–10% mit and a 13–39k shield. Opposite Thordan is as far as possible. East and west are slightly toward the north. | Nothing. A death on the real leap is a fail. Not full HP is the healers. Full HP is missing mitigation. Pull 68 Kitana Kahn was full, multiplier 1.00, no shield. | Another holder's leap on them, or a second leap on one player at about 600–760k. Whoever was out of position owns it. |
| 25543 | Heavenly Heel | The off tank lives it at 159–174k before mit. In this log that is the paladin, with Rampart, Holy Sheltron, and Knight's Resolve. | Nothing. The off tank takes it, properly mitigated. The main tank then takes the three-hit Ascalon's Might, also properly mitigated. Sanctity of the Ward is next. | A non-tank hit is theirs. The main tank taking it is his. Pull 60 Gigalad is the real 165,404 hit. He is the main tank, and he had only 10% mit and Desperate Measures. That is not raw. |
| 25575 | Hiemal Storm | Tanks about 14–25k. Healers about 23–38k. DPS about 26–40k. Eight players. | Tank ≤50k. Healer and DPS ≤55k. The 76k tank hit on pull 49 is outside the placed band. | Every death, minimum about 104k. A puddle that covers a tower is a wrong drop. |
| 25549 | Lightning Storm | One hit each. Tanks 26–29k, healers 38–42k, DPS 38–45k. Healer front, melee left, ranged right, tank back, one of each per triangle. | Inside the role cap (DPS 60k, healer 55k, tank 40k). None of the deaths were. | A clip. Pull 31 is Kite Noodle and Spring Nymphar, both bolts, about 431–468k. Both own it. A doubled non-tank role, a wrong spot, and a Spiral Thrust hit are also mistakes. This log has no positions, so those are not called from damage. |
| 25299 | Holy Bladedance | About 20–22k on the tethered tank, with personal mitigation. | Tank ≤55k, and under 15k HP goes to **low**. A tank death on that hit without personal mitigation is a fail. | A non-tank in the cone. The hits at ~230k and ~370k. |
| 25295 | Bright Flare | No clean hit. A tank lived about 61k on the new log and that hit is still a mistake. | Any hit. One orb is about 61–67k on a tank and about 93–111k on everyone else. | A hit, including the old 12k HP case. An overlap splits across the players in the burst. |
| 25545 | Ascalon's Mercy Concealed | Clean pulls take 0. The opener is one in front and seven behind. During Strength the party is walking in through Heavy Impact, so that cast is a 4/4 split. | | Any hit, about 190–220k. The player who is hit owns it. The out-of-stack baiter rule is the opener only. |
| 25560, 25559 | Heavy Impact | Clean pulls take 0. | | The knight's pulses. A hit stuns and applies Damage Down. About 51–57k. Both ids. |
| 25554, 25553 | Dragon's Glory / Gaze | A successful gaze is 0. | | About 40–45k. |
| 25297 | Holy Shield Bash | A stretched tether on a tank is often fully shielded. The hit stuns. No lived unmitigated band. | | A non-tank takes the stun and dies. A short tether is hundreds of thousands to millions, with Physical Vulnerability Up. |
| 25570 | Shining Blade | | | Failed cleave. |
| 28591 | Heavens' Stake | | | Standing in the fire. Not the meteor. |
| 25541 | Ascalon's Might | One tank. The opener is about 71–86k, on the main tank. After Heavenly Heel the main tank's three hits are about 59–86k. Both takes are properly mitigated. On the later three-hit the warrior uses Vengeance, Bloodwhetting, and Stem the Flow. | | A second body, a non-tank, the off tank who already took the heel, or a tank who dies on the real hit without personal mitigation. Pull 14 Gigachad ate the 153k cleave after taking the heel. |
| 25564 | Dimensional Collapse | No lived sample in the fetched events. | | The floor puddles in the second wave. A hit applies Heavy and Damage Down. One death, pull 29. |
| 1002946 | Frostbite | | | Failed ice soak. |
| 1002945 | Burns | | | The fire's damage over time. Standing in the fire. |

Role caps used when the packet had an unmitigated amount:

- Eternal Conviction `25568`, the Strength hit only: tank 75,000, healer and DPS 115,000. After 100 seconds any hit is the empty tower.
- Sacred Sever `25571`: tank 120,000, healer 90,000, DPS 85,000
- Hiemal Storm `25575`: tank 50,000, healer and DPS 55,000
- Holy Impact `25578`: any hit is the comet overlap
- Dragon's Rage `25551`: 130,000 tank, 140,000 others, and anything over 200,000 is a fail
- Skyward Leap `25565`: healer and DPS 78,000, over 150,000 is a fail
- Holy Bladedance `25299`: 55,000
- Heavenly Heel `25543`: tank 190,000
- Lightning Storm `25549`: tank 40,000, healer 55,000, DPS 60,000
- Bright Flare `25295`: any hit

Dodge ids, always a fail: `25545`, `25560`, `25559`, `25554`, `25553`, `25570`, `28591`, `1002946`, `1002945`, `25564`, `25297`, `25578`, `25295`. Sanctity Eternal Conviction `25568` after 100 seconds is a fail as well. The Strength hit of that same guid is not.

## Reading a packet

`amount` is HP removed. `overkill` is the excess when the hit killed. `absorbed` is the shield. Total hit is amount + overkill + absorbed. `unmitigatedAmount` is before party mit. `multiplier` is the mit still on the hit: 1.00 is none, 0.95 is about 5%, 0.90 is about 10%.

Known fail auras: Magic Vulnerability Up `1002941`, Physical Vulnerability Up `1002940`. Buffs are often missing on the damage packet (`buffs` empty) even when a calculated-damage sibling had them. Conviction and Holy Impact deaths sit in one tight band, which a vuln amp would have broken. A borderline death should be checked against the calculated-damage sibling before it is called raw.

## How the log was read

FFLogs sits behind a human check and Cloudflare. curl and headless Chrome get the challenge page. A headed Chrome session that clicks through, then `fetch()` from the page with same-origin credentials, returns the report JSON. `page.request` does not share those cookies. Fetch the report origin, not `assets.rpglogs.com` (CORS).

Damage-taken responses cap near 300 events and return `nextPageTimestamp`. Page by replacing the start time until the next timestamp is missing.

Useful paths, hostility 0, boss filter `-1.0.-1.-1`, cutoff 0, classes Any:

- Fights: `/reports/fights-and-participants/<code>/0`
- Deaths table: `/reports/deaths/<code>/<fight>/<start>/<end>/0/0/0/-1.0.-1.-1/0/Any/0/<start>`
- Damage taken: `/reports/events/damage-taken/<code>/<fight ids dotted>/<start>/<end>/source/0/0/0/0/0/<ability>/-1.0.-1.-1/0/Any/Any/0`

## Blame confidence

Each blame names an owner and a percent. 100 is one person. When several people could own the death, each gets an equal share of 100, rounded down: 50 for two, 33 for three.

A personal miss stays at 100 even when someone else died to a different miss on the same cast: a gaze, a ring, a cone, a puddle, a cleave, vulnerability, a non-tank tankbuster, or a tank's own missing personal mitigation.

A Lightning Storm clip or a Bright Flare overlap splits across the players in that overlap, 50 each. Skyward Leap under full HP splits across the two healers, 50 each. Full HP with the mit missing is "Assigned mitigation" at 50. An empty tower is "Missed soak" at 50, unless someone was missing from it. A player already dead, or alive and not hit by the tower soak (Conviction `29564` or `28651`), owns it, split evenly. A player who was missing because they were dead passes it on to whoever owned that death: themselves for their own mistake, the other player for a clip or an earlier empty tower, the healers for a raw death. Shares that only sit beside an owner, such as "Party mitigation" and "Earlier mistake", do not pass on. Two players on one tower's soak instance shared a tower and own it too. Holy Impact is not a missing body: it lands before the outer towers. It belongs to whoever dropped the two comets that landed under about 5 yalms apart, read from the Holy Comet positions. Pull 53 of `8DYNHQx4C7ytdLb9` was first read as the dead paladin's empty tower. The comets show Kite Noodle's last comet on Speed Panda's first, so they own it at 50 each. A Bright Flare overlap is the players on one orb's packet. Two orbs at the same moment are two personal hits. A healer already dead passes their share on to whoever owned that healer's death. A clip is "Out of position" at 33. A death from another player's Skyward Leap, by its vulnerability or the leap itself, belongs to whoever was out of position: the marker holder off their spot, or the player who stood in a leap on its spot, at 100. Both off splits it, 50 each. With no positions, the holder owns it. The marker holder is the first target in that leap's packet. A second leap whose holder was already dead is "Earlier deaths" at 100. A short stack is "Missing bodies" at 100 divided by the missing count, unless the log names who was missing (Sacred Sever below, Eye of the Tyrant). A raw full share blames the healers at 50, and "Party mitigation" joins them at 33 when the packet shows no party mit. A low hit blames the healers and "Earlier damage" at 33.

A raw or low death right after the player lived their own avoidable hit is theirs at 100, not the healers'. The avoidable hits are the ones that are always a mistake: a gaze, a dodge, a puddle, or an orb. A tank's own tether is their job and does not count. It counts when that hit, shield included, was at least what they were short: with it back they would have lived. 10 deaths in the three logs, mostly a Dragon's Glory look a second before the Sacred Sever share. The outcome stays raw or low, so the 86 does not move. Pull 11, Kitana Kahn and Speed Panda.

Sacred Sever alternates groups (`alternating` on `sacred-sever`). The group for a jump is whoever took the jump two before it. The first two jumps have nothing that early, so their group is everyone the other group's jump missed. A player who dies with the last jump's Physical Vulnerability Up, and is not in this jump's group, took a jump that landed on the wrong group because that group's players were already dead. Those dead players own it, passed on as above, and the right group's living players do not: the knight follows the sword, not the stack. 25 deaths were called each victim's own amp. `3wzL6x4VHTmvNkhq` pull 49 is the clearest: all four of the first group looked at Dragon's Glory, and the third jump killed the other four. A player who is in the group and still had the amp took both jumps, and it stays theirs (`3wzL6x4VHTmvNkhq` pull 24, Kitana Kahn). A short jump names the group's players who were dead or alive and not in it. When nobody of the group is missing, it stays Missing bodies (pull 49 here).

Dive from Grace: the first towers, before 42 seconds, need the 3s, and the 2s and 3s are the Eye of the Tyrant stack (`needs_everyone` with `holders` on those two mechanics). A dead 3 left a first tower empty, and a dead 2 or 3 left the stack short. Both pass on as above. With every 3 alive, an empty first tower is still Missed soak (`8DYNHQx4C7ytdLb9` pulls 36 and 50).

A deathwall walk after other players' mistakes is shared with "Earlier mistake". When every death and Damage Down or Hysteria earlier in the pull was the walker's own, it is theirs at 100 (`8DYNHQx4C7ytdLb9` pull 18).

## Still open

- Dimensional Collapse `25564` is a failed puddle: Heavy and Damage Down. It has no lived baseline, so the one death stays a fail.
- Dragon's Rage: the person does not know whether the tanks belong in the stack. Lived hits are usually the three unmarked non-tanks plus both tanks, so a share of 5 stays full and a share of 3 stays short.
- Skyward Leap at 59–70k is the blue marker. A death on it is a healer mistake or a missing mitigation. The 600–760k hits are not towers. Each is a second leap on a player in the same instant as the markers. The positions say who was off their spot.
- Sacred Sever's per-player hit is about the same total split by the stack: a non-tank takes about 43k in a 4, 57k in a 3, 81–91k in a 2, and 160–181k alone. The role caps (DPS 85k, healer 90k) were set from the 4-share and the tanks' lone shares, so a healer's 91k in a 2 and a non-tank's 160–181k alone are called cleaves. `dsr-sacred-sever` names the 181k on `8DYNHQx4C7ytdLb9` pull 36 a cleave. Which it is decides whether a lone jump is the marked player running the wrong way or missing bodies. The person has not said.
- The first jump, about 112 seconds, is sometimes far larger than its stack: four players at about 400k on pull 27, and 71–99k in a 4 on pull 35, where one of the four is under the DPS cap and called raw. No amp shows on those packets. The cause is not known.
- Deathwall walks right after an early death of both healers, or of most of the party, look like deliberate resets: the rest of the party walks in within a few seconds (pulls 23, 31, 33, 45). They stay fails shared with "Earlier mistake", as the person decided.
- Party mit and shields are missing on many damage packets, so a vuln that never landed on the packet would be missed.
- Strength Eternal Conviction, around 63 seconds, still has no lived healer or DPS sample. The 90–108k band is the death cluster of that raidwide, matched against the tank hit (~64k). That window stays raw. Sanctity Eternal Conviction is the empty tower and is a fail. Holy Impact is the comet overlap and is a fail. Whoever dropped the two comets owns Holy Impact. Missed soak owns the empty tower only when the log names nobody.
- Conviction `29564` (about 135s) and `28651` (about 148s) are the soaked towers, about 3k on a tank and 5k on everyone else. Holy Comet `25577` is the light meteor drop, about 1–2k. Faith Unmoving `25308` is the knockback, about 3–5k. None of those guids killed anyone in the reference log.
- The next reviews (other phases, other reports) should reuse these bands only for Thordan. Other phases need their own lived samples.

## Dive from Grace

Report `8DYNHQx4C7ytdLb9`. Eight pulls reached Nidhogg. The strat is LPDU Easthogg. Ability files for these guids are not stored, and the packets have no unmitigated amount, so the number is the total hit. This is the baseline, not a cast survey.

Arrows resolve facing east. An up arrow goes west, a down arrow goes east, and a 2 goes northwest or northeast on the same rule. The mitigations replay stores the number and arrow debuffs, and the positions replay stores where each diver stood and faced at the snapshot. The facing decides where the tower drops. A circle has no side, so circles sharing a landing are a miscommunication.

Final Chorus and the auto cleave are not this stop. A blank killing blow at the dive, with the dive in the last hits, is the knock into the wall. Pull 33. It is a Deathwall fail.

| Guid | What the hit is | Call |
|---|---|---|
| 26382, 26384 | Over 150k, an arrow on the wrong side | Fail. The arrow holder owns every death in that landing. Pull 27, Loki Doki took the down arrow west, facing west, onto Spring Nymphar's up arrow. |
| 26382, 26384 | Over 150k, only circles out of place | Fail. Miscommunication, split across the landing. Pull 46. |
| 26388 | About 37–70k | Raw when they were healthy. The healers, and party mitigation when the mit is unknown. |
| 26388 | Over 100k | Fail. Short stack. The 2s and 3s stack, and a dead one owns the gap, passed on. Pull 16. |
| 26389, 26390 | About 12–23k | Fail. Wrong side of the in-and-out. Still a fail under 15k HP. |
| 26385 | About 445–570k | Fail. Soaked while they still had the dive debuff. |
| 26395 | Tanks about 32–54k, others about 59–80k | Raw, or low when already under 15k HP. |
| 26395 | About 1.4–3.0 million | Fail. Empty tower. The first towers are the 3s. A dead 3 owns it, passed on. With every 3 alive, Missed soak. |
| 26378 | One player in the line | Fail. That player. |
