# DEV_AUX task2618 Chess learner comparison — design audit

**Status: design and runner implementation in progress; not registered or
launched.** The WDL shared-path run was a cost-only scan. The shared learner,
evaluation, and finite-panel analysis runners now have focused unit tests,
while write-once registration and end-to-end preflight remain pending.

## Decision question

At equal paid search-node budgets against one fixed uniform-price opponent, does
the whole TreeStrap learner package improve actual terminal standard-Chess W/L
over episode TDLeaf(lambda=.95) and a finite-WDL proposal selector, starting
from paired random material weights? Training loss and update density are
diagnostics; only actual terminal outcomes on the frozen evaluation panel are
the strength endpoint. Four seeds and 32 root families are a finite pilot, not
a population estimate or a claim of faithful historical paper reproduction.

## Frozen comparison choices

- Rules and features: python-chess 1.11.2, standard Chess, existing five
  signed-count features `(P,N,B,R,Q)`, pawn fixed at `1`, linear material model
  with existing scale `10`; four other coefficients initialized independently
  as `Uniform(.5,1.5)` from the same seed-matched vector for every method.
- No human price priors or material-based move ordering, SEE, or pruning. The
  shared training search is task2492 `AlphaBeta(2,0)` / `Receipt`, with random
  legal-action order independent of coefficients. Its one-sided bounds remain
  bounds. Incomplete receipts supply no TreeStrap or TDLeaf target.
- Training methods: TreeStrap interval semi-gradient (`eta=.05`); episode
  TDLeaf `lambda=.95, eta=.05`, buffering complete candidate receipts and
  applying the known terminal white-relative Chess outcome when available;
  finite-WDL control using the frozen task2618 coordinate proposal, four-game
  order, and strict-positive paired interval acceptance. Do not change these
  hyperparameters after exposure.
- Four outcome-blind seeds are deterministically derived by
  `audit_learning_protocol_inputs.py`. The first 32 prospective training roots
  (task2619 indices `0:32`, families `810001:810033`) are excluded because the
  WDL cost scan used their terminal labels in memory. The remaining 480
  full-history starts (`32:512`, families `810033:810513`) form four disjoint
  120-root seed blocks. Within each block all three methods receive the same
  roots in the same order; no outcome-driven root substitution or extension.
- Each of 12 method-by-seed arms receives at most 1,000,000 combined candidate
  plus fixed-foe nodes (4M per method); max search budget 8,192 nodes / 2 seconds,
  depth 2, max 1,024 plies. The fixed foe has `[1,1,1,1,1]` coefficients.
  TreeStrap updates from each complete candidate receipt; TDLeaf updates at
  episode boundaries; WDL updates only after a complete four-game block. All
  candidate and foe searches are charged. A partial game/block, cap exhaustion,
  or missing terminal is retained and censored, never filled as a draw.
- Evaluation: endpoints are initialization plus the three trained methods.
  Reuse the task2619 32 outcome-blind evaluation start roots against the same
  fixed foe, both learner colors, all four seed-matched endpoints. This is
  `32 * 4 seeds * 4 endpoints * 2 colors = 1,024` slots. Use the common task2617
  evaluation policy/search implementation for every endpoint; assign balanced
  20k/40k both-side family caps before outcomes (16 roots per cap), shared across
  all methods/seeds/colors on a family. Total possible eval work is 30.72M
  nodes. Actual W/D/L is read only from Chess rules; UNKNOWN remains `[-1,+1]`.
- Compare each learned endpoint with initialization and both other learners by
  matched `(root, seed, learner-color)` rewards. For each endpoint UNKNOWN,
  retain `[-1,+1]`; subtract intervals and average over the fixed 256 matched
  slots per contrast. Report exact finite-panel bounds, censoring, per-seed
  counts, per-root clusters, training losses/update/receipt counts, paid nodes,
  and wall time. No CI, population claim, best seed, or eval tuning.

## Cost and registration boundary

The current cost-scan projection is 95.768 minutes, scaling each shared
AlphaBeta/Receipt 400k-node cost-only scan to 4M paid nodes per method, then
using the slower complete 1,024-slot Chess evaluation, 25% margin, and 900s
reserve. The all-in cap remains 6,600s (110m):
2,100s training, 3,600s evaluation, 900s setup/audit. This is below the 120m
Chat-assessment threshold, but the projection is not a guarantee. Do not split
the run or extend caps. Keep all uncompleted method arms and evaluation slots
as partial/UNKNOWN if any cap binds.

Before registration, audit and hash the common runner, finite-panel analyzer, exact arm/episode order,
fresh randomized family cap map, evaluation binding, decision analyzer, and
invariant tests as one end-to-end bundle. Recompute cost from the exact final
artifacts. Registration must be write-once and pre-search. If the final
expected cost reaches 120m, wait for the user's scoped assessment in an incoming
project Chat message or direct confirmation before launch; otherwise no
assessment is required. This audit does not authorize search or
make any strength claim.

## Evidence and limits

- Input audit: `learning-input-audit-v2.json`, status
  `PREPARATION_AUDIT_ONLY_NOT_REGISTERED`; exact-history train/eval overlap 0;
  no search or outcome access.
- Existing root audit claim is limited to complete start-record identity
  against enumerated historical starts and reconstructed task2616 training
  starts. It does not establish descendant/transposition or distributional
  independence.
- The task2618 WDL cost-only scan consumed 400k nodes and 53.134s; task2612
  attempt-4 consumed 400k nodes per learner for TreeStrap and TDLeaf. These
  receipts are used only for cost projection. The WDL scan roots are excluded
  from learner training.
- The task2618 shared learner/evaluation runners are implemented with focused
  tests, but registration, end-to-end preflight, and final source pinning remain
  pending. Cost scaling is not a runtime guarantee.
