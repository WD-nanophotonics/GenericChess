# task2633 finite-board movement audit

## Question and method

The generator recorded 16/16 raw movement signatures as new against 519 saved
`results/dev_aux` rule files. This audit asks whether that raw novelty survives
the finite 8x8 board geometry. For each piece type and each source square, it
enumerates leap targets and ray targets together with the ray's intervening
squares. It compares those exact movement/path relations with every saved rule
piece type on the same board size. It separately checks initial-piece counts by
owner and whether swapping owners plus rotating every square 180 degrees
reproduces the initial setup.

## Result

The audit scanned 519 saved rule files, covering 86 distinct exact finite-board
piece movement/path behaviors. The 16 generated rules contain 96 piece-type
instances and 79 distinct behaviors (78 among non-anchor types). Sixteen
candidate piece-type instances matched a saved behavior; all are the shared
eight-neighbor `K` anchor. No generated non-anchor type matched any saved type
in this movement-only comparison.

Two additional within-batch collisions show why per-rule raw novelty does not
mean each type is unique: seed2633008 `A` equals seed2633012 `X`, and seed2633010
`X` equals seed2633011 `B` under the exact finite-board movement/path relation.
All16 setups have equal per-type piece counts by owner and pass the exact
owner-swap/180-degree setup symmetry check. Thus this batch provides novel
non-anchor movement behavior within the saved artifact corpus, but does not
vary arbitrary ownership allocation.

## Decision and limits

Retain all16 candidates as outcome-blind generator outputs; do not select by
movement novelty or any outcome and do not treat them as a training/evaluation
pool. The source corpus is not a population sample and excludes built-in
Chess/Western rules. Equality for one piece type does not imply full ruleset
equivalence. The audit does not establish legal reachability after play,
full-history non-exposure, feature/action availability, W/L/D, search, learning,
or strength. A later panel needs a new frozen question and exact-history
exclusion before roots are admitted.

The deterministic machine-readable result is
`finite-board-movement-equivalence.json` (SHA-256
`04af9b455957d813da699bb05e85b855ea71be9f97e31270120105b4f2633f4a`). Two
consecutive executions of the final audit script produced byte-identical
results. It binds the candidate index SHA-256
`1b7d11d7f79040a3641f589a6eaa8ae593cc5ffe0077678f1bc12bc856e05f5e` and saved
input manifest SHA-256
`8ba54cbe0ef88fc9e26191d3f498499e3b54c03c82dccc5140cd2f8f5620e7e3`. The audit
script is `audit_finite_board_movement_equivalence.py`.
