# Rule Semantics Architecture Audit & Semantic Ownership Contract

Phase 1.9A-1.  Architecture audit only: no rule primitives were implemented,
no Core/Rules/native/learner source was changed.  This document answers, with
code-path-level evidence, *who defines, compiles, executes and owns rules* in
GenericChess today, and defines the contract the next phase (Rule IR design)
must follow.

## 1. Executive summary

GenericChess is a **Python-first generic rule engine with a C hot-path
backend**.  The Python Core is the executable reference specification and
correctness oracle; the native kernel is an optimized executor of the same
compiled semantics.  The audit found:

* no correctness-level (P0) blocker;
* no game-specific interpretation in Python Core or native C;
* no per-node Python callback in the native hot path (0 `PyObject_Call*` in
  `_native/*.c`);
* one mechanical duplication risk: movement-geometry lowering exists twice
  (Python precomputes per-square tables; native recomputes the same targets
  from the same atom definitions at move-generation time);
* the current action/state model cannot express multi-piece effects,
  off-target captures, history-derived state or post-action/legal-reply
  constraints — the exact dimensions required by Cannon / Castling /
  En Passant / Nifu / Uchifuzume.

Final verdict: **`ARCHITECTURE_READY_FOR_RULE_IR_DESIGN`** — the boundaries
are healthy enough to design a generic semantic layer, provided the new IR
honours the ownership contract and the 12 invariants in §26.

## 2. Repository inventory

Measured by `scripts/audit_rule_architecture.py`
(`artifacts/rule_semantics_audit/architecture_inventory.json`):

| inventory | count | LOC |
| --- | ---: | ---: |
| Python (package) | 155 files | 23,880 |
| C sources+headers (`_native/`) | 24 files | 4,800 |
| Tests | 75 files | 12,866 |
| Native bridge Python (`native/`) | — | included above |

Layer directories (Python LOC): `core/` (executor semantics), `rules/`
(schema/validation/compiler), `generation/`, `session/`, `cli/`, `ui/`,
`ai/`, `learning/`, `native/` (bridge + adapter + engine wrappers).  Native C
modules: `native_module.c` (FFI), `native_rules.c` (compiled payload → C
tables + deterministic Zobrist seeding), `native_state.c` (pack / make /
unmake), `native_movegen.c`, `native_attack.c`, `native_hash.c`,
`native_perft.c`, `native_eval.c`, `native_search.c`, `native_tt.c`,
`native_clock.c`, `native_cancel.c`.

## 3. Current module dependency map (real imports)

```
rules/schema.py ──► rules/validation.py ──► rules/compiler.py ──► CompiledRuleSet
   ▲                                                                 │
   │ (RuleSet definition)                                            ▼
generation/* ──────────────────────────────────────────────► core/* (executor)
                                                                │
   core/attacks ◄── core/movegen ◄── core/transition ◄── session/session.py
        │                                        ▲            │
        │                                        │            ▼
   core/terminal ◄── core/repetition ◄── core/keys ◄── ui/controller.py
                                                                │
   native/compiler.py ◄── CompiledRuleSet (mechanical flatten)  ▼
   native/adapter.py ◄── pack position/action          ai/* (limits, budget)
   _native/native_module.c (FFI)                                │
   native_rules / native_state / native_movegen / native_attack /
   native_hash / native_perft / native_eval / native_search / native_tt
        ▲
   native/engine.py (NativeSearchEngine — one FFI call per search)
        ▲
   learning/* (arena, selfplay, diagnostics, leverage, phase18)
```

`session/session.py` imports only `core.actions/errors/keys/movegen/
position/transition` and `session.record/result` — no native, no rules
compiler, no AI.  `ui/controller.py` imports Core public APIs for display
only (cached `legal_actions`, `is_in_check`, `position_key`); it never
adjudicates.  `learning/*` consumes `core.*` + `native.compiler/engine` +
`session` public semantics.

## 4. Semantic execution paths (verified call paths)

### Python reference path

