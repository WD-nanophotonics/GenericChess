# Rule Semantic IR v2 — Executable Contract (Phase 1.9B-1.5)

This document fixes what a future Python/Core executor may assume about the
compiled IR and what it must never infer at runtime.  It is the contract the
Phase 1.9B-2 reference executor will be written against.

## 1. Version contract

* `COMPILED_SEMANTIC_IR_VERSION = 2`.  IR v1 (Phase 1.9B-1) was a
  design/foundation artifact and is rejected by `validate_ir`
  (no silent reinterpretation).
* `SEMANTIC_DSL_VERSION = 2` is serialized only for semantic rulesets;
  legacy serialization and fingerprints are byte-identical to pre-1.9B.
* Legacy fingerprints are pinned: R2 `2c56e08b…99883`, Shogi9
  `3d0407b1…57b4d`.

## 2. What the executor may read

1. `CompiledSemanticIR` (geometry catalog, zones, patterns, aux slots,
   triggers, capabilities);
2. the current `Position`;
3. a candidate runtime binding (`pattern_id`, source, target, promotion
   choice — plus any aux-slot square values).

## 3. What the executor must never read

* the high-level `RuleSet` / `RuleSemanticAction`;
* `PieceType.movement_atoms` (semantic geometry is fully lowered into
  `geometry_ids` + per-source ordered paths);
* pattern debug `name`;
* game metadata.

## 4. What the executor must never infer

* which ray / which leap / which geometry (resolved to `geometry_ids`);
* which piece types are matched (typed `TypeRef` / `compare_field`);
* which partner and where it moves (`from_ref`/`to_ref` square refs +
   piece binding on the effect);
* which square is referenced (typed `SquareRef`: SOURCE / TARGET / FIXED /
   OFFSET_FROM_* / PATH_STEP / AUX_SLOT_SQUARE);
* which aux slot is read/written (slot ids; typed value kind + scope);
* capture disposition (`capture_to_hand` vs `remove_from_game` — legacy
   lowering uses `capture_to_hand`);
* promotion behavior (`promotion_mode`: none | inherit_compiled_masks |
   explicit);
* composition behavior (the normalized `patterns` are the final action set;
   `composition`/`replaced_pattern_ids` are audit metadata);
* transition triggers (compiled `triggers` are the only invalidation
   mechanism);
* stratum / cost (compile-time metadata, never re-derived).

## 5. Geometry contract

`CompiledGeometry.paths[owner][source]` is the canonical ordered path
(Design A single lowering).  `geometry_candidates(geometry, owner, source)`
derives candidates mechanically:

* leap: `[(path[0], ())]`;
* ray: `[(path[i], path[:i]) for i in range(min_steps-1, len(path))]`
  (target = path[i]; intermediate path excludes source and target).

`validate_executable_completeness` proves: every `geometry_ids` reference
exists; paths exclude the source; no repeats; `path_step` square refs are
within the static range for exact rays.

## 6. Composition contract

`CompiledSemanticIR.patterns` is the **normalized final action set**:

```
legacy patterns − replaced + AUGMENT additions + REPLACE_LEGACY replacements
```

`REPLACE_LEGACY` records `replaced_pattern_ids` (resolved structurally, never
by name) and fails closed on zero matches or ambiguity unless
`replace_all_matching=True`.

## 7. Effect contract

Each effect carries its full typed operands; per-kind well-formedness is
validated (`_EFFECT_REQUIREMENTS`).  `remove` always carries
`disposition`; `move`/`shift` always carry `from_ref`+`to_ref`;
`set_current_type` always carries `type_ref`; slot effects reference the
correct value kind; `count == 1` in v2.

## 8. Aux state contract

`CompiledAuxSlot{slot_id, value_kind(bool|square_or_none), scope(global|
per_owner), lifetime(persistent|expire_next_turn), initial}`.  Value kind
and lifetime are orthogonal.  EP tokens store the **legal EP landing
square** (midpoint), not the victim square.

## 9. Lifecycle contract (EXPIRE_NEXT_TURN)

Future executor rule (frozen now):

1. ephemeral values are visible during the current side's action
   generation/guard evaluation;
2. on child creation: bind effect operands from pre-action state; copy child
   aux from parent; reset previously-set `expire_next_turn` values to
   default; then apply the action's effects (which may re-set those slots);
3. values set by the current action survive into the child and are visible
   to the opponent's next turn.

No age counter is needed.

## 10. Transition-trigger contract

`CompiledTransitionTrigger{slot_id, event(piece_leaves_square |
piece_removed_from_square), square_ref, owner}` is the only auxiliary
invalidation mechanism.  Castling rights are modeled as PER_OWNER BOOL
slots cleared by triggers watching the actor origin and partner origin
(leave/removal); a replacement piece returning to the watched square never
restores the right.

## 11. Placeholder audit

The v2 IR contains no placeholder square references
(`partner_square`/`token`/`FIXED_SQUARE` strings are gone); every square
ref self-resolves from a candidate binding + position + aux state.

## 12. Capability / fail-closed contract

* legacy Core: legacy rulesets only (semantic rulesets refused at
  `compile_ruleset`);
* native 0.3.0: legacy rulesets only;
* `new_ir_core_executable` stays `False` until the Phase 1.9B-2 reference
  executor exists;
* a semantic ruleset that somehow reaches a legacy/native path must be
  rejected explicitly, never silently executed.
