# ADR-094: Counterfactual Causal Reclassification

## Status

Accepted as the corrective R1 interpretation of the frozen F31 measurement
checkpoint. It does not change production behavior.

## Context

F31 measured root tactical, qsearch, horizon, Native, evaluator, and policy
effects, but its first classifier treated execution before fallback as proof
that root tactical scanning was a primary throughput cause. Chat review found
that this was tautological and that qsearch removal consistently recovered one
main-search ply.

## Decision

F31R1 consumes `tests/fixtures/f31_causal_manifest.json` and
`tests/fixtures/f31_causal_diagnosis.json` byte-identically. It classifies a
component from its disabling/bypass effect on depth, fallback frequency,
time-to-iteration, equal-wall-time work, or measured share. It keeps quality
and efficiency dimensions separate.

The corrected evidence labels evaluator/value MATERIAL, accessible horizon
efficiency PRIMARY, root tactical scan computational overhead NOT_SUPPORTED,
root fallback mechanism NOT_SUPPORTED as a computational cause, qsearch cost
PRIMARY, qsearch decision-quality contribution MATERIAL, TT/order/PVS
UNRESOLVED, Python semantic/runtime throughput PRIMARY, and Native capability
gating UNRESOLVED with status `NATIVE_COUNTERFACTUAL_UNAVAILABLE`.

At 0.50 s, qsearch OFF changes depth 0→1 on all ten roots, removes 10/10
fallbacks, and reduces external-reference hits 4→3. At 2.00 s it changes
depth 1→2 on all ten roots, leaves fallback at 0/10, and reduces hits 3→2.
Root-tactical OFF changes neither depth nor fallback at either control and
reduces 0.50 s reference hits 4→1. Thus qsearch must not simply be disabled;
the next investigation is budget/defer/restructure of quiescence while
retaining its tactical quality contribution.

## Boundary

The single corrected next boundary is
`F32_SEARCH_HORIZON_AND_QUIESCENCE_DIAGNOSIS`. No Native repair, evaluator
retuning, new paired benchmark, or production change is authorized by this
corrective.
