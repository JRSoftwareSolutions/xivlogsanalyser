---
name: dsr-dimensional-collapse
description: >-
  Identify Dimensional Collapse (guid 25564) deaths in Dragonsong's Reprise
  Thordan. No lived baseline is stored, so any hit stays a fail and out of
  the raw count. Use when the killing blow is Dimensional Collapse or 25564.
---

# Dimensional Collapse

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `dimensional-collapse` in `fights/dsr/mechanics.json`. Guid `25564`. `any_hit_is_fail` is true. The wiki's Strength of the Ward puddle is Dimensional Slash. This death guid is Dimensional Collapse. Treat them as the same component only after the person says so (`dsr-strength-of-the-ward`).

No lived sample is stored. The reference log has one death, about 50k, on pull 29. It stays out of the 187 raw deaths. That exclusion is unsettled, not a proven raw band.

## How to tell

Any hit is a fail until a lived baseline is written into `mechanics.json` on purpose. A hit near 50k is still a fail. Survivable-looking damage is not a raw call without a lived sample.

## Fault

`{player}` took Dimensional Collapse. With no baseline, the hit is a fail.

Adding a lived band is a correction: update `mechanics.json`, this skill, and `notes/classification.md`, then `python -m xivloganalyzer reanalyze`. Update `tests/test_reference.py` only when the 187 raw deaths on `XVz8bCqgPw1KRh9d` are meant to change.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast before replacing `any_hit_is_fail`. The reference log has one death, about 50k, on pull 29, and no lived sample. That death stays out of the raw count until the survey finds hits people lived and the band is written down on purpose.
