---
name: dsr-skyward-leap
description: >-
  Identify Skyward Leap (guid 25565) deaths in Dragonsong's Reprise Thordan:
  the blue marker, a leap that hit someone else, a second leap on one player,
  and whose fault it was by position. Use when the killing blow is Skyward
  Leap or 25565.
---

# Skyward Leap

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Entry `skyward-leap` in `fights/dsr/mechanics.json`. Guid `25565`. Part of Strength of the Ward (`dsr-strength-of-the-ward`).

The blue marker is Skyward Leap. Three non-tanks have it. The one directly opposite Thordan stands as far away as possible. East and west are slightly offset toward the north, not too far. Everyone else stacks on Thordan's side. A real leap is 59–70k unmitigated, usually with 5–10% mit and a 13–39k shield. `fail_above` is 150,000. A death on the marker uses that line only. A death over 150,000 uses the `moments` row with `above` 150000.

A death on that leap is a mistake. It is not raw.

Each leap is a circle of about 24 yalms around its holder. The three spots are about 26 yalms apart, so a holder a few yalms off their spot reaches another holder or the stack. A leap that reaches someone who is not its holder leaves Magic or Physical Vulnerability Up. A second leap on the same player in the same instant hits for about 600–760k.

## How to tell

Apply these to a Skyward Leap death in this order:

- Another holder's leap hit them (`clipped_by` is set): a clip or an overlap. Fault is by position, below.
- Over 150,000 with nobody else's leap on them: they took a second leap whose own holder was already dead. Pull 68 Kiara Blaiddyd is that case. Only she and Kitana Kahn were alive for three leaps. "Earlier deaths" owns it.
- Already under 15,000 HP on a 59–70k hit: low. The leap was the normal one.
- HP below their max: not fully healed. The healers own it. Pull 13 Kiara Blaiddyd was at 36,457 of 68,662. Pull 18 Kiara was at 51,175.
- At full HP: mitigation was not enough. The players who were supposed to mitigate this leap own it. Name the mit the packet is missing. Do not invent the cooldown plan. Pull 68 Kitana Kahn was at 61,737 of 61,737, multiplier 1.00, no shield.

## Position

`spots` on `skyward-leap` sets the check. Angles are from the arena center, with Thordan at 0. The spots are at the edge, 20 yalms out, at 97 degrees each side and at 180. A holder is on their spot within 3 yalms. Anyone else is in position when they are farther than 24 yalms from every spot, so no correct leap reaches them.

Positions come from `positions/fight-NN.json` when the leap landed. With no positions, or no Thordan sample, the old rule stands: the holder owns it.

The data puts the side spots about 7 degrees past square, away from Thordan. Of the 350 leaps that hit nobody else, 98% landed within 3 yalms of a spot.

## Fault

Not fully healed: the healers. `{player}` was short of full HP. That is a healer mistake even when the hit also had light mitigation.

Missing mitigation: `{player}` was fully healed and the leap still killed. Whoever was supposed to mitigate it, and did not, owns the death.

Clip: someone's leap hit `{player}`, who does not hold a marker. They die to the vulnerability on the next hit, Dragon's Rage or Holy Shield Bash, or to the leap itself. Whoever was out of position owns it:

- The holder off their spot, the player in position: the holder at 100. Pull 4 of `8DYNHQx4C7ytdLb9`: Spring Nymphar stood at 68 degrees and the leap hit the stack. Speed Panda, Kiara Blaiddyd, and Kitana Kahn died to Dragon's Rage, and Absolute Gigachad died to Holy Shield Bash. All four are Spring's.
- The holder on their spot, the player out of position: the player at 100. They stood in a placed leap. Pull 59 of `XVz8bCqgPw1KRh9d`: Absolute Gigachad stood in Spring Nymphar's leap.
- Both off: 50 each.

Overlap: two holders hit each other. The holder off their spot owns both deaths at 100. Pull 59 of `XVz8bCqgPw1KRh9d`: Kitana Kahn was 15.5 yalms out instead of 20, and her leap and Kiara Blaiddyd's hit each other. Both deaths are Kitana's. Pull 21: Loki Doki stood 7.8 yalms out on the opposite spot, and his leap reached Kitana and Kite Noodle. All three deaths are Loki's. When both holders are off their spots, it is 50 each.

A marker holder who dies with only the vulnerability from their own leap keeps it at 100.

Each leap is one packet per knight. It lands on its targets nearest the center first, so the first target in the packet, the `calculateddamage` row included, is the marker holder. When most of the non-tanks are already dead, a tank can hold a marker. When a holder is dead, their leap lands on someone who is already first in another packet. `marker_owns_clip` on `skyward-leap` turns the clip on.

## Parameters

One cast, about 59–60 seconds, with the stack and the tethers. 50 casts. 41 of them are three bodies, the non-tanks outside the Dragon's Rage stack. Those hits, when people live them, are 59–70k. That is the marker.

Every 600–760k hit in these logs is in a leap packet, at the same instant as the markers, on a player who was already hit by another leap. None of them is a tower. The Strength towers resolve later, about 63 seconds, and are not this guid.
