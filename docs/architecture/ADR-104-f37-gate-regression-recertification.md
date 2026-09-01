# ADR-104 — F37 gate and regression recertification

- Status: Accepted
- Date: 2026-09-01
- Work order: `GENERICCHESS-F37-CORRECTIVE-R1-GATE-AND-FULL-REGRESSION-RECERTIFICATION`

## Decision

Additive R1 evidence independently recomputes the exact preregistered F37
static-signal predicate from the frozen first-pass ranking fixture. The final
clause is evaluated as three separate booleans:

`AS050_mean_rank_improvement >= 0.15 OR AS200_mean_rank_improvement >= 0.15 OR
best_mean_rank_improvement >= 0.20`.

It is not implemented as `max(...) >= 0.15`. The independent result is R37A
false, R37B true, and R37C true; the eligible set is R37B/R37C and the frozen
lexicographic selection remains R37C. The first-pass defect is therefore
classified as `NON_OUTCOME_CHANGING_GATE_IMPLEMENTATION_DEFECT`.

## Preservation

The original F37 manifest, decomposition, rank, search-shadow, selection,
ADR-103, and audit script are hash-bound and byte-identical. No F37 candidate,
microbenchmark, search shadow, AlphaSho run, paired benchmark, or production
code was rerun or changed. Production diff remains zero.

The second corrective gate is a fresh full `pytest` on the final F37 R1 tree.
It collected 1,251 tests, with 1,238 passing and exactly the 13 historical
failures (F13×4, F14×2, F21×6, and F24F×1); no unexpected failures occurred.
The focused R1-to-F24A regression passed 28/28. These results are recorded in
the R1 fixture and closeout report and bound to
`F37_FULL_REGRESSION_CURRENT_TREE_CERTIFIED`.
