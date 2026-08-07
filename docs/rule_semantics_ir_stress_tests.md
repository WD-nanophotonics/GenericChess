# Rule Semantic IR Stress Tests (Phase 1.9A-2)

Design-level mappings of the five stress rules and five counterexample
"weird" rules onto the proposed IR.  Nothing is implemented; the structural
prototype (`experiments/rule_ir_design_prototype.py`) validates each
mapping (strata, effect cardinality, typed slots, cost class, no
game-name execution tokens).

## 1. Stress test 1 — screen ray (Xiangqi cannon)

Two templates over the same generic primitives:

* quiet: `geometry=ray`, `target=target_empty`,
  `path=path_clear`, effect `move`; cost C1; stratum S3.
* capture: `geometry=ray`, `target=target_enemy`,
  `path=path_count_eq(1, owner=any)`, effects `remove(target), move`;
  cost C2; stratum S3.

Pseudo-attack: a royal square is attacked by a screen-ray piece iff the
**capture** template's path predicate holds (exactly one screen) — attack
uses capture eligibility, never "all pseudo destinations".

Generic categories used: geometry(ray), target predicate, path predicate,
effects.  No `CANNON` primitive.

## 2. Stress test 2 — king-side shift (castling)

* right slot: `AuxSlot(0, right, persistent)`.
* template: `geometry=leap(±2,0)`, `target=target_empty`,
  `path=path_clear`, `slot_guard=SlotQuery(0, eq, 1)`,
  `invariants=squares_not_attacked(source, transit, destination)`,
  effects `move(actor), move(partner_square), clear_right(0)`; cost C3.
* right invalidation: normal king/rook movement templates carry the same
  generic `clear_right(0)` effect — this is **action-specific effects**
  emitted by the compiler when lowering the actor's movement pattern
  (decision: effects, not a runtime state-trigger engine).
* rook captured: the right is cleared by the owner's own king/rook move
  effects; a captured rook does not need special handling (the right is
  not about the rook's existence at a square).
* identity/hash/undo: slot 0 enters position key, native hash (slot-id
  Zobrist), serialization, and the fixed undo slot snapshot.

## 3. Stress test 3 — double-step token capture (en passant)

* token slot: `AuxSlot(1, token_square, expire_next_turn)`.
* creation: two-step forward move with `path=path_clear` → effects
  `move, set_token(1, passed_square)`; cost C2.
* capture: leap to adjacent enemy target with
  `slot_guard=SlotQuery(1, eq, target)` → effects
  `move, remove(token_square), clear_token(1)`; cost C2.
* expiry: uniform turn-boundary lifecycle step clears `expire_next_turn`
  slots after the opponent's move; deterministic and undo-simple.
* state safety: the token is in position identity, native hash, undo,
  serialization and TT key (full ten-point contract).

No `EN_PASSANT` action; the off-target capture is a generic `remove`
effect with `square_ref=token`.

## 4. Stress test 4 — file-occupancy drop guard (nifu)

```
geometry=drop, target=target_empty,
guard = count(self, type_mode=base, promoted=no, location=board,
             spatial=same_file(target)) == 0,
effects = remove_from_hand(base), place
```

* promoted pieces are excluded via `promoted=no`;
* base/current distinguished via `type_mode=base`;
* owner-relative via `owner=self`;
* board only via `location=board` (hand excluded);
* hand counts are not consulted by this guard.

The IR knows no "pawn": it only knows "matching base type on the same
file".  Cost C1; stratum S1 (pure state query).

## 5. Stress test 5 — drop with no legal reply (uchifuzume)

```
geometry=drop, target=target_empty,
invariant=own_anchor_safe,
postconditions = [opponent_checked, no_legal_reply(probe_stratum=S3)],
effects = remove_from_hand, place; cost C4; stratum S4
```

Execution order: cheap prefilter (only drops, only the guarded base type,
only if the drop gives check — `opponent_checked` postcondition after trial
make) → then the bounded reply probe.  The probe runs the reply side's
generation + cheap guards + trial make + invariant **up to S3** (S4
disabled in nested probes): single-level, early-exit existence scan, no
`legal → terminal → legal` recursion.  Termination is static.

## 6. Counterexample weird rules

1. **weird ray** — quiet `path_clear`, capture `path_count_eq(2)` (same
   primitives as cannon, different constant);
2. **zone occupancy drop** — drop guard
   `count(self, current, any, board, zone) < 3` (state query only);
3. **temporary right** — promotion template effects
   `set_current_type, set_token(right slot), move` with
   `expire_next_turn` lifetime;
4. **compound shift** — `move(actor), shift(partner_square)` (two-effect
   action, generic);
5. **restricted finish** — a capture template with the same
   `opponent_checked + no_legal_reply` postconditions (generic
   restricted-finish; same primitives as uchifuzume, no "pawn" semantics).

All five validate in the prototype.

## 7. Primitive reuse matrix

| Primitive / Category | Screen Ray | Shift | Double-step | File-guard Drop | No-reply Drop | Weird rules |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| geometry leap | | x | x | | | x |
| geometry ray | x | | x | | | x |
| geometry drop | | | | x | x | x |
| target_empty | x | x | x | x | x | x |
| target_enemy | x | | | | | x |
| path_clear | x | x | x | | | x |
| path_count_eq | x | | | | | x |
| state query (count/file/zone) | | | | x | | x |
| slot guard (right/token) | | x | x | | | x |
| effect move | x | x | x | | | x |
| effect remove | x | | x | | | x |
| effect remove_from_hand / place | | | | x | x | x |
| effect clear_right / set_token / clear_token | | x | x | | | x |
| invariant squares_not_attacked | | x | | | | |
| postcondition opponent_checked / no_legal_reply | | | | | x | x |

Only one category is used by a single stress test — `squares_not_attacked`
(castling) — and it is fundamental: a multi-square transit safety query,
not a game-specific primitive (`WHY THIS IS FUNDAMENTAL`: any
multi-square move or transit check needs it; it generalizes
`own_anchor_safe` to an arbitrary square list).

## 8. Conclusion

The five stress rules and five weird rules are expressed with a closed set
of ~31 execution primitive kinds; no primitive exists solely for one
traditional game, and the only single-use invariant is a fundamental
generalization of royal safety.
