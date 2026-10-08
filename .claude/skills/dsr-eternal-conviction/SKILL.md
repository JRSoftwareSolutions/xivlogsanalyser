---
name: dsr-eternal-conviction
description: >-
  Identify Eternal Conviction (guid 25568) deaths in Dragonsong's Reprise
  Thordan: the empty Strength tower or the empty Sanctity tower, and whose
  fault it was. Use when the killing blow is Eternal Conviction or 25568.
---

# Eternal Conviction

Follow `review-mechanic` for the packet, the outcome order, and a correction. Entry `eternal-conviction` in `fights/dsr/mechanics.json`. Guid `25568`. Hits around 63–66s are the Strength of the Ward stop (`dsr-strength-of-the-ward`). Hits around 137s and around 150s are the Meteors stop (`dsr-sanctity-of-the-ward`). Every hit is the explosion of an empty tower.

## How to tell

- Around 63–66 seconds, about two seconds after Conviction `25567`: a Strength tower was empty. The six towers are soaked by the healers and DPS. It is not a raidwide. The person: "it sounds like a tower explosion. if it caused a damage down or other debuff it's probably cos someone didn't soak a tower".
- Around 137 seconds, about two seconds after Conviction `29564`: the first towers were empty. This does not land when those towers are soaked correctly.
- Around 150 seconds, about two seconds after Conviction `28651`: the eight outer towers were empty. Same explosion. A clean resolve of either tower set stores no `25568`.

Eight small Conviction hits can still be followed by this explosion. That is two players in one tower and another tower empty. Pull 19 and pull 29 of `8DYNHQx4C7ytdLb9` are that case.

The Sanctity explosion is tanks about 58–66k and everyone else about 90–105k. The Strength one is tanks about 61–67k and everyone else about 86–108k. It does not scale with stack size. It is still a mistake. A player already under 15,000 HP died to the explosion, not to a normal raidwide.

## Fault

Every hit is a fail: a tower was empty. `{player}` died to the explosion. The players who missed the tower own it. `needs_everyone` in `mechanics.json` names them from the tower soak in the four seconds before the first death. Before 100 seconds the soak is Conviction `25567`, and only healers and DPS are in it (`roles`). After 100 seconds it is Conviction `29564` or `28651`:

- A player already dead, and not raised (Weakness `1000043`), left their tower empty. They own it.
- A player alive and not hit by the soak was not in a tower. They own it.
- Two players on one tower's soak (the same `sourceInstance`) shared a tower. They own it. Pull 19 of `8DYNHQx4C7ytdLb9` is Spring Nymphar and Kiara Blaiddyd, and pull 29 is Loki Doki and Speed Panda.
- Several owners split it evenly. A dead player passes it on to whoever owned their death: their own mistake stays theirs, an earlier empty tower goes to whoever left that one empty, a raw death to the healers.
- Missed soak at 50 only when none of these shows in the log. When the soak's ability file was not fetched and nobody was dead, the judgment lists it in `missing`, such as `ability 25567`. `XVz8bCqgPw1KRh9d` and `8DYNHQx4C7ytdLb9` have no `25567` file.

## Parameters

Follow `analyze-mechanic-parameters`. The Strength cast lands only when a Strength tower was empty. Tanks live about 61–67k. Healers and DPS die at about 86–108k. A `moments` row with `until` 100 and `fail` true is that assignment, and the `needs_everyone` row with `until` 100 is its soak.

The Sanctity casts were walked on `8DYNHQx4C7ytdLb9`, 31 pulls that reached 105 seconds into phase 2. The explosion is absent on pulls that soak every tower, including the phase 3 clears 16, 26, 27, 30, 33, 36, 46, and 50. Where it lands, the party is hit and the non-tanks die. A `moments` row with `after` 100 and `fail` true is that assignment. The mechanic's own `should_have_been` is the empty tower.
