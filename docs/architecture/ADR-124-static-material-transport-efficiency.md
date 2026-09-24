# ADR-124: Rule-derived static transport efficiency

- Status: feature hypothesis diagnostic; no material score term is added
- Scope: full-board Chess and Standard Shogi directed transport graphs under frozen V2B density
- V2B material formula and production evaluator: unchanged
- Dataset role: Chess residual comparison is development-set description, not independent validation

## Causal diagnostic and minimum observation

The single unknown is whether same-type multi-move spatial transport efficiency, derived only from executable movement semantics, descriptively distinguishes the Rook/Queen underprediction remaining after V2B from the Chess types already near/above the fitted global scale. The minimum observation is the complete directed all-pairs transport-efficiency feature for each board type, compared only after the feature and raw Chess/Shogi values are frozen. No games, search, Arena, Heavy, or new rulesets are necessary.

This feature is diagnostic only. It is not added to V2B material values, and no human-fitted coefficient or piece/game-specific correction is allowed. The five Chess types are a development-set diagnostic whose residual signs were known before this order; report descriptive Pearson/Spearman only, with no significance claim.

## Frozen graph definition

For each non-anchor type and each owner, nodes are all board squares. A directed source-to-target edge exists when one or more intrinsic, type-preserving semantic actions can move that type between the squares under the supported local occupancy model. Use the same coverage boundary and event union as V2B, at the already-frozen executable-inventory `rho_max`. Union all quiet/capture/action descriptions that reach the same owner/source/target state before evaluating the probability `p(s,u)`; never sum descriptions as independent mass.

For every positive edge probability, define the proxy cost `c(s,u)=1/p(s,u)`. Its interpretation is limited to the expected number of independent opportunity samples under the fixed local V2B occupancy measure before that edge is executable. It is not a real-game expected move count, time, or material value. Define `D_t(s,v)` as the minimum additive proxy cost over directed paths. Unreachable destinations have infinite cost. The feature is the mean `1/D_t(s,v)` over every owner and every ordered distinct square pair, with unreachable pairs contributing zero.

The report also gives unweighted reachable fraction, mean finite unweighted hop distance, mean finite weighted proxy cost, unreachable fraction, mean outgoing one-move probability mass, directed edge count, directional asymmetry count, source-restriction counts, and all excluded type-transition edges. Promotion/type changes, held/drop actions, history-only actions and dynamic global positional legality remain ledgered but outside the primary graph. Graph coverage fails closed for unsupported intrinsic semantics.

## Required metamorphic checks

Synthetic tests establish type-label and owner-mirror invariance; monotonic reachability and efficiency after adding a valid edge; non-increasing direct-edge sets after deletion; zero efficiency for a disconnected graph; unit efficiency for a complete always-executable graph; exact `1/p` edge costs and additive multi-edge proxy costs; zero contribution from unreachable pairs; and inclusion of capture-conditioned movement. Real Chess Pawn promotion and dynamic-legal constraints must be ledgered and excluded from the same-type graph. Feature construction imports neither human references nor V2B residual results.

## Freeze and residual comparison

Freeze this ADR, implementation, tests, transport raw output and their SHA-256 values before reading the previously recorded V2B residual report. The validation step verifies all freeze hashes first, then reads the existing V2B validation output. For Chess report V2B raw value, best-global-scale value, required correction `human_reference - scaled_V2B`, `E`, reachable fraction, mean finite proxy cost and E-rank for P/N/B/R/Q. Pearson and Spearman between E and correction are descriptive only. The preregistered direction is supported only if Pearson is positive and mean E for underpredicted types exceeds mean E for overpredicted types. Shogi reports every ordinary/promoted type's same feature beside its existing scaled V2B residual; no new Shogi gate is defined.

Classification is `STATIC_MATERIAL_TRANSPORT_HYPOTHESIS_SUPPORTED`, `STATIC_MATERIAL_TRANSPORT_HYPOTHESIS_NOT_SUPPORTED`, or `STATIC_MATERIAL_TRANSPORT_HYPOTHESIS_INCONCLUSIVE` for complete directional evidence, complete feature with failed directional condition(s), or incomplete intrinsic graph coverage, respectively. A supported result does not authorize a transport term; a failed result does not authorize coefficient fitting. No formula change, density scan, production evaluator edit, Xiangqi, games or Heavy are in scope.
