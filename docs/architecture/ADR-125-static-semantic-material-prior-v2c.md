# ADR-125: Finite-population maximum-entropy token-state prior (V2C)

- Status: formula candidate; exact coarse token-state model, frozen before human-reference validation
- Scope: static zero-game Western Chess prior and Standard Shogi retention control
- V2/V2A/V2B event construction: unchanged; V2A's shared event-grouping routine receives an optional exact event-measure callback
- Production evaluator and transport diagnostic: unchanged/not used

## Causal diagnostic and minimum observation

The single unknown is whether replacing scalar-density assumptions with an explicit finite-population prior over conserved physical-token persistence states improves the frozen Chess ratios while retaining Shogi. The minimum observation is a static exact recomputation of the existing distinct-successor occupancy events using the source-conditioned joint label-count distribution. No games, search, Heavy, learning or Xiangqi are needed.

This is a declared coarse token-state maximum-entropy model, not a probability distribution uniquely entailed by game rules and not a distribution of legal game positions. The executable rules establish token classes and conservation. They do not dictate equal state probabilities or independence. Conditional uniform placement and, for Shogi, symmetric owner labels are explicit modeling assumptions selected before target comparison.

## Physical-token inventory and entropy model

Read the initial executable position, anchor metadata, capture dispositions, drop effect pairing and promotion/base-type transitions. Every anchor token is mandatory-board. Every non-anchor token must have exactly one audited persistence class: board/removed-from-game or board/hand. Unknown/mixed dispositions, unpaired hand/drop effects, or token creation fail closed. Promotions change current type but preserve physical-token identity/base type. Captured Shogi promoted pieces enter hand by base type and re-enter as the dropping side's base-type piece.

For each of the `m` initial non-anchor physical tokens, declare an independent binary persistence variable `B_i` with `P(B_i=board)=P(B_i=off-board)=1/2`. This is maximum entropy on the explicitly chosen Cartesian product of coarse binary token states. For `a` mandatory anchors:

`N_board = a + Binomial(m, 1/2)`.

The prior does not claim that rules imply 1/2 or that every full board/hand/history state has equal probability. It uses only compiled inventory/effects to extract `a` and `m`, never game-name constants or human values.

Chess board tokens retain their initial owner. For Shogi, board/hand status does not determine owner, and initial owner is not conserved. Separately and explicitly, conditional on each other token being on-board, assign its owner symmetrically to either side with probability 1/2, independently across those tokens. This is the declared maximum-entropy owner-relation prior; it is not inferred from an absent capture history and is not a free fitted parameter. If required inventory/owner joint counts cannot be constructed consistently, classify INCONCLUSIVE.

## Source-conditioned finite-population event measure

The evaluated source token is fixed on-board exactly once and removed from the random status pool. For a non-anchor source:

`N_board | source-on-board = a + 1 + Binomial(m-1, 1/2)`.

For each source owner, derive the exact joint PMF `P(E,O,X | source-on-board)` over empty, own and enemy labels on the other `A-1` squares. In Chess, survivor counts retain initial owners. In Shogi, first draw the number of other board tokens from `Binomial(m-1,1/2)`, then draw their own/enemy split under the separate symmetric owner prior. The source token's owner is fixed and is never resampled.

Conditional on joint counts `(E,O,X)`, place labels exchangeably over the `A-1` non-source squares without replacement. For `e`, `o`, and `x` distinct specified empty/own/enemy squares, respectively:

`Pr = (E)_e (O)_o (X)_x / (A-1)_(e+o+x)`,

where `(n)_k=n(n-1)…(n-k+1)`. For a union of semantic occupancy cubes, combine the cubes exactly under this finite-population measure before averaging over `P(E,O,X | source-on-board)`. Do not approximate this joint model with independent square labels at `rho=n/A`.

## Unchanged semantic score and ledgers

Reuse V2A's compiled-rule semantic groups, distinct-successor union, source restrictions, paths/screens, capture/quiet outcomes, owner/source averaging, immediate promotion branches, and intrinsic/dynamic/held/history coverage boundary. The only scoring change is the exact event measure. Report V2 fixed `rho=2/3`, V2A `Uniform[0,rho_max]`, V2B fixed `rho_max`, and V2C side by side. Every piece row includes exact raw V2C score and quiet/capture/path/source/promotion components where rational arithmetic permits.

The raw candidate states `human_reference_imported=false`, `transport_term_used=false`, `free_density_parameter=false`, and `density_scan_used=false`. Candidate computation imports no human fixture or V2B residual and transport efficiency is not used.

## Freeze and frozen gates

### Erratum: source double-count in the first freeze

The first frozen candidate (`.generic_chess_flow/static-semantic-material-prior-v2c-board.json`, SHA-256 `c7cd2aba998b6f451e5708a92dca44ae6268389326cb9edce92a391b7c6a0013`) and its post-freeze human comparison are invalidated. In `_source_joint_counts`, the conditioned source had already been removed from the anchor/optional pool but was then added again to `own`, although these counts describe only the other `A-1` squares. This made the non-source occupied expectation one token too high (Chess `35/2` rather than `33/2`; Shogi `43/2` rather than `41/2` for an optional source). The fix is only to omit that extra source from the non-source counts; the persistence prior, separate Shogi owner assumption, semantic event construction, coefficients, gates and references are unchanged. Anchor sources are likewise excluded after decrementing their mandatory anchor count. The invalidation record is retained in `.generic_chess_flow/static-semantic-material-prior-v2c-source-double-count-erratum.json`; the corrected candidate must be recomputed and frozen under new hashes before its validation is considered.

Before human-reference access, freeze this ADR, implementation, focused tests, exact inventory/persistence/owner assumptions, PMFs, all raw per-piece values/components and a SHA-256 manifest. The post-freeze validator verifies every hash and complete inventory/semantic coverage before loading human references.

Western Chess gates remain N/P `2.5–3.5`, B/P `2.5–3.75`, R/P `4–6`, Q/P `7.5–11`, plus sensible ordering and positive semantic Pawn value. Standard Shogi retention remains cosine `>=0.95`, Spearman `>=0.90`, pairwise ordering `>=0.90`; Pearson and piece residuals are diagnostic. Report all four candidate generations, pawn-normalized ratios, best global scale, cosine, Pearson, Spearman, ordering and scaled residuals. No gate or prior assumption may be revised after observing V2C.

Classification is `STATIC_MATERIAL_PRIOR_V2C_MAXENT_TOKEN_ENSEMBLE_PASS`, `...NEEDS_GENERAL_REVISION`, or `...INCONCLUSIVE` exactly as defined by the work order. No production evaluator change, transport term, probability/owner refit, density scan, Xiangqi, games or Heavy is authorized.
