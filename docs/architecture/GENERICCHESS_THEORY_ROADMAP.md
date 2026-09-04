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

### 2. Increasing the Action Gap: A Unifying Perspective on Asymmetric Losses

**Authors:** Marc G. Bellemare, Georg Ostrovski, Arthur Guez, Thomas Schaul,
Remi Munos.  
**URL:** <https://arxiv.org/abs/1512.04860>

**Core idea:** action-gap increasing transformations can improve robustness of
  value-based action selection under approximation error.  
**GenericChess relevance:** small score errors matter chiefly when they reorder
  close legal moves.  
**Diagnostic/design consequence:** measure action gaps and regret by gap
  quartile; do not use aggregate MSE as the sole policy-risk proxy.

### 3. Classification-based Approximate Policy Iteration

**Authors:** Mohammad Ghavamzadeh, Alessandro Lazaric, Rémi Munos.  
**URL:** <https://arxiv.org/abs/1407.0449>

**Core idea:** approximate policy iteration can separate value estimation from
  classification/policy improvement over actions.  
**GenericChess relevance:** a search engine consumes an ordering/choice, not a
  scalar in isolation.  
**Diagnostic/design consequence:** add explicit policy-side gates (top-1,
  regret, ranking) before considering a learned evaluator deployable.

### 4. Thinking Fast and Slow with Deep Learning and Tree Search

**Authors:** Thomas Anthony, ZhengTian, David Barber.  
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

### 6. Targeted Search Control in AlphaZero

**Authors:** Maxime Trudeau, Michael Bowling.  
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

### 8. Learning to Search Better than Your Teacher

**Authors:** Ching-An Cheng, Xuefeng Bai, Yaser Abbasi-Yadkori, Wei-Lun Chao,
Wei Chai, Bo Li, et al.  
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

**Authors:** Cameron Browne et al.  
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

**Authors:** Daniil Shaposhnikov et al.  
**URL:** <https://openreview.net/forum?id=bERaNdoegnO>

**Core idea:** Gumbel-based planning allocates a fixed search budget to improve
  policy decisions through a structured candidate set and sequential halving.  
**GenericChess relevance:** candidate coverage and budget allocation can change
  the action spectrum seen by the learner even with a fixed evaluator.  
**Diagnostic/design consequence:** freeze the evaluator/search architecture for
  F59 and measure spectrum coverage, budget-dependent top-action stability, and
  regret before considering a planning redesign.

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

