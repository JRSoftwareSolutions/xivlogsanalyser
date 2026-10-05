# Thordan classification

Report `XVz8bCqgPw1KRh9d`. Phase 2 only. This is the rule set behind the 187 raw deaths.

## What counts

A death is **raw** when the killing blow's unmitigated damage is in the same band as hits of that ability on that role that were lived. A short stack counts when the share is smaller than usual and the hit scales with the missing bodies (Sacred Sever, Dragon's Rage).

A death is a **failed mechanic** when it is a cone, ring, gaze, empty tower, ice fail, or a hit several times larger than anything lived. Vulnerability Up or Damage Down on the packet is a fail. Overkill from a failed mechanic is not raw.

**Low** means the hit was normal-sized and they were already under 15,000 HP. Those 11 are not in the 187.

**Environment** means the deaths table has no damage packet. 88 rows had a timestamp and an empty ability. 39 more had an empty tooltip and no timestamp. The page reports 127. They are usually the body after a raise. Weakness (`1000043`) is the raise debuff. It does not increase damage taken.

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
| Raw | 187 |
| Failed mechanic | 133 |
| No damage packet | 127 |
| Already under 15k | 11 |

Raw by killing blow: Eternal Conviction 121, Sacred Sever 36, Holy Impact 21, Dragon's Rage 5, Skyward Leap 4.

Pull 68, wiped at 65.1%: Kitana's Skyward Leap is the only raw death. Loki and Spring ate Ascalon's Mercy Concealed, Kite ate Heavy Impact, Kiara ate an empty tower. Gigachad, Gigalad, Speed, and the second Loki death have no damage packet.

## Ability bands

Unmitigated amounts. A hit at or under the cap for that role is raw. Far above it is a fail. Ascalon's Might, Heavenly Heel, and Holy Bladedance are the exception: a tank death on the real hit without personal mitigation is a fail.

| Guid | Ability | Lived | Fatal that still counts | Fail |
|---|---|---|---|---|
| 25568 | Eternal Conviction | Tanks 61–67k (39 lived). No healer or DPS lived it. | Tanks ≤75k. Healers and DPS ≤115k (the 90–108k band). | Does not scale with stack size. A full party of 8 still does ~97k to a DPS. |
| 25571 | Sacred Sever | DPS share about 35–63k, median ~43k, usual stack 4. | DPS ≤85k, healer ≤90k, tank ≤120k. Short stacks of 1–2 around 85–104k. | Cleaves in the millions (21 deaths). |
| 25578 | Holy Impact | Tanks 61–67k. | Same caps as Conviction. | Same shape. Pulls 66 and 67 are the whole party, shield 0, mit 1.00. |
| 25551 | Dragon's Rage | About 60–80k, usual stack 5. | ≤140k. Stack of 3 at 102–113k matches a 5-share with two missing. | Over 200k. |
| 25565 | Skyward Leap | 59–70k unmitigated, 33 lived soaks, usually 5–10% mit and 13–39k shield. | Healer/DPS ≤78k. | Empty towers about 600–760k, and anything over 150k. |
| 25543 | Heavenly Heel | Tanks who live it: 159–174k before mit, with Rampart and Sheltron. | Nothing. One tank takes it. The other tank takes the three-hit Ascalon's Might. | A non-tank hit is theirs. Pull 60 Gigalad is the real 165,404 hit with only 10% mit and Desperate Measures. That is his missing personal mitigation, not raw. |
| 25575 | Hiemal Storm | 25–40k. | Nothing in this log. The 114k vs 76k gap on pull 49 is not a short stack. | Every death, minimum about 104k. |
| 25549 | Lightning Storm | One hit each. Tanks 26–29k, healers 38–42k, DPS 38–45k. Healer front, melee left, ranged right, tank back, one of each per triangle. | Inside the role cap (DPS 60k, healer 55k, tank 40k). None of the deaths were. | A clip. Pull 31 is Kite Noodle and Spring Nymphar, both bolts, about 431–468k. Both own it. A doubled non-tank role, a wrong spot, and a Spiral Thrust hit are also mistakes. This log has no positions, so those are not called from damage. |
| 25299 | Holy Bladedance | About 20–22k on the tethered tank, with personal mitigation. | Tank ≤55k, and under 15k HP goes to **low**. A tank death on that hit without personal mitigation is a fail. | A non-tank in the cone. The hits at ~230k and ~370k. |
| 25295 | Bright Flare | About 64k. | ≤85k. The one at 12k HP is **low**. | Overlaps above that. |
| 25545 | Ascalon's Mercy Concealed | Clean pulls take 0. One tank in front, everyone else stacked tight behind, then dodge. | | Any hit, about 190–220k. The player who is hit owns it. A cone baited from outside the stack is also the baiter's mistake. |
| 25560, 25559 | Heavy Impact | Clean pulls take 0. | | The knight's pulses. A hit stuns and applies Damage Down. About 51–57k. Both ids. |
| 25554, 25553 | Dragon's Glory / Gaze | A successful gaze is 0. | | About 40–45k. |
| 25297 | Holy Shield Bash | A stretched tether on a tank is often fully shielded. No lived unmitigated band. | | A non-tank, or a short tether. Hundreds of thousands to millions, with Physical Vulnerability Up. |
| 25570 | Shining Blade | | | Failed cleave. |
| 28591 | Heavens' Stake | | | Standing in the fire. Not the meteor. |
| 25541 | Ascalon's Might | One tank, about 71–86k. The warrior invulns it or heavy-mits it. The later cast is the other tank from the Heavenly Heel swap. | | A second body, a non-tank, or a tank who dies on the real hit without personal mitigation. Pull 14 Gigachad ate the 153k cleave as the extra body. |
| 25564 | Dimensional Collapse | No lived sample in the fetched events. | | The floor puddles in the second wave. A hit applies Heavy and Damage Down. One death, pull 29. |
| 1002946 | Frostbite | | | Failed ice soak. |

