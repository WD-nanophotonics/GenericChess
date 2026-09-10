# GenericChess theory roadmap

This is the compact theory baseline for evaluator, learning, self-improvement,
and playing-strength decisions. It is a route-selection document, not a claim
that any cited method is already implemented. The current empirical carryover
is that nonlinear value capacity alone was insufficient: F58 improved the
intermediate value fit in Shogi but severely damaged transfer to the action
chosen by search.

## Authority hierarchy

Use the following order when diagnosing a learning change:

* **T0 correctness:** legal actions, state transitions, perspective/sign,
  terminal semantics, Native/Python parity, and reproducibility.
* **T1 teacher action spectrum/action gap:** teacher stability, top-action
  identity, pairwise ordering, regret, and the gap between the best and nearby
  actions.
* **T2 state distribution:** whether the fitted states resemble the states on
  which the evaluator will make decisions, including self-play and PV corridors.
* **T3 supervision objective:** pointwise value fitting versus pairwise ranking,
  policy distillation, or a decision-focused regret objective.
* **T4 representation architecture:** feature sufficiency, invariances,
  capacity, and regularization after T1--T3 are controlled.
* **T5 runtime and arena strength:** speed, completed depth, nodes, paired
  strength, and only then broader deployment conclusions.

State-value MSE is an intermediate diagnostic. Higher-authority signals for a
search policy are teacher action regret, action ranking, policy improvement, and
paired strength. A lower MSE does not establish any of those outcomes.

## Source map

Each entry states the consequence for GenericChess. URLs are canonical public
paper pages.

### 1. TDLeaf(lambda): Combining Temporal Difference Learning with Game-Tree Search

**Authors:** Jonathan Baxter, Andrew Tridgell, Lex Weaver.  
**URL:** <https://arxiv.org/abs/cs/9901001>

**Core idea:** combine temporal-difference learning with minimax search by
learning from leaf evaluations and eligibility traces.  
**GenericChess relevance:** this is the conceptual ancestor of the frozen
TDLeaf/self-play trajectory path.  
**Diagnostic/design consequence:** keep leaf/root perspective and trace
  semantics explicit; test that a better leaf value does not silently change
  the search objective or action-sign convention.

### 2. Increasing the Action Gap: New Operators for Reinforcement Learning

**Authors:** Marc G. Bellemare, Georg Ostrovski, Arthur Guez, Philip S. Thomas,
Rémi Munos.
**URL:** <https://arxiv.org/abs/1512.04860>

**Core idea:** action-gap increasing transformations can improve robustness of
  value-based action selection under approximation error.  
**GenericChess relevance:** small score errors matter chiefly when they reorder
  close legal moves.  
**Diagnostic/design consequence:** measure action gaps and regret by gap
  quartile; do not use aggregate MSE as the sole policy-risk proxy.

### 3. Classification-based Approximate Policy Iteration: Experiments and Extended Discussions

**Authors:** Amir-massoud Farahmand, Doina Precup, André M. S. Barreto,
Mohammad Ghavamzadeh.
**URL:** <https://arxiv.org/abs/1407.0449>

**Core idea:** approximate policy iteration can separate value estimation from
  classification/policy improvement over actions.  
**GenericChess relevance:** a search engine consumes an ordering/choice, not a
  scalar in isolation.  
**Diagnostic/design consequence:** add explicit policy-side gates (top-1,
  regret, ranking) before considering a learned evaluator deployable.

### 4. Thinking Fast and Slow with Deep Learning and Tree Search

**Authors:** Thomas Anthony, Zheng Tian, David Barber.
**URL:** <https://arxiv.org/abs/1705.08439>

**Core idea:** Expert Iteration uses tree search as an expert to produce policy
  improvement targets and a learner to generalize them.  
**GenericChess relevance:** the 80k search is an expert surface, while v2/v4
  are learners evaluated through weaker search.  
