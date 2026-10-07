---
name: dsr-dive-from-grace
description: >-
  Identify Dive from Grace deaths in Dragonsong's Reprise Nidhogg, using the
  LPDU Easthogg spots: the dive landing, the north stack, the in-and-out,
  the tower soak, the empty tower, and Geirskogul. Use when the killing blow
  is Dark High Jump, Dark Elusive Jump, Eye of the Tyrant, Gnashing Wheel,
  Lashing Wheel, Darkdragon Dive, or Geirskogul.
---

# Dive from Grace

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Cluster `dive-from-grace` in `fights/dsr/mechanics.json`. Phase 3. The strat is LPDU Easthogg.

The cast is about 17 seconds into Nidhogg. These packets have no `unmitigatedAmount`, so the number is amount plus overkill plus shield. Ability files for these guids are not stored. The bands are the death-table hits on `8DYNHQx4C7ytdLb9`, eight pulls. Deaths do not set a lived band except where a tooltip shows the same hit with overkill `-1`.

Final Chorus and the auto cleave are not this stop. An up arrow is Dark Spineshatter Dive. This log stores no guid for it. Do not invent one.

## Easthogg

True north. Nidhogg faces north. The stack is north, in front of him.

When the numbers appear, claim a spot. That spot stays if the number has no arrows.

- 1s and 3s: west, south, and east, on the hitbox.
- 2s: northwest and northeast, out at max melee.

Arrows replace that number's spots. Face east.

- Up arrow: west. A 2 stands northwest. The tower drops in front, on the west side.
- Circle: south, or the spot already claimed. The tower drops there.
- Down arrow: east. A 2 stands northeast. The tower drops behind, on the east side.

Soak order:

- The 3s soak the towers the 1s drop.
- The east and west 1s soak the towers the 2s drop.
- The 2s and the south 1 soak the towers the 3s drop.

A dive and a soak each leave Fire Resistance Down II and Physical Vulnerability Up. Soaking again with those debuffs kills. You do not soak your own tower.

## How to tell

Apply these to the killing blow.

- Dark High Jump `26382` or Dark Elusive Jump `26384`, over 150,000: someone stood in the landing. Each player in that burst owns it. Pull 27, both healers, is the down arrow. Pull 46, four players, is the circle.
- Those guids at about 9–23k: the landing connected. A death there is raw, or low if they were already under 15,000 HP. This log has no such death. The circle has lived hits in that band. The down arrow has no small hit stored.
- A death with no killing blow, at the same moment, last hit the dive: the knock into the wall. The row has no packet, so it is a Deathwall fail. Pull 33 is that case.
- Eye of the Tyrant `26388` at or under the role cap: the stack of five. Tanks about 37–48k. Everyone else about 50–70k. Dying there from a healthy bar is the healers. Pull 26, three players from full HP at about 71k with no shield.
- Eye of the Tyrant over 100,000: the stack was short. Pull 16 is 116k on Gigalad and 182k on Kitana Kahn. The log has no stack count, so the missing bodies stay unnamed.
- Gnashing Wheel `26389` or Lashing Wheel `26390`: any hit is a fail, including under 15,000 HP. About 12–23k and Damage Down. Gnash is inside the hitbox, so out is safe. Lash is outside, so in is safe. Gnash and Lash means out, then in. Lash and Gnash means in, then out.
- Darkdragon Dive `26385`: any hit is a fail. About 445–570k. They soaked while they still had the dive debuff. Pull 33, Kite Noodle and Speed Panda. Pull 27, Speed Panda. Pull 46, Kitana Kahn.
- Darkdragon Dive `26395` at or under the role cap: the soak. Tanks about 32–54k. A non-tank hit that killed from a high bar was about 59–80k. No survived non-tank soak is stored. Dying to it from a healthy bar is the healers. Already under 15,000 HP is low. Pull 27, Kite, Kitana, and Gigalad were low.
- Darkdragon Dive `26395` over 150,000: an empty tower. About 1.4–3.0 million. The assigned soaker owns the miss. On the first towers, about 37–39 seconds, those are the 3s. The log does not store the number debuff, so the call is Missed soak. A wrong facing would move the fault to the diver. Damage cannot show the tile.
- Geirskogul `26378`: any hit is a fail. One player in the line owns it. Pull 36 Gigachad was at 12,516 HP. Pull 46 Kite Noodle took about 109k. Several players in one line would be the baiter. This log never has more than one.

Standing on the wrong clock spot, while the tower still lands on a soakable tile and nobody extra is in the dive, does not show in the damage.

## Fault

Dive landing over 150,000: `{player}` stood in the dive. Each player in that landing owns an equal share.

Eye of the Tyrant inside the cap: the resolve. Name the shield and the mit. Party mitigation joins the healers when the mit is unknown.

Eye of the Tyrant over 100,000: the players who were not in the north stack. The log cannot name them or count them. Missing bodies.

In-and-out: `{player}` was on the wrong side.

Debuffed soak: `{player}` soaked a tower while they still had the dive debuff.

Soak inside the cap: the resolve, or low when they were already under 15,000 HP.

Empty tower: `{player}` died to the explosion. Missed soak. The first towers belong to the 3s. This log cannot name which 3.

Geirskogul: `{player}` stood in the line.

## Parameters

Follow `analyze-mechanic-parameters`. Surveyed from the death table on `8DYNHQx4C7ytdLb9`, not from ability files. Time zero is the phase 3 start. The first landings are about 31 seconds. The wheels are about 35–38 seconds. `26385` is about 37 seconds. `26395` is about 39 seconds. A later circle landing on pull 46 is at 52 seconds. Geirskogul is about 45 and 55 seconds.