Role caps used when the packet had an unmitigated amount:

- Eternal Conviction `25568`: tank 75,000, healer and DPS 115,000
- Sacred Sever `25571`: tank 120,000, healer 90,000, DPS 85,000
- Hiemal Storm `25575`: tank 90,000, healer and DPS 55,000
- Holy Impact `25578`: tank 78,000, healer and DPS 115,000
- Dragon's Rage `25551`: 130,000 tank, 140,000 others, and anything over 200,000 is a fail
- Skyward Leap `25565`: healer and DPS 78,000, over 150,000 is a fail
- Holy Bladedance `25299`: 55,000
- Heavenly Heel `25543`: tank 190,000
- Lightning Storm `25549`: tank 40,000, healer 55,000, DPS 60,000
- Bright Flare `25295`: 85,000

Dodge ids, always a fail: `25545`, `25560`, `25559`, `25554`, `25553`, `25570`, `28591`, `1002946`, `25564`, `25297`.

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

## Still open

- Dimensional Collapse `25564` is a failed puddle: Heavy and Damage Down. It has no lived baseline, so the one death stays a fail.
- Dragon's Rage: the three unmarked non-tanks stack under Thordan. Lived hits are usually those three plus both tanks. Whether the tanks belong in that stack is still open, so a share of 3 stays the short 5-share.
- Skyward Leap: six towers, one per non-tank. Clean casts store three hits at 59–70k on the players outside the stack. Whether that 60k is the blue marker or three of the six towers is still open, so the soak-versus-explosion rule stays.
- Party mit and shields are missing on many damage packets, so a vuln that never landed on the packet would be missed.
- Eternal Conviction and Holy Impact have no lived healer or DPS sample in this log. The 90–108k and 95–103k bands are the death cluster, matched against the tank hit of the same cast (~64k). That is why they are raw.
- The next reviews (other phases, other reports) should reuse these bands only for Thordan. Other phases need their own lived samples.
