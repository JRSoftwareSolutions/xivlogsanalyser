---
name: dsr-holy-impact
description: >-
  Identify Holy Impact (guid 25578) deaths in Dragonsong's Reprise Thordan.
  It is the comet overlap, and the prey players own it. Use when the killing
  blow is Holy Impact or 25578.
---

# Holy Impact

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `holy-impact` in `fights/dsr/mechanics.json`. Guid `25578`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). The session stop is Meteors.

The prey players drop Holy Comet `25577`. When two of those comets land too close, this explosion hits the party and puts Damage Down on everyone. The two prey players own it.

## How to tell

Any damage from this guid is a fail. A clean resolve stores none. Report `8DYNHQx4C7ytdLb9` has it on 10 of the 31 pulls that reached Sanctity, and not on the pulls that cleared the comets.

The explosion is tanks about 57–66k and everyone else about 91–106k. It does not scale with stack size. A tank is sometimes hit twice. Missing bodies do not explain it. Damage Down is what the explosion applies. The killing packet in these logs often has empty `buffs`, so the guid itself is the fail, not an amp check.

A player already under 15,000 HP still died to the overlap.

## Fault

The two prey players dropped the comets too close. `{player}` died to the explosion. The packet does not name the prey markers, so the blame is Prey markers.

## Parameters

Follow `analyze-mechanic-parameters`. Surveyed on `8DYNHQx4C7ytdLb9`. No one lived this cast. The numbers above are the explosion, not a lived band. Holy Comet is the light raidwide from a correct drop (`dsr-holy-comet`).
