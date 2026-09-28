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

## Current direction boundary

The scoped RuleSet prerequisite is frozen. The existing rule-only scalar
family and AMTU candidate were negative within their declared tests; neither
authorizes an arbitrary replacement formula. The later computation-free
neutral-kernel proposal also stopped at `UNDERDETERMINED`: rule-preserving
symmetry and transition support do not uniquely choose a transition kernel
or the mass among multiple reachable recurrent classes. Chat accepted this
result in the reply to `GENERICCHESS-20260928-063632-e9f42e86` and issued no
further Worker order. The current research phase is closed, not the project.

Do not repeat kernel, horizon, entropy, conductance, class-weighting, or
identity-only probes for the same uncertainty. A new rule-derived principle
must either justify the missing statistical choices independently or avoid
that statistical object. No human material references, numerical fitting,
Arena, or Heavy are authorized by the closed proposal. Absence of an order is
not a reason to repeat the same Courier message or generate status-only turns.

## Latest structural result and next direction

The bounded simulation-dominance diagnostic was closed through Courier request
`GENERICCHESS-20260928-065828-1158d5b3`. Chat accepted
`SIMULATION_DOMINANCE_CONTEXT_DEPENDENT`: executable RuleSet semantics yield a
sound, nontrivial *context-indexed* alternating-simulation partial order, but
the same piece-type pair can reverse order in different legal contexts. It
does not yield a context-independent material scalar. A scalar would need an
additional justified context comparison or aggregation principle. Preserve
this positive structural fact and its limit; do not turn dominance counts,
uniform contexts, a neutral transition kernel, or another unmotivated choice
into a score.

The project does not require proof that a scalar formula is uniquely forced
by the rules. It requires a general, scientifically explained, cheap prior
whose terms and numerical choices are stated before human-value comparison
and tested without fitting those scarce references. Stop the sequence of
abstract uniqueness probes about kernels, measures, or aggregation unless a
new independent game-theoretic principle supplies the missing choice.

Subsequent bounded diagnostics established that immediate legal recapture and
capture-to-hand resource persistence are genuine semantic consequences that
the frozen board-only U/C components do not directly express. Neither alone
established the direction of a material-value error without an extra context
or strategy assumption. Chat then accepted `SHOGI_REAL_SUPPORT_FILTER_NOOP` in
the reply to `GENERICCHESS-20260928-081653-26081f4d`: every relevant Standard
Shogi drop seed has a real rule source, so filtering fictitious drop support
does not change this ruleset's support sets or explain its scalar failure.
Close the exchange-survivability attribution, hand-resource eligibility, and
drop-seed filtering routes on this evidence. Do not issue another small
"find one omitted feature" order merely because the previous one was negative.

The next bounded mainline step is one *model-design synthesis*, owned by Chat
and executed by the Worker through the existing Courier session. Compare the
recorded failure modes of the existing scalar families with rule-derived
material-prior literature, especially the scope and limitations of Pell's
METAGAMER. Propose at most one complete, inexpensive, game-name-independent
scalar-prior hypothesis. State its general game-theoretic assumptions, the
meaning of every term and numerical choice, and one smallest synthetic RuleSet
counterexample that could falsify it before consulting human values. A
scientifically justified prior need not be mathematically unique. If no such
hypothesis survives this review, report the exact missing modeling assumption
and stop this design round rather than searching another feature. This is a
read-only design gate, not permission to implement or benchmark a new formula.
Chat should narrow it to a finite order and time bound. Human material values
remain validation evidence only: no fitting, no new Chess/Shogi reference
values, no Xiangqi material values, no Arena/Heavy, publication, or promotion.
The frozen Xiangqi holdout is preserved.
