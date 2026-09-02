# ADR-116: F46 density-profile feature prototype diagnosis

- Status: Diagnosis-only F46 boundary
- Baseline: `b0fc4d2da1a6cb0b818b713305dce84cef3e8e6e`
- H46A: `fbcf61dd0497647692c66ddb15e2cb324aa3bb43` (published, but corrected by H46R1A)
- H46R1A: `69c9c5b`
- H46R2A: `5a941d9`
- Audit: `scripts/audit_f46_density_profile.py`
- Production change: none; no evaluator formula was integrated

## Decision

F46 tested exactly four fixed reductions over the existing five-point density
curve and existing weights: weighted arithmetic control, weighted geometric,
weighted harmonic, and lower envelope. The arithmetic control exactly
reproduces current F42/F45 mobility for Western Chess and Standard Shogi.
All reducers pass deterministic finite/non-negative, monotonicity,
scale-equivariance, constant-curve, point/weight, and no-new-parameter gates.

The first-pass evidence-derived result was
`DENSITY_PROFILE_REDUCTION_INSUFFICIENT`, with next boundary
`F47_ENDPOINT_DENSITY_COMPOSITE_DIAGNOSIS`. Geometric and harmonic reductions
pass structural and Shogi controls and reduce all Western N/B/R/Q raw ratios,
but fail the frozen Western broad bands. Lower envelope also failed the first
pass Shogi metric, which was corrected in H46R2A before the final result.

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

## Corrective R1 closure

The first-pass F46 metric used Pearson correlation of raw capability values,
an algebraically constant hand/board ratio, a hardcoded reachability map, an
incomplete algebra gate, partial D46-0 reproduction, and a qualification
matrix that did not include the semantic-control predicate. H46R2A was
published as standalone commit `5a941d9` after H46R1A and before corrective
execution.

The corrective computes cosine as dot product over norms of candidate
normalized board values against the accepted current normalized board profile,
retains rounded hand-value construction, checks every curve coordinate for
monotonicity, checks `min <= harmonic <= geometric <= arithmetic`, tests paired
label/order invariance, and verifies D46-0 full mobility/raw/board profiles
for both rulesets. Qualification now conjunctively includes the F44 blocker
witness, constant and equal-arithmetic shape controls, unchanged non-mobility,
normalization, endpoint algebra, graph terms, candidate population, and no
new feature/parameter. All six selector cases execute `_select()`.

After correction D46-3 passes the Shogi gate (cosine `0.9791`, with largest
rank displacement `5.0`). All three non-control reducers pass corrected
structural, semantic, Shogi, and Western residual-reduction predicates but
fail the frozen Western broad bands. The final classification remains
`DENSITY_PROFILE_REDUCTION_INSUFFICIENT` with
`F47_ENDPOINT_DENSITY_COMPOSITE_DIAGNOSIS`.

## Corrective R2 closure

R2 closes the remaining no-drift gate defect without changing the H46R2A
protocol or any manifest. For every reducer and both rulesets, the audit now
records per-type equality for the consumed F42 density curve, with an aggregate
candidate-population gate. It also compares coverage, reachability, and path
efficiency against the F42 component ledger per type, rather than evaluating
dictionary truthiness. The endpoint-algebra comparison is exposed as a named
evidence record.

Normalization is independently recomputed through the accepted F42 helper and
the frozen median/rounding/anchor/clamp contract, then compared per type with
the F46 candidate board vector. The no-new-feature/parameter gate is derived
from exact reducer-set, point, weight, reducer-signature, non-mobility,
population, and endpoint-algebra predicates. D46-0 now exposes per-type curve,
reduced-mobility, raw-capability, and normalized-board reproduction for both
rulesets. The corrected result remains
`DENSITY_PROFILE_REDUCTION_INSUFFICIENT` →
`F47_ENDPOINT_DENSITY_COMPOSITE_DIAGNOSIS`; F47 remains unexecuted.
