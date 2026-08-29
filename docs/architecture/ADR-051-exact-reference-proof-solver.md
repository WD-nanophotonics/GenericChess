# ADR-051: Versioned exact reference proof solver V2

## Status

F23K correctness foundation completed and was not advanced to a corpus phase.
The next boundary is `F23L_EXACT_REFERENCE_SOLVER_FOUNDATION_R2`.

## Compatibility boundary

The historical `scripts/exact_generic_preference_solver.py` remains unchanged
and is the differential oracle for all frozen corpus builders. F23K adds the
separately versioned `exact_generic_preference_solver_v2.py`; it does not
rewrite historical labels or V1–V6 artifacts.

## Correctness changes

The new solver maps terminal results generically: an authoritative winner equal
to the root actor is `WIN`, a winner equal to the opponent is `LOSS`, and a
winner-less terminal is `DRAW`. This fixes the prior CHECKMATE-only mapping,
including `PERPETUAL_CHECK` winner semantics. `ONGOING` alone continues the
search.

The proof search remains exact over `LOSS < DRAW < WIN`. It evaluates every
root action, refuses node/depth caps and active-stack cycles, keeps full state
and history in its identity key, and records terminal-status counts,
repetition/perpetual-check adjudications, legal successor counts, and cap or
proof-cutoff statistics. Its bounded TT distinguishes `EXACT`, `LOWER`, and
`UPPER` entries; extremal proof cutoffs are promoted to exact only when the
three-valued minimax result is mathematically established.

## Verification

The focused F23K suite covers checkmate, stalemate, repetition/max-ply draw
mapping, perpetual-check winner/loss mapping, node/depth/cycle refusal,
deterministic certificates, and differential parity against historical F23E
and F23G cases. All tests pass. The fixed capability matrix covers one
representative from each non-control F23J construction family plus one
historical auxiliary control. All six rows preserve legacy parity; the
control solves with the deep budget, while the five non-control rows remain
explicitly unresolved at the fixed shallow diagnostic budget. No evaluator,
ADR-040 feature, F23F/F23I coefficient, Shogi, AlphaSho, or production search
path was used.

The bounded capability gate therefore fails: the new solver has not yet
demonstrated exact solving in four independent non-control families. This is a
capability result, not a correctness failure and not permission to relax the
reference contract.

## Decision

Keep V6 unchanged, do not create V7, do not fit Evaluator V2, and continue with
F23L exact-reference efficiency/history foundation work. The next phase may
improve proof efficiency and history-aware exact search, but must preserve the
legacy oracle, winner-generic terminal semantics, complete root-action
certification, and explicit unresolved outcomes.
