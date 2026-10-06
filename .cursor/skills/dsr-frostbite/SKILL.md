---
name: dsr-frostbite
description: >-
  Identify Frostbite (guid 1002946) deaths in Dragonsong's Reprise Thordan.
  Frostbite is the failed ice soak, not a Hiemal Storm share. Use when the
  killing blow is Frostbite or 1002946.
---

# Frostbite

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `frostbite` in `fights/dsr/mechanics.json`. Guid `1002946`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). The session stop is Meteors. It is the tick from standing in a Hiemal Storm puddle.

Frostbite is the tick from a failed ice soak. Hiemal Storm `25575` is the placed ice damage and is judged with `dsr-hiemal-storm`.

## How to tell

Any Frostbite damage is a fail. Do not read it as a large Hiemal share or a short stack.

## Fault

`{player}` failed the ice soak and died to Frostbite.

## Parameters

Follow `analyze-mechanic-parameters`. Walked on `8DYNHQx4C7ytdLb9`, separate from Hiemal Storm `25575`. The ticks sit about 134–137 seconds, around 49–63k, after the placed ice. Pull 5 has one lived tick, and it is still a failed soak. There is no correct Frostbite band. The player who is hit failed to run out of the ice.
