# task2636 frozen-root branching and cost review

## Question and method

How does legal root branching compare between the frozen task2636 candidate
panel and the later task2625 four-rule reference roots? A read-only,
outcome-blind census re-hashed the task2636 plan, candidate index and root
pool, then replayed every frozen full history and counted its current legal
actions. It did the same for the task2625 reference plan, its pinned four-rule
files and its pinned task2624 root pool. No search, training, evaluation,
parameter selection or W/L/D read was performed. The census finished in
13.766 seconds; complete distributions and source hashes are in
`root-branching-cost-audit.json`.

## Results

| Frozen root phase | task2636 (2,176 roots) | task2625 reference | Mean ratio |
|---|---:|---:|---:|
| Training legal actions | mean 38.17; median 31; p90 73; max 149 | mean 10.84; median 10; p90 19; max 31 | 3.52× |
| Evaluation legal actions | mean 38.63; median 32; p90 71; max 124 | mean 10.94; median 10.5; p90 20; max 27 | 3.53× |

Candidate-level means are heterogeneous: task2636 training ranges from 17.58
(candidate 15) to 68.34 (candidate 0); evaluation ranges from 15.06 (candidate
15) to 70.31 (candidate 0). The equal frozen root counts therefore do not
equalize legal-action opportunity or root complexity.

## Decision and limits

This comparison alone does not test the exact root manifests underlying the
estimate. It compares against a later completed four-rule runtime reference;
board and ruleset differences are confounded. Do not describe these roots as
the direct roots of the 66.70-minute projection. A separate source-pinned
audit, `cost-basis-root-branching-audit.json`, compares task2636 against the
training cost-scan roots from task2621 and evaluation roots from task2609,
which are the estimate's direct root-panel references. That audit found only
8 task2621 training roots (two per rule; mean 10.125 legal actions) and 64
task2609 evaluation roots (mean 8.938), versus task2636's 1,920 training
roots (mean 38.166) and 256 evaluation roots (mean 38.629): 3.77× and 4.32×
root-action means. The direct-basis comparison therefore also weakens
confidence that the old projection represents candidate complexity, while
the very small task2621 root sample sharply limits this diagnostic.

Neither census implies a runtime multiplier. Root branching does not measure
descendant branching, move-generation cost per node, pruning, query counts or
node throughput. The evidence leaves the projection unvalidated for these
candidates and supplies no replacement numerical runtime estimate.

The exact cost formula was independently reconstructed from the pinned
`task2621/cost-feasibility.json`: training is
`4,000,000 / 80,000 × 1.5 × 28.1409069s` (the slowest of four task2621
80k-node arms) = 2,110.568s. Evaluation uses task2609's measured 1,536-slot
run at 691.419s unchanged as a conservative projection for 1,024 slots. The
later task2625 completed-run timings are not the formula inputs; they are a
separate runtime comparator. Exact plan, source, result and root-manifest
bindings plus the reconstructed arithmetic are in
`estimate-basis-receipt-verification-v2.json`.

## Fixed-root depth-two legal-action expansion

To check whether root branching alone hides substantially wider child action
sets, a second read-only census expanded every legal first move from the
lowest eight frozen family IDs for each of the16 task2636 candidates (128
training and128 evaluation roots). It counted legal replies after each such
move and summed those replies with the root actions. It used all8 task2621
training cost-scan roots and all64 task2609 evaluation roots. The deterministic
selection and all plan, rule, pool, registration and manifest hashes are in
`depth2-legal-action-expansion-audit.json`.

The mean unpruned two-ply legal-action edges per root were1,643.07 for the
task2636 training subset versus129.50 for task2621 (12.69×), and1,656.73 for
the task2636 evaluation subset versus85.61 for task2609 (19.35×). The
candidate-group means vary widely:279–4,453 training and299–4,992 evaluation
edges per root. These counts show that the one-ply contrast did not capture
the full branching difference in this fixed subset. They do not count
AlphaBeta nodes: search ordering, alpha-beta cutoffs, per-node overhead and
actual query paths are absent. The task2636 subset is only8 of120 roots per
candidate, the task2621 reference has2 roots per rule, and candidate/reference
rules differ. Treat this as a complexity warning and a reason the old runtime
projection is unvalidated, not a12.69×/19.35× time multiplier or a replacement
cost estimate. No AlphaBeta search, model use, query, outcome or W/L/D read was
performed; task2636 remains unregistered.

Across the16 candidate-group means, root legal-action mean and summed child
reply count are descriptively correlated (`r=0.939` training, `r=0.947`
evaluation). This says the root count tracks the broad ordering of candidate
branching in this subset; it does not calibrate descendant search, pruning or
elapsed time and is not an independent validation sample.

## Relation to the frozen per-query node budget

The pinned search is depth2 with quiescence0 and a2,048-node training
per-query limit. In task2492 AlphaBeta, a full-width call sequence visits the
root and each legal first move, then each legal reply; absent terminal
short-circuiting and pruning, its walk-call count is
`1 + root_actions + sum(child_reply_actions)`. Applying that structural upper
bound to the same128 fixed training roots gives34 roots (26.6%) above2,048;
the8 task2621 cost-scan reference roots are all below the cap. Some task2636
candidate groups have6/8 roots above the bound, while the group-level counts
remain highly heterogeneous. Results and exact frozen inputs are in
`query-cap-screen.json`.

This is not an observed node-cap hit rate. AlphaBeta may prune many branches,
and terminal short-circuits, action ordering, model values and wall limits
change actual visits. It does show a concrete unvalidated load mismatch
between candidate and cost-reference roots under the frozen query budget, so
preserve the UNKNOWN-on-incomplete-search rule and do not treat the 66.70-minute
projection as a candidate runtime guarantee. No search was executed and no
outcome was read.

To test whether the first-eight-root result was a selection artifact, the same
bound was then evaluated over all1,920 frozen training roots. It exceeds2,048
for549 roots (28.59%), with median1,118, mean1,625.50, p90 3,574 and maximum
9,690; the reference remains0/8. Candidate counts range from0/120 (indices
2,9,14,15) to112/120 (index0) and110/120 (index7). The subset rate26.56% is
close to the full-pool rate, but per-candidate heterogeneity is large. Complete
distribution and source bindings are in `query-cap-fullpool-audit.json`. This
confirms the structural warning across the frozen training pool while retaining
the same limits: it is an unpruned, no-terminal-shortcut upper bound, not an
actual cap-hit, UNKNOWN or time rate.

The frozen stage arithmetic shows why training throughput remains the main
runtime sensitivity. The projected 4,000,000 training nodes in 2,110.568s imply
1,895 nodes/s; completing those nodes within the 2,400s training cap requires
at least 1,667 nodes/s, about 12.1% below the projected rate. The task2625
measured reference rate was 2,285 nodes/s. Evaluation projects 1,254,951 nodes
in 691.419s (1,815 nodes/s); the 3,000s stage cap would require only 418
nodes/s for that same node count. These are arithmetic sensitivities, not
candidate runtime predictions. Root-action counts cannot determine whether
task2636's realized training throughput will cross the stage threshold.

Keep the 6,600-second cap, stage allocations, frozen roots and rules unchanged.
Keep task2636 unregistered until the whole-result adapter, stop-safe writes,
actual-terminal replay gate and revised all-in estimate are resolved. This
census is a cost diagnostic over the existing fixed roots; it creates no new
evaluation slots or outcome evidence and establishes no learner-strength or
population claim.
