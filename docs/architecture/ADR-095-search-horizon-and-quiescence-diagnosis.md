# ADR-095: Search Horizon and Quiescence Diagnosis

## Status

F32 audit protocol; no production change is authorized by this decision.

## Decision

F32 consumes the immutable F30, F31, and F31R1 evidence and freezes a new
manifest before qsearch probes. It measures production qnode composition,
qdepth and qnode-cap behavior, non-check stand-pat scheduling, noisy-action
discovery counters, in-check work, runtime attribution, and per-root
VALUE/QSEARCH/HORIZON/MIXED classification.

The audit distinguishes exact-semantics reorderings from bounded-budget and
reduced-semantics variants. `LAZY_NONCHECK_LEGAL_GENERATION` is an audit-only
exact-semantics model; if safe root injection is unavailable, it is reported as
`ROOT_INJECTION_NOT_RUN` rather than treated as a production timing result.
Qdepth/cap ladders and Q1–Q3 noisy reductions remain diagnostic policies.

## Findings

The frozen manifest is `dfd8b8394ba25136b650450b25e3429c3487a9de05d25d4c253c2ecebc6e6b2b`.
The completed result is recorded at
`tests/fixtures/f32_qsearch_diagnosis.json` (SHA-256
`878dccd45d2d9bf325d26d1947a5ee8e85b8005176e3dbfdf0772c9e46becd56`).
All ten frozen roots use the Python authority fallback; no production files
changed. At fixed budgets, qsearch averages 0.506–0.538 of visited nodes,
while the wall-time controls average 0.264 at 0.5 seconds and 0.404 at 2.0
seconds. The audit records 10/10 roots as `QSEARCH_COST_LIMITED`: disabling
qsearch raises completed depth from 0 to 1 at 0.5 seconds and from 1 to 2 at
2.0 seconds. A qnode cap of 16 triggers qsearch-budget termination on the
cap subset; larger caps reduce but do not eliminate the budget boundary.

The lazy non-check schedule preserves the modeled terminal, declaration,
in-check, stand-pat, qdepth, and noisy-action order, but root injection was
not run (`ROOT_INJECTION_NOT_RUN`), so its avoided-generation count is
notional and not a production timing claim. Q0–Q3 noisy-action reductions
are likewise audit-only. These results select
`F33_QUIESCENCE_BUDGET_ARCHITECTURE` for the next bounded investigation.

## Boundary

F32 selects exactly one F33 boundary from the measured evidence. No evaluator
retuning, Native repair, rules/session/runtime change, new paired benchmark,
AlphaSho rerun, or production qsearch change is included.
