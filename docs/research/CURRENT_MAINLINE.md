# Current GenericChess research mainline

This document holds the changing research route delegated by `AGENTS.md`.
The latest user instruction and `AGENTS.md` prevail if they conflict with it.
Update this document when the direction changes; do not encode a research
phase in the Worker's persistent Goal objective.

## Rule infrastructure and validation sequence

The user-directed prerequisite is to complete and validate generic executable
RuleSet semantics needed for Chess, Standard Shogi, and Xiangqi, with bounded
reusable primitives for other chess-like variants where evidence identifies a
concrete gap. Finish this rule-infrastructure phase before changing or
benchmarking material scores. Keep each new rule primitive game-name-independent
and test its smallest direct consequence; do not turn this prerequisite into
open-ended product or strength work. Reading Xiangqi rules and testing legal
moves is necessary for RuleSet coverage and does not consume the later
*material-value* holdout. Do not inspect Xiangqi human material values, tune a
score formula against them, or select score coefficients from Xiangqi outcomes
before a formula is frozen. If later value-based diagnostics influence a
formula, mark that ruleset as diagnostic and use a different untouched ruleset
for independent confirmation.

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
with human references. Record separate rule-derived components for each piece
so the reason for its score can be audited.

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

## Current direction decision

The captured Chat reply to request `GENERICCHESS-20260928-042453-357b78f5`
contains no work order. It reports the scoped RuleSet prerequisite frozen,
the existing rule-only scalar family and AMTU candidate negative within their
declared tests, and a missing canonical stationary typed measure. This is a
phase boundary, not whole-project completion. Do not repeat those tests or
infer that an arbitrary new formula is authorized.

The Supervisor authorizes one bounded, computation-free *theory proposal* as
the direction to return through the same Courier session: examine whether
rule-preserving symmetries and a game-independent neutral transition process
can define a canonical distribution over executable piece states. The object
to define is the distribution, before any material score or coefficient is
chosen. The single unknown is whether those principles determine it without
game-specific assumptions; the minimal observation is a written argument or
small counterexample from existing RuleSet semantics. No human material
references, new games, numerical fitting, code, Arena, or Heavy are needed.
Stop this proposal after one explicit construction or one counterexample;
ask Chat to turn the result into a bounded order or to identify the exact
remaining scientific decision. This direction does not pre-approve a score
formula or change a frozen holdout.
