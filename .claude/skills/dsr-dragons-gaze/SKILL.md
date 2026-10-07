---
name: dsr-dragons-gaze
description: >-
  Identify Dragon's Gaze (guid 25553) deaths in Dragonsong's Reprise Thordan.
  A successful gaze deals 0; any hit means they looked. Use when the killing
  blow is Dragon's Gaze or 25553. Dragon's Glory 25554 is a different cast.
---

# Dragon's Gaze

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `dragons-gaze` in `fights/dsr/mechanics.json`. Guid `25553`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). It resolves together with Dragon's Glory and inflicts Hysteria.

A successful gaze deals 0, and the log still stores that 0 on each player. A hit is about 40–44k and applies Hysteria. Hysteria makes them run, sometimes into the wall or into a dash or an orb. That later hit is still their look when the packet shows Hysteria. These later packets do not show it.

## How to tell

Any damage from this guid is a fail. Name this cast Dragon's Gaze. Dragon's Glory is guid `25554` and is a different cast (`dsr-dragons-glory`).

## Fault

`{player}` looked at Dragon's Gaze.

## Parameters

Follow `analyze-mechanic-parameters`. Walked on `8DYNHQx4C7ytdLb9`, separate from Dragon's Glory `25554`. About 112–113 seconds, all eight players, amount 0 on a clean look. Pull 17 Kiara is the looked-at hit, 43,670 unmitigated. The player who is hit owns the mistake.
