---
name: dsr-hiemal-storm
description: >-
  Identify Hiemal Storm (guid 25575) deaths in Dragonsong's Reprise Thordan.
  Placed ice does not split like a stack; a failed soak is a fail. Use when
  the killing blow is Hiemal Storm or 25575. Frostbite 1002946 is a different
  skill.
---

# Hiemal Storm

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `hiemal-storm` in `fights/dsr/mechanics.json`. Guid `25575`. Part of Sanctity of the Ward (`dsr-sanctity-of-the-ward`). The session stop is Meteors. Four players of one role are marked; each circle is shared by a pair and applies Ice Resistance Down II. A pair is one support, tank or healer, and one DPS (`pairs`). Frostbite is the puddle left behind.

A placed ice hit is the pair share. Tanks take about 14–25k. Healers take about 23–38k. DPS take about 26–40k. It does not split further. A larger hit is not a short share. A puddle that completely covers a tower is a wrong drop.

## How to tell

- At or under the role cap: the placed ice. A death on that hit is raw, or low if they were already under 15,000 HP. The reference log has no death in this band. `8DYNHQx4C7ytdLb9` pulls 17 and 45 are raw: a normal hit on a player who was not full.
- Over the role cap: a failed soak. Every Hiemal death in the reference log is this case. The smallest fatal hit is about 104k.
- An ice that hit only one player had no partner. That is a fail, owned by the partners from the other side who were dead, passed on, alive and in no circle, or doubled up in another circle. Transcendent `1000418` counts as dead. Reference pull 15 is Kitana Kahn's ice: Absolute Gigalad and Loki Doki doubled up in another one.
- The 114k versus 76k gap on pull 49 is two failed hits, not a stack with missing bodies. The 76k tank hit was lived and sits above the placed band. The tank cap is 50,000 so that hit is not the real share.

Frostbite `1002946` is the failed-ice tick. Judge that with `dsr-frostbite`, not as a big Hiemal share.

## Fault

Fail: `{player}` failed the Hiemal Storm soak.

Fail, no partner: the ice had no partner because `{partners}` were dead, in no circle, or in another one. They own it, split evenly.

Raw, a placed hit inside the cap: the resolve, not the placement.

## Parameters

Follow `analyze-mechanic-parameters`. Walked on `8DYNHQx4C7ytdLb9`. One cast about 130–131 seconds, eight players, multiplier 1.00, usually a shield. The placed band is the lived hits above. It does not split like a stack. The 76k tank hit on reference pull 49 is outside that band. Deaths in the reference log start around 104k and are fails. Frostbite `1002946` is a separate parameter set (`dsr-frostbite`). The ice drops on supports or on DPS. Everyone runs out. A puddle that covers a tower is a wrong drop.
