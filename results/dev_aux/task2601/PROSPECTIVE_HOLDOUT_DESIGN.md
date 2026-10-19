# Deferred alternative — cluster-partition holdout (task2601)

**Status: considered alternative, deferred for the immediate next task after Dot reply.** It remains as a documented candidate-pool estimator, not the selected protocol. See DOT_RECONCILIATION.md and ROOT_ADMISSION_PROTOCOL_V3.md. This does not register or launch a new learner experiment. Dot's root-target consultation remains pending. It does not reopen task2592/2595.

## Separate the target from the holdout rule

For a learner whose task is to choose an action, a defensible target is the generator's four-ply legal-history distribution conditioned on the resulting position being nonterminal. Write this explicitly as
`P_decision = P(root history | four legal plies completed, position nonterminal)`.
This is a decision-bearing-position estimand, not the unconditional distribution of all prefixes (which puts substantial weight on games that already ended), nor a claim about arbitrary game-start states.

Do **not** further condition this target on “not seen in TRAIN” by deleting EVAL candidates after drawing them. That changes the target in a second, TRAIN-dependent way. Keep repeated histories with their source-distribution multiplicity; they are weighted draws, not independent observations.

## A bounded, outcome-blind split

1. Freeze the rule/configuration, candidate-family stream and cap, PRNG/domain separation, exact four-ply replay, terminal predicate, canonical full-history serialization, and target above.
2. Materialize the finite candidate pool before any learner fitness. Exclude terminal histories only because the stated target is `P_decision`; count and publish their mass as a separate sampler diagnostic. Preserve all multiplicities among accepted nonterminal histories.
3. Group accepted draws by exact canonical full history. Before fitness, assign each complete-history cluster to TRAIN or EVAL by a predeclared, outcome-blind seeded hash/split. All duplicate draws of one history must stay in the same partition. Do not use nominal family-ID ranges as a proxy for history identity.
4. Record each cluster's source multiplicity and the split's retained target mass. Freeze and hash both manifests before fitness. If the EVAL pool cannot meet the predeclared unique-cluster/mass floor within the candidate cap, retain an admission failure; no extension or replacement after seeing outcomes.
5. Train from TRAIN clusters and evaluate every candidate/baseline on the same EVAL clusters, sides, foes and costs. Use the original source multiplicity as the target weight (with the predeclared split inclusion weight if using a randomized split); report both the weighted target estimate and unweighted cluster summary. Treat canonical root as the resampling unit for uncertainty, while preserving paired outcomes within root/foe/role.
6. Keep W/L/D and UNKNOWN/missing distinct. Search bounds remain censored/one-sided training targets; none are exact labels. Final strength is actual complete-rule game outcomes.

This avoids post-draw rejection on TRAIN identity while preserving a declared finite-pool target in expectation under the randomized cluster split. It does **not** claim the selected finite EVAL clusters exactly equal the infinite-population distribution. Report the actual split mass, unique clusters, terminal mass, and any root overlap audit.

## Claim boundary

The split guarantees only that an EVAL **initial full-history root** is absent as a TRAIN initial root. If the claim requires an unseen-history holdout over every training observation, audit complete TRAIN trajectories and cluster against every full state/history exposed to updates; that is a stronger and potentially more costly target. Do not silently upgrade the claim.

Task2595's observed 37.0% terminal TRAIN mass and 3,702 unique histories among 8,192 rows motivate separating decision-state conditioning from duplicate weighting. Its frozen admission failure remains unchanged and is not used to choose new rules, roots, or learner outcomes.
