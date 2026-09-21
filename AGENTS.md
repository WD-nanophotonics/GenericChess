# GenericChess agent policy

This file is the sole policy authority. Work only in
`GenericChess-sandbox`; preserve unrelated changes. Keep one registered
Worker, Courier session, worktree, and Heavy job. Never create a replacement
request, Worker, browser, or worktree. Generated binaries, raw benchmarks,
Courier runtime, and transient evidence stay out of Git. Publish only tested
checkpoints to `origin/sandbox` and verify the full remote SHA. Never use
Gmail, `gc-bridge`, a background Courier daemon, WSL, or a bypass transport.

## Current mainline route

Standard Shogi comes first. Use the fixed ABP/search/checkmate/ordering/
quiescence/TT stack. The evaluator is material score only: Anchor and King
are fixed at zero, with one learnable value per ordinary/promoted piece type.
Start from bad or random material values and optimize the small material vector
directly from self-play/Arena wins using the simplest interpretable mutation
plus champion-selection/evolution strategy.

Do not use teacher loss, Q regression, search compression, PST, learned policy,
nonlinear evaluators, or a proxy objective as the primary objective. Human
material values are sanity checks only. First use the user-authorized Arena
score race as behavioral fitness: each non-anchor capture is +1, each checking
move is +1, capture+check is +2, and the first side to 10 wins; formal Core
decisive outcomes take precedence. Use fresh paired role-swapped openings and
keep this score independent of material values. Require score-race `Gen1 >
Gen0`, then `Gen2 > Gen1`, before full-game Standard Shogi validation. If this
minimal benchmark fails, diagnose that failure instead of adding a more
complex learner.

F143 is stopped and is not to be continued, published, or closed out as
mainline. Search compression, generic evaluator work, TreeStrap,
policy-distillation, Gumbel-MCTS, learned ordering, and related expansions are
secondary and must receive no further work orders unless the new material-only
benchmark later proves they are required.

## Worker loop

Use the existing Courier request in a loop: obtain the next order, implement
it, test it, commit it, publish it, close it out, and obtain the next order in
the same turn. A phase result, wait, context compression, or recoverable error
is not a stop. Stop only for explicit whole-project completion, user stop,
active Supervisor HOLD, ownership conflict, uncertain irreversible effect, or
severe harness failure. Retry ordinary transport faults with the same
immutable request once before escalation; never create a replacement request.

## Compute and promotion

Use `generic-chess-flow.cmd heavy` or `heavy-start` for long tests and Arena
runs, with one declared resource envelope and never two Heavy jobs. Promotion
is fail-closed: clean synchronized trees, successful required tests, an exact
tested and published candidate SHA, explicit promotion approval, and
fast-forward only.
