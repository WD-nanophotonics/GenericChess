# ADR-060: Horizon reference certification foundation

- Status: Accepted as F23R evidence; advancement gate not passed
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23R-HORIZON-REFERENCE-CERTIFICATION-FOUNDATION`
- Source V10 fixture SHA-256: recorded in `tests/fixtures/f23r_v10_horizon_certification.json`

## Decision

Add a separate reference-only horizon abstraction in
`scripts/exact_generic_horizon_abstraction.py`. The authoritative V3 solver
and its MAX_PLY terminal semantics remain unchanged. In this abstraction,
MAX_PLY is the three-valued result `UNRESOLVED_MAX_PLY`, not a win, draw, or
loss. Threshold propagation is conservative: a maximizing node proves true if
one child proves true and proves false only when every child proves false; a
minimizing node is dual. Unknown results are never cached as exact proofs.

The module also contains a pure finite-tree oracle. Exhaustive assignments of
unknown leaves are used by permanent tests to check that a true proof holds for
every continuation and a false proof holds for none. An unknown result is
required exactly when both truth outcomes remain possible.

## F23R certification

The audit reads the frozen V10 effective representatives and reconstructs each
root without rewriting V10 or changing any production evaluator/search/Native
code. Each root is attempted with the SMALL/MEDIUM/LARGE reference ladder and
an 8-second isolated-worker cap. An abstract result is compared with the V10
root-action certificate; any mismatch would be an explicit
`ABSTRACT_BASE_CONTRADICTION`.

The resulting fixture covers all 42 effective roots: 32 DEVELOPMENT and 10
HOLDOUT. It records zero abstract/base contradictions, zero abstract-certified
roots, 41 semantic horizon-unknown roots, and one computationally unresolved
root. The gate therefore fails its development horizon-quality minimum. Since
semantic uncertainty dominates computational uncertainty, the selected next
boundary is `F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9`.

## Scope and integrity

V1–V10 and all F23Q scientific artifacts remain byte-identical. No historical
horizon labels are rewritten. The abstraction is an overlay for certification
only; it is not a production evaluator, search, Native, workflow, or
governance change. Durable behavior guarantees are covered by
`tests/test_f23r_horizon_certification.py`.

