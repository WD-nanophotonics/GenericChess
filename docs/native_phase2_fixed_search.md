# Native Phase 2A–2B: Kernel Hardening + Fixed-Depth AlphaBeta

## Summary

Phase 2A hardened the native kernel identity and move-generation paths; Phase
2B added a fixed-depth native Negamax/AlphaBeta with a dedicated Python
oracle. Python Core remains the specification and correctness reference.

Native schema: `native-0.2.0` (kernel version `0.2.0`).

## Phase 2A fixes

### Hash identity (base type included)

The old hash keyed pieces only by `(owner, square, current_type, promoted)`.
Two pieces with the same current type but different base types (for example
`A→X` and `B→X` promotions that later demote differently on capture) would
collide. The Zobrist contribution is now the XOR of independent components:

* `piece_owner_square_hash[stream][owner][square]`
* `piece_base_hash[stream][square][base_type]`
* `piece_current_hash[stream][square][current_type]`
* `piece_promoted_hash[stream][square]`

`gc_hash_full`, `gc_hash_xor_piece`, make, unmake, pack and replay all use the
same identity. Hand counts are per `(owner, type, slot)`; counts above
`GC_MAX_HAND` are rejected at pack time instead of silently clamped.

### Complete history replay

`pack_native_search_position(compiled, native_rules, session)` replays the
entire session history through the *checked* native make path, starting from
the Python `initial_state`. The native history stack therefore contains every
position of the game, so a position that appeared three times before the root
is correctly counted when the search revisits it (non-root repetition). The
root is verified field-by-field (side, ply, board, hands, terminal) against
the Python session state before any search starts. Resignation is a
session-level end and never becomes a native board terminal.

### Checked public actions

The Python-visible action entry is `gc_make_move_checked`, which validates the
packed action structurally and then requires exact membership in the native
legal move list (the same truth source as the search). The search hot path
uses `gc_make_move` (trusted) which keeps only cheap memory-safety guards.
Malformed integers fail with `NativeActionError` carrying an enum status code
plus `packed/kind/from/to/base/promo/fingerprint/ply`; the position is never
mutated.

### Non-truncating move lists

Fixed 4096 buffers are gone. `GCMoveList` grows geometrically (64 → 128 →
…) with checked multiplication; allocation failure is an explicit error, not
an empty-looking list. Perft and the search reuse per-level/per-ply scratch
lists, so the hot path never allocates. A 16×16 drop-heavy position with
>4096 legal actions is verified set-equal to Python.

### Capacity and metadata

* `max_ply > GC_MAX_PLY` is rejected at compile with fingerprint and limits.
* History capacity is checked before every make (`history_len < capacity`).
* Hand counts are validated at pack and never silently clamped.
* `NativeCompiledRules.type_map` is a `MappingProxyType` and `type_ids` a
  tuple; external mutation is impossible.

## Phase 2B: fixed-depth native search

### Native-compatible evaluator

The C kernel never re-derives piece values. `compile_native_evaluation`
receives the rule-derived `RuleSetEvaluationProfile` tables (board value by
current type, hand value by base type, promotion gain), validates the
fingerprint and `config_hash`, and builds a `GCEvaluationTables` object that
is deliberately separate from `GCRules` so different evaluation configs never
share state.

`NativeCompatibleEvaluator` / `evaluate_native_reference` mirror the C formula
exactly:

```
score = Σ board_value[current_type] (owner 0) − Σ board_value[current_type] (owner 1)
      + Σ hand_value[base_type] (owner 0) − Σ hand_value[base_type] (owner 1)
if side_to_move == 1: score = -score
clamp to [-MAX_STATIC_EVAL, MAX_STATIC_EVAL]
```

Anchors carry no material value. This is **not** the full production
Evaluator (which adds mobility, anchor-escape and promotion-potential terms);
differential tests use only the native-compatible reference.

### Reference minimax oracle

`reference_fixed_depth_minimax(state, compiled, evaluator, depth)` is a pure,
easily-audited minimax: fixed depth, no TT/qsearch/ordering, terminal score
`±(MATE_SCORE − ply)` for wins/losses and `0` for draws, and a deterministic
canonical tie-break (smallest packed native action value).

### Native search semantics

* `GCSearchContext` owns per-ply pseudo/legal move lists and a triangular PV
  table; no per-node allocation.
* Node order: count node → terminal query (legal moves generated once) →
  terminal score → depth-0 material eval → numerically sorted children with
  trusted make/unmake → best/PV/alpha update → beta cutoff.
* Terminal precedence matches Core `_terminal_from_parts`: no legal moves →
  checkmate/stalemate, then repetition, then max-ply.
* Mate distance uses the evaluation config's `mate_score`; quicker mates win,
  delayed losses score better.
* The C entry releases the GIL during the search, restores the root position,
  and raises a clean error if restore fails.

`native_fixed_depth_search` (Python wrapper) replays history, verifies the
root, runs the C search, decodes actions, checks the best action is in the
Python legal set and replays the PV through Python Core legality.

## Differential evidence

* 12-fixture Phase 1 correctness corpus, depths 0–3: score, canonical action,
  best-action-set minimum, terminal — all equal.
* 6 targeted fixtures (multi-evasion, near-repetition, checking/non-checking
  drop, low-anchor-escape, low-branching), depths 1–2.
* Deterministic fuzz (smoke rulesets, seeded), depths 1–2.
* Repetition-cycle session (same board, different history → different child
  terminal), promotion/drop rulesets, owner-swap score negation.
* Committed `tests/fixtures/native_search_corpus_v1.json` (reference scores +
  canonical packed actions) validated against native.

## Not implemented (out of scope for this phase)

* Native TT, iterative deepening, qsearch, PVS, aspiration, killer/history.
* Time/node/cancellation budgets in the native search.
* Production `SearchBackend` / UI integration (the fixed-depth entry is
  experimental and function-level only).

## Benchmark

`scripts/native_fixed_search_benchmark.py` compares Python reference minimax,
a plain Python fixed-depth alpha-beta, and the native search with the same
evaluator and tie-break. On the dev machine the native search was roughly
6–49× faster than the plain Python alpha-beta; compile and replay costs are
reported separately from search wall time.
