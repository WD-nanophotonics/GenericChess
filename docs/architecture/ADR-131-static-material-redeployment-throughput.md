# ADR-131: Static Material Redeployment Throughput

Status: pre-reference, falsifiable static material-prior candidate; not a production evaluator change.

## Research question

`CAUSAL_DIAGNOSTIC`. The single unknown is whether a generic semantic redeployment-service rate produces relative material values that satisfy the already-frozen Western Chess bands while retaining Standard Shogi. The minimum direct observation is a zero-game candidate computed from the frozen ADR-130 directed type-square graph and ADR-129 source-local capability, followed by the preregistered validation only after the candidate bytes and input hashes are frozen. Complete games are unnecessary for this static rule-derived hypothesis.

## Frozen rule-derived inputs

For owner `o`, current type `r`, and square `v`, use the exact frozen ADR-129 local capability

`b(o,r,v) = u(o,r,v) + c(o,r,v)`.

Use the frozen ADR-130 augmented directed graph on `(current_type, square)`. Every edge is one positive-intrinsic-probability executable own semantic action. Its action cost is one. Shortest directed graph distance is an abstract count of required own actions. Do not use ADR-124's `1/p` transport edge cost: occupancy-conditioned probability is already part of `b`, while this declared task measures semantic action count, not expected waiting time under a stochastic occupancy process.

## Declared service task and formula

Choose owner uniformly, starting square uniformly, and a distinct target board square uniformly. For a reachable resulting current type `r` at target `v`, define its delivered capability rate from start `(t,s)` as

`b(o,r,v) / d((t,s),(r,v))`,

where `d` is the minimum directed graph-hop count and `v != s`. The token's abstract controller chooses the resulting state with the greatest rate:

`W(o,t,s,v) = max_r b(o,r,v) / d((t,s),(r,v))`.

Only reachable states with finite `d >= 1` participate. An unreachable distinct target contributes zero. No `+1` distance convention is used. The sole candidate score is

`M(t) = (1 / (2*A*(A-1))) * sum_o sum_s sum_{v != s} W(o,t,s,v)`.

The factor `1/d` is the ordinary rate for delivering one local capability amount after `d` required own actions in this explicitly declared idealized service task; it is not a fitted discount curve. The averaging denominator is the count of owner, source, and distinct-target tasks. Target squares are the exhaustive rule-defined board set. There is no free context, material, path-cost, or transition coefficient. Owner choice and the maximum over controllable branches are part of this hypothetical service task, not claims about realized play.

Co-optimal resulting states have equal `W`. For deterministic reporting only, select the co-optimal state with shortest distance and then lexical type ID, while recording every co-optimal type. This reporting tie-break cannot change `M` and must not enter validation scoring.

## Interpretation limits

This is a falsifiable, optimistic structural-potential model, not a measured in-game utility or probability. An ADR-130 edge certifies an intrinsic executable semantic outcome under its frozen event model; it does not guarantee that a player controls opponent occupancy or that every edge on a multi-action shortest path can be jointly realized in one position or game. The maximum over branches assumes controllable choice in the declared abstract task. Destination `b(o,r,v)` is latent local capability available at arrival, not an additional move already executed. Shortest paths do not model opponent replies, blockers changing during a route, strategic safety, survival, realized game frequency, or actual deployment time.

These limits must accompany raw results and closeout. Do not relabel `M` as a guaranteed payoff, real-game deployment probability, or uniquely correct material value. A failed frozen human-agreement gate rejects this candidate; it does not authorize tuning the formula.

## Required frozen diagnostics

For each non-anchor Chess/Shogi type, preserve exact frozen V2D `B0`, ADR-130 mean source `q`, mean finite minimum target distance, unreachable-target fraction, frequency with which a selected state changes type, selected destination capability, mean reciprocal selected distance, exact `M`, and selected-result-type counts as diagnostics. Preserve owner/source/target task rows with target, selected type, selected distance, destination `b`, `W`, and co-optimal types. Include per-owner graph hashes, shortest-path digests, transition ledgers, and the inherited drop/history/dynamic-legality exclusions.

Reconstruct V2C `U`, V2D `C`, and every source-local `b=u+c` exactly from the frozen ADR-129 tables. Reproduce ADR-130 graph hashes before computing distances. Freeze candidate source, implementation, focused tests, raw exact components, and all V2C/V2D/ADR-128/ADR-129/ADR-130 input hashes before reading any human reference.

## Validation and decision route

Only after the pre-reference freeze, compare the frozen candidate with existing development references under the unchanged Western Chess bands and Standard Shogi retention gates. Human values are validation targets only and must not enter candidate computation. Report V2C, V2D, and V2G ratios, raw values, best single global scale, cosine, Pearson, Spearman, pairwise ordering, and scaled residuals.

If and only if the unchanged frozen candidate passes Western Chess and retains Standard Shogi, the next holdout is Xiangqi with that exact formula and no Xiangqi-specific adjustment. Do not put Shogi held/drop/re-entry extension ahead of Xiangqi. A failed candidate receives component-level diagnosis only; no distance-exponent, additive-distance, coefficient, or named/game-specific correction is authorized.

No production evaluator change, games, Search, Heavy, learning, ADR-124 transport term, or V2E continuation value is authorized by this ADR.
