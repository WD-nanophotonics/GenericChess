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

## Boundary

F32 selects exactly one F33 boundary from the measured evidence. No evaluator
retuning, Native repair, rules/session/runtime change, new paired benchmark,
AlphaSho rerun, or production qsearch change is included.
