# ADR-014 — Semantic Runtime Binding, Aux Scope, and Transition Events

Status: frozen amendment for Phase 1.9B-2 Review R1

## 1. Public Core ownership

The existing Core entry points remain the game-state authority.

`CompiledSemanticRuleset` support is additive. The semantic executor may be an
internal/reference helper, but public game-state creation/application/terminal
resolution must not fork into an unrelated second engine lifecycle.

A public application path always validates legal-action membership before
transition. Any unchecked semantic transition is private.

## 2. Runtime action binding

A semantic runtime action is a binding, not an effect script supplied by the
caller.

The binding must uniquely determine:
- pattern;
- exact actor/drop type;
- source when applicable;
- target;
- promotion choice when applicable.

Callers never provide arbitrary effects.

For multi-type patterns, actor/drop type and geometry compatibility must be
explicit. `type_ids[0]` is never a runtime default.

## 3. TypeRef semantics

`ACTION_BASE` and `ACTION_CURRENT` are resolved from the pre-action actor
binding exactly once.

State-query candidates do not redefine action-relative TypeRefs.

## 4. Auxiliary scope

GLOBAL slot:
- one logical value.

PER_OWNER slot:
- independent owner-0 and owner-1 logical values.

The physical Python representation is implementation-defined, but all of:
- initialization/default lookup;
- slot guards;
- effects;
- expiration;
- transition triggers;
- semantic position identity;
must preserve this logical scope.

## 5. Transition event semantics

Trigger matching uses a pre-bound event trace.

`move` / `shift` emits:
- `piece_leaves_square(piece, from_square)`.

`remove` emits:
- `piece_removed_from_square(piece, square)` when a piece was present.

Later effects do not erase earlier events. Thus a capture may emit
`piece_removed_from_square(victim,target)` followed by
`piece_leaves_square(attacker,source)` even though the target is occupied in the
final board.

For PER_OWNER slots, a trigger declared with owner `self` is evaluated relative
to the logical slot owner, not blindly relative to the action mover.

## 6. Anchor rule

Pseudo-attack and legal capture remain separate:
- an anchor square can be attacked;
- an anchor can never be a legal capture/removal result.

## 7. Fail-closed capability

The B-2 runtime may execute a semantic ruleset only when its declared capability
is actually supported.

S4/postcondition rulesets are rejected as a whole. Unsupported S0-S3 primitive
combinations are also rejected rather than silently approximated.

## 8. PATH_BETWEEN

`PATH_BETWEEN(A,B)` is the set of strict intermediate integer-lattice points on
the line segment AB.

Let:
- `df = B.file - A.file`
- `dr = B.rank - A.rank`
- `g = gcd(abs(df), abs(dr))`

If `g <= 1`, the result is empty.

Otherwise:
- `step = (df/g, dr/g)`
- selected squares are `A + k*step` for `k = 1..g-1`.

Endpoints are excluded. Bounding-box membership is not PATH_BETWEEN.

## 9. Hand predicates

The current v2 IR has no satisfactory spatial contract for pieces in hand.
Review R1 therefore does not invent one.

Until a dedicated hand-query contract is added, any semantic rule containing a
state predicate with `location="hand"` must be marked non-executable or rejected
explicitly. It must never be silently evaluated as false.
