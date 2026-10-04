# Material-sensitive leaf-decision deployment draft

2026-10-04. Construction, faithful semantics and usefulness are separate.
This design completes the memo's deployment task without sampling new roots
or estimating coefficients. Status: DRAFT, NOT A FROZEN CORPUS AUTHORIZATION.
A new independently motivated candidate is still missing. The sparse motif
is not silently substituted for it or for a static material vector.

## Evaluation and complete choices

First isolate a one-ply, pure-material leaf-order operator. Exhaust the same
public complete choices once for candidate, unit-token and zero baselines.
Preserve full action identity including semantic pattern/geometry, promotion
and hand drops. Include Session declarations through PublicGame. A complete
immutable child table may be shared: all methods face identical legal choices
and identical transitions. This is finite minimax at depth1, not production
ABP with its evaluator, iterative deepening, TT, ordering or qsearch. A later
ABP test needs a separate frozen operator; do not generalize this result to it.

Features are signed own0-minus-own1 counts keyed separately by current board
type and held base type. Anchors contribute0. A candidate must explicitly cover
every reachable material mode/type used by the operator, including promotion
and capture-to-hand. Missing weights are unsupported, not0. Its static vector
is normalized by its maximum ordinary mode/type coefficient before use; this
fixes a gauge, not relative ratios. Existing sparse board-only diagnostics do
not yet supply this complete vector. Unit baseline gives every ordinary board
and held token1; zero gives0. Neither imports conventional piece prices.

Let N bound physical ordinary tokens across this declared standard-game scope.
Use nonterminal E=sum w_t Phi_t/(N+1), with0<=w_t<=1. Then |E|<1. Authoritative
terminal wins/losses use owner-zero +/-1 and qualified draws0; terminal utility
strictly dominates any nonterminal material score. There is no mate-distance
preference, score-dependent budget or mixture with other terms. RESTART,
NO_CONTEST and unqualified/censored Shogi stalemate make the scalar choice
incomplete. They are never silently scored0 or removed from the legal choices.
Terminal/history cache and full legal effects must remain consistent.

Owner0 maximizes, owner1 minimizes. Ties use ascending canonical complete
choice ID, independent of coefficients and goal labels. Save all choice IDs,
child-state identities, count features, exact scores, selected IDs and hashes
before querying any independent outcome labels. Partial enumeration is not a
completed selection. No fallback to the last visited action or smaller corpus.

## Candidate-independent roots

A prospective finite pilot can use fresh actual-inventory Q roots, with its
already declared structural/quiet/ongoing constraints, new seeds and no overlap
with exposed reference/deployment boards. Do not reuse the failed service
corpus or condition on candidate performance, goal labels or the threat motif.
Exact seeds and source hashes must be reserved only after a candidate is frozen.

Filter for at least two ongoing legal children whose mode/type count difference
has both positive and negative components. This is a cheap positive-material
pairwise sensitivity witness. A difference with all nonnegative coordinates
only tests positive-weight dominance, not relative ratios. Mixed signs guarantee
some positive vectors reverse that PAIR's order; they do not guarantee that
either child is globally optimal among all choices. Retain this limitation;
different actual frozen choices and their outcome margins supply use evidence.
All accepted roots keep every legal choice, including terminal ones/claims.
The filter is purely structural and excludes no root after learning its labels.

Suggested prospective caps:4 roots/game,128 whole-board proposals TOTAL/game,
5,000 public materializations/15 seconds across generation/child tables,128
choices/root; any exceeded cap is incomplete, not permission to drop a root,
renormalize or increase the cap. These match/conservatively restrict previous
small experiments. This draft has run ZERO new proposals/transitions or labels.
Such a conditional law tests a finite material-choice stratum, not natural play.

## Independent goal observation and verdict

After selection freeze, give every unobserved choice [-1,1]. Observe only the
union of candidate/unit/zero selected children if desired: at most3 per root.
Public goal observer depth2,64 transitions/256 visits/5 seconds per child,
and at most1,536 transitions/30 seconds overall for8 roots. Preserve full child
history; do not reset it for observation. Remaining observations become unknown
when the total cap is spent. These are qualified executable-game WDL intervals,
not calibrated material scores. Domain mismatches or RESTART remain unknown.

Use exact paired R_baseline-R_candidate=V_candidate-V_baseline. Same selected
choice gives0 even if its outcome is unknown. Predeclare delta=1/10 as an
engineering additive WDL-regret margin, not a coefficient or rule consequence.
Require certification against BOTH baselines per game under equal frozen root
weights. Unknown intervals mean inconclusive, not failure or0. Failure to meet
the margin is distinct from proof that the candidate is worse. A pass supports
only this finite conditioned corpus. No human or Xiangqi holdout is opened.

Known risk: fresh full-inventory roots may yield almost no decisive labels at
this shallow cap. The old capped-goal/repeated-mate failures already warn against
larger-budget retries. Investigate compatible independent outcome certificates
or a different separately motivated population before running an uninformative
pilot. Root filter and successful structural tests do not solve that risk.

## Immediate executable work and remaining gates

Implement only exact feature/sensitivity/one-ply selection primitives and
independent controls now. Qualify positive-vector pair reversal, held/current
type separation, terminal dominance, both owners, canonical ties, unsupported
weights, unresolved claims and incomplete tables. No candidate/corpus is admitted
by those tests. Next choose a coherent construction and a demonstrably applicable
label source; then freeze the entire population/operator before measurements.