```
RuleSet ──► compile_ruleset()
  ├─ validation.py (field checks, invariants)
  └─ compiler.py _build_tables()  ──► CompiledRuleSet
        (leap_targets, ray_paths, empty_mobility, empty_forward_mobility,
         drop_allowed, promotion_allowed, promotion_forced — all derived)

legal_actions_from_position(position, compiled)
  ├─ _expanded_pseudo_actions: _piece_actions (tables) → _promotion_variants
  │                            → _drop_actions (static masks)
  └─ filter via _is_legal: make (movegen._apply_action_unchecked)
        → anchor_square → is_square_attacked (attacks.pseudo_attacks)

transition: core/transition.py _transition (single child-state builder)
  → _apply_action_unchecked → position_key → update_repetition_counts
  → _terminal_from_parts

terminal: _terminal_from_parts → has_legal_action (first-legal scan, NOT
  full legal_actions) → is_in_check → repetition limit → max_ply
```

### Native path

```
CompiledRuleSet ──► native/compiler.py build_compile_payload()
  (flattens atoms, promo pairs/forced/alive, drop masks, limits — no
   semantic decisions)
        ──► _native_core.compile_rules(payload) ──► GCRules
  (C stores atoms + bitsets; Zobrist tables seeded from fingerprint)

pack_native_position(payload) ──► gc_position_pack (full hash, history
  stack, repetition context)

native search: NativeSearchEngine.search(session, limits)
  ──► pack_native_search_position ──► native_iterative_search (ONE FFI call)
  per node (all in C):
    gc_terminal_with_pseudo (uses the node's pseudo/legal lists)
    gc_legal_actions: pseudo (atoms on-the-fly) → gc_legal_filter
        (make → gc_find_anchor → gc_is_square_attacked → unmake)
    gc_make_move / gc_unmake_move per child
```

## 5. Single source of truth audit

| Semantic | User Rule Definition | Lowering Site | Python Execution | Native Lowering | Native Execution | Duplicate Interpretation? |
| --- | --- | --- | --- | --- | --- | --- |
| movement atoms | `PieceType.movement_atoms` (Leap/Ray) | `rules/compiler.py _build_tables` | compiled tables in `movegen._piece_actions` | atoms flattened into payload | C recomputes targets on the fly from atoms | **suspected** (geometry lowering duplicated; same atom source, differential-tested) |
| leap | `LeapAtom(offset)` | compiler per-square targets | `leap_targets` | `GCAtom{kind=0,vec}` | `gc_pseudo_actions` steps offset | same source, two executors |
| ray / blockers | `RayAtom(direction, max_steps)` | compiler ordered paths | `ray_paths`, stop at first occupant | `GCAtom{kind=1,vec,max_steps}` | stepping, stop at first occupant | same source, two executors |
| attack / pseudo-attack | derived from atoms | compiled tables | `attacks.pseudo_attacks` | — | `native_attack.c gc_is_square_attacked` | same semantics, two executors |
| royal safety | `PieceType.is_anchor` | compiled `types_by_id` | `attacks.is_in_check` | payload `is_anchor` | `gc_find_anchor` + attack query | none (config-derived) |
| capture | Core transition rule (capture → hand base type) | compiled (implicit) | `_apply_action_unchecked` | — | `gc_make_move` | same semantics, two executors |
| promotion | `promotion_allowed/forced` + `promotion_target_ids` | compiler pairs/squares | `_promotion_variants` | payload pairs/forced/alive bitsets | `gc_expand_promotion` | **none** — native consumes the compiled masks |
| forced promotion | `promotion_forced` dest squares | compiler | `_promotion_variants` | payload bitset | `gc_promo_forced` | none |
| drop | `drop_allowed` static masks | compiler (derived) | `_drop_actions` | payload bitset | `gc_drop_allowed` | none |
| hand / base type | captures add `base_type_id` | Core transition rule | `_apply_action_unchecked` | — | `gc_make_move` (hand add/remove) | same semantics, two executors |
| promoted/current type | `Piece.current_type_id` | compiler validates | pieces carry both | payload board | `GCPiece{base,current,promoted}` | none |
| anchor | `is_anchor` | compiled | anchors uncapturable | `is_anchor` bitset | same | none |
| legal move | own-anchor-safety after make | Core `_is_legal` | Python filter | — | `gc_legal_filter` | same semantics, two executors |
| transition | Core transition rule | `core/transition.py _transition` | Python | — | `gc_make_move` (+hash/history) | same semantics, two executors |
| repetition | `repetition_limit` | compiled | `repetition.py` counts | payload limit | history stack + `gc_repetition_context` | same semantics, two executors |
| terminal | `stalemate_result`, `max_ply`, repetition | compiled | `terminal._terminal_from_parts` | payload limits | `gc_terminal_with_pseudo` | same semantics, two executors |
| position key | Core stable key | `core/keys.position_key` | SHA-256 over ruleset+side+board+hands | — | 128-bit Zobrist (search hash, not archive key) | different by design (documented) |
| history | `GameState.repetition_counts` | `core/transition._transition` | counts tuple | — | history stack + repetition context | same semantics, two executors |
| material evaluation | profile/checkpoint | `learning/material.py` | `features.linear_value` | `native_eval` tables | `native_eval.c` | same semantics, two executors |
| action encoding | `Action` (BoardMove/DropMove) | `core/actions.py` | Python objects | `GCPackedAction` bit layout | C packed actions | one encoding, two representations |

