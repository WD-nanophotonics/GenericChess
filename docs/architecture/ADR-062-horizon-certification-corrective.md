# ADR-062: Horizon certification corrective R1

- Status: Accepted as corrective F23R evidence; advancement gate not passed
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23R-CORRECTIVE-R1-HORIZON-EVIDENCE-PRECEDENCE-AND-PROOF-PROVENANCE`
- Baseline: `eda9f86e01ef807285389ba70509557fc7c42912`

## Decision

Preserve ADR-060 and the first-pass F23R fixture as historical evidence, and
add a corrective v2 abstraction instead of rewriting either artifact. A
threshold proof now returns a typed status, proof depth, and the necessary
unresolved-cause set. Only exact TRUE/FALSE results enter the policy-aware
transposition table. At a decisive maximizing/minimizing short-circuit, causes
from irrelevant siblings are discarded; at a non-decisive combine, only causes
from unresolved children that remain necessary are propagated.

The pure-tree oracle models independently named abstract leaves U1, U2, and so
on as independent values in `{-1, 0, +1}`. Its finite value-set propagation is
both sound and complete: it returns exact TRUE/FALSE when every independent
concretization agrees, otherwise UNKNOWN. Permanent tests exhaustively cover
the independent assignments and both maximizing/minimizing nesting.

## Evidence precedence

The corrective audit reconciles the abstract result with accepted F23Q
base/+2/+4 exact evidence in this order:

1. A fully exact abstract certificate must match V10 and may not contradict
   accepted material evidence.
2. An unresolved abstraction retains F23Q `HORIZON_STABLE_EXACT`.
3. An unresolved abstraction retains F23Q
   `MATERIALLY_MAX_PLY_DEPENDENT`.
4. Only otherwise is the root classified as
   `HORIZON_SENSITIVITY_UNKNOWN`.

The report records action-level base W/D/L, GE_WIN/GE_DRAW status, abstract
value, necessary cause set, MAX_PLY dependency, and proof depth. Material roots
retain the first exact alternate horizon and changed action values/optimal
sets; stable roots retain exact base/+2/+4 resolving tiers.

## Frozen V10 result

The same 42 effective roots were reconstructed without additions, substitutions,
removals, resplitting, V10 rewriting, or production changes. The corrective
totals are:

| Final class | Count |
| --- | ---: |
| MAX_PLY_ABSTRACT_CERTIFIED | 0 |
| HORIZON_STABLE_EXACT | 3 |
| MATERIALLY_MAX_PLY_DEPENDENT | 15 |
| HORIZON_SENSITIVITY_UNKNOWN | 24 |

Unknown provenance is 12 semantic, 10 mixed semantic/computational, and 2
computational. There are zero abstract/base and zero abstract/material
contradictions. DEVELOPMENT/HOLDOUT remains 32/10; the development
horizon-quality numerator is 3/32, below the required 16. The final frozen-V10
gate therefore fails primarily on necessary horizon uncertainty, and the
selected boundary is `F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9`.

The per-family DEVELOPMENT/HOLDOUT matrix is retained in
`tests/fixtures/f23r_v10_horizon_certification_r1.json`, including empty cells;
the accepted F23Q secondary totals remain 24 unknown, 15 material, and 3
stable.

## Engine-level verification

The real GenericChess fixtures cover horizon-independent WIN, LOSS, and DRAW;
a base DRAW that becomes WIN at a deeper exact horizon; irrelevant MAX_PLY
visitation; a mixed root; and tied optimal actions. TT on/off and forward/
reverse traversal produce identical normalized exact certificates. Focused R1,
F23R, F23M, F23P, and F23Q tests pass.

No F23S corpus is constructed by this ADR. V1–V10, ADR-060, the first-pass
F23R fixture, and all F23Q scientific artifacts remain byte-identical.

