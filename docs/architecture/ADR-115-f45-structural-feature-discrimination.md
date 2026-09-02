# ADR-115: F45 structural feature discrimination

- Status: Diagnosis-only F45 boundary
- Baseline: `1f4fc5f1dc12675e6bafcf1992245441d36104f5`
- H45A protocol: `tests/fixtures/f45_structural_feature_discrimination_manifest.json`
- Audit implementation: `scripts/audit_f45_structural_feature_discrimination.py`
- Production change: none; no evaluator feature was integrated

## Decision

F45 reproduces F44 exactly, then assigns consumer placement and tests the
frozen residual obligations with parameter-free structural coordinates. The
minimum admissible explanatory subset is
`S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY` alone. The resulting
classification is `DENSITY_PROFILE_FEATURE_PRIMARY`; the next boundary is
`F46_DENSITY_PROFILE_FEATURE_PROTOTYPE`.

## Consumer placement

Endpoint/control is `STATIC_MATERIAL_ADMISSIBLE`. The dynamic evaluator's
`pseudo_attacks` path consumes a position-dependent destination union/count,
but `generic_chess/core/attacks.py::pseudo_attacks` has no quiet-versus-enemy
endpoint relation. The F44 matched collision therefore remains at the
complete pre-search feature representation. The unique split is not
equivalently consumed, although a future consumer must account for partial
dynamic overlap.

Conditional capability is `DYNAMIC_EVALUATOR_ADMISSIBLE`, not static. The
audited Western Pawn reserve contains state and slot guards (double-step and
en-passant patterns), while no promotion-related transition is present in
this F44 conditional population. `generic_chess/core/semantic_executor.py`
consumes those guards and `Evaluator._promotion_bonus` consumes a separate
position-dependent promotion signal. A compile-once type constant cannot
assume guard availability, so the reserve is not permanently active static
material.

Density-profile shape is `STATIC_MATERIAL_ADMISSIBLE` and is not equivalently
consumed. `build_movement_capability` retains the complete curve,
`_raw_capability_score` reduces it to the configured weighted mobility scalar,
and the runtime evaluator has no independent curve-shape consumer. The
matched synthetic controls have equal empty-board mass but different curves;
the shape is therefore an executable rule-derived information gap rather than
an arbitrary new coefficient.

S44-C remains `DIAGNOSTIC_ONLY_NOT_ADMISSIBLE`: its real concentration metrics
are measured, but the one-versus-two-channel matched control does not collide
in the current four-component representation.

## Residual and orientation results

The endpoint probe covers R1 (Pawn-anchor) but not R2 (Knight versus long ray).
The conditional reserve covers R1 structurally but not R2 and remains runtime
owned. The density probe retains mobility retention, weighted retention,
maximum drop, curvature, and blocker ordering; it covers both R1 and R2.
The Standard-Shogi positive control remains within the frozen cosine,
Spearman, pairwise-ordering, and hand/board gates, and its larger board and
directional/compound movement distribution does not reproduce the Western
relative-compression path.

Western Pawn can be nonzero in both endpoint and conditional ledgers, but the
redundancy audit finds different executable causes: endpoint relation versus
guard availability. Neither is recoverable from the other, and neither is
interchangeable with density blocker shape. The minimum subset is selected by
set coverage of R1/R2, not by comparing unlike numeric scores.

## Boundary and prohibited work

F45 is diagnosis/discrimination only. It does not integrate a density feature,
choose a weight, run a search/benchmark/training loop, expand geometry, alter
human values, or promote master. F46 is authorized only to prototype the
selected density-profile feature under a new frozen work order.
