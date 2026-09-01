# ADR-105 — F38 activity and anchor-control evaluator prototype

- Status: H38A protocol frozen
- Date: 2026-09-01
- Work order: `GENERICCHESS-F38-ACTIVITY-AND-ANCHOR-CONTROL-EVALUATOR-PROTOTYPE`

## Decision

Freeze the independent holdout-selection protocol before any R37C candidate
scoring. H38A replays the already-frozen F30 R1 paired transcript in canonical
game/event order and selects the first AlphaSho board/drop action per game that
is legal, ongoing, 8–64 additional plies from the imported root, outside all
F37 ten-root/direct-child states, and not a duplicate selected canonical state.

Selection records provenance, exact replay state, state hash, played move, and a
legality witness. It never reads evaluator scores/ranks and never invokes
AlphaSho. The resulting descriptor contains 20 unique positions and meets the
minimum of 16.

## Authority and safety

The H38A manifest binds the actual SHA-256 identities of F37 first-pass/R1
evidence, F36 selection, F30 R1 paired/fresh evidence, the F25 ten-root
descriptor, and the production evaluator/profile/config sources. R37C is fixed
as the selected F37 candidate; no tuning from results is permitted; the
external holdout is validation data only; production diff is zero.

Only after this protocol-freeze checkpoint is published may H38B create
prototype identity, holdout ranking, search, cost, and selection evidence.
F38 remains audit/prototype-only and does not modify production evaluator or
search code.
