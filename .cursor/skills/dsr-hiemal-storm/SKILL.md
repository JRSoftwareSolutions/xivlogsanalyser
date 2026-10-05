---
name: dsr-hiemal-storm
description: >-
  Identify Hiemal Storm (guid 25575) deaths in Dragonsong's Reprise Thordan.
  Placed ice does not split like a stack; deaths are failed soaks. Use when
  the killing blow is Hiemal Storm or 25575. Frostbite 1002946 is a different
  skill.
---

# Hiemal Storm

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `hiemal-storm` in `fights/dsr/mechanics.json`. Guid `25575`. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). The session stop is Meteors. Four players of one role are marked; each circle is shared by a pair and applies Ice Resistance Down II. Frostbite is the puddle left behind.

A placed ice hit is about 25–40k. It does not split like a stack. A larger hit is not a short share.

## How to tell

- At or under the role cap: the placed ice. A death on that hit is raw, or low if they were already under 15,000 HP. The reference log has no death in this band.
- Over the role cap: a failed soak. Every Hiemal death in the reference log is this case. The smallest fatal hit is about 104k.
- The 114k versus 76k gap on pull 49 is two failed hits, not a stack with missing bodies.

Frostbite `1002946` is the failed-ice tick. Judge that with `dsr-frostbite`, not as a big Hiemal share.

## Fault

Fail: `{player}` failed the Hiemal Storm soak.

Raw, if a future log has a placed hit inside the cap: the resolve, not the placement.

## Parameters

Follow `analyze-mechanic-parameters`. Not walked in cast order yet. Survey every cast, including hits people lived. Record bodies per cast and the unmitigated band of placed hits. The current parameter is that this does not split like a stack: the 114k versus 76k gap on pull 49 is not missing bodies. Deaths in the reference log start around 104k and are fails. Frostbite `1002946` is a separate parameter set (`dsr-frostbite`). Who is assigned to each puddle is not confirmed.
