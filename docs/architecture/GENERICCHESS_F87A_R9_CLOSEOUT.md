# GenericChess F87A-R9 Western Dynamic Discovery Closeout

- Baseline: `178b06b04e1ee47f03fe12688ca6067e75721135`
- Scope: a small ruleset-agnostic dynamic terminal-discovery control after the R8 witness.
- Policy: existing `canonical_common_tape_random`, with three fixed seeds, one role-swapped pair per seed, and a 256-ply horizon.
- Prohibited: Western-specific opening, hand-authored mate tape, external engine, training, Arena, and Heavy.

## Result

The production semantic runtime discovered one `checkmate` in six role-swapped
games across seeds `9011`, `9012`, and `9013`; the other five trajectories
reached the bounded 256-ply horizon and were reported as `CENSORED`. The policy
uses only canonical legal-action ordering and seeded common tapes, so this is
dynamic discovery evidence rather than the R8 solution tape.

This is not a dynamic viability PASS: five of six trajectories were censored.
The result narrows the Western blocker to reproducible bounded coverage, but it
does not authorize training, promotion, or changing the qualification status
from `DEFER`.

## Evidence

- Manifest SHA-256: `00a8b4978c57afa0aebcf06069a0bd69d5e144ad786922c1238eee3dcb6626be`
- Results SHA-256: `a22b36b16992a97156b2e332b32db28dab2e361e4636fc498bf12aff58be8a31`

R9 is a bounded negative/positive mixed calibration: terminal discovery is now
observed under a generic policy, while full viability remains deferred.
