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

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey this guid separately from Hiemal Storm `25575`. The current parameter is `any_hit_is_fail`: Frostbite is the failed-ice tick, not a large Hiemal share. Confirm the casts sit on failed soaks and that no lived Frostbite band exists. The player who dies to it failed the ice soak.
