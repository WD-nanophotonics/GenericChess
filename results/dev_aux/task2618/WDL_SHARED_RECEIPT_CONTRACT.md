# Task2618 WDL adapter contract for the shared receipt runner

This is an implementation contract, not a registered protocol or experiment.
It makes explicit why the historical task2568 WDL timing cannot be treated as
the final common-path timing.

## Existing interfaces

- Task2612 attempt-4's common path uses `ChessEnv`, `AlphaBeta(2, 0)` and
  `Receipt`; on every turn it routes the candidate model for the assigned
  learner color and the fixed opponent model for the other color. Both actors'
  nodes are charged to the arm budget.
- TreeStrap consumes complete receipts' internal one-sided samples;
  TDLeafEpisode consumes complete candidate receipts and censors only the
  terminal residual when the game ends UNKNOWN. Task2612's cost-only runner
  already exercises these two learner interfaces under one receipt contract.
- Task2568 WDL does not update from search values. It proposes a one-coordinate
  material change and accepts only if a paired four-game actual-terminal W/D/L
  interval has strictly positive lower bound. Its games currently use
  `TrainingSearch`, so its recorded 4M-node timing is only a historical proxy
  for the task2612 `AlphaBeta`/`Receipt` path.

## Exact behavior to preserve when adapting

1. Initialize from the existing seeded uniform interval, with pawn fixed at 1.
2. For proposal round `r`, change coordinate `1 + r % 4` by multiplying its
   incumbent value by `exp(U[-ln(2), ln(2)])`, using the frozen task2568 seed
   formula. Do not add another proposal or widen the step.
3. Evaluate exactly four episodes from the same eight-ply family root, in order:
   incumbent as White, proposal as White, proposal as Black, incumbent as Black.
   The assigned candidate model controls only its color; the same fixed foe
   controls the other side.
4. Convert actual terminal result to learner reward with color orientation.
   For each UNKNOWN result use `[-1,+1]`; do not treat it as draw. Compute the
   paired interval from known incumbent/proposal rewards and accept iff the
   lower endpoint is strictly greater than zero. An incomplete four-episode
   block is retained as partial/censored and cannot be silently completed.
5. Charge all candidate and opponent search nodes to the same per-arm cap used
   by TreeStrap and TDLeaf. A fixed evaluation panel, not training WDL, remains
   the final strength endpoint.

## Required focused tests and cost measurement

Before registration, port the deterministic proposal and interval arithmetic
without importing task2568's `TrainingSearch` runner; test exact game order,
actor/model routing, color orientation, all-terminal acceptance/rejection,
UNKNOWN interval bounds, partial blocks, and candidate-plus-foe node accounting.
Then run a bounded WDL shared-path cost scan on reserved training-only roots,
with its exact cap and sources frozen first. It may use actual terminal values
internally for proposal acceptance, but must not emit a strength conclusion or
reuse those roots for final training/evaluation. Recompute the final expected
all-in cost from all three methods and evaluation after pinning the exact runner.

The task2618 93.47m estimate currently uses task2568's WDL runtime and is
therefore provisional. Keep the proposed 110m all-in cap; if the revised
expected run reaches 120m, consult Dot before launching the full comparison.
