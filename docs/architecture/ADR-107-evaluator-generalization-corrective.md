# ADR-107 — F39 evaluator generalization corrective

- Status: F39 diagnosis PASS; no production integration
- Date: 2026-09-01
- Work order: `GENERICCHESS-F39-EVALUATOR-REENTRY-GENERALIZATION-CORRECTIVE`

F39 is diagnosis-only. Before calculating any new R37A/R37B holdout result,
the manifest freezes the F37/F38/R1 evidence identities, tie-aware rank
definitions, component-additivity and causal labels, distribution-shift rules,
the limited 2048-node A/B-only search protocol, and the mechanical F40 mapping.

The consumed F38 holdout is validation evidence, not an optimization oracle.
F39 cannot select, tune, or integrate R37A/R37B/R37C into production.

## Result

F39 reproduced the frozen F38 V1/R37C fields wherever they overlap and found
no rank-tie-instability-primary explanation: of 20 rows, 2 are material-value
worsenings, 10 are mixed rank-and-margin rows, 0 are rank-tie instabilities,
and 8 are unchanged or improved. The original deterministic-rank gate remains
failed; its negative result is not erased by tie-aware analysis.

The frozen F37 representations are additive on every scored F38 child.
R37A, R37B, and R37C all lack positive transfer on both frozen holdout strict
rank and normalized-margin aggregates. R37B and R37C are recorded as
in-sample-only signals relative to F37; F39 makes no global-strength claim.
Rule-generic distribution summaries flag material differences between the F37
selection set and F38 holdout, including occupancy, hand inventory, legal
action count, capture fraction, activity/ring term ranges, and material
imbalance.

The mechanically selected aggregate diagnosis is
`BROAD_REPRESENTATION_TRANSFER_FAILURE`. The exact next boundary is
`F40_RULE_DERIVED_MATERIAL_AND_FEATURE_UTILIZATION_AUDIT`. It is an audit
boundary, not authorization to select R37A/R37B/R37C or modify production.
