# ADR-123: Full-inventory-density static material prior (V2B)

- Status: candidate; formula selected before human-reference validation
- Scope: zero-game Western Chess board prior with Standard Shogi retention control
- Production evaluator: unchanged
- Semantic event grouping and coverage boundaries: unchanged from ADR-122 (V2A)

## Causal diagnostic and minimal observation

The single unknown is whether V2A's remaining Western Chess pawn-normalized ratio distortion is caused primarily by averaging uniformly across every density from an empty board to the executable full-inventory density. The minimal direct observation is to evaluate the unchanged V2A conditional event polynomials once at `rho_ref = rho_max`, using the executable initial conserved physical-token inventory divided by board area. Standard Shogi is the retention control. No games, search, Arena, self-play, learning, Heavy compute, or additional ruleset is required: this is a static rule-semantic measurement, not a playing-strength claim.

This is a preregistered, falsifiable, parameter-free hypothesis. `rho_ref` is selected from executable inventory semantics before reading human references; no intermediate density is searched. The V2A results motivate the question but do not select a fitted density.

## Formula and invariants

For each distinct semantic successor event, retain the exact V2A union of occupancy cubes and its conditional probability polynomial `p(rho)`, with `P(empty)=1-rho`, `P(own)=rho/2`, and `P(enemy)=rho/2`. V2B changes only the final density evaluation:

`V2B(event) = p(rho_max)`

where `rho_max = min(1, initial conserved physical token count / board square count)`. The executable inventory audit must prove that moves/promotions preserve physical-token count, captures transfer or remove a token, and drops transfer one token from hand to board; unknown creation effects fail closed. The expected audit references are Chess `32/64` and Shogi `40/81`.

All V2A semantic grouping, source averaging, owner averaging, path/screen semantics, promotion branches, guards, ledger classifications, and intrinsic-value normalization stay unchanged. The implementation also checks that fixed evaluation at `rho=2/3` reproduces V2, while V2A remains the default integrated calculation. Human values, names, and game labels do not enter candidate computation.

## Freeze before reference access

The candidate audit reports, for every type, V2 fixed-`2/3`, V2A uniform-`[0,rho_max]`, V2B fixed-`rho_max`, raw exact rational values, quiet/capture/path/source/promotion components, dynamic-legality counts, held/drop counts, and semantic coverage. The candidate module imports no human reference.

The formula, implementation, tests, ADR and pre-reference candidate output are frozen together. Their SHA-256 values are recorded in `.generic_chess_flow/static-semantic-material-prior-v2b-freeze.json`; the sidecar includes this ADR's hash to avoid a self-referential hash table. The post-freeze validator must verify every hash and complete intrinsic semantic and inventory coverage before it reads any human-reference data.

## Frozen human-validation gates

Only after freeze verification and complete semantic coverage, compare against the already-frozen references and report raw values, pawn-normalized ratios, best single global scale, cosine, Pearson, Spearman, pairwise ordering, and scaled residuals.

Western Chess ratio bands remain N/P `2.5–3.5`, B/P `2.5–3.75`, R/P `4–6`, Q/P `7.5–11`; also require correct ordinal ordering and a positive semantic Pawn value. Standard Shogi retains cosine `>=0.95`, Spearman `>=0.90`, and pairwise ordering `>=0.90`; Pearson and piece-level residuals are diagnostic.

Classification is `STATIC_MATERIAL_PRIOR_V2B_FULL_DENSITY_BOARD_PASS` only if every Chess and Shogi gate passes. A complete but failed gate is `STATIC_MATERIAL_PRIOR_V2B_FULL_DENSITY_BOARD_NEEDS_GENERAL_REVISION`; incomplete semantic or inventory coverage is `STATIC_MATERIAL_PRIOR_V2B_FULL_DENSITY_BOARD_INCONCLUSIVE`. No gate may be changed after observing V2B. Failure reports the residual pattern; no density scan, piece/game correction, production evaluator change, Xiangqi, game, Search, Arena, Heavy, or next hypothesis is authorized. A pass stops here and leaves Shogi held/drop value as a separate question.
