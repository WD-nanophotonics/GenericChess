# Service-to-material memo question: conditional bridge, unsupported application

The outstanding memo task was to seek an independently specified connection
from state-dependent service to static material use/objective, rather than
repeat count batches. That investigation is now complete within this scope:
we specify sufficient modelling premises, prove a conditional bridge,
give an exact counterexample to an unconditional bridge, and select a precise
goal-prediction objective. No usable real-game material model is established.

## Conditional bridge

Let X_t be own-minus-opponent BOARD counts of ordinary type t in a declared
mode scope; held/promoted coordinates require separate qualification, not
silent conversion. Let B be the corresponding own-minus-opponent successful
actor-service count, with each side's acting-state convention specified.
Assume each type's actor success mean conditional on X is the same v_t for
both owners and every supported inventory. Linearity then gives
E[B|X]=sum_t X_t v_t. Independence of actors is unnecessary; invariance across
inventories and the opposing side is sufficient, not necessary (individual
residual means can cancel in the signed aggregate). The actual data currently
tests only a narrow owner-zero projection, not that complete signed premise.

Separately choose a bounded game-goal target U and state probability law D,
with complete known labels from declared executable rules/solution. Assume
E[U|X]=alpha+lambda E[B|X] for a separately justified lambda>0. Then
f(X)=alpha+lambda sum X_t v_t is the conditional mean of U and minimizes
expected squared prediction loss among ALL inventory-only predictors. Proof:

E[(U-f(X))^2] = E[Var(U|X)] + E[(E[U|X]-f(X))^2].

The second term vanishes for that f. The positive scale/offset and goal/service
calibration do not follow from expected-count additivity, physical capture,
hand transfer or the terminal rule. They must be declared and supported by
independent goal evidence. A finite count-risk failure is adverse evidence for
the inventory-invariance approximation at the frozen budget, not proof that
every population violates it. No evidence currently supports the goal linkage.
Thus the theorem cannot be installed as a material prior for this project.

## Independently specified static objective

For a zero-order static approximation, choose U(s) as a bounded solved game
goal value and explicitly specify D. Minimize R(alpha,w)=E_D[(U-alpha-w.X)^2].
This tests how much goal-relevant state information static material inventory
retains; it does not train against human material prices. D, goal unit and loss
are modelling choices. Exact minimax labels are one declared option, not a
permission for unlimited game solving or teacher fitting. A bounded horizon,
censoring or unknown value cannot be silently called draw/zero. No such new
real-game labelling experiment was started here.

Writing G=Cov_D(X,X) and b=Cov_D(X,U), optimal slopes satisfy G w=b and
alpha=E[U]-w.E[X]. A unique vector requires full-rank G; otherwise nullspace
directions are unidentifiable. A fixed actual-inventory reference has G=0,
so state-level goal prediction on that reference cannot identify separate
material slopes, even if actor marking identifies local v_t. This states
which information a NEW objective needs rather than selecting favourable
contexts, fitting existing failed validation labels or reopening old probes.
It is not a claim that all approximate rule-derived priors are impossible.

## Exact falsifier and controls

The frozen `SERVICE_MATERIAL_BRIDGE_PROTOCOL.md` defines one finite transition
system with two contexts. Each has the same initial physical tokens, one legal
capture and one opponent pass, with both two-ply prefixes still ongoing. Actor
and captured-token custody agree; local service=1 in both. Two later forced
passes reach opposite authoritative terminal winners. Complete acyclic minimax
gives U=+1 and -1. The contexts differ in the game's goal-controlling context,
which the inventory/service statistic omits; no Chess/Shogi witness is claimed.

Uniform context mass gives risk R(c)=1+c^2 for every common statistic-only
prediction c, minimized by c=0 with irreducible risk1. Thus local service alone
cannot identify even the sign of future goal utility. This does not prohibit
a rule-aware approximate model or independently weighted deployment; it
excludes claiming that the existing two-ply statistic supplies a universal
bridge without the stated calibration/invariance premises.

The exact ten-state certificate is
`data/service_material_bridge_20261004.json`. Same-inventory covariance rank0
is checked with arbitrary slope/intercept cancellations. A separate full-rank
four-axis algebra control has rank2 and zero risk for its declared linear
target; its slopes are arbitrary proof inputs, not material values. Scale and
offset controls verify the declared utility unit. Empty ongoing actions,
cycles and time-cap failure never yield qualified values. Four tests pass.

## Memo task closure and research decision

The previous memo's theoretical bridge/objective task is closed: the bridge
has been explicitly derived and its applicability boundaries checked. Reject
promoting the failed local-service coefficients to static material utility.
Keep the diagnostic, exact sampler and both finite failures. No new score batch,
fitted state terms, held/promoted pricing, human reference, old deployment
label or Xiangqi holdout was used. Dot's complete existing advice was reread
without a new supplement; no acknowledgement/reply loop or new delegate arose.

The overall scientific objective remains open. Any future route must supply
its own goal target, defensible deployment measure, identifiable inventory
support and cheap sound-label cost premise BEFORE an experiment; this is
a research admissibility boundary, not an already queued or approved batch.
`PARTIAL_GOAL_RISK_RESULTS.md` subsequently shows that sound partial goal
intervals can certify some frozen comparisons without solving every label.