**Diagnostic/design consequence:** compare learner actions against the expert's
  action spectrum and preserve a held-out policy surface, not just held-out
  scalar targets.

### 5. Mastering Chess and Shogi by Self-Play with a General Reinforcement Learning Algorithm

**Authors:** David Silver et al.  
**URL:** <https://arxiv.org/abs/1712.01815>

**Core idea:** AlphaZero couples self-play reinforcement learning with a
  policy/value network and Monte Carlo tree search.  
**GenericChess relevance:** strength is a closed loop between representation,
  search distribution, targets, and evaluation.  
**Diagnostic/design consequence:** treat state distribution, search budget, and
  action policy as first-class experimental variables; do not extrapolate from
  offline MSE to self-play strength.

### 6. Targeted Search Control in AlphaZero for Effective Policy Improvement

**Authors:** Alexandre Trudeau, Michael Bowling.
**URL:** <https://arxiv.org/abs/2302.12359>

**Core idea:** search-control choices alter the state distribution and the
  resulting policy improvement; targeted search can focus computation where it
  changes decisions.  
**GenericChess relevance:** D0 random, D1 v2 self-play, and D2 v2 PV-corridor
  states are plausible but different policy surfaces.  
**Diagnostic/design consequence:** compare distributions before changing the
  model, and report distribution-sensitive teacher stability, gaps, and regret.

### 7. A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning

**Authors:** Stéphane Ross, Geoffrey Gordon, Drew Bagnell.  
**URL:** <https://arxiv.org/abs/1011.0686>

**Core idea:** DAgger reduces covariate shift by querying the expert on states
  visited by the learner and aggregating those examples.  
**GenericChess relevance:** a v2-generated state distribution can differ from a
  random reachable corpus or from a deeper-search PV corridor.  
**Diagnostic/design consequence:** quantify distribution mismatch before
  attributing policy failure to architecture; later data collection may need
  learner/on-policy states.

### 8. Learning to Search Better Than Your Teacher

**Authors:** Kai-Wei Chang, Akshay Krishnamurthy, Alekh Agarwal, Hal Daumé
III, John Langford.
**URL:** <https://arxiv.org/abs/1502.02206>

**Core idea:** learning-to-search objectives can optimize the learner's future
  decisions rather than merely imitate a teacher's action.  
**GenericChess relevance:** v4 may be a numerically different evaluator whose
  weak-search action is worse even when its fitted values look better.  
**Diagnostic/design consequence:** distinguish teacher imitation from learner
  regret and evaluate the action actually selected at the deployment budget.

### 9. Decision-Focused Learning: Through the Lens of Learning to Rank

**Authors:** Jayanta Mandi, Víctor Bucarey, Maxime Mulamba, Tias Guns.  
**URL:** <https://arxiv.org/abs/2112.03609>

**Core idea:** decision-focused learning can be viewed as learning to rank
  feasible solutions, with pointwise, pairwise, and listwise losses; controlling
  the candidate subset controls runtime with limited regret impact.  
**GenericChess relevance:** legal actions and independently searched child
  candidates form a concrete feasible-action subset.  
**Diagnostic/design consequence:** on the same action-spectrum split, compare
  pointwise Q, pairwise ranking, and soft policy distillation; report regret and
  ranking before MSE.

### 10. Approximate Modified Policy Iteration

**Authors:** Bruno Scherrer, Victor Gabillon, Mohammad Ghavamzadeh, Matthieu
Geist.  
**URL:** <https://arxiv.org/abs/1205.3054>

**Core idea:** approximate modified policy iteration unifies fitted-value,
  fitted-Q, and classification-based policy iteration, with error propagation
  controlled by the iteration/improvement balance.  
**GenericChess relevance:** evaluator fitting and search-based policy improvement
  are coupled approximate operators.  
**Diagnostic/design consequence:** report where error enters (state fit,
  action selection, or policy improvement) and avoid treating a single fitted
  value pass as a complete policy-iteration result.

