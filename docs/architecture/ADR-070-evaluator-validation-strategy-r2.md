# ADR-070: layered evaluator validation strategy

## Status

Accepted F23W strategy assessment; F23X is selected but not implemented.

## Context

F23V R2 established that complete exact root-action W/D/L plus full horizon
abstraction produced only 4/30 usable mechanic-active roots under the bounded
contract. That route is too sparse and disproportionately expensive to remain
the default evaluator-validation mechanism. The result does not falsify the
five-feature analytic hypothesis.

## Decision

Retire complete exact W/D/L supervision as the default. Retain V3/F23R for
targeted tactical proofs, solver correctness, and bounded diagnostic fixtures.
Adopt a layered validation philosophy:

1. local semantic/metamorphic correctness;
2. real-game search-shadow evidence;
3. external mature-engine benchmarks as validation labels;
4. playing-strength evidence later.

F23W compared four strategies on simplicity, genericity, horizon dependence,
leakage, production complexity, data burden, compute, falsifiability,
mixed-mechanic/Shogi/Western validation, overfit risk, and distance to actual
playing strength. The selected strategy is
`LOCAL_METAMORPHIC_PLUS_REAL_GAME_SEARCH_SHADOW`, with boundary
`F23X_MINIMAL_ANALYTIC_EVALUATOR_METAMORPHIC_AND_SHOGI_SHADOW`.

The five-feature budget is unchanged: material/inventory, safe mobility/control,
attack/defense/anchor safety, forcing capture/recapture, and capability-gated
promotion/drop, with `[1,1,1,1,1]` and `S * sum(feature_i)`. No game-name branch,
concrete-piece scoring rule, parameter table, coefficient fitting, self-play,
or F23X implementation is introduced.

## Validation design

F23X must first run ten generic metamorphic contracts (two per feature), with
renamed-equivalent variants and separate capture-to-hand/remove-from-game and
mixed-mechanic cases. These contracts establish feature meaning only; they are
not Elo or optimal-play evidence.

The next search-shadow experiment will use the ten preserved F22 Standard
Shogi positions from commit
`3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38`, read-only. It compares production
evaluator-v1 with the unchanged five-feature candidate behind identical search,
legality/runtime, TT, and move ordering. Fixed-node budgets are 128/512/2048;
fixed-time budgets are 0.25/1.0 seconds. It records selected move, frozen
reference rank/top-k, score ordering, PV, nodes/depth/nodes-per-second,
evaluator calls/time, total wall time, and evaluator fraction.

Pre-registered quality gates are candidate top-choice agreement at least two
positions better than v1 or mean reference rank at least 10% better, no lost
agreement-control result, and complete execution of all ten positions. The
performance gate is candidate evaluator time at most 25% of total search wall
and no more than 35% median fixed-time nodes/second decline. No AlphaSho label
will choose features, signs, coefficients, thresholds, or individual cases.

The next experiment should use one audit-only read-only EvaluationContext
design pass to share legal actions, captures, promotions, drops, semantic
attack/check facts, anchor safety, recent-action target, and RuleSet-derived
profile facts across the five feature consumers. This is design-only in F23W;
it is not a production framework change.

Western Chess is a later axis: correctness/perft, verified mature reference,
fixed-node/time search, then matches. The mixed RuleSet remains semantic
genericity evidence, not a mature-game strength benchmark. Evidence remains
separated into SEMANTIC_CONTRACT_EVIDENCE, REAL_GAME_BENCHMARK_EVIDENCE, and
PLAYING_STRENGTH_EVIDENCE.

## Consequence

F23X is selected for the next authorized task. F23W itself changes no
production code and does not rerun F23V or create a corpus. F23V first-pass,
R1, and R2 artifacts remain byte-identical; the two R2 ledger corrections are
documented: the earlier four-certification count used V3 MAX_PLY visitation,
not abstraction visitation, and Western zero-drop must be tested by equality to
zero. Promotion remains HOLD.
