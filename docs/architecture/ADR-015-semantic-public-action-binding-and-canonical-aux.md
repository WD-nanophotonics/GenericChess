# ADR-015 — Semantic Public Actions, Binding Context, and Canonical Aux State

Status: frozen amendment for Phase 1.9B-2 Review R2

## 1. Legacy actions remain stable

Existing `BoardMove` and `DropMove` remain unchanged in field meaning, equality
and legacy serialization.

Semantic execution SHALL NOT squeeze a semantic binding into those legacy types
when doing so loses pattern or geometry identity.

## 2. Semantic public action variants

Core SHALL expose explicit semantic board/drop action variants (names may be
`SemanticBoardMove` / `SemanticDropMove` or equally explicit names).

A semantic public action contains:
- `pattern_id`;
- `geometry_id`;
- exact actor/drop type;
- board source when applicable;
- target;
- promotion choice when applicable.

Equality/hash/serialization include semantic identity. Same visible coordinates
may correspond to distinct semantic actions.

Core `action_to_dict` / `action_from_dict` must round-trip semantic actions.
Session/GameRecord v1 may explicitly reject them until a later schema phase.

## 3. Runtime ActionBindingContext

The executor builds one immutable pre-action binding context containing at least:
- pattern id;
- geometry id;
- actor owner;
- actor/drop type;
- actor base/current type;
- source;
- target;
- promotion choice;
- exact candidate path.

All action-relative TypeRef/SquareRef evaluation, S1 guards, effects and
invariants consume this context. ACTION_BASE/ACTION_CURRENT always mean the
pre-action actor.

## 4. Canonical auxiliary key

Semantic `Position.aux_state` uses one physical key shape:

`AuxKey = (slot_id, owner_tag)`

- GLOBAL -> owner_tag `-1`;
- PER_OWNER owner 0 -> `0`;
- PER_OWNER owner 1 -> `1`.

Children are sorted by AuxKey.

Any sparse semantic position is normalized against compiled defaults before
hashing/execution.

## 5. Logical aux identity

For every compiled slot:
- GLOBAL contributes one logical value;
- PER_OWNER contributes owner 0 and owner 1;
- absent physical entries equal `slot.initial`.

Absent/default and explicit/default hash identically.

## 6. expire_next_turn

At transition:
1. bind pre-action operands;
2. normalize/copy parent aux;
3. reset every logical instance of every `expire_next_turn` slot;
4. board/hand/type effects + event trace;
5. transition-trigger invalidation;
6. explicit aux effects;
7. switch side.

PER_OWNER expiration is not keyed only to the current mover.

## 7. AUX_SLOT_SQUARE

GLOBAL resolves the one logical value. PER_OWNER resolves the value for the
binding/perspective owner. Implicit defaults are valid values.

## 8. Public Core identity

All semantic public Core operations validate the Position fingerprint against
the compiled semantic ruleset. `legal_successors` is part of the same public
lifecycle and dispatches semantically.

## 9. Pseudo-attack perspective

Pseudo-attack is S0+S1 capture eligibility:
- exact type/geometry binding;
- path predicates;
- state guards;
- slot guards;
- attacker-relative SELF/OPPONENT.

It does not call full legal generation and does not apply S3 own-anchor safety.

## 10. Effect safety

- `remove` requires matching occupant and enforces owner/type binding;
- `move`/`shift` require matching source and empty destination;
- `place` requires empty destination;
- no implicit capture/overwrite;
- capture is explicit remove then move.

Legacy capture lowering binds removed victim to OPPONENT.

## 11. Phase boundary

Still Phase 1.9B-2:
- S4 fail-closed;
- Native unchanged;
- Search/Learner unchanged;
- Session/UI do not own legality state.
