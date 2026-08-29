# ADR-046: Deeper exact reference-preference corpus R2

## Status

F23G accepted. The V4 artifact is a reference corpus only; no production
evaluator, search, Native path, HOLDOUT fit, or F23F candidate was changed.

## Decision

Extend the exact, evaluator-free reference boundary with 30 new generic roots
in `tests/fixtures/evaluator_v2_corpus_v4.json`. The new stratum contains five
distinct compiled movement geometries and six deterministic state variants per
geometry. The solver uses authoritative legal successors, transitions,
terminal adjudication, complete position/history identity, and explicit
refusal on cycles or node/depth caps.

Each selected root has a unique best W/D/L preference whose proof includes two
ordinary opponent reply plies. The development roots contain 25 samples, the
sealed split contains 5, and all 30 are `MULTIPLY_DEPENDENT`; none is classified
as immediate or max-ply-dependent. Every development root has both a DRAW
optimal action and a LOSS alternative. The development ruleset groups are
balanced at five roots per group, and all 25 development roots have differing
root action values.

The V1, V2, V3, and rejected F23F candidate-spec bytes are guarded by tests and
remain unchanged. The temporary candidate probe is not retained as a durable
artifact.

## Consequence and next boundary

The deeper ordinary-reply gate passes, so select exactly
`F23H_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R3`. F23H must keep V4 HOLDOUT
sealed, use only the DEVELOPMENT reference stratum for fitting, and retain the
same grouped, cross-ruleset rejection gates before any promotion is considered.
