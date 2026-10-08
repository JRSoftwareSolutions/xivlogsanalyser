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

Final Chorus `26377`, about 2.5 seconds, is Nidhogg's opening raidwide: a death on it is the healers and party mitigation. Nidhogg's first auto-attack `26416`, about 8 seconds, is a frontal cleave: a non-tank it hits owns that. Both sit on this stop's card. They are not part of the dive. An up arrow is Dark Spineshatter Dive. This log stores no guid for it. Do not invent one.

## Easthogg

True north. Nidhogg faces north. The stack is north, in front of him.

When the numbers appear, claim a spot. That spot stays if the number has no arrows.

- 1s and 3s: west, south, and east, on the hitbox.
- 2s: northwest and northeast, out at max melee.

Arrows replace that number's spots. Face east at the snapshot. The facing decides where the tower drops, so a diver on the right side facing the wrong way still misplaces it.

- Up arrow: west. A 2 stands northwest. The tower drops in front, on the west side.
- Circle: south, or the spot already claimed. The tower drops there.
- Down arrow: east. A 2 stands northeast. The tower drops behind, on the east side.

The mitigations replay stores the number debuffs (First, Second, Third in Line) and the dive markers: High Jump Target `1002755` is the circle, Spineshatter Dive Target `1002756` the up arrow, Elusive Jump Target `1002757` the down arrow. A marker comes off just before its landing. The positions replay gives where each diver stood and faced at that moment. `dive_markers` on the landing mechanics in `mechanics.json` carries the side and facing each arrow should have. The fact keeps them as `divers`. `debuffs` on the cluster lists every player's number and dive marker on the pull card, so a review can check who had which arrow.

Soak order:

- The 3s soak the towers the 1s drop.
- The east and west 1s soak the towers the 2s drop.
- The 2s and the south 1 soak the towers the 3s drop.

A dive and a soak each leave Fire Resistance Down II and Physical Vulnerability Up. Soaking again with those debuffs kills. You do not soak your own tower.

## How to tell

Apply these to the killing blow.

- Dark High Jump `26382` or Dark Elusive Jump `26384`, over 150,000: someone stood in the landing. Read the divers whose markers resolved there. An arrow diver within 6 yalms of the player who died, standing on the wrong half (more than 2 yalms off the north–south line), owns every death in that landing. Pull 27: Loki Doki had the down arrow and stood west, facing west, on Spring Nymphar's correct up arrow. Loki owns both deaths. Spring is not the pull's first mistake. The first-mistake line says Spring died to Loki's dive. A landing that hit the stack (more than two players) belongs to its dive targets, the first target of each such landing: a dive target never stands in the stack, so it is not a miscommunication. Pull 46, five players, Speed Panda's and Absolute Gigalad's circles in the stack. When no arrow is out of place and the landing missed the stack, only circles collided, and the overlap is a miscommunication. Without the replays, each player in the burst owns an equal share.
- Those guids at about 9–23k: the landing connected. A death there is raw, or low if they were already under 15,000 HP. This log has no such death. The circle has lived hits in that band. The down arrow has no small hit stored.
- A death with no killing blow, at the same moment, last hit the dive: the knock into the wall. The row has no packet, so it is a Deathwall fail. Pull 33 is that case.
- Eye of the Tyrant `26388` at or under the role cap: the stack of five. Tanks about 37–48k. Everyone else about 50–70k. Dying there from a healthy bar is the healers. Pull 26, three players from full HP at about 71k with no shield.
- Eye of the Tyrant over 100,000: the stack was short. Pull 16 is 116k on Gigalad and 182k on Kitana Kahn. The stack is the 2s and 3s, read from the number debuffs, so a 2 or 3 already dead is a missing body. Kite Noodle, Loki Doki, and Kiara Blaiddyd were dead on pull 16. Each gap passes on to whoever owned that death.
- Gnashing Wheel `26389` or Lashing Wheel `26390`: any hit is a fail, including under 15,000 HP. About 12–23k and Damage Down. Gnash is inside the hitbox, so out is safe. Lash is outside, so in is safe. Gnash and Lash means out, then in. Lash and Gnash means in, then out.
- Darkdragon Dive `26385`: any hit is a fail. About 445–570k. They soaked while they still had the dive debuff. Pull 33, Kite Noodle and Speed Panda. Pull 27, Speed Panda. Pull 46, Kitana Kahn.
- Darkdragon Dive `26395` at or under the role cap: the soak. Tanks about 32–54k. A non-tank hit that killed from a high bar was about 59–80k. No survived non-tank soak is stored. Dying to it from a healthy bar is the healers. Already under 15,000 HP is low. Pull 27, Kite, Kitana, and Gigalad were low.
- Darkdragon Dive `26395` over 150,000: an empty tower. About 1.4–3.0 million. The assigned soaker owns the miss. On the first towers, about 37–39 seconds, those are the 3s, read from the number debuff (`needs_everyone` with `holders` and `until` on `darkdragon-dive`). A 3 already dead owns the empty tower, passed on to whoever owned that death: pulls 16, 26, 30, and 33. With every 3 alive the call stays Missed soak, because the soak hits are not stored: pulls 36 and 50. The later towers are not read yet. A wrong facing would move the fault to the diver. Damage cannot show the tile.
- Geirskogul `26378`: any hit is a fail. One player in the line owns it. Pull 36 Gigachad was at 12,516 HP. Pull 46 Kite Noodle took about 109k. Several players in one line would be the baiter. This log never has more than one.

