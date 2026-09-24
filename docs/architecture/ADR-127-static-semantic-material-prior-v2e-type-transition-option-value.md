# ADR-127: V2E executable type-transition option value

- Status: zero-game diagnostic hypothesis; no production evaluator change
- Base: frozen V2D capture-affordance board capability
- Scope: Western Chess and Standard Shogi; Shogi remains board-plus-transition-only

## Causal diagnostic

The unknown is whether the future type-state capability reachable through an executable type transition, valued in the same units as the frozen board capability, corrects remaining Chess material ratios while retaining Shogi. The minimum observation is an exact static sum over unique type-changing movement events under the unchanged V2D/V2C source-conditioned finite-population event measure. No games, search, Heavy, density change, transport feature, Xiangqi, or evaluator edit is authorized.

## Base and transition premium

Let the frozen V2D board capability be `B0(t)=U(t)+C(t)`. For one physical transition event `e` from source type `t`, let `A_e` be the set of legally available resulting types. Optional transitions include `t`; forced transitions do not. Ordinary type-preserving actions are not transition events.

Let `B1(r)=B0(r)+T(r)` be the capability after including downstream transition options. For a destination `r != t`, use its already-computed reverse-topological `B1(r)`. If optional stay at `t` is legal, its stopping value in this event is `B0(t)`, not `B1(t)`; this avoids a self-reference while `T(t)` is being computed. Then:

`V_after(e) = max({B1(r): r in A_e and r != t} union {B0(t) if t in A_e})`

`delta(e) = V_after(e) - B0(t)`

`T(t) = sum_e Pr(e) * delta(e) / (2*A)` and `B1(t)=B0(t)+T(t)`.

This is the exact recursive interpretation of downstream transition value, while preserving the work-order's one-step `max(B0(r))-B0(t)` result for terminal destinations. Optional lower/equal-only choices produce zero; forced transitions may be negative and are never clipped. The coefficient on `T` is one because `delta` is already expressed in the exact same `B0` capability unit. No temporal discount or played-game survival assumption is introduced.

If the executable type-transition graph is acyclic, compute terminal types first and propagate in reverse topological order. Any cycle is `INCONCLUSIVE`; no discount or infinite-horizon equation may be invented.

## Physical event identity and deduplication

Build transitions from compiled executable promotion/type-transition semantics, owner-specific compiled masks and actual legal source/target geometry. Event identity preserves actor owner, source, target, quiet versus capture outcome, actual removed-square/effect identity where capture occurs, and allowed resulting type set. Capture+promotion and quiet+promotion remain distinct when their occupancy predicates differ. For one physical result and one resulting-type set, union occupancy-equivalent cubes before evaluating its exact probability; optional destination branches are alternatives and are not summed. If overlapping descriptions imply incompatible result sets that cannot be distinguished from compiled predicates, fail closed.

The removed-effect identity is canonical physical state, not reference syntax: it is the sorted set of `(resolved removed square, disposition)` pairs. Keep the original compiled square-reference representation in the diagnostic ledger only. Thus `target` and a zero offset from target that resolve to the same square/disposition are one physical removal event. Multiple distinct removed squares remain distinct members of the same action's removal identity.

Anchors remain outside material-reference gates. All `B0` values are read exactly from the frozen V2D raw candidate and its SHA manifest. No human target, prior validation residual, transport metric, or game/piece-name rule is used in candidate calculations.

## Freeze, diagnostics and gates

Before V2E reads references, freeze ADR-127, implementation, focused tests, V2D input manifest/raw file, transition graph, topological order or cycle evidence, per-event probability/options/destination capabilities/delta, and exact per-type `U/C/B0/T/B1` values with hashes. Candidate flags state `base_v2d_reproduced=true`, `transition_coefficient=1`, and no temporal discount, transport, density scan, or piece/game adjustment.

After preflight, report V2C/V2D/V2E Chess pawn ratios and global-scale/cosine/Pearson/Spearman/pairwise/scaled-residual diagnostics under unchanged gates: Chess N/P 2.5–3.5, B/P 2.5–3.75, R/P 4–6, Q/P 7.5–11, positive Pawn and sensible ordering; Shogi cosine >=0.95, Spearman >=0.90, pairwise >=0.90. Label Shogi `board_plus_type_transition_only`; held/drop/re-entry value remains excluded. Do not tune transition weights or gates after seeing results.

Classification: `STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_PASS`, `...NEEDS_GENERAL_REVISION`, or `...INCONCLUSIVE`. A pass freezes the Chess/Shogi board+transition prior and moves the next Priority-1 diagnostic to Shogi held/drop/re-entry; Xiangqi remains unauthorized until then. A complete failure returns exact residuals for a new general hypothesis. No production evaluator change is authorized.

### Pre-publish erratum: reference-syntax key alias

The first V2E freeze and its post-freeze validation are invalidated before publication. The transition key initially included the textual `CompiledSquareRef` representation, so two references resolving to the same physical removed square and disposition could be counted as separate events. The correction removes reference syntax from event identity and retains it only in the ledger; the transition recurrence, V2D inputs, event probabilities, gates and references are unchanged. The invalidated candidate SHA-256 was `0cb78dc8dc95805db5327f2f377d8f6df61c02ac94138d031a1f37538ac8e9e8`. The new freeze records prior freeze/validation hashes and summary in `.generic_chess_flow/static-semantic-material-prior-v2e-key-identity-erratum.json`; its corrected candidate must be recomputed, freshly frozen and validated before review.
