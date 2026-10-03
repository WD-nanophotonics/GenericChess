# Common-context exchange result: complete, conditional differentiation

The [frozen protocol](SECURED_EXCHANGE_COMMON_CONTEXT_PROTOCOL.md) was written
and SHA256-checked before execution. Protocol hash:
`18c1d2a420487149ef1fcfcaf22a2e433dd2c2dd06c9ffbe60f12547ecec542f`.
Execution base was sandbox `22f8a538594d3a37fb28e36299beec345a79f05f` plus the
new script whose hash is retained in the output. No human material reference,
Xiangqi holdout, fitting or horizon adjustment was used.

## Observed result, 2026-10-03

All 15 predeclared Chess/Standard Shogi roots were valid and ongoing. Every
focal legal action and opponent reply was evaluated, including quiet and refuted
actions, without success cutoffs. Core streaming checkpoints and the external
35-second timeout remained active. The run completed in 0.469 s with 1,973
materialized legal transitions, below the 30-second/20,000-transition cap.
The transition cap counts all materializations, a conservative bound on distinct
transitions. Budget failure returns no complete score; it is never labelled draw.

| Game/type | Diagonal open | Orthogonal open | Diagonal defended | Equal-mass score |
| --- | ---: | ---: | ---: | ---: |
| Chess B | 1 | 0 | 0 | 1/3 |
| Chess R | 0 | 1 | 0 | 1/3 |
| Chess Q | 1 | 1 | 0 | 2/3 |
| Standard Shogi B | 1 | 0 | 0 | 1/3 |
| Standard Shogi R | 0 | 1 | 0 | 1/3 |

The prediction was stated before execution and survived complete enumeration.
Queen's score combines two useful modes without weighting the number of actions;
the diagonal defender refutes the apparently available capture. This extends the
earlier selected-action witness to best choice over every focal action under a
single common physical-context mixture. It confirms task-level differentiation
and inexpensive enumeration in this sparse scope, not a useful material prior.

The raw output preserves each root's position key, every focal action, complete
reply count, success flag and first refutation (action, custody delta, terminal).
See `data/secured_exchange_common_context_20261003.json`. Source/protocol hashes
and golden reproduction tests bind this evidence to the declared experiment.

## Decision and limits

Retain this task as a conditional candidate; do not install these three scores
as engine material values or compare them to human references. The successful
cost/contract check removes one small implementation uncertainty. The experiment
does not choose or validate the context law. It samples five long-range types,
three motifs and sparse synthetic boards; held/promoted/Pawn/Knight and dense
blocking distributions are not covered. Equal-token custody and two-ply success
still differ from full-game utility and additive leaf evaluation.

In this support the defended motif contributes no successes for any type. Its
weight therefore affects raw magnitude rather than relative differentiation;
the B/R relation comes entirely from the two open motif masses. This follows
directly from the observed per-context table, not a new fitted formula. No weight
sweep or reweighting toward material agreement is warranted.

An explicit test moves the nonmoving Chess king onto Bishop's attack line:
that root is invalid and is rejected rather than discarded or scored zero.
Thus extending the common law to all physical placements still needs a declared
treatment of invalid, type-dependent configurations. Common-support conditioning
is itself a modelling assumption, not evidence supplied by this pilot. Before
larger computation, settle the population definition and verify its independent
motivation, coverage and cheap evaluation contract. Do not enlarge this motif
set just to tune its scores or repeat local recapture checks.
