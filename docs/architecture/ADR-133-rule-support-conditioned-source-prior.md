# ADR-133: Rule-support-conditioned source prior

Status: zero-game, pre-reference candidate-generation hypothesis; no production evaluator change.

## Causal diagnostic

`CAUSAL_DIAGNOSTIC`. The single unknown is whether conditioning the source variable on independently rule-generated current-type support yields an exact, internally consistent static candidate while preserving frozen V2C occupancy semantics and V2D's `U+C` event definitions. The minimum direct observation is exact reconstruction of each owner's support and source-local `u`, `c`, and `b`, followed by conditional source averages. Complete games are unnecessary because the question concerns a finite static probability space, not realized play or strength.

The scientific rationale is maximum entropy: after excluding source states impossible under the executable rules and inherited semantic exclusions, assign equal probability to every remaining supported square because the model contains no further source-location information. Owner remains uniform. This is a hypothesis about the source prior, not a claim about empirical visitation.

## Definition

For each owner `o` and current type `t`, derive `S(o,t)` as the squares reachable in the rule-derived current-type graph from that owner's initial on-board seeds and allowed drop/re-entry seeds. The graph includes positive-support same-type edges and positive-support type-transition edges, under the frozen V2C/V2D/ADR-128 exclusions. Board occupancy and path conditions retain the frozen V2C finite-population model for capability events; topology edges are positive-support witnesses, not visitation probabilities. Anchor types are excluded from the material vector.

Use `P(o|t)=1/2` and `P(s|o,t)=1/|S(o,t)|` for `s` in `S(o,t)`, zero otherwise. Reconstruct source-local `u(o,t,s)` from executable rules and the frozen V2C event measure, `c(o,t,s)` from unique physical-removal events in frozen V2D, and `b=u+c`. Then:

`U_support(t) = (1/2) * sum_o mean_{s in S(o,t)} u(o,t,s)`

`C_support(t) = (1/2) * sum_o mean_{s in S(o,t)} c(o,t,s)`

`B_support(t) = U_support(t) + C_support(t)`.

No visitation, center, distance, transition-depth, or drop-frequency weight is introduced; no fitted coefficient, smoothing mass, piece-specific correction, or game-specific correction is permitted. All inherited V2C occupancy, token-persistence, owner, movement, capture-identity, promotion, and semantic-exclusion definitions remain unchanged.

## Reconstruction and interpretation

Reconstruct support from the frozen executable-rule evidence, not the transient ADR-129 source ledger: initial placements, compiled allowed drop masks, frozen ADR-128 positive-support same-type edges, and frozen positive-support type-transition events. The exact expected support cardinalities are Chess P 48 per owner (96 of 128 across owners), Shogi L 72 per owner (144 of 162), Shogi N 63 per owner (126 of 162), and Shogi P 72 per owner (144 of 162). All other non-anchor types are expected to have full-board support for each owner. A mismatch or incomplete inherited semantic coverage is `INCONCLUSIVE`.

For restricted types, the exact `B_support` reconstruction gates are Chess P `23945/13392`, Shogi L `19728450347/5917542400`, Shogi N `2519/1260`, and Shogi P `1559/1280`. For every full-support type, `U_support`, `C_support`, and `B_support` must reproduce the corresponding frozen V2D components exactly. For every type, owner-averaged `U_support+C_support` must equal `B_support` exactly. Failure is `INCONCLUSIVE`; no numerical adjustment is allowed.

The candidate, focused tests, inherited input hashes, owner/type support digests, source component vectors, and exact candidate vector must be frozen before any Chess or Shogi human-reference data are read. This phase is zero-game, one CPU lane, hard-bounded to 60 seconds, and uses no Heavy/Search/Arena/self-play, no production evaluator modification, and no publication or promotion. Human values remain solely for a separately authorized, post-freeze validation order.
