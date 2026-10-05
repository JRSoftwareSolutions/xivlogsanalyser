---
name: dsr-holy-shield-bash
description: >-
  Identify Holy Shield Bash (guid 25297) deaths in Dragonsong's Reprise
  Thordan. Killing hits are the failed bash, hundreds of thousands to
  millions. Use when the killing blow is Holy Shield Bash or 25297.
---

# Holy Shield Bash

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `holy-shield-bash` in `fights/dsr/mechanics.json`. Guid `25297`. `any_hit_is_fail` is true. Part of Strength of the Ward (`dsr-strength-of-the-ward`). The tether hit gets smaller as the tether gets longer.

Hits that kill are the failed bash: hundreds of thousands to millions. A lived baseline for a successful bash is not stored.

## How to tell

Any damage from this guid is a fail. Do not invent a raw band from a smaller number until a lived sample is added to `mechanics.json` on purpose.

## Fault

`{player}` took the failed Holy Shield Bash.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast before adding a lived band. Killing hits are hundreds of thousands to millions, and `any_hit_is_fail` stays until a lived sample is written down on purpose. Who is allowed to be hit is not confirmed.
