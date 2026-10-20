# Side-1 generated-semantic search matches reference minimax — 2026-10-20

## Question

Does public AlphaBeta preserve side-to-move score orientation and optimal-action
selection on an ongoing generated-semantic position after a real transition?

## Method and result

Reuse the generated 7x5 rectangular cannon fixture and apply its first legal
semantic action, yielding an ongoing root with side 1 to move. At fixed depth 2,
compare the public result with reference minimax and the set of reference-optimal
root actions, while validating the PV and preserving the submitted root. The
caller returns score -100, an optimal legal action, depth 2, and an unchanged
root. This confirms one opposite-side generated-semantic caller contract; no
score-orientation defect was observed.

## Limit

This uses one fixture, evaluator and depth, without Native search. It is not a
claim of all-ruleset parity, general playing strength or backend equivalence.
No engine change is warranted by this result.
