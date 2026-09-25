# GenericChess agent policy

This file is the sole policy authority. Work only in
`GenericChess-sandbox`; preserve unrelated changes. Keep one registered
Worker, Courier session, worktree, and Heavy job. Never create a replacement
Courier request, browser, or worktree except for an explicitly authorized
supersession of a proven unsubmitted request. Replace a Worker only under the
Goal-blocked or three-refusal rule below. Generated binaries, raw benchmarks,
Courier runtime, and transient evidence stay out of Git. Publish only tested
checkpoints to `origin/sandbox` and verify the full remote SHA. Never use
Gmail, `gc-bridge`, a background Courier daemon, WSL, or a bypass transport.

## Current mainline route

Priority 1 is to derive material scores from complete executable game-rule
semantics and test whether the resulting relative values agree, within
reasonable scale-invariant tolerances, with accumulated human material-value
experience. Develop and diagnose the generic prior with a zero-game static
Western Chess benchmark, using Standard Shogi as a retention control. If the
prior passes those tests, evaluate the frozen formula on Xiangqi as a new
holdout before considering further games. Do not replace the production
evaluator merely because an isolated prior has been implemented.

Each term used to calculate a piece's score must have an explicit scientific
or game-theoretic explanation that applies across games. Derive it from rule
consequences such as executable quiet and capture movement, occupancy and
blocking, reachability, restricted regions, directional asymmetry, promotion
or other state transitions, and drop or re-entry options where applicable.
Piece labels and game names may identify results but must not change the
formula or its coefficients. Explain every universal coefficient, weighting,
normalization, or discount from a general principle before comparing scores
with human references. Record the separate rule-derived components for each
piece so that the reason for its score can be audited.

Human material values are validation targets only. Never import them into the
score calculation, fit coefficients to them, or add piece-specific or
game-specific corrections to reach a target ratio. Engineering convenience,
project milestones, a benchmark pass condition, or a desire to make numbers
look right are not scientific reasons to change a piece's score. If a generic
formula fails a frozen human-agreement gate, report the component-level
failure and test a new general rule-derived hypothesis; do not patch that
piece's value to force a pass. Conditional rules must appear in the semantic
ledger even when a generally justified model gives them negligible weight.

Reliable human material values are scarce independent evidence. Do not use
them to optimize even a small set of generic weights, a parameter matrix, a
threshold, or a discount, directly or through repeated selection of the
best-matching candidate. A failed comparison may reveal which rule consequence
the model misses or exaggerates, but the next formula and every numerical
choice must follow an independently stated scientific or game-theoretic
argument. Once a game's human values have been inspected, label that game as
diagnostic evidence rather than an untouched holdout; seek a new, previously
unseen ruleset for independent confirmation of a revised frozen formula.

Priority 2 starts only after Priority 1 yields a satisfactory frozen prior:
test whether the generic RuleSet/ABP path has a meaningful node-efficiency or
practical move-choice disadvantage against mature fixed Chess and Shogi
Alpha-Beta implementations under controlled equal-node conditions. The old
sigma-.70 score-race Gen1/Gen2 route is deferred; it does not authorize new
Arena, self-play, mutation, or Heavy work. F143 remains stopped and is not to
be continued, published, or closed out as mainline. Search compression,
TreeStrap, policy-distillation, Gumbel-MCTS, learned ordering, and related
expansions remain secondary without a new evidence-based work order.

## Experimental selection

At the start of every research order, state in ordinary prose the current
single unknown variable, the minimal direct observation that can test it, and
why full games are or are not needed. Label the order `CAUSAL_DIAGNOSTIC` or
`STRENGTH_BENCHMARK`. This is prose guidance only: do not add schema fields,
state-machine stages, IDs, SHA gates, approval commands, or audit material.

## Worker loop

The Supervisor remains responsible for continuity. A refusal counts only
when the Worker declines or stops work without one of the legal stop
conditions below, after receiving a clear continuation instruction. Count
three distinct consecutive refusals, not three hourly observations of the
same stopped turn. A resumed work turn resets the count. On the first such
stop, continue the same Worker using gpt-6-luna / high and require it to
enable or resume a persistent Goal in its own task. After the third
consecutive refusal, retire the old Worker, delete its task if the app
supports deletion, and register exactly one new Worker using gpt-6-luna /
high with an active persistent Goal. If the app offers only archive, archive
the old task and tell the user explicitly that it was not deleted. Preserve
the existing Courier session and immutable request, worktree, evidence, and
Heavy state during the replacement. If the Worker's Goal is actually marked
blocked, replace the Worker immediately without waiting for three refusals.
Do not infer a blocked Goal from an idle task, a Courier escalation, or an
unavailable Goal status. Ordinary errors and temporary waits do not justify
asking the Worker to stop or enter Supervisor HOLD; keep its Goal active and
continue independent authorized work while the Supervisor repairs the issue.
A legitimate stop or severe harness failure is not a refusal; the Supervisor
must keep investigating and report the actual blocker. The Supervisor does
not enable Goal for itself.

Use the existing Courier request in a loop: obtain the next order, implement
it, test it, commit it, publish it, close it out, and obtain the next order in
the same turn. A phase result, wait, context compression, or recoverable error
is not a stop. A phase-level result continues to the next work order. Stop
only for explicit whole-project completion, user stop, active Supervisor HOLD,
ownership conflict, or uncertain irreversible effect. A severe harness failure
pauses only the affected operation while the Supervisor repairs it; it does
not by itself block the Goal or halt independent authorized work. Retry
ordinary transport faults with the same immutable request once before
escalation; supersede a proven unsubmitted request only on explicit user
authority and preserve its evidence.
A Chat `COMPLETE` closes the whole project only when the response explicitly
says no further GenericChess work is needed.

## Compute and promotion

Use `generic-chess-flow.cmd heavy` or `heavy-start` for long tests and Arena
runs, with one declared resource envelope and never two Heavy jobs. Promotion
is fail-closed: clean synchronized trees, successful required tests, an exact
tested and published candidate SHA, explicit promotion approval, and
fast-forward only.