## 6. Semantic duplication risks

* **Confirmed**: none (no semantic is independently *interpreted* from
  high-level rules in both Python and C).
* **Suspected**: movement-geometry lowering (Python `_build_tables`
  precomputes per-square leap/ray tables; C recomputes equivalent targets
  from the same atoms inside `gc_pseudo_actions`).  Both derive from the
  same atom definitions and are kept aligned by the native differential
  suite; it is a mechanical duplication, not a divergent interpretation.
* **None**: promotion, forced-promotion, drop masks, anchor, terminal and
  repetition semantics are consumed by C as compiled bitsets/tables — no
  reinterpretation.

## 7. CompiledRuleSet audit

`CompiledRuleSet` is a frozen dataclass holding: `ruleset_fingerprint`,
`board_size`, `piece_types`, `types_by_id`, `initial_position`,
`initial_entity_count`, `leap_targets`, `ray_paths`, `empty_mobility`,
`empty_forward_mobility`, `drop_allowed`, `promotion_allowed`,
`promotion_forced`, `repetition_limit`, `max_ply`, `stalemate_result`.

* All fields are **fully derived** from the `RuleSet` by
  `rules/compiler.py`; none contain runtime state (no side-to-move, no
  history, no hand contents).
* Python Core executes from the compiled tables (`movegen`,
  `attacks`); the high-level `RuleSet` is not consulted during execution —
  no `HIGH_LEVEL_RULE_LEAK_INTO_EXECUTION`.
* The native adapter consumes only `CompiledRuleSet` fields (never the raw
  `RuleSet`).

## 8. Native compilation audit

* Input: the `CompiledRuleSet` (flattened by `native/compiler.py`
  `build_compile_payload`).
* The adapter does **not** read the raw `RuleSet` and performs **no**
  semantic decisions: promotion/drop/anchor/terminal data are packed
  verbatim from compiled masks; atoms are serialized as `{kind, df, dr,
  max_steps}`.
* C sees a **flattened compiled representation** (atoms + bitsets), not
  partially-interpreted high-level rules.  This is the closest thing to a
  semantic IR today and is the natural seed for the formal Rule IR.
* The only C-side re-derivation is per-square move-target computation from
  atoms (see §6).

## 9. Python Core authority audit

Python Core is the executable reference specification: deterministic,
public-API based, and the oracle for all native differential tests.  No
`REFERENCE_AUTHORITY_DRIFT` was found: the native differential suite
(`native/differential.py`, `tests/`) compares native outputs against Core,
and no Core code replicates native-specific hacks.

## 10. Native executor audit

Native is an optimized executor of already-defined semantics:

* move generation (`native_movegen.c`): compiled atoms + bitsets;
* attack (`native_attack.c`): geometry + occupancy;
* make/unmake (`native_state.c`): mechanical board/hand/hash/history
  updates with full undo;
* history/repetition (`native_hash.c`): history stack + repetition-context
  fingerprint;
