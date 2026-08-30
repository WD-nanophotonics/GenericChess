# ADR-054: Threshold/runtime exact reference solver

- Status: Accepted for F23M foundation; capability gate passed
- Date: 2026-08-30
- Scope: development-only exact reference proof backend

## Decision

F23M adds `scripts/exact_generic_preference_solver_v3.py`. It proves the two
Boolean predicates `value >= 0` and `value >= 1`, then derives LOSS/DRAW/WIN
and the complete root optimal-action set. It uses `SearchPathRuntime` for every
successor transition and asserts balanced push/pop state before returning.

The authoritative horizon is the compiled `max_ply` (or its support metadata)
when callers pass `max_depth=None`. The transposition key is repetition-count
based for ordinary draw adjudication and retains full runtime history for
continuous-check loss. Unresolved descendants are never inserted into the
threshold table, so a cap or cycle cannot become a false proof.

## Capability-v4 evidence

The frozen five-family F23M plan used SMALL/MEDIUM/LARGE node budgets of
2,000/20,000/100,000, with an 8-second process wall cap per attempt. Four of
five non-control representatives resolved, all four with proof depth 6; the
drop-hand representative resolved at MEDIUM and the other three at SMALL.
Every resolved row had equal push/pop counts and zero differential mismatches
against the fixed control oracle. V2 comparison attempts were unresolved within
the same wall cap, so no V2 parity claim is made for these non-control rows.

The gate passed (4 resolved families, 4 deep proofs), while the unresolved
semantic auxiliary row and the capped SMALL drop-hand attempt identify
combinatorial branching as the dominant remaining cost. The next boundary is
`F23N_REFERENCE_PREFERENCE_CORPUS_R5`; no V7 corpus is introduced here.

## Consequences

This backend is suitable as a development reference for the next corpus
boundary, not as a production evaluator or search implementation. F23M keeps
all V1-V6 corpora and prior capability fixtures immutable and records runtime
and threshold behavior in tests.
