# What a cheap search teacher would have to predict — 2026-10-31

A successful PV, a small certificate, an action's cutoff frequency and the
decision value of another computation are different targets. Current source
does not turn any of them into an identified cheapest-search label.
This source assessment also gives a positive conditional route: predict a
**declared fixed-service proof-completion/cost event**, without pretending that
solver UNKNOWN supplies a latent WDL label. No new model, logger, wrapper,
search policy, training run or PRIMARY mechanism is implemented here.

The actual new terminal evidence remains in
[AUX_NEW_PREFIX_TERMINAL_20261031](AUX_NEW_PREFIX_TERMINAL_20261031.md).
Its one known losing branch is not a strict error of the saved selected action.

## Original sources and exact coverage

[Furtak and Buro2009](https://ijcai.org/proceedings/2009/0089.pdf), sections2/5/6/8,
distinguishes target and minimax proof graphs, gives a known-tree minimum-proof
calculation, and derives a size/cut-probability order in a fixed-window model.
Its practical experiments use synthetic trees and Skat, with tuned combinations;
their node reductions are not GenericChess forecasts. A known full tree/value
input is substantially more information than one saved PV.
Original PDF SHA256211f11ee3cc1f7d699c738be045f62ce8c00ccb527a588073e77ad26032fc07a,
7pages; relevant complete text and PDFpages4/5visually checked. The NP reduction
was read, not independently reproduced. No original PDF/text is republished.

[Hay et al2012](https://proceedings.mlr.press/r10/hay12a.html), sections2-4,
models computation selection using posterior utilities and an explicit
computation cost. Its myopic rule can stop before a useful multi-step sequence;
context can reverse the preferred investigation. Constant cost and independent
actions are explicit restrictions for particular results. We adopt no MCTS,
Go result or numerical runtime bound. PDF
SHA25691d78c7a25ea67dc491a3e03bd90c325f7c2be55d3be58ca4a7f02e4004c6042,
10pages; relevant complete sections and PDFpages4/5visually checked.

Source metadata, exact own arithmetic and limits are in
[data](data/aux_search_teacher_cost_20261031/). These are small exact analytical
controls, not empirical game observations or another theorem/fixture campaign.

## Current consumer and missing cost information

Shared product source is sandbox480b01b7e3df1fb6a147edc40d05cfc7aa286b90;
the inspected orderer, search, TT and Runtime paths are unchanged locally.

MoveOrderer optionally uses(cutoffs+1)/(entered attempts+2) to reorder eligible
quiet slots. It contains no per-action subtree-cost estimator. The attempt is
recorded before child negamax; PVS re-searches count only once, but an interrupted
entered child need not produce a completed cutoff outcome. This is an existing
heuristic, not an asserted calibrated probability or a product defect.

TTEntry stores key,depth,score,bound,best_action,generation, not subtree cost.
SearchStatistics has aggregate generation/evaluation/ordering measurements.
Those aggregates do not identify the cost of unsearched alternatives or the
counterfactual marginal cost under another order/TT state.

The root legal-action list is available. A candidate CHILD's legal out-degree
generally is not: computing it can require a push and another full child
frontier, or an actually retained earlier count. The current Runtime legal cache
is position-local and restored on pop, not an all-child cost table. The paper's
already-expanded child counts therefore cannot simply be called free here.
Section8 of the original paper explicitly reuses expanded-node annotations
from the previous iterative pass and randomizes still-unexpanded children.
Its practical weighted combination is not a pure ratio-only policy. A future
caller with retained child counts could reuse them; this finding does not
require proactively expanding every child or adding a cost logger.
This is a source distinction, not a new timing measurement.

## Proof size and proof verification can prefer different actions

The previous source-derived accepted ordinary-certificate replay count is
N*h0 + sum(depth_i), where h0 is the authoritative root-prefix length.
It counts direct Session submissions, not CPU cost or solver discovery work.
Here h0 means the FULL authoritative GameRecord action count. It is not the
new terminal packet's lifecycle prefix label, which omits its three-action
opening. The concrete witness has h0=4despite metadata prefix=1. No cost
comparison between the abstract tree shapes and that actual witness is claimed.

Consider two ABSTRACT valid alternating proof-tree shapes. A shallow tree has
one defender node with four replies, each followed by a winning move:
N=10, depthsum=21, rank3. A narrow single path has N=8,depthsum=28,rank7.
Their replay counts are10*h0+21 and8*h0+28. At h0=0 the shallow tree costs21
versus28; at h0=4 it costs61versus60. Cardinality, mate depth and replay count
can disagree, even before adding unsuccessful search branches and real Core
cost. These shapes are not newly realized Leaper games or a speed experiment.
Neither a winning PV nor one emitted certificate identifies the cheapest
undiscovered proof in an actual root.

## A cutoff label depends on its window, context and overhead

For two independent, fixed-cost tests i,j at a fixed cut-node window, expected
work is c_i+(1-p_i)*c_j. Swapping saves p_j*c_i-p_i*c_j. Any added feature,
inference and reordering cost H must fit below that saving in the SAME cost
unit. For(c_i,p_i)=(10,.9),(c_j,p_j)=(1,.5), gross saving is4.1; an overhead5
reverses it. These are exact abstract costs, not measured milliseconds.

A pooled marginal ratio does not handle arbitrary correlations. In two
equiprobable input types, a and b both cut in one type, while only c cuts in
the other. Costs are a=1,b=.9,c=1.1, all marginal cut probabilities=.5.
The ratio order b,a,c costs1.95 on average; b,c,a costs1.45. After b fails,
a's conditional cut probability is0and c's is1. This qualifies the fixed-product
expectation; it does not claim the source proved a universal correlated-case rule.

Nor does a cut-node result solve full-window ROOT ordering. For a MAX root with
MIN children A=[3,4] and B=[2,100], standard left-to-right alpha-beta uses3
leaf evaluations for AthenB versus4for BthenA. Both root actions are examined
and neither cuts the infinite root beta: the saving comes from alpha tightening
in a later child. A universal per-move cutoff label misses that context.

Cache state is another source of changing marginal work. Abstract AND
obligations A={X:10,Y:3},B={X:10,Z:5} cost13versus15cold; with Z already
available they cost13versus10. This is no current verifier timing claim.
Actual mature Player/TT lifecycle, not a board-only immutable cost label, is
the appropriate consumer context.

## Multi-step value can be positive when one-step value is zero

Own exact epistemic example: a known DRAW fallback has utility0. Another action
is WIN+1only when two independently unknown bits are both1, otherwise LOSS-1.
Each bit is equally likely0or1and can be revealed at abstract payoff-cost.05.
One reveal cannot improve the best posterior mean, so a myopic rule stops.
Revealing the first bit, then the second only when the first is1, achieves
expected selected payoff.25, expected1.5computations and net utility.175.
This is an analytical hypothesis about delayed useful evidence, not a calibrated
prior, algorithm or new Leaper solve. It prevents a blanket inference from
one-step non-improvement to uselessness of every bounded proof phase.

A separate exact recalculation of the source's two-uncertain-action context
example gives investigation values(21/20,81/80)when the known alternative is0,
and(91/80,6/5)when it is1. The initial best posterior mean stays1in both cases,
yet the preferred first investigation reverses. These Qvalues include the
option to investigate the remaining arm after the first result, rather than
just a single observation followed by compulsory stopping. A scalar best estimate alone
does not identify the computation worth doing.

The paper's cost is expressed in utility units. No milliseconds-to-WDL conversion
is supplied here. Under the project's matched-service objective, fallback
opportunity cost must instead be assessed under that same whole service; seconds
cannot be subtracted from WDL. Hard resource/user limits remain binding.

## A useful operational target need not be game-theoretic value

Three possible supervised operational targets are distinct:

- Solver returns a proof at its declared allowance.
- A proof is independently verified and usable by the actual decision service.
- Actual charged wall/CPU is consumed under the declared complete policy.

Those can have observable outcomes even when latent full-history WDL remains
unknown. They do not authorize converting UNKNOWN to LOSS/DRAW, dropping lost
returns, treating every emitted certificate as usable, or making oracle-selected
experiential starts. Solver-only, checker and physical selection/commit labels
must stay separate.

Consumed service also differs from unlimited time-to-proof. Two equal-mixture
laws with latent solve times[1,3]and[1,100]produce the same observed[1,2]spent
times and SUCCESS/UNKNOWN returns under a2second cap. Mean charged service is1.5
in both; the unlimited solve-time means are2and50.5. Regressing the cap as an
uncensored solve-time label would answer the wrong question.

A context- and budget-conditioned prediction of usable proof completion is
therefore a legitimate FUTURE supervised hypothesis, separate from material
value learning. Real matching receipts, a cheap actual caller and an honest
prospective test are still needed to judge usefulness; no universal precision
or full-WDL prerequisite is imposed. The present review supplies no calibrated
predictor, counterfactual solver dataset or new implementation request.

## Decision

Close the unqualified cheapest-PV/cheapest-certificate teacher idea. Retain the
operational completion/cost hypothesis as a conditional alternative, not an
automatic new campaign. Reuse existing PN, verifier, full typed Player and
ordering controls if an actual published consumer makes it useful. PRIMARY owns
its current implementation/producer; AUX has not duplicated it. More abstract
controls or another instrumentation framework are not the next task.

## Independent closing review

Exact Fraction arithmetic independently checks all four existing proof replay
rows, six existing correlated-world order costs and both two-arm context
decisions. A separate finite-belief Bellman recursion confirms the four saved
adaptive Qvalues; it does not introduce new priors or cases.
[Review receipt](data/aux_search_teacher_cost_20261031/arithmetic-review.json).

Theorem6.1's statement does not spell out statistical independence, while its
displayed product expectation requires suitable factorization and unchanged
conditional subtree cost. Our report uses that qualified model. The correlated
example identifies the boundary of using pooled marginal probabilities in this
project; no distribution-free practical optimality is attributed to the source.

The actual TT fields and aggregate statistics still contain no retained
per-action subtree cost or expanded-child degree table. Runtime legal cache
restores the parent cache on pop and discards that child's tuple from the live
slot. These source facts identify an information gap, not a mandate to build
instrumentation or evidence that the existing heuristic is defective.

Fresh alternatives at this checkpoint are explicit in the review receipt.
Training from cheapest-PV labels still lacks an actual cost target; adding a
second continuation orderer duplicates an existing component and PRIMARY's
single-policy task; refilling the terminal study would violate its closed cap.
These are execution decisions grounded in current sources, not indefinite
research bans or a request for renewed approval. New compatible consumer
evidence can change the next selection. No current option justifies more
examples, an extra caller, another observer campaign or old-data relabeling.
