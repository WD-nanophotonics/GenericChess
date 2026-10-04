# Partial goal-label admission protocol

Base a8efd053653d51617e9cf300fba947f092dc82a6. Before computation, fix this
question: does comparison of a frozen static predictor require every game-goal
label to be solved exactly? No new game roots, service estimates, human prices,
old deployment labels or Xiangqi holdout will be inspected.

Choose the SAME bounded goal target U in [-1,1] and fixed finite probability
measure D for candidate and baseline. Each label has a sound interval [l,h]
containing its true U. Unresolved leaves may use [-1,1]; do not impute zero.
Intervals must be justified by authoritative terminal/legality semantics and
sound max/min propagation, not scores from the candidate under evaluation.
A max node's bounds are max lower/max upper over ALL legal children; a min
node uses min lower/min upper. Unexpanded children retain full bounds. Synthetic
max-ply draws remain draws only for that synthetic target, not real game labels.
Shogi's unqualified stalemate convention is not an official label source.

Fix candidate predictions p, baseline predictions b and rho=9/10 BEFORE seeing
evaluation labels. Compute exact risk bounds and paired margin bounds for
M=E[rho*(U-b)^2-(U-p)^2]. Certified improvement requires baseline lower risk>0
and margin lower>=0. Margin upper<0 certifies failure; all other cases are
inconclusive, with no resampling or budget increase implicit in that verdict.
The 10% margin is a declared comparison control, not a scientific material unit.

Freeze a four-state arithmetic CONTROL, not Chess/Shogi evidence: inventory
features (+1,0),(-1,0),(0,+1),(0,-1); weights 3/8,3/8,1/8,1/8. Known labels
+1,-1 on first two states, full unknown intervals [-1,1] on last two.
Candidate slopes (1/2,0), intercept0; baseline0. Slopes are declared test inputs,
never fitted or proposed material prices. Retain unknown labels without reading
or generating them; calculate whether the gate can pass for ALL completions.
Also check all-unknown inconclusiveness and a known opposite-sign failure.

Use exact rational arithmetic and <=4 observations, no engine materializations.
Independent tests check endpoint/interior extrema, input rejection and that
partial intervals contain every checked completion. No new search infrastructure,
game batch, deployment law or material prior is admitted by this algebra alone.
