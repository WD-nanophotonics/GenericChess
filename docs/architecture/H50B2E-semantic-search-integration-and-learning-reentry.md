# H50B2E: Semantic Search Integration and Learning Re-entry

Status: implemented in sandbox; promotion remains on hold.

Parent checkpoint: `dd2178d53d06b009933adecea469832e0c33532c`

## Decision

The semantic Native search path now has a persistent engine object. A single
engine owns one compiled semantic rules capsule, one bound material/evaluator
profile, and one compact transposition table (TT). The Python wrapper exposes
`SemanticSearchEngine` (also exported as `NativeSemanticSearchEngine`) and
keeps the engine reusable across `GameSession` searches.

The engine lifecycle is explicit:

- `clear_tt()` increments the TT generation and removes all entries.
- `bind_checkpoint()` validates the ruleset, replaces the bound material
  profile, and recreates the native engine with a fresh TT.
- `bind_evaluator()` performs the same safe rebind for a new evaluator
  configuration.
- `tt_info()` reports generation, occupancy, probes/hits/cutoffs, entry size,
  and allocation so callers can verify reuse and invalidation.

The Native TT entry is 88 bytes. It stores semantic identity, search depth,
score/bounds, best action, and generation metadata; it does not cache a fixed
64-action PV. Principal variations are reconstructed by full-window replay,
which keeps PV decoding correct across cache hits and avoids coupling cached
entries to a particular Python history object.

## Semantic position and history binding

`pack_semantic_search_position()` transports the current board, hands, side to
move, auxiliary state, and the complete `GameSession` repetition/check history.
Each history witness is canonicalized with the compiled semantic ruleset and
packed into four 64-bit identity words, together with actor and gave-check
metadata. The current packed identity is checked against Core's
`position_identity_key()` before Native search starts.

Consequently, identical board material reached through different repetition or
check histories cannot cross-reuse a TT result. The persistent TT is therefore
safe across moves in one session while remaining isolated across materially
different histories and checkpoint bindings.

## Declarations and Standard Shogi

Declaration decisions are represented internally as tagged virtual actions
(`0x8000000000000000 | declaration_index`). Generic declaration assessment is
performed through the semantic runtime assessor, so the engine can select a
winning declaration even when no board action is available. Declaration
results are returned as `declaration_id`, decoded into the public decision line,
and terminate self-play/arena games through `GameSession.declare()`.

The normal semantic root-parallel helper now preserves declaration semantics by
delegating declaration-bearing positions to the declaration-aware iterative
path instead of dropping out-of-band decisions.

## Learning re-entry

Semantic compiled rulesets now enter the real self-play and arena call chains
through `SemanticSearchEngine`. They do not pass through the legacy piece-type
evaluation compiler. Checkpoint validation and profile quantization remain in
the learning layer; a checkpoint change rebinds the persistent engine and
clears its TT without recompiling the semantic `RuleSet`.

Legacy compiled rulesets retain their existing `NativeSearchEngine` path.

## Verification

Native extension rebuild:

```text
C:\Users\wdai\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\build_native_zig.py
```

Focused Courier heavy validation passed:

```text
generic-chess-flow.cmd heavy -- .venv\Scripts\python.exe -m pytest -q --basetemp .generic_chess_flow\b2e-final tests\test_h50b2a_semantic_native_search.py tests\test_h50b2e_semantic_search_engine.py tests\test_native_semantic_probe_search.py tests\test_native_semantic_position.py tests\test_generic_declaration_semantics.py tests\test_learning_selfplay_arena.py
```

Result: 87 tests passed. The broader B2E learning/diagnostics run also passed
88 tests after assigning a repository-local pytest base directory. Additional
smoke coverage exercised Standard Shogi semantic search, declaration decoding,
checkpoint TT invalidation, history isolation, cancellation/node budgets, and
the actual semantic self-play call chain.

No raw benchmark output, generated binaries, or transient Courier evidence is
tracked. This checkpoint has not been promoted.
