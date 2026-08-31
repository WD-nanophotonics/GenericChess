# ADR-096: Executable Qsearch Counterfactual Certification

## Status

Accepted F32 corrective audit; no production change is authorized by this
decision.

## Decision

F32 R1 adds an audit-process-only lazy runtime qsearch and an exact noisy-action
classifier. The lazy runtime preserves terminal, declaration, in-check,
stand-pat, qdepth, and qnode-budget semantics, and defers complete non-check
legal-action materialization until expansion is required. The classifier
compares its action sequence with the independent production classifier while
counting direct captures/promotions, terminal-child pushes, checking board/drop
pushes, and quiet/non-checking rejections.

The frozen first-pass identities are manifest
`dfd8b8394ba25136b650450b25e3429c3487a9de05d25d4c253c2ecebc6e6b2b` and result
`878dccd45d2d9bf325d26d1947a5ee8e85b8005176e3dbfdf0772c9e46becd56`.
The R1 result is at `tests/fixtures/f32r1_qsearch_exact_counterfactual.json`
with SHA-256
`0805a97b12de1fd011386a11e1e0a532e13c42b44266269671a2499f29259b88`.

## Findings

All ten frozen roots passed executable value parity on completed bounded
calls, and the independent noisy classifier had zero sequence mismatches.
At fixed 512 nodes, complete legal-generation calls fell from 2984 to 1503
(49.6%); legal actions generated fell from 85866 to 40465. The .50/2.00-second
root matrix remained Python authority fallback. The lazy materiality gate did
not pass its >=3-root depth or fallback improvement threshold in this run
(2/10 for each), so it does not authorize direct lazy production work.

The exact production-instrumented classifier recorded rejection rates of
97.17% at 512 nodes and 96.12% at 2048 nodes. Classification parity passed,
and the branch witnesses executed terminal root/child, declaration WIN,
RESTART, and LOSS handling, plus the unchanged in-check full-evasion path.
The qnode-cap behavior remains `MIXED`: caps can abort qsearch while the
outer search may retain a completed result or fall back.

The measured next boundary is therefore
`F33_SEMANTIC_CHECKING_ACTION_DISCOVERY_FASTPATH`: exact discovery rejection
is material, while the lazy scheduling materiality gate is not satisfied.
Q0–Q3 remain recursive-policy diagnostics, not discovery-cost measurements.

## Constraints

The R1 audit changed no file under `generic_chess/`, reran no AlphaSho or
paired benchmark, repaired no Native implementation, and made no evaluator,
rules, session, or production qsearch change.