### 11. The Value Equivalence Principle for Model-Based Reinforcement Learning

**Authors:** Christopher Grimm, André Barreto, Satinder Singh, David Silver.  
**URL:** <https://arxiv.org/abs/2011.03506>

**Core idea:** a model need only preserve Bellman updates for the relevant
  functions and policies; exact state-transition reconstruction can be more
  than is needed.  
**GenericChess relevance:** the useful fidelity of an evaluator is fidelity to
  the decisions/search updates it supports, not necessarily global scalar
  reconstruction.  
**Diagnostic/design consequence:** prioritize action-regret and search-consistent
  tests; only add representation capacity when the policy-relevant surface is
  demonstrably underfit.

### 12. Deep Learning for General Game Playing with Ludii and Polygames

**Authors:** Dennis J. N. J. Soemers, Vegard Mella, Cameron Browne,
Olivier Teytaud.
**URL:** <https://arxiv.org/abs/2101.09562>

**Core idea:** studies deep learning and general game-playing systems across
  varied games, emphasizing reusable game representations and search/learning
  interfaces.  
**GenericChess relevance:** GenericChess must preserve ruleset-generic behavior
  while supporting very different action spaces and state encodings.  
**Diagnostic/design consequence:** keep ruleset fingerprints and cross-ruleset
  parity gates; any architecture change must prove that genericity did not hide
  a policy regression.

### 13. Policy Improvement by Planning with Gumbel

**Authors:** Ivo Danihelka, Arthur Guez, Julian Schrittwieser, David Silver.
**URL:** <https://openreview.net/forum?id=bERaNdoegnO>

**Core idea:** Gumbel-based planning allocates a fixed search budget to improve
  policy decisions through a structured candidate set and sequential halving.  
**GenericChess relevance:** candidate coverage and budget allocation can change
  the action spectrum seen by the learner even with a fixed evaluator.  
**Diagnostic/design consequence:** freeze the evaluator/search architecture for
F59 and measure spectrum coverage, budget-dependent top-action stability, and
regret before considering a planning redesign.

## Current empirical status after F59

* **T1:** teacher action surfaces are budget-sensitive, but equal-budget
  candidate spectra are usable.
* **T2:** policy-relevant state distributions differ observationally.
* **T3:** learning-objective mismatch remains unresolved.
* **T4:** representation is not currently the leading authorized bottleneck.

## F59 decision protocol

F59 freezes the v2 parent, corrected F58 encoding, and the current v4 Shogi
observational comparator. It builds three state distributions: D0 random
reachable, D1 v2 self-play, and D2 deeper v2 PV-corridor states. For each root,
all legal actions are compared with equal-budget child searches, v2/v4 searches,
and a high-budget teacher; unstable teacher roots are excluded from objective
gates. The primary quantities are teacher regret, top-action/ranking agreement,
and gap-conditioned behavior. Pointwise Q, pairwise ranking, and soft policy
distillation are compared with the representation held fixed and with untouched
action-spectrum holdouts.

The allowed conclusions are diagnostic classifications, not causal claims:
`TEACHER_POLICY_SURFACE_UNSTABLE`, `VALUE_TO_POLICY_OBJECTIVE_MISMATCH_SUPPORTED`,
`POLICY_RELEVANT_DISTRIBUTION_DIFFERS`, `STATE_DISTRIBUTION_MISMATCH_SUPPORTED`,
`REPRESENTATION_REMAINS_PRIMARY`, or a documented mixture. Western is a smaller
sanity diagnostic; F59 does not run AlphaSho.

## Current empirical status after F61/F62

* **F61:** the corrected Gen0 -> Gen1 Standard Shogi mechanism produced a
  confirmed internal paired-strength improvement.
* **F62:** one exact-mechanism Gen1 -> Gen2 replacement re-distillation changed
  4 of 8 fresh search decisions but scored 0.15625 across the frozen 8-pair
  Arena. It therefore did not establish monotonic next-generation improvement.
