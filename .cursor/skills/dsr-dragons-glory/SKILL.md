---
name: dsr-dragons-glory
description: >-
  Identify Dragon's Glory (guid 25554) deaths in Dragonsong's Reprise Thordan.
  A successful gaze deals 0; any hit means they looked. Use when the killing
  blow is Dragon's Glory or 25554. Dragon's Gaze 25553 is a different cast.
---

# Dragon's Glory

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `dragons-glory` in `fights/dsr/mechanics.json`. Guid `25554`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). It is the eye's gaze and resolves together with Dragon's Gaze.

A successful gaze deals 0. A hit is about 40–45k.

## How to tell

Any damage from this guid is a fail. Name this cast Dragon's Glory. Dragon's Gaze is guid `25553` and is a different cast (`dsr-dragons-gaze`).

## Fault

`{player}` looked at Dragon's Glory.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey casts separately from Dragon's Gaze `25553`. Record time in the phase and whether successful resolves deal 0. The current parameter is `any_hit_is_fail`, with a looked-at hit about 40–45k. The player who is hit owns the mistake.