* terminal (`native_terminal` inside search): uses pseudo/legal lists;
* evaluation (`native_eval.c`) and search (`native_search.c`): consume
  legal actions/transitions only.

No game-name symbols appear in `core/` or `_native/` (token scan: only
header guards and docstrings).  Classification: **GENERIC /
CONFIG-DERIVED** throughout; no GAME-SPECIFIC or SUSPICIOUS execution logic.

## 11. FFI boundary

* Compile time: one `compile_rules(payload)` call per ruleset, one
  `compile_evaluation(...)` per evaluator.
* Search initialization: `create_search_engine`, `pack_position` /
  `pack_native_search_position`, `create_cancel_flag`.
* Per search: **one** `native_iterative_search` call; the engine object
  owns the TT; per node/move everything stays in C.
* Per node / per move: **no Python callback** — 0 `PyObject_Call*` in
  `_native/*.c` (`HOT_PATH_BOUNDARY_VIOLATION`: none).  The "one coarse FFI
  call per search" principle holds.
* FFI entry points (26): `native_available`, `native_version`,
  `native_capabilities`, `native_rules_info`, `compile_rules`,
  `pack_position`, `replay_position`, `native_legal_actions`,
  `native_pseudo_actions`, `native_attack_map`, `native_terminal`,
  `native_child_snapshot`, `native_snapshot`,
  `native_make_unmake_roundtrip`, `native_long_make_unmake_roundtrip`,
  `native_make_checked`, `native_perft`, `compile_evaluation`,
  `native_fixed_depth_search`, `create_search_engine`,
  `search_engine_clear_tt`, `search_engine_tt_info`,
  `engine_fixed_depth_search`, `create_cancel_flag`, `request_cancel`,
  `native_iterative_search`.

## 12. State ownership table

| State | Python State | Native State | Serialized | Position Key | Native Hash | Undo | Session-owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| board occupancy | `Position.board` | `GCPosition.board` | yes | yes | yes | yes | no |
| side to move | `Position.side_to_move` | `GCPosition.side_to_move` | yes | yes | yes | yes | no |
| current type | `Piece.current_type_id` | `GCPiece.current_type` | yes | yes | yes | yes | no |
| base type | `Piece.base_type_id` | `GCPiece.base_type` | yes | yes | yes | yes | no |
| promoted flag | `Piece.promoted` | `GCPiece.promoted` | yes | yes | yes | yes | no |
| hand | `Position.hands` | `GCPosition.hand_counts` | yes | yes | yes | yes | no |
| ply | `GameState.ply_count` | `GCPosition.ply` | yes | no (not in identity) | no | yes | no |
| history / repetition | `GameState.repetition_counts` | history stack + `repetition_context` | yes (record) | no (history-dependent, not position identity) | context hash | yes | no |
| max ply | compiled `max_ply` | `GCRules.max_ply` | yes | — | — | — | no |
| hash | — | `GCPosition.hash_lo/hi` | no (derived) | Python stable key separate | yes | yes | no |
| repetition context | — | `repetition_context_lo/hi`, `history_complete`, `root_hash_count` | no | no | yes | yes | no |

`Session` holds no semantic state that changes legal/terminal/transition
outcomes: it owns the record, the replay stack and `displayed_ply`
(view-only).  No `SEMANTIC_STATE_OUTSIDE_CORE`.

## 13. Position identity / hash audit

Python `position_key` covers ruleset fingerprint, side to move, every
square's owner/base/current/promoted, and both hands.  It intentionally
excludes ply and repetition counts (they do not change future legality for
the same position).  The native 128-bit Zobrist hash covers the same
semantic fields (owner, base/current type, promoted, hand counts, side);
history/repetition are maintained separately (history stack +
repetition-context fingerprint) and are *not* part of the position hash —
consistent with Python's separation of position key vs repetition counts.
`_verify_replay_root` in the adapter guards that native search is only
entered from a replay-complete root so repetition context is exact.

For future state-dependent rules (castling rights, en-passant token,
cooldowns, nifu file state, uchifuzume probes), the 10-point checklist in
§25 must be applied — identity, hash, serialization, make/unmake and TT
must all be extended together.