Standing on the wrong clock spot, while the tower still lands on a soakable tile and nobody extra is in the dive, does not show in the damage.

## Fault

Dive landing over 150,000, arrow on the wrong side: `{holder}` took the arrow to the wrong side, facing where they faced. Everyone else that landing killed got hit by `{holder}`'s dive. The holder owns it at 100, and only the holder fails it on the pull card.

Dive landing over 150,000 in the stack: `{diver}` dove into the stack. The dive targets own it, split evenly.

Dive landing over 150,000, no arrow out of place, outside the stack: `{player}` stood in the dive, a miscommunication. "Miscommunication" at the landing's share.

Eye of the Tyrant inside the cap: the resolve. Name the shield and the mit. Party mitigation joins the healers when the mit is unknown.

Eye of the Tyrant over 100,000: the players who were not in the north stack. A 2 or 3 already dead is named and passes it on to whoever owned that death. With none dead, Missing bodies.

In-and-out: `{player}` was on the wrong side.

Debuffed soak: `{player}` soaked a tower while they still had the dive debuff.

Soak inside the cap: the resolve, or low when they were already under 15,000 HP.

Empty tower: `{player}` died to the explosion. The first towers belong to the 3s, and a dead 3 owns it, passed on to whoever owned that death. Missed soak only when every 3 was alive.

Geirskogul: `{player}` stood in the line.

## Parameters

Follow `analyze-mechanic-parameters`. Surveyed from the death table on `8DYNHQx4C7ytdLb9`, not from ability files. Time zero is the phase 3 start. The first landings are about 31 seconds. The wheels are about 35–38 seconds. `26385` is about 37 seconds. `26395` is about 39 seconds. A later circle landing on pull 46 is at 52 seconds. Geirskogul is about 45 and 55 seconds.

Darkdragon Dive `26395` lands only when a tower went unsoaked, about 2 seconds after the soak `26385`, and hits the whole raid. Pull 46 on `8DYNHQx4C7ytdLb9`, with every tower soaked, has none. Every `26395` hit is a fail, even a 50k tank hit. On the first towers the 3s (`Third in Line`) soak: a 3 who was alive and not hit by `26385` owns the empty tower, and a 3 already dead passes it on to whoever owned that death. A soaker's Physical Vulnerability Up from `26385`, or from a Dark High Jump's own snapshot, is not their mistake.