* **Authority:** equal-budget paired Arena is the strength authority;
  teacher-fit and offline metrics remain diagnostic.
* **Boundary:** the unresolved question is repeatable policy improvement and
  teacher-to-student transfer, not evaluator feature invention. F63 therefore
  tests whether deeper Gen1 search is itself an improving teacher before
  evaluating a bounded champion-retention candidate loop.

## F63-R2 strength-first route update

The old F63 deeper-teacher gate supplied a useful diagnostic signal, but the
long equal-budget common-4 Arena was computationally expensive. The user
redirected and cooperatively paused its incomplete three-seed continuation;
its unequal exposure is historical side evidence only and cannot select a candidate. Future candidate
selection therefore uses a staged strength-first funnel:

1. bounded correctness and cheap search diagnostics;
2. short-horizon middlegame/endgame strength screening;
3. complete 2-pair, then 4-pair, then 8-pair equal-budget Arena stages;
4. a separately approved final confirmation, if warranted.

Teacher agreement, regret, action-spectrum ranking, and scalar fit remain
diagnostic signals. Equal-budget paired game strength is the promotion
authority. The candidate population stays frozen: Gen1
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`, seeds
59011/59012/59013, with 59012 the exact persisted F62 Gen2 and 59011/59013
reconstructed from the same frozen F62 training evidence. No retraining recipe,
evaluator architecture, handcrafted feature family, or external-engine role is
changed.

## F64 zero-compute generation-operator contrast

F64 compared Gen0, accepted Gen1, and all three frozen replacement children on
the same 96 cached F62 action spectra. The children retained Gen1's top action
on 72/96, 72/96, and 71/96 roots, but their centered output correlations with
one another were 0.989--0.991 versus 0.699--0.707 against Gen1. Their maximum
absolute residuals were approximately 240k, versus 20k for Gen1. The evidence
supports replacement forgetting/over-correction on this frozen batch; it does
not classify `59013`, whose strength run was unresolved, as weak.

The route is closed as
`F63_FROZEN_REPLACEMENT_BATCH_NOT_WORTH_FURTHER_STRENGTH_COMPUTE`, with
`GEN1_RETAINED_AS_CHAMPION`. The one selected next mechanism is
`PARENT_RETENTION / BOUNDED_CORRECTION`: preserve Gen1 as an anchor and learn
only a bounded additive correction. This is a design diagnosis, not an
implemented learner or a claim that the mechanism is globally impossible.

## F65 exact blend breakpoint feasibility

Using only the 96 cached F62 action rows, all three frozen replacement
directions have a nonzero safe affine prefix, but each permits only one
diagnostically supported correction before an unsafe transition. The prescribed
tie break selects seed 59011 with virtual `alpha*=0.004315178940`; this changes
only root 44 to the stable/ordinary cached teacher action and preserves all 24
upper-quartile Gen1 decisions. The result is
`BLEND_REUSE_FEASIBLE_BUT_RUNTIME_EXTENSION_REQUIRED`: exact blending of the
different width-32 parent and child networks needs a width-64 concatenation,
while the current Native runtime accepts only width 16 or 32. No blend
checkpoint or runtime extension was implemented.

## F66 analytic fixed-feature output correction

F66 froze Gen1's feature map and solved a one-direction output-weight
perturbation toward the stable/ordinary root-44 teacher action. The exact
safe interval is `[0.144922902134, 1.740628460696)`, with fixed midpoint
`beta*=0.942775681415`; it changes exactly root 44, preserves all 24/24
high-confidence Gen1 actions, and increases the cached residual maximum only
from about 20,303 to 20,513. The classification is
`FIXED_FEATURE_OUTPUT_CORRECTION_FEASIBLE`. The correction fits the existing
width-32 `CompactNonlinearResidual` by changing only `output_weights`; no
runtime extension or checkpoint has yet been created.
