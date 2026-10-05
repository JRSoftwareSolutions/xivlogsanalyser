---
name: dsr-bright-flare
description: >-
  Identify Bright Flare (guid 25295) deaths in Dragonsong's Reprise Thordan:
  one orb versus an overlap, and whose fault it was. Use when the killing
  blow is Bright Flare or 25295.
---

# Bright Flare

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `bright-flare` in `fights/dsr/mechanics.json`. Guid `25295`. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). These are the orbs dropped by the Shining Blade dashes.

One orb is about 64k. The role cap is 85,000.

## How to tell

- At or under the cap: one orb. A death is raw, or low if they were already under 15,000 HP. The reference low case is about 12k HP on a normal orb.
- Over the cap: orbs overlapped.

## Fault

Fail: `{player}` overlapped Bright Flare.

Raw: one orb, and the resolve lost. Name the shield, the mit, and the HP.

Low: one orb, and they were already under 15,000 HP.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast. Record bodies per orb burst and the unmitigated band of single orbs people lived (currently about 64k, cap 85,000) versus overlaps over that cap. Who soaks which orb is not confirmed. A death on one orb under 15,000 HP is low.