## 14. Make / unmake audit

`GCUndo` stores: `from`, `to`, `moved` (piece before make), `captured`
(occupant of `to`, empty if none), `was_drop`, `was_promotion`, `old_side`,
`old_ply`, `old_history_len`, `old_hash_lo/hi`,
`old_repetition_context_lo/hi`.

| State field | Make modifies? | Unmake restores? | Hash updated? | Failure rollback? |
| --- | --- | --- | --- | --- |
| board (`from`/`to`) | yes | yes (via moved/captured/from/to) | yes | yes |
| hand counts | yes (capture add / drop remove) | yes (via was_drop/captured) | yes | yes |
| side to move | yes | yes (`old_side`) | yes | yes |
| ply | yes | yes (`old_ply`) | no | yes |
| hash lo/hi | yes | yes (`old_hash_lo/hi`) | — | yes |
| history stack | append | truncate (`old_history_len`) | context updated | yes |
| repetition context | yes | yes | yes | yes |

Every native state mutation has an exact undo (`I8` satisfied).  Caveat for
the future: `root_hash_count`/`history_complete` are fixed at pack time and
not part of `GCUndo` — new per-move state must either join `GCUndo` or be
derived incrementally, and the search's make/unmake contract must be
extended centrally rather than per-rule.

## 15. Action model audit

Python `Action = BoardMove | DropMove`:

* `BoardMove(from_square, to_square, promotion_target_id=None)`
* `DropMove(base_type_id, to_square)`

Native packed action (64-bit): `to` (8), `from` (8, 0xFF = drop sentinel),
`promotion target` (8), `base type` (8), `kind` (4), reserved bits checked.
The model assumes **one source → one destination → optional capture on the
destination**.

| future feature | current expressibility |
| --- | --- |
| Castling (two pieces move) | **CURRENTLY NOT EXPRESSIBLE** (single from/to) |
| En passant (off-target capture) | **CURRENTLY NOT EXPRESSIBLE** (captured square must equal `to`) |
| Cannon capture | **PARTIALLY EXPRESSIBLE** (action shape is normal; capture *legality* differs — a path/state predicate is missing) |
| Nifu | **PARTIALLY EXPRESSIBLE** (action shape normal; dynamic legality missing) |
| Uchifuzume | **PARTIALLY EXPRESSIBLE** (action shape normal; post-action legality probe missing) |

## 16. Movement model audit

Two primitives: `LeapAtom(offset)` and `RayAtom(direction, max_steps)`
(primitive integer directions only).  Ray semantics: ordered path, stop at
the first occupied square; capture on an enemy non-anchor occupant; enemy
anchor blocks without capture; `max_steps=None` unbounded.

**Cannon gap**: the ray model fuses "quiet" and "capture" into one
blocker-pass rule (stop at first occupant).  Xiangqi cannon capture needs a
*path predicate*: exactly one intervening screen between source and target
for captures, and zero screens for non-captures.  The blocking dimension
that would express this (occupancy-count predicate along the ray) does not
exist; geometry itself is sufficient.

## 17. Drop model audit

Drop semantics today: hand count > 0, static per-square `drop_allowed`
mask, destination empty, self-check guard.  The mask is derived from
movement geometry and is **static per (type, player, square)**.

* **Nifu gap — state-query limitation**: legality depends on a file-wide
  same-side pawn query; no state predicate exists in the drop path.
* **Uchifuzume gap — postcondition limitation**: legality depends on
  whether the *resulting* position is checkmate (a legal-reply
  existential); no post-action constraint stage exists.

Neither is a generation bug: the mask derivation is correct for static
semantics.  The missing capabilities are a *state-query predicate* and a
*post-action/legal-reply guard*, both absent from the current model.

## 18. Attack / legality dependency audit

Verified dependency graph (acyclic):

```
movement tables ──► pseudo_attacks ──► is_square_attacked
                                    ──► is_in_check (anchor square attacked)
movegen ──► pseudo actions ──► _is_legal (make → own anchor safe?)
        ──► legal_actions_from_position (filter)
terminal ──► has_legal_action (first-legal scan) ──► is_in_check
```

