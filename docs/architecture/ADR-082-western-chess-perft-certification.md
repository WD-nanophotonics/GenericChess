# ADR-082: Western Chess perft certification boundary

## Status

F24F stopped at the first falsified mandatory perft boundary.

## Evidence

The certification-only Western ruleset is built entirely from the existing
generic Semantic DSL. Direct contracts for pawn movement and promotion,
transient en-passant state, castling rights and attacked-square safety,
terminal behavior, public action identity, serialization, and SearchPathRuntime
push/pop passed. Non-pawn captures are explicitly lowered as
`remove_from_game`; no legacy board capture pattern remains reachable.

The standard initial position reached the mandatory totals through depth 4:
20, 400, 8902, and 197281.

The exact FEN supplied by the F24F work order for Kiwipete failed at depth 1:
the semantic engine produced 45 legal actions while the work order expects 48.
The exact root divide and digest are retained in
`tests/fixtures/f24f_western_chess_perft.json`.

## Decision

F24F is a one-shot certification. No production, ruleset, FEN-loader, or
perft-harness patch is made after observing this mismatch. The supplied FEN is
preserved verbatim; its discrepancy with the canonical Kiwipete reference is
diagnostic evidence, not a license to alter the frozen certification input.

The smallest next boundary is
`F24G_WESTERN_CHESS_PERFT_DIAGNOSIS`: compare the frozen FEN, expected corpus,
and root divide before any Western rule productization work.

## Consequences

- F24F does not claim full Western perft certification.
- The production semantic diff for F24F is zero.
- Native unavailability for the subject-bearing certification ruleset remains
  expected and nonblocking.
- No promotion is authorized.
