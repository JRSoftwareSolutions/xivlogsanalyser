---
name: dsr-bright-flare
description: >-
  Identify Bright Flare (guid 25295) deaths in Dragonsong's Reprise Thordan:
  one orb versus an overlap, and whose fault it was. Use when the killing
  blow is Bright Flare or 25295.
---

# Bright Flare

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `bright-flare` in `fights/dsr/mechanics.json`. Guid `25295`. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). These are the orbs dropped by the Shining Blade dashes.

`any_hit_is_fail` is true. A clean pull stores none.

## How to tell

Any damage from this guid is a fail. One orb is about 61–67k on a tank and about 93–111k on a healer or DPS, which kills a healer or DPS on its own. Each orb is one packet (`packetID`). Two players on one packet overlapped. Two players hit at the same moment by two packets were each hit by their own orb: reference pull 39. A player already under 15,000 HP still got hit. Pull 22 Gigalad in the reference log was that case, at about 12k HP, and it is a fail.

Anyone without Hysteria who is hit owns it. A player in Hysteria was carried there by the gaze. These packets do not show Hysteria, so the death stays this hit.

## Fault

One player: `{player}` got hit by Bright Flare.

Overlap: each player on that orb's packet, survivors included, named from the packet. Reference pull 34: Kite Noodle and Absolute Gigalad, who lived.

## Parameters

Follow `analyze-mechanic-parameters`. Walked on `8DYNHQx4C7ytdLb9` and the reference deaths. No clean pull stores this guid. One tank lived about 61k on pull 54 of the new log, and that hit is still a mistake. No personal mitigation is required because the orb is dodged.
