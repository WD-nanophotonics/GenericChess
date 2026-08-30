# ADR-071: minimal analytic evaluator metamorphic and Shogi shadow

## Status

F23X completed as an audit-only experiment. Phase A passed; Phase B ran and
failed its pre-registered quality/performance gates. The next boundary is
`F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT`.

## Scope and invariants

F23X preserved the five-concept hypothesis:

- material and inventory;
- safe mobility and control;
- attack, defense, and anchor safety;
- forcing capture and recapture;
- capability-gated promotion and drop.

The coefficient vector remained `[1,1,1,1,1]` and the score form remained
`S * sum(feature_i)`. There was no coefficient fitting, self-play/TD code,
game-name branch, concrete-piece scoring table, or production evaluator,
search, Native, rules, workflow, or governance change.

## Phase A: semantic contract evidence

The audit executed exactly the ten pre-registered F23W metamorphic contracts,
two for each feature family. Every contract recorded an intervention witness,
preserved comparison conditions, a strict-positive variant, and a
renamed-equivalent execution. Coverage included capture-to-hand,
remove-from-game, drop, promotion, history-sensitive recapture, and mixed
mechanics. All 10/10 passed.

An audit-only immutable `EvaluationContextAudit` computed shared semantic
facts: per-side legal actions, captures, promotions, drops, attack/check
facts, anchor locations/safety, recent-action target, inventory, and the
RuleSet-derived profile. Five context consumers used those facts. On eight
non-terminal fixed audit states, the context candidate matched the corrected
F23V-R1 five-feature vector and total score within `1e-12`. Type-ID renaming
invariance and the complexity audit passed.

This is `SEMANTIC_CONTRACT_EVIDENCE`, not an Elo or optimal-play claim.

## Phase B: real-game benchmark evidence

The experiment read the ten frozen F22 Standard Shogi positions and reference
moves from commit
`3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38`. Candidate and production
evaluator-v1 used identical unchanged search, legality/runtime, TT, move
ordering, and quiescence settings. The v1 harness parity control passed on
all ten positions at 512 nodes.

Fixed-node budgets were 128/512/2048. Each evaluator ran once per position
and budget (60 runs total). A 3-second safety cap was used only to prevent a
pathological semantic search from occupying the workflow indefinitely; a
run that hit that cap was recorded as not completing its declared node
budget. Candidate runs did not complete the declared node budgets; at the
2048 diagnostic, v1 top-1 agreement was 2/10 and candidate was 1/10. The
candidate therefore had a top-1 delta of -1 and both preserved agreement
controls regressed. Full reference rank was not inferred from selected move;
the unchanged search API exposed only the selected completed root result, so
the mean-rank gate was recorded as not computed.

Fixed-time budgets were 0.25s and 1.0s, with three repetitions for every
position/evaluator/budget: 120 runs total. Candidate median evaluator-time
fraction was approximately 98.2% and 98.9%; candidate median NPS was only
approximately 0.33% and 0.49% of v1. Both independent performance gates
failed.

These are `REAL_GAME_BENCHMARK_EVIDENCE`; `PLAYING_STRENGTH_EVIDENCE` was
not run. The result does not justify production routing or an Elo claim.

## Decision

F23X Phase A establishes that the five concepts can satisfy the declared
local semantic contracts and can be computed through an audit-only shared
read-only pass. Phase B does not establish useful real-game decision quality
and exposes unacceptable candidate runtime cost. Select
`F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT`; do not add features or tune
coefficients from this result.

The historical F23V/F23W artifacts remain byte-identical. F23W strategy
bookkeeping remains historical at 13 criteria, maximum 65, and totals
60/46/35/23.
