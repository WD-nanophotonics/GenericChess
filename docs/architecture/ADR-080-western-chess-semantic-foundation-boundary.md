# ADR-080: Western Chess certification requires a source-bound semantic foundation

## Status

Accepted boundary for F24D; follow-up `F24E_WESTERN_CHESS_SEMANTIC_FOUNDATION`.

## Context

F24D audits whether the existing generic RuleSet/Semantic DSL can express a
complete Western Chess ruleset before running standard perft. The DSL already
has the required shape primitives for ordinary movement, captures, promotion
masks, square-token expiry, castling rights, transition triggers, and attacked
square invariants.

## Decision

Do not certify perft with the current DSL. A `RuleStateGuard` can inspect a
fixed square or a rank, but it cannot express the conjunction “the current
action source is on the pawn starting rank.” A guard that checks the starting
rank therefore leaks double-step eligibility to another pawn whenever any pawn
occupies that rank. Expanding one action per file does not solve this because
the guard remains independent of the bound source.

This is a semantic expressibility boundary, not a production search/runtime
defect. F24D stops before perft and selects the broad Western foundation
boundary so the eventual primitive can be designed and tested once for pawn
source-bound predicates while preserving generic, game-name-free semantics.

## Consequences

- No production Core, search, runtime, or native changes are made by F24D.
- The preflight evidence is retained in
  `tests/test_f24d_western_chess_perft.py` and its compact fixture.
- The standard perft vectors remain unclaimed until F24E supplies an exact
  source-bound semantic primitive and its behavior guarantees.
