---
name: dsr-burns
description: >-
  Identify Burns (guid 1002945) deaths in Dragonsong's Reprise Thordan. Burns
  is the fire's damage over time from standing in the fire. Use when the
  killing blow is Burns or 1002945.
---

# Burns

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `burns` in `fights/dsr/mechanics.json`. Guid `1002945`. `any_hit_is_fail` is true. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). The session stop is Meteors.

Burns lands about 131 seconds, as the Heavens' Stake fire resolves, and ticks for up to 60 seconds. The deaths table links it as a status (`#status/1945`), not an action. It is a real killing blow, not the deathwall.

## How to tell

Any Burns damage is a fail. The ticks that kill are about 50–77k. Pull 35 of `8DYNHQx4C7ytdLb9` is Kiara Blaiddyd: Burns at 131.6 seconds, dead at 135.8.

## Fault

`{player}` stood in the fire and died to Burns.

A Burns death before the towers leaves a tower empty. That player owns the Eternal Conviction or Holy Impact that follows.

## Parameters

Not walked yet. The sample is the five Burns deaths in the saved reports. Heavens' Stake `28591` is the fire's direct hit and is judged with `dsr-heavens-stake`.
