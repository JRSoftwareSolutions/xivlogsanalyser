---
name: dsr-holy-shield-bash
description: >-
  Identify Holy Shield Bash (guid 25297) deaths in Dragonsong's Reprise
  Thordan. Tanks take one tether each. A non-tank hit or a short tether is
  the failed bash. Use when the killing blow is Holy Shield Bash or 25297.
---

# Holy Shield Bash

Follow `review-mechanic` for the packet, the outcome order, and a correction. Follow `analyze-mechanic-parameters` when changing these parameters. Entry `holy-shield-bash` in `fights/dsr/mechanics.json`. Guid `25297`. `any_hit_is_fail` is true. `tanks_only` is true. Part of Strength of the Ward (`dsr-strength-of-the-ward`). The cone after this dash is Holy Bladedance.

## Parameters

About 60 seconds into phase 2, as the second Heavy Impact pulse goes off. Two of the three knights that drop spawn a tether. Each tank takes one. The hit stuns. A non-tank who takes that stun dies. They stretch the tether and use personal mitigation. The hit gets smaller as the tether gets longer.

46 casts. 40 of them hit exactly two tanks. A stretched hit in this log is often amount 0: multiplier about 0.37–0.65 and a shield that covers it. Unmitigated is missing on those, so there is no lived band to promote into a raw cap. `any_hit_is_fail` stays.

A non-tank hit is theirs. The stun kills them. Pull 30, Kitana Kahn, 4,228,180. Pull 36, Loki Doki, 4,126,915. Both had Physical Vulnerability Up.

A short tether is the failed bash: hundreds of thousands to about 1.1 million, with Physical Vulnerability Up. The tank deaths in this log are that shape, and they already had personal mitigation on the packet. The vuln is the failed tether, not a missing Rampart. When that vuln came from someone else's Skyward Leap that clipped the tank, whoever was out of position owns the death (`dsr-skyward-leap`, clip).

## How to tell

- No death, two tanks, the hit absorbed: the tethers were stretched.
- A non-tank: fail. They took a tether.
- Hundreds of thousands to millions, or Physical Vulnerability Up: fail. The tether was short.
- Do not call a death raw from a smaller number until a lived unmitigated band is written down on purpose.

## Fault

`{player}` is not a tank: they took the Holy Shield Bash stun. Only a tank takes this tether, and the stun kills anyone else.

`{player}` is a tank and the hit is huge or has vulnerability: the tether was short. Personal mitigation was on the packet and the hit was still the failed bash.
