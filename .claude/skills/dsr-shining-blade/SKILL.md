---
name: dsr-shining-blade
description: >-
  Identify Shining Blade (guid 25570) deaths in Dragonsong's Reprise Thordan.
  Hits that kill are the failed cleave. Use when the killing blow is Shining
  Blade or 25570.
---

# Shining Blade

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `shining-blade` in `fights/dsr/mechanics.json`. Guid `25570`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`), the paladin dash. Bright Flare `25295` is the orbs from the same dash.

The two knights dash in an hourglass. Hits that connect are the failed cleave. A clean resolution stores none of this guid. A player in Hysteria from a gaze was carried into the dash. These packets do not show Hysteria, so the death stays this hit.

## How to tell

Any damage from this guid is a fail. It is not a raidwide with a raw band.

## Fault

`{player}` took the failed Shining Blade cleave.

## Parameters

Follow `analyze-mechanic-parameters`. Walked on `8DYNHQx4C7ytdLb9`. Thirty of 31 Sanctity pulls store no hit. Pull 17 is one DPS death, about 3.7 million. There is no lived cluster. The player who is hit owns the mistake.
