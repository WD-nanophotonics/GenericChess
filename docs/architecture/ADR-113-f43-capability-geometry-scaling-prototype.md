# ADR-113: F43 capability geometry-scaling prototype

- Status: Corrected diagnosis-only F43 boundary
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
| Linear control | pass | pass | fail | fail | fail | pass | no |
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
order. The three log variants reduce raw inflation relative to the corrected
linear control for all four pieces, but none enters the frozen broad bands.
The linear control is the F42 reproduction and is not itself an inflation
reduction.

| Variant | Raw ratios | Normalized ratios | Broad bands |
|---|---|---|---:|
| Linear control | 4.5333, 5.8530, 8.5550, 14.2744 | 4.5322, 5.8480, 8.5497, 14.2632 | fail |
| Per-geometry log | 4.2183, 3.9749, 5.2079, 9.0111 | 4.2194, 3.9747, 5.2110, 9.0127 | fail |
| Per-source log | 2.4402, 2.6977, 3.1734, 3.8033 | 2.4394, 2.6954, 3.1698, 3.8005 | fail |
| Hierarchical log | 2.4993, 2.4121, 2.8180, 3.5547 | 2.5000, 2.4125, 2.8175, 3.5550 | fail |

## Shogi positive control

All four variants pass the Shogi gates. Metrics are cosine, Spearman, and
pairwise ordering against the current board values; hand/board range is
unchanged at `[0.8992673992673993, 0.900355871886121]`.

| Variant | Cosine | Spearman | Pairwise | Largest rank displacement | Hand/board range |
|---|---:|---:|---:|---:|---|
| Linear control | 1.000000 | 1.000000 | 1.000000 | 0 | unchanged |
| Per-geometry log | 0.985370 | 1.000000 | 1.000000 | 0 | unchanged |
| Per-source log | 0.963305 | 1.000000 | 1.000000 | 0 | unchanged |
| Hierarchical log | 0.953152 | 0.912791 | 0.935897 | 5 | unchanged |

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

## Corrective R1 provenance

The first submitted implementation was rejected because it used F42's
descriptive `_pattern_rows()` helper as the option-mass source. That helper
includes both ordinary and conditional capability patterns. Accepted F41/F42
material capability uses only the ordinary-pattern predicate. For Western
Pawn this distinction is three ordinary versus three conditional patterns;
including the conditional rows inflated Pawn mass and falsely compressed the
first-pass N/P, B/P, R/P, and Q/P ratios.

R1 changes only the audit extraction to use the accepted F41 ordinary
candidate population. A hard `G43_LINEAR_CONTROL_REPRODUCES_F42` gate now
checks density-weighted mobility, raw capability, and normalized board value
per type for Western Chess and Standard Shogi before qualification. The
corrected Western Pawn contract reports ordinary participation, conditional
exclusion, and accepted mobility `0.9496484375`. The corrected G43-0 Western
raw ratios are `4.533327`, `5.853043`, `8.555032`, `14.274351`, and its board
values are P `171`, N `775`, B `1000`, R `1462`, Q `2439`.

The corrected four-variant evidence, including exact Shogi board vectors,
rank displacement, synthetic controls, and first-pass provenance, is in
`.generic_chess_flow/f43_geometry_scaling.json`. The corrected classification
remains `GEOMETRY_SCALING_INSUFFICIENT` because all four Western band gates
fail; this result is recomputed rather than carried forward from the invalid
first pass.
