# ADR-065: Final natural-terminal reference corpus R10

- Status: Accepted as F23T evidence; synthetic supervision strategy reassessment required
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23T-NATURAL-TERMINAL-REFERENCE-CORPUS-R10`
- R10 plan SHA-256: `7f2a499b93f640bd5d7ecb283afe5a5115cb21d4efbd4e92d740bb1dd5fbb39f`

## Decision

Run one final deterministic natural-terminal enumeration with six retained
construction families. The finite spaces are structurally prefiltered before
any W/D/L solving for non-terminal roots, legal-root branching, actual
mechanic availability, and short non-MAX terminal visibility. Canonical
semantic descriptors exclude display IDs, splits, labels, solver tiers, and
evaluator information; lineage IDs and splits are then derived from those
descriptors. The plan is frozen before R10 solving.

V3 and F23R abstraction both use isolated SMALL/MEDIUM/LARGE workers with an
8-second wall per tier, stopping at the first complete result. R10 strict root
witnesses require an actual capture, drop, promotion target, custom `sem_*`
semantic pattern, designated leaper action, or conservative anchor terminal;
the witness W/D/L must differ from another legal root choice. A V12
supervision root additionally requires exact V3 and complete MAX_PLY-abstract
certification with identical action values and optimal set.

## Frozen R9 diagnosis

The frozen R9 diagnosis records that R9 declared but did not enforce its
isolated V3 runner or abstraction ladder. Its permissive witness also accepted
unrelated WIN/LOSS actions; the sole R9 semantic root
`f23s-r9-semantic-02` fails strict re-audit because its selected action is a
legacy semantic-board pattern rather than the custom `sem_*` pattern.

## R10/V12 result

The deterministic R10 plan contains 60 candidates: ordinary 12, capture 12,
drop 12, promotion 12, semantic 2, and leaper 10. The planned split is 47
DEVELOPMENT / 13 HOLDOUT, with 60 unique source lineages. Structural filtering
produced 19 V3-exact roots, 8 preference-bearing strict-witness roots, and 41
V3 unresolved roots. Of the 8 strict-witness roots, 7 were abstraction-certified
and 1 was abstraction-refused; 11 all-equal roots remain diagnostics.

The final clean V12 effective set is 6 DEVELOPMENT / 1 HOLDOUT. All seven are
MAX_PLY_ABSTRACT_CERTIFIED and multiply dependent. Effective core mechanics
are anchor/check 5, capture/recapture 1, drop/hand 0, and promotion 0. There
are two W/D/L partitions, no observed or residual cross-split orbit leakage,
no residual source-lineage leakage, zero contradictions, and no V10/V11
historical root in V12 eligibility.

The full gate fails scale, core-mechanic representation, and missing HOLDOUT;
the signal-probe gate also fails. Since the abstraction is healthy for the
roots that reach it but the clean eligible pool remains far below both gates,
the selected next boundary is
`F23U_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT`. R10 is the final automatic
synthetic-corpus attempt; no R11 or evaluator fitting is authorized here.

## Integrity and scope

V1–V11, all F23R/F23S artifacts, prior plans, capability evidence, and ADRs
remain byte-identical. No production evaluator/search/Native/workflow/
governance file changed. V12 is a diagnostic/eligibility artifact only.

