---
name: dsr-shining-blade
description: >-
  Identify Shining Blade (guid 25570) deaths in Dragonsong's Reprise Thordan.
  Hits that kill are the failed cleave. Use when the killing blow is Shining
  Blade or 25570.
---

# Shining Blade

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `shining-blade` in `fights/dsr/mechanics.json`. Guid `25570`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`), the paladin dash. Bright Flare `25295` is the orbs from the same dash.

Hits that kill are the failed cleave. A clean resolution of this mechanic deals no killing blow of this guid.

## How to tell

Any damage from this guid is a fail. It is not a raidwide with a raw band.

## Fault

`{player}` took the failed Shining Blade cleave.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast, including resolves that dealt no hit of this guid. The current parameter is `any_hit_is_fail`: a killing hit is the failed cleave, not a raidwide band. Confirm that no lived cluster exists before keeping it. The player who is hit owns the mistake.
