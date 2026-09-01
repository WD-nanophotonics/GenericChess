# ADR-108 — F40 rule-derived material and feature-utilization audit

- Status: F40 diagnosis PASS; no production integration
- Date: 2026-09-01
- Work order: `GENERICCHESS-F40-RULE-DERIVED-MATERIAL-AND-FEATURE-UTILIZATION-AUDIT`

F40 is audit-only. H40A freezes the current profile and evaluator sources,
the two mature product RuleSets, historical learning authorities, the precise
material-reference validation bands, utilization-ledger states, classification
rules, and F41 boundary mapping before material or feature results are
calculated. It cannot fit, train, benchmark, or introduce a production change.

## Result

The current Western Chess rule-derived profile has a severe normalization
pathology: the Pawn's zero raw capability is floored to one while the next
non-anchor type is 775. Consequently its Pawn-normalized Knight/Bishop/Rook/
Queen values are 775/1000/1462/2439, far outside the deliberately broad
validation bands. This is a profile-scale finding, not a fitted replacement.

The current product Standard Shogi profile remains healthy against the
consumed Phase 1.8 material reference (cosine 0.98899, Pearson 0.97615,
Spearman 0.97502, and pairwise ordering 0.96450). Its drop freedom and drop
mobility are computed and stored with material profiles, vary by base type,
but do not affect the final hand value: hand is mechanically
`round(board * 0.9)`. That is a meaningful utilization gap.

F40 therefore selects `MATERIAL_AND_FEATURE_UTILIZATION_GAP` and exactly
`F41_RULE_DERIVED_MATERIAL_PRIOR_AND_SIGNAL_UTILIZATION_CORRECTIVE`. This
does not authorize a production evaluator or search change.
