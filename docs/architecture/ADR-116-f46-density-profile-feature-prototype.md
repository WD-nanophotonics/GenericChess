# ADR-116: F46 density-profile feature prototype diagnosis

- Status: Diagnosis-only F46 boundary
- Baseline: `b0fc4d2da1a6cb0b818b713305dce84cef3e8e6e`
- H46A: `fbcf61dd0497647692c66ddb15e2cb324aa3bb43` (published, but corrected by H46R1A)
- H46R1A: `69c9c5b`
- Audit: `scripts/audit_f46_density_profile.py`
- Production change: none; no evaluator formula was integrated

## Decision

F46 tested exactly four fixed reductions over the existing five-point density
curve and existing weights: weighted arithmetic control, weighted geometric,
weighted harmonic, and lower envelope. The arithmetic control exactly
reproduces current F42/F45 mobility for Western Chess and Standard Shogi.
All reducers pass deterministic finite/non-negative, monotonicity,
scale-equivariance, constant-curve, point/weight, and no-new-parameter gates.

The corrected evidence-derived result is
`DENSITY_PROFILE_REDUCTION_INSUFFICIENT`, with next boundary
`F47_ENDPOINT_DENSITY_COMPOSITE_DIAGNOSIS`. Geometric and harmonic reductions
pass structural and Shogi controls and reduce all Western N/B/R/Q raw ratios,
but fail the frozen Western broad bands. Lower envelope also fails the Shogi
cross-rule gate. No non-control reducer qualifies.

## Controls and matrices

The F44 matched equal-empty-board-mass short-path versus long-path witness is
preserved: every reducer gives the blocker-sensitive long curve a lower result
than the matched short curve. A constant curve returns its constant. Two
numeric curves with equal weighted arithmetic mean but different shape remain
equal under D46-0 and are separated by D46-1/2/3.

Western and Standard-Shogi matrices retain complete curves, reduced mobility,
unchanged non-mobility components, raw capability, board values, and ratios.
The Shogi cosine, Spearman, pairwise-ordering, and hand/board gates are
reported per reducer against the accepted current profile.

## Protocol correction and boundary

The first H46A mistakenly listed density points `(0, .25, .5, .75, 1)`;
the actual `EvaluationConfig` points are `(0, .125, .25, .375, .5)` with
weights `(.25, .2, .2, .18, .17)`. H46A was not rewritten. H46R1A was
published as a separate correction before reducer execution and binds the
actual points/weights, four reducers, structural gates, semantic controls,
Western bands, Shogi gates, and six qualification mappings without freezing an
observed result.

F46 remains prototype/audit only. It does not integrate a production
evaluator, alter normalization or non-mobility weights, add density points,
fit coefficients, add endpoint/conditional features, combine F43, run
AlphaSho/search/self-play/training, execute F47, or promote master.
