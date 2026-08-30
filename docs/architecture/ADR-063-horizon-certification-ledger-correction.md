# ADR-063: Horizon certification ledger correction R2

- Status: Accepted as corrective F23R ledger evidence; advancement gate not passed
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23R-CORRECTIVE-R2-DEVELOPMENT-GATE-AND-LADDER-PROVENANCE`
- Baseline: `35e6f374b08f6cee90772e6dec8751233f22a9d4`

## Decision

Reconcile the saved F23R R1 ladder deterministically; do not rerun the
expensive GenericChess proofs or alter the v2 abstraction. For each root
action and each GE threshold, the R2 ledger scans every completed
SMALL/MEDIUM/LARGE action-level result. Any exact threshold proof wins over
lower unresolved evidence. A completed semantic-only MAX_PLY proof is retained
as semantic evidence even when a later tier ends in an external timeout. If no
semantic-only proof exists, all remaining necessary proof-local and external
computational causes are retained, including mixed semantic/computational
cases.

The ledger exposes exact status, highest completed tier, semantic-complete
tier, necessary semantic/computational causes, later external refusals, and a
reconciled status for both GE_WIN and GE_DRAW. Root provenance is derived from
the unresolved action set, not from one selected tier or a global visit count.

## Corrected frozen-V10 result

The effective set remains exactly 42 roots, split 32 DEVELOPMENT / 10 HOLDOUT.
The final class totals remain unchanged from R1 because F23Q precedence is
preserved:

| Final class | Count |
| --- | ---: |
| MAX_PLY_ABSTRACT_CERTIFIED | 0 |
| HORIZON_STABLE_EXACT | 3 |
| MATERIALLY_MAX_PLY_DEPENDENT | 15 |
| HORIZON_SENSITIVITY_UNKNOWN | 24 |

The corrected DEVELOPMENT-only horizon-quality numerator is 1/32: one stable
DEVELOPMENT root qualifies, while two stable roots are HOLDOUT. Material
dependence is 10 DEVELOPMENT and 5 HOLDOUT. UNKNOWN provenance by split is:

| Split | Semantic | Mixed | Computational |
| --- | ---: | ---: | ---: |
| DEVELOPMENT | 11 | 10 | 0 |
| HOLDOUT | 1 | 0 | 2 |
| Total | 12 | 10 | 2 |

All frozen non-horizon V10 gate items remain true: effective DEVELOPMENT and
HOLDOUT minimums, family/mechanic coverage, family and lineage concentration,
multiply-dependent minimum, W/D/L diversity, partition diversity, and both
residual leakage checks. The only recomputed failing item is the
DEVELOPMENT horizon-quality minimum of 16.

Because DEVELOPMENT contains 10 material roots and 21 horizon-unknown roots,
the selected next boundary is `F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9`.
No F23S work is performed by this ADR.

## Integrity

ADR-060, ADR-062, the first-pass and R1 F23R fixtures, the engine fixtures,
V1–V10, and all F23Q scientific artifacts remain byte-identical. No production
evaluator/search/Native/workflow/governance file changes. Synthetic ladder
records and the permanent F23R A–G/TT/order tests cover the reconciliation and
preserve the prior behavior guarantees.