* Attack query does **not** call legal move generation.
* Legal move generation calls attack (once per pseudo move, after a trial
  make).
* `has_legal_action` returns at the first legal candidate (does not build
  the full set).
* `ATTACK_LEGALITY_DEPENDENCY_CYCLE`: **none currently**.
* Castling transit-square attack queries would slot into
  `is_square_attacked` naturally (no new cycle).

## 19. Terminal / history audit

Python `_terminal_from_parts`: no-legal-moves → checkmate/stalemate
(via `is_in_check`), then repetition limit, then max ply.  It calls
`has_legal_action` (first-legal scan), **not** the full `legal_actions`.
Native `gc_terminal_with_pseudo` consumes the pseudo/legal lists already
generated for the node (no extra move generation).

Future risk (documented, not solved): uchifuzume needs
`action legality → after-action → opponent checkmate`, i.e. a
legal-reply probe inside the legality filter, creating a potential
`legal → terminal → legal` recursion.  The contract (§24/§25) requires any
such probe to be statically identifiable and bounded.

## 20. Hot path cost map (native search)

| step | frequency | cost class | allocates? | scans board? | touches history? | calls attack? |
| --- | --- | --- | --- | --- | --- | --- |
| terminal/repetition check | per node | O(legal) via existing lists | no | no (lists) | yes (context) | no |
| pseudo movegen | per node | O(squares × atoms) | move list growable (amortized) | yes | no | no |
| legal filter | per pseudo move | trial make + anchor attack | no | partial (trial make) | yes (make/unmake history) | yes |
| make | per child | O(1) + hash xors | no | no | yes | no |
| recursive search | per child | — | no | no | no | no |
| unmake | per child | O(1) + hash xors | no | no | yes (restore) | no |

`native_search.c` has no `malloc` in the search loop (allocation only in
rules compile / move-list growth).  Compile-time: rules/eval compile +
Zobrist seeding.  Per-game: engine/pack.  Per-search: one FFI call.
Per-node: no Python.  Per-action: no Python.  A future rule predicate that
is cheap and statically identifiable (e.g., a file-occupancy query or a
post-action probe bounded by a single legal scan) would fit this shape;
anything per-node Python is forbidden.

## 21. Generator boundary

`generation/*` produces high-level `RuleSet` definitions only.  It imports
Core movegen for the opening legal-move *report* and rules compiler for
validation, and never imports `native/` or `ai/search`.  No
generator→native/executor coupling.

## 22. Session / UI / AI / Learning boundary

* **Session**: consumes `legal_actions`, `apply_action`, `initial_state`,
  `position_key` — no native, no legality decisions of its own.
* **UI**: caches session-provided `legal_actions` for preview; uses
  `is_in_check`/`position_key` for display.  No `UI_SEMANTIC_DUPLICATION`
  (no self-adjudicated drops/moves).
* **AI**: search consumes legal actions, make/unmake, terminal and
  evaluation only; no piece-name or game-specific legality in
  `ai/search.py`/native search.
* **Learning**: changes evaluator/profile/checkpoint only; `tdleaf.py`,
  `selfplay.py`, `arena.py` implement training/measurement, never legality.

## 23. Architecture risk register

* **P0 — correctness architecture blocker**: none found.
* **P1 — future Rule IR blockers**:
  1. geometry lowering duplicated (Python tables vs C on-the-fly) —
     the IR should define one lowering;
  2. action model locked to one-from/one-to/on-target-capture;
  3. no state-query predicate and no post-action guard stage;
  4. history/identity model has no slot for rights/tokens/ephemeral state.
* **P2 — maintainability**: adapter and engine wrappers contain duplicated
  profile/pack helpers across `native/compiler.py`/`adapter.py`/
  `engine.py`/`learning/`; naming of search wrappers (fixed-depth vs
  iterative) is inconsistent.
* **P3 — cosmetic**: none actioned.

## 24. Semantic Ownership Contract

* **Layer A — Rule Definition** (Python `rules/schema.py`): user-facing
  declarative representation, serialization, versioning.  Knows game and
  movement concepts; must not know C layout, search, TT, node budgets.
