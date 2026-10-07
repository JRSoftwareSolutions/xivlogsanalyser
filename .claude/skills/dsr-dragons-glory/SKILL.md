---
name: dsr-dragons-glory
description: >-
  Identify Dragon's Glory (guid 25554) deaths in Dragonsong's Reprise Thordan.
  A successful gaze deals 0; any hit means they looked. Use when the killing
  blow is Dragon's Glory or 25554. Dragon's Gaze 25553 is a different cast.
---

# Dragon's Glory

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `dragons-glory` in `fights/dsr/mechanics.json`. Guid `25554`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). It is the eye's gaze and resolves together with Dragon's Gaze.

A successful gaze deals 0, and the log still stores that 0 on each player. A hit is about 40k and applies Hysteria. Hysteria makes them run, sometimes into the wall or into a dash or an orb. That later hit is still their look when the packet shows Hysteria. These later packets do not show it.

## How to tell

Any damage from this guid is a fail. Name this cast Dragon's Glory. Dragon's Gaze is guid `25553` and is a different cast (`dsr-dragons-gaze`).

## Fault

`{player}` looked at Dragon's Glory.

## Parameters

Follow `analyze-mechanic-parameters`. Walked on `8DYNHQx4C7ytdLb9`, separate from Dragon's Gaze `25553`. About 112–113 seconds, all eight players, amount 0 on a clean look. Pull 48 Kitana is the looked-at hit, 39,587 unmitigated. The player who is hit owns the mistake.
