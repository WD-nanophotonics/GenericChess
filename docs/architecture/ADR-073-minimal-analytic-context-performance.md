# ADR-073: minimal analytic context performance probe

## Status

F23Y is complete as a bounded audit-only performance experiment. Its semantic
and mathematical parity gates passed, but the fixed-time performance gates and
the valid 2048-node quality gate failed. The selected boundary is
`F23Z_EVALUATOR_REPRESENTATION_REASSESSMENT`.

## Corrected F23X interpretation

F23X R1 established executable local semantic direction evidence, subject to
the two preflight checks closed here. Its 2048-node real-game quality result
was previously not evaluable when the candidate timed out; fixed-time
implementation performance failed; playing-strength evidence was not run.
F23Y does not treat the incomplete F23X 2048 moves as a quality regression.

## Scope and invariants

The five concepts, coefficients `[1,1,1,1,1]`, and score form
`S * sum(feature_i)` were frozen. P0 is the unchanged F23X-R1 context shape.
P1 is one audit-only context design: it builds the static profile once, scans
inventory/anchors once, enumerates legal actions once per owner, classifies
captures/promotions/drops in those passes, and builds one exact bulk attack set
per owner for reuse by mobility, check, safety, and exposure. No production
evaluator, search, Native, rule, workflow, or governance code changed.

## Preflight evidence

The frozen M9 before/after pair contains zero legal promotions before and one
legal promotion after. The selected action is an actual `P` to `G` promotion,
the rule-derived `promotion_gain_by_type[P]` is `635` (positive), and the
measured capability feature delta is `0.40875`.

All ten metamorphic contracts were rerun with actual states. A deterministic
bijective type-ID renaming was applied to each actual before/after RuleSet and
state pair, preserving movement, promotion, drops, capture disposition, and
history action targets. All 10 contracts and 14 variants passed before/after
vector, target delta, and score invariance.

The frozen microbenchmark contains all ten F22 Standard Shogi roots, the
available deterministic legal-child sample (none were available from these
root side-to-move positions), and the eight F23X/R1 generic audit states: 48
states total. The exact descriptor list is stored in the fixture under the
SHA-256 `1d5797b6f9c0284d61961b9cb144bd45cea828b572c785162989dc472804fe9c`.

## P1 semantic and mathematics parity

Bulk attack parity compared every square and both owners against
`SemanticEngine.is_square_attacked()` with zero mismatches. Bulk-derived anchor
check matched `SemanticEngine.in_check()` for every owner/state. Cached legal
actions matched the current semantic action set and order. P1 reproduced all
five P0 feature components, total scores, and the ten metamorphic deltas within
`1e-12` across the 48-state set.

The environment attempted the same Native provider policy for both paths and
recorded `PYTHON_AUTHORITY_FALLBACK`; Native was not forced off. v1 harness
parity passed 10/10 at 512 nodes.

## Cost evidence

On the frozen set with five measurements per state, P0 median evaluate time was
approximately 38.3 ms (p95 53.1 ms), P1 was approximately 12.9 ms (p95 19.1
ms), and production v1 was approximately 0.510 ms (p95 0.647 ms). P1/P0
median speedup was approximately 2.97x.

P1 bulk attack and safety work became small relative to legal-action
enumeration; feature aggregation remained negligible. For the Standard Shogi
portion, P1's 200 calls accumulated about 2.42 s in owner legal-action passes,
0.174 s in bulk attack traversal, 0.015 s in classification, and 0.008 s in
attack/check/safety work, with one profile build. This attributes the remaining
cost to dynamic semantic legal-action construction rather than the linear
five-term sum itself.

## Search evidence and boundary

The fixed-time matrix contains 120 runs: 0.25 s and 1.0 s, three repetitions,
ten F22 positions, both evaluators, and alternating order. The authoritative
paired candidate/v1 median NPS ratios were approximately `0.161` and `0.263`;
candidate evaluator-time fractions were approximately `0.844` and `0.865`.
The strict `<=0.25` fraction and `>=0.65` paired-NPS gates failed.

Both v1 and P1 completed the 128, 512, and 2048 fixed-node matrices. Root-rank
instrumentation was unavailable and remains explicitly
`ROOT_RANK_HARNESS_UNAVAILABLE`. At 2048, candidate top-1 minus v1 top-1 was
`-1`; one valid frozen control regressed, so the primary quality gate failed.
No AlphaSho outcome was used for selection, and playing-strength evidence was
not run.

The performance stop rule therefore selects
`F23Z_EVALUATOR_REPRESENTATION_REASSESSMENT`. Do not start another context
optimization generation automatically, add features, tune coefficients, or
route production through P1. The F23X first-pass and R1 artifacts remain
byte-identical. Historical F23W bookkeeping remains 13 criteria, maximum 65,
with totals 60/46/35/23.