* **Layer B — Validation/Compiler** (Python `rules/compiler.py`): single
  lowering authority.  `ONE SEMANTIC → ONE LOWERING SITE`; Python Core and
  native must not each reinterpret a high-level rule.
* **Layer C — Compiled Semantic Representation** (`CompiledRuleSet` and the
  future Rule IR): semantic source of execution truth for both executors.
* **Layer D — Python Reference Executor** (`core/`): executable
  specification and correctness oracle; deterministic, no UI/search/native
  hacks, no game-name special cases.
* **Layer E — Native Adapter** (Python `native/compiler.py`/`adapter.py`):
  mechanical lowering/packing only; forbidden to invent semantics.
* **Layer F — Native Executor** (C): movegen/attack/transition/make/unmake/
  history/terminal/evaluation; knows only compiled generic semantics —
  never "Shogi/Chess/Xiangqi/Pawn/Cannon/Castling/Nifu" as game semantics.
* **Layer G — Search**: consumes legal actions, apply/make, undo, terminal,
  evaluator, generic action metadata; never interprets rule language.
* **Layer H — Session/UI/Learning**: consume public semantics only; never a
  second source of rule truth.

## 25. State Ownership Contract

Any runtime information that changes future legal actions, terminal results
or transitions belongs to Core Position semantic state — **not** Session,
UI or AI state.  A new semantic state is `DESIGN INCOMPLETE` until all ten
items are answered: 1) Definition, 2) Python storage, 3) Native storage,
4) Serialization, 5) Position identity, 6) Native hash, 7) Make, 8) Unmake,
9) Repetition interaction, 10) TT safety.

## 26. Architecture invariants

| invariant | status |
| --- | --- |
| I1. Rule semantics have one lowering authority | **PARTIALLY SATISFIED** (compiled masks are single-lowered; movement geometry is lowered twice — same source, mechanical) |
| I2. Python Core is the correctness oracle | **SATISFIED** |
| I3. Native does not invent game-specific semantics | **SATISFIED** |
| I4. Search never interprets high-level rules | **SATISFIED** |
| I5. Session/UI/Learning never own legality state | **SATISFIED** |
| I6. No per-node Python callback | **SATISFIED** |
| I7. Runtime semantic state participates in identity/hash when required | **SATISFIED for current semantics; NOT YET APPLICABLE for rights/tokens** (no such state exists yet) |
| I8. Every native state mutation has exact undo | **SATISFIED** |
| I9. Attack semantics do not recursively depend on full legal-action semantics | **SATISFIED** (acyclic) |
| I10. Generator produces Rule Definitions, not executor instructions | **SATISFIED** |
| I11. New semantics must be differential-testable Python vs Native | **SATISFIED** (differential suite exists) |
| I12. Expensive legality probes must be statically identifiable | **PARTIALLY SATISFIED** (today all legality is make+attack; post-action/legal-reply probes do not exist yet) |

## 27. Stress-test gap matrix

| Feature | Cannon | Castling | En Passant | Nifu | Uchifuzume |
| --- | --- | --- | --- | --- | --- |
| Geometry extension | partial (ray path ok) | missing (two-piece) | missing (two-square) | not applicable | not applicable |
| Path predicate | **missing** | not applicable | not applicable | not applicable | not applicable |
| State query | missing (screen count) | missing (rights) | missing (en-passant token) | **missing** (file occupancy) | missing (result probe) |
| History-derived state | not applicable | missing (rights) | missing (token) | not applicable | not applicable |
| Multi-piece effect | not applicable | **missing** | partial (actor+captured) | not applicable | not applicable |
| Off-target capture | not applicable | not applicable | **missing** | not applicable | not applicable |
| Pre-action guard | missing (screen predicate) | missing (rights/legality) | missing (token) | missing (file query) | not applicable |
| Attack query | partial (existing) | partial (transit squares would work) | not applicable | not applicable | not applicable |
| Post-action constraint | not applicable | not applicable | not applicable | not applicable | **missing** |
| Legal-reply existential | not applicable | not applicable | not applicable | not applicable | **missing** |
| Hash/state impact | none | rights token | token | none (file query from board) | none |
| Undo impact | none | rights | token | none | none |

