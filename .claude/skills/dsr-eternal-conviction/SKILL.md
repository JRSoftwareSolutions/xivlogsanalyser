---
name: dsr-eternal-conviction
description: >-
  Identify Eternal Conviction (guid 25568) deaths in Dragonsong's Reprise
  Thordan: the Strength raidwide versus the Sanctity empty tower, and whose
  fault it was. Use when the killing blow is Eternal Conviction or 25568.
---

# Eternal Conviction

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `eternal-conviction` in `fights/dsr/mechanics.json`. Guid `25568`. Hits around 63s are the Strength of the Ward stop. Hits around 137s and around 150s are the Meteors stop. The person assigned the later hits (`dsr-sanctity-of-the-ward`). The 63s hit is still unassigned.

## How to tell

- Around 63 seconds: the Strength raidwide. It does not scale with stack size. A full party of 8 still hits a DPS for about 97k of the same cast that hits a tank for about 64k. At or under the role cap, that is the real raidwide. Over the cap, or with Vulnerability or Damage Down, it is a failed hit. Missing bodies do not explain a larger hit.
- Around 137 seconds, about two seconds after Conviction `29564`: the first towers were empty. This does not land when those towers are soaked correctly.
- Around 150 seconds, about two seconds after Conviction `28651`: the eight outer towers were empty. Same explosion. A clean resolve of either tower set stores no `25568`.

Eight small Conviction hits can still be followed by this explosion. That is two players in one tower and another tower empty. Pull 19 and pull 29 of `8DYNHQx4C7ytdLb9` are that case.

The explosion is tanks about 58–66k and everyone else about 90–105k. It does not scale with stack size. It is still a mistake. A player already under 15,000 HP died to the explosion, not to a normal raidwide.

## Fault

Around 63 seconds, at or under the cap: the resolve. Name the shield, the mit, and the HP.

Around 63 seconds, over the cap: `{player}` took a hit that is not this raidwide. Do not call it a short stack.

Around 63 seconds, already under 15,000 HP, and the hit is the normal raidwide: low.

Around 137 or 150 seconds: a tower was empty. `{player}` died to the explosion. The players who missed the tower own it. The log does not name them from this packet, so the blame is Missed soak.

## Parameters

Follow `analyze-mechanic-parameters`. The 63-second cast was not walked again. Its parameter is unchanged: tanks about 61–67k lived, healers and DPS in the 90–108k death band of that same cast, and a full party of 8 still lands on the DPS band.

The Sanctity casts were walked on `8DYNHQx4C7ytdLb9`, 31 pulls that reached 105 seconds into phase 2. The explosion is absent on pulls that soak every tower, including the phase 3 clears 16, 26, 27, 30, 33, 36, 46, and 50. Where it lands, the party is hit and the non-tanks die. A `moments` row with `after` 100 and `fail` true is that assignment. The Strength line stays the mechanic's own `should_have_been`.
