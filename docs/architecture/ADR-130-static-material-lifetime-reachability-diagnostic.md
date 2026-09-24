# ADR-130: Static Material Lifetime Reachability Diagnostic

Status: pre-reference diagnostic, no material formula authorized.

## Research question

`CAUSAL_DIAGNOSTIC`. The single unknown is how executable on-board current-type transitions alter the board squares a physical token can reach relative to its same-type directed movement and ADR-128 weak domains. The minimum direct observation is an owner-specific augmented `(current_type, square)` directed graph and its source-conditioned reachable sets, with the frozen ADR-129 source capability overlaid only as a declared random-target diagnostic. Complete games are unnecessary: the question is about finite rule topology, not realized play or outcome strength.

## Frozen inputs and edge construction

The graph contains `(t,s)` nodes for every non-anchor current type `t` and board square `s`. The registered Western Chess and Standard Shogi compiled rulesets identify anchor types; anchors remain present in the frozen upstream manifests but are excluded from this graph and its source summaries.

For each owner, add same-type edge `(t,s)->(t,u)` exactly when the frozen ADR-128 positive-mass directed topology contains that edge. Add transition edge `(t,s)->(r,u)` for each destination type in an ADR-128 executable transition-ledger event whose frozen corrected V2C finite-population event model establishes positive intrinsic probability. Optional transitions retain their already-recorded same-type branch as well as each resulting-type branch; forced transitions add only resulting-type branches. Zero-probability outcomes add no edge. Graph traversal is directed. Occupancy after a move, opponent response, and dynamic global legality are not modeled.

This graph is a finite semantic reachability abstraction. Graph hops are not game plies, elapsed time, transition survival, or a probability of visiting a square in real play. Cycles are handled by ordinary graph traversal.

Drops/re-entry and held-piece actions, history or auxiliary-state actions without a stationary prior, and dynamic global positional legality are excluded and retained in the inherited semantic exclusion ledgers. V2E continuation values, destination material values, human references, fitted probabilities, and transport metrics are not inputs.

## Source-conditioned observations

For owner `o`, initial type `t`, and source square `s`, let `Reach(o,t,s)` be all graph nodes reachable from `(t,s)`, including the start node. The reachable board-square set is the projection of this set onto squares, and

`q(o,t,s) = |reachable board squares| / A`.

For every source, report reachable node count and digest, board-square count and exact `q`, reachable current types, minimum number of actual type changes to each reachable type, minimum graph-hop distance to each reachable board square, and the board squares reachable without a type change versus only after one or more type changes. Neither transition depth nor graph-hop distance is interpreted as a time or payoff.

For each transition-bearing type and owner, also report executable outgoing types, event source/target squares, initial source squares that can eventually reach a transition event, their fraction, pre-transition versus lifetime mean reachable-board fractions, added board-square counts, and squares reachable only after a type change.

For terminal types, the augmented graph must reduce to the frozen type-preserving directed edge set. Compare source reachability against ADR-128 weak components and ADR-129's same-domain random-target quantity `J`; do not equate directed reachability with weak connectivity. Any foreign type, source escape from its ADR-128 weak component, cross-domain same-type edge, or failed frozen baseline reconstruction makes the result inconclusive.

## Descriptive capability overlay; not a score

Reuse the frozen ADR-129 source-local `b(o,t,s)=u(o,t,s)+c(o,t,s)` without modification. Define only the fully specified random-target diagnostic

`Q_cap(t) = (1/(2A)) * sum_o sum_s b(o,t,s) q(o,t,s)`.

It is the exact expectation when owner and source are uniform, a target board square is independently uniform, and source-local capability is retained iff that target is lifetime-reachable. It is named `lifetime_reachability_joint_capability_diagnostic`; it is not a material-value candidate. Do not add it to `B0`, multiply `B0` by it, normalize it against human values, or use it to change any score. For terminal types, compare `Q_cap` descriptively with ADR-129 `J`, explaining any difference through directed versus weak reachability.

## Required audit conditions

- Reproduce every included source-local ADR-129 `u`, `c`, and `b` exactly; verify `b=u+c` and the frozen V2C/V2D/ADR-128/ADR-129 hashes.
- Use only frozen positive-probability topology events; reject missing or unsupported semantic coverage.
- Test forced and optional branches, zero-probability events, directionality, source-specific transition access, terminal checker-colour components, cycles, identifier renaming, and owner mirroring.
- Preserve excluded drop, history, and dynamic-legality ledgers. Import no human fixture, V2D validation residual, V2E value, or ADR-124 transport metric.
- Freeze graph and per-source summaries, transition-accessibility evidence, `Q_cap`, terminal `J` comparisons, and a SHA-256 manifest before any later order can authorize a different analysis.

No formula, material coefficient, human-agreement gate, production evaluator, games, Search, Heavy, or Xiangqi evaluation is authorized by this diagnostic. If a later generic Chess/Shogi formula is independently justified, frozen, and passes its existing gates, the next holdout remains unchanged-formula Xiangqi before any Shogi drop/re-entry extension.
