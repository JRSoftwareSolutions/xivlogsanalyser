---
name: dsr-dragons-gaze
description: >-
  Identify Dragon's Gaze (guid 25553) deaths in Dragonsong's Reprise Thordan.
  A successful gaze deals 0; any hit means they looked. Use when the killing
  blow is Dragon's Gaze or 25553. Dragon's Glory 25554 is a different cast.
---

# Dragon's Gaze

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `dragons-gaze` in `fights/dsr/mechanics.json`. Guid `25553`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). It resolves together with Dragon's Glory and inflicts Hysteria.

A successful gaze deals 0. A hit is about 40–45k.

## How to tell

Any damage from this guid is a fail. Name this cast Dragon's Gaze. Dragon's Glory is guid `25554` and is a different cast (`dsr-dragons-glory`).

## Fault

`{player}` looked at Dragon's Gaze.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey casts separately from Dragon's Glory `25554`. Record time in the phase and whether successful resolves deal 0. The current parameter is `any_hit_is_fail`, with a looked-at hit about 40–45k. The player who is hit owns the mistake.
