# ADR-126: V2D board capture-removal affordance

- Status: zero-game diagnostic hypothesis; no production evaluator change
- Base: corrected, frozen V2C checkpoint at `fb47f6b4df512a0d84b847d7d891d0ce41baf5f8`
- Scope: Western Chess and Standard Shogi board-only material prior

## Causal diagnostic and single unknown

The unknown is whether an executable opponent-board-token removal is a second generic material affordance, distinct from the movement/state-choice represented by V2C successor options, and whether counting both once improves the frozen Chess ratios while retaining Shogi. The minimum observation is exact static evaluation of unique capture-removal opportunities under the unchanged V2C finite-population event measure. No games, search, Heavy, Xiangqi, learning, transport diagnostic, or production evaluator change is authorized.

## Hypothesis and units

Let `U(t)` be the corrected V2C expected number of distinct executable intrinsic successor options for type `t`. Let `C(t)` be the expected number of distinct executable opponent physical-token removals from board squares, under the same source-conditioned finite-population ensemble. The candidate is `M(t) = U(t) + C(t)`.

The fixed coefficient is exactly one: each term counts one distinct executable rule consequence in its own class—one successor-state choice in `U`, and one opposing board resource removed in `C`. This 1:1 additivity is a falsifiable scientific hypothesis, not a demonstrated universal law, a human-fitted weight, or an arbitrary claim that captures are intrinsically “worth double.” Do not refit it after observing validation.

A quiet successor contributes only to `U`. A capture successor contributes to `U`, and once to `C` for the physical opponent token it removes. Capture-to-hand counts only removal from the opponent's board; no hand/re-entry/drop value is included. Shogi validation must be labelled `board_capture_affordance_only` because future hand value remains unresolved.

## Generic capture identity and event measure

Derive `C` only from compiled `remove` effects whose `piece_owner` is explicitly `opponent`, recognized capture disposition, and a generically resolved actual `square_ref`. Do not infer it from target relation or V2C's capture component. Resolve source, target, fixed, offset, and path-step references from compiled geometry bindings; if a state-free scored effect square is unsupported or ambiguous, fail closed as `INCONCLUSIVE`.

For each actor owner, source square, and actual removed square, union all compatible occupancy cubes before applying the exact frozen V2C event measure. This key identifies one physical board-resource removal regardless of duplicate semantic descriptions or optional promotion branches. Different removed squares are distinct. Preserve multiple successor branches in `U`, but collapse them to one physical removal in `C`; record the promotion choices collapsed into each key. Record the compiled capture disposition.

History/auxiliary-state captures are ledgered with their effect square reference and resolved removed-square identities when possible, but excluded from this state-free score because no stationary prior for their auxiliary state is declared. Self-removal and state-management effects are not opponent board captures. Ambiguous or unresolvable scored capture effects make coverage incomplete; do not guess.

## Unchanged V2C inputs

Use the exact corrected V2C frozen raw `U` values and verify their manifest. Keep its source conditioning, physical-token maximum-entropy persistence model, separate Shogi owner model, exact without-replacement sampling, movement/path/source/restricted-region semantics, promotion successor construction, and coverage boundaries unchanged. Retain V2A/V2B/V2C for comparison. No transport feature, density scan, fitted weight, piece/game-specific adjustment, tactical search, future promotion value, or held/drop bonus is allowed.

## Freeze, gates and reporting

Before this order reads human-reference files, freeze this ADR, implementation, focused tests, corrected V2C baseline manifest/raw input, and exact per-piece `U`, quiet/capture parts of `U`, `C`, `M`, capture event keys, dispositions, collapsed promotion branches, exclusions, and SHA-256 hashes. Candidate output explicitly records `human_reference_imported=false`, `capture_affordance_coefficient=1`, its one-unit rationale, and no density/transport/piece/game adjustment.

After hash and coverage preflight, compare to the same frozen references and gates: Chess N/P 2.5–3.5, B/P 2.5–3.75, R/P 4–6, Q/P 7.5–11, positive Pawn, and sensible ordering; Shogi cosine >=0.95, Spearman >=0.90, pairwise ordering >=0.90. Report raw `U/C/M`, V2C and V2D pawn ratios, global scale, cosine, Pearson, Spearman, pairwise ordering and scaled residuals. No gate or assumption changes after seeing results.

Classification is `STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_PASS`, `...NEEDS_GENERAL_REVISION`, or `...INCONCLUSIVE`. Pass freezes the Chess+Shogi board formula and moves Priority 1 to Shogi held/drop/re-entry theory; it does not authorize Xiangqi until that combined formulation is frozen. A failed but complete result reports residuals and awaits a new general hypothesis. Inconclusive reports the generic semantic ambiguity. No evaluator change is authorized.
