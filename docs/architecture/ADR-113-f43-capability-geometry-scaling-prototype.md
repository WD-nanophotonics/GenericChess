# ADR-113: F43 capability geometry-scaling prototype

- Status: Diagnosis-only F43 boundary
- Baseline: `6504a45dff2e1a726feb94d6aa83ac5128e0985d`
- H43A protocol: `tests/fixtures/f43_geometry_scaling_manifest.json`
- Audit implementation: `scripts/audit_f43_geometry_scaling.py`
- Production change: none; no evaluator formula was integrated

## Decision

The F43 result is `GEOMETRY_SCALING_INSUFFICIENT`. The next boundary is
`F44_STRUCTURAL_CAPABILITY_FEATURE_DIAGNOSIS`. No geometry-scaling candidate
qualifies for integration.

The audit evaluates exactly four frozen, parameter-free counterfactuals over
the accepted F42 canonical semantic candidate extraction:

| Variant | Transform |
|---|---|
| `G43-0_LINEAR_CONTROL` | unchanged linear channel mass |
| `G43-1_PER_GEOMETRY_LOG` | `sum(log1p(channel mass))` per geometry |
| `G43-2_PER_SOURCE_LOG` | `log1p(total source mass)` per source |
| `G43-3_HIERARCHICAL_LOG` | `log1p(sum(log1p(channel mass)))` per source |

All variants preserve F41/F42 path-clear and endpoint semantics, use canonical
geometry signatures rather than generated IDs or type/game names, and remain
audit-only. Structural, monotonicity, diminishing-growth, Western, Shogi, and
no-new-feature gates are conjunctive; no post-result alternative is selected.

## Qualification matrix

| Variant | Structural | Monotone | Diminishing vs linear | Western inflation reduced | Western bands | Shogi | Qualifies |
|---|---:|---:|---:|---:|---:|---:|---:|
| Linear control | pass | pass | fail | pass | fail | pass | no |
| Per-geometry log | pass | pass | pass | pass | fail | pass | no |
| Per-source log | pass | pass | pass | pass | fail | pass | no |
| Hierarchical log | pass | pass | pass | pass | fail | pass | no |

The linear control is correctly rejected by the diminishing-growth gate: its
ray and direction marginal ratios versus linear are both `1.0`. The three log
variants pass that gate. Their ray marginal ratios are respectively
`0.272968`, `0.272968`, and `0.122382`; their direction marginal ratios are
`0.850929`, `0.459736`, and `0.469342`.

## Western evidence

The raw and normalized N/B/R/Q ratios are shown below in N/P, B/P, R/P, Q/P
order. Every variant reduces the raw inflation relative to the linear control
for all four pieces, but none enters the frozen broad bands.

| Variant | Raw ratios | Normalized ratios | Broad bands |
|---|---|---|---:|
| Linear control | 1.7382, 2.2442, 3.2802, 5.4731 | 1.7377, 2.2422, 3.2780, 5.4686 | fail |
| Per-geometry log | 1.7198, 1.6206, 2.1233, 3.6739 | 1.7212, 1.6213, 2.1256, 3.6764 | fail |
| Per-source log | 1.3929, 1.5398, 1.8114, 2.1709 | 1.3945, 1.5408, 1.8120, 2.1726 | fail |
| Hierarchical log | 1.4136, 1.3643, 1.5939, 2.0106 | 1.4144, 1.3649, 1.5941, 2.0113 | fail |

## Shogi positive control

All four variants pass the Shogi gates. Metrics are cosine, Spearman, and
pairwise ordering against the current board values; hand/board range is
unchanged at `[0.8992673992673993, 0.900355871886121]`.

| Variant | Cosine | Spearman | Pairwise | Hand/board range |
|---|---:|---:|---:|---|
| Linear control | 1.000000 | 1.000000 | 1.000000 | unchanged |
| Per-geometry log | 0.985370 | 1.000000 | 1.000000 | unchanged |
| Per-source log | 0.963305 | 1.000000 | 1.000000 | unchanged |
| Hierarchical log | 0.953152 | 0.912791 | 0.935897 | unchanged |

The exact normalized Shogi board vectors and all per-piece curves are retained
in `.generic_chess_flow/f43_geometry_scaling.json`; the vectors are produced
by the same compiler/analyzer and do not change production state.

## Synthetic geometry controls

The same analyzer/compiler covers one-step leap versus multi-square ray, short
versus long ray, single versus multi-direction, quiet/capture/quiet+capture,
and directional/symmetric controls. All eight structural gates pass:
zero-to-zero, nonnegative, finite/deterministic, owner mirror, type/ruleset
rename, action-pattern order, candidate deduplication, and monotone option
mass. The log variants preserve positive monotonic growth while reducing the
ray and direction marginal growth listed above.

## Scope and boundary

F43 does not fit coefficients, change the evaluator, add a feature, invoke
AlphaSho/search/self-play/TDLeaf/R37, or start F44. Focused F43 tests assert
the frozen transform set, structural controls, all Western/Shogi metrics, and
the single final selection. Full regression differential evidence and the
published candidate SHA are recorded at closeout.
