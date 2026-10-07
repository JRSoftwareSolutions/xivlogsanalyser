---
name: dsr-holy-impact
description: >-
  Identify Holy Impact (guid 25578) deaths in Dragonsong's Reprise Thordan.
  It is two comets landing too close, and the prey players whose comets
  they were own it. Use when the killing blow is Holy Impact or 25578.
---

# Holy Impact

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `holy-impact` in `fights/dsr/mechanics.json`. Guid `25578`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). The session stop is Meteors.

## What happens

Two players get Prey (`1000562`) at about 122 seconds. From about 136 seconds each drops 7 Holy Comets (`25577`), one every 1.43 seconds, where they stood about a second before. Both run clockwise along the edge from their cardinal. Two comets that land under about 5 yalms apart explode about 2.1 seconds after the later one lands. That explosion is Holy Impact. Each explosion hits every living player twice, once from each comet. Non-tanks die to the first hit. Tanks die to the second.

It lands before the outer towers (`28651`, about 148 seconds). An empty outer tower is Eternal Conviction about 150 seconds, not Holy Impact (pulls 13, 20, and 35 of `8DYNHQx4C7ytdLb9`).

## How to tell whose comets

The Holy Comet actor's position samples are in `positions/fight-NN.json`. Each drop is a new spot. The explosion is a moment whose samples all sit on earlier drops. Chain the drops into one trail per prey player, and give each trail to the prey player standing nearest its first drop. `drops` on the mechanic sets the debuff, the actor, and the 1 yalm reach.

Every pair of comets under 4.97 yalms in the three saved reports exploded. No pair at 5.06 yalms or more ever did.

## Fault

- Both comets from one prey player: that player at 100. They slowed down or doubled back. Pull 24 of `8DYNHQx4C7ytdLb9`: Loki Doki's fourth and fifth comets, 4.7 yalms apart.
- One prey player's last comet on the other's first: both prey players at 50. Pull 53 of `8DYNHQx4C7ytdLb9`: Kite Noodle's seventh comet 3.6 yalms from Speed Panda's first. Starting 20–30 degrees off the cardinal is common on clean pulls, so the log cannot say which of the two ran too far.
- A prey player already dead and not raised: their comets pile up. The explosion passes on to whoever owned that death.
- Without comet samples, the prey players named from the debuff at 50 each. "Prey markers" only when the debuff is missing too.

A death earlier in the pull is not the cause unless that player held Prey.

## Parameters

Follow `analyze-mechanic-parameters`. Surveyed on `8DYNHQx4C7ytdLb9`. No one lived this cast. The explosion is tanks about 57–66k and everyone else about 91–106k. Holy Comet is the light raidwide from each drop (`dsr-holy-comet`).