## 28. Proposed scope for Phase 1.9A-2

Design (not implement) the semantic categories and IR requirements:

1. a single movement-geometry lowering (one authority for leap/ray/path);
2. path-sensitive occupancy predicates (screen counts, file queries);
3. pre-action guards and post-action/legal-reply constraints with a static
   cost classifier (bounded probes);
4. an extended action record (optional second square / off-target capture /
   compound effect) and matching identity/hash/undo/serialization slots;
5. rights/tokens/ephemeral-state extension points following the §25
   checklist;
6. differential-testable dual-executor lowering for every new primitive.

## 29. Observed

* 155 Python files / 23,880 LOC; 24 C files / 4,800 LOC; 75 test files /
  12,866 LOC; 26 FFI entry points; 0 `PyObject_Call*` in `_native/*.c`.
* `session.py` imports only Core public modules; `ui/` caches session legal
  actions; `learning/*` consumes Core + native public semantics.
* Native compiler input is `CompiledRuleSet`; C receives flattened atoms +
  compiled bitsets; token scan found no game-name execution logic in
  `core/` or `_native/`.
* `terminal._terminal_from_parts` uses `has_legal_action` (first-legal),
  not full `legal_actions`; attack never calls legal movegen.
* `GCUndo` restores every mutated field; `native_search.c` has no
  allocation in the search loop; one `native_iterative_search` FFI call per
  search.
* `position_key` = ruleset + side + board (owner/base/current/promoted) +
  hands; repetition/history are separate; native 128-bit hash matches the
  same semantic fields with a separate repetition context.

## 30. Inferred

* The two-executor geometry lowering is the main structural duplication;
  keeping it aligned relies on the differential suite, so a formal IR should
  define geometry exactly once.
* The compiled payload already behaves like a primitive semantic IR
  (atoms + masks); extending it with predicates/guards is the natural
  Phase 1.9A-2 path rather than introducing a parallel system.
* Because Session/UI/Learning own no semantic state and attack is acyclic,
  new rules can be added at the compiled-representation layer without
  touching search, provided the action/state identity contracts are
  extended first.

## 31. Not established

* Whether any P0 divergence exists between Python and native for
  *unexplored* rulesets (the differential suite covers the corpus; this
  audit did not run an exhaustive ruleset fuzz).
* The exact cost of a future post-action/legal-reply probe in the native
  hot path (no such probe exists to measure).
* UI deep-audit completeness: only legality-related interactions were
  checked; rendering/notation paths were not audited for semantics.

## 32. Known limitations

* Single machine; inventory LOC counts are structural, not quality
  measures.
* Dependency map is module-import level; function-level call graphs were
  verified by source reading for the audited paths only.
* The token scan covers `core/` and `_native/`; `ui/`, `ai/`, `learning/`
  were audited by targeted import/call inspection, not full token scan.

## 33. Tests

Run in this phase:

* `tests/test_rule_semantics_architecture.py` — new boundary/invariant
  tests (see below).
* native differential tests (part of full suite).
* learning tests and full pytest — all existing behaviour unchanged.

## 34. Performance

Audit wall times (measured, `scripts/audit_rule_architecture.py`):

| phase | wall (s) |
| --- | ---: |
| source inventory | 0.016 |
| dependency audit | 0.453 |
| token scan | 0.093 |
| FFI scan | 0.003 |
| total audit | 0.564 |

No performance optimization was performed.

## 35. Files

* `scripts/audit_rule_architecture.py` — inventory generator (new).
* `docs/rule_semantics_architecture.md` — this contract (new).
* `tests/test_rule_semantics_architecture.py` — boundary tests (new).
* `pyproject.toml` — version `0.8.0a6` (new, version-only).

```
Core semantics: unchanged
Rule schema: unchanged
Native semantics: unchanged
Learner: unchanged
```

## 36. Git

Commit + push to `origin/master`; `HEAD == origin/master`; working tree
clean.  No force push.

## 37. Final verdict

**`ARCHITECTURE_READY_FOR_RULE_IR_DESIGN`**
