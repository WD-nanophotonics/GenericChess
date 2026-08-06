# Native Phase 2C: Boundary Closure, Repetition-Safe TT, Iterative Search, Budgets

## Summary

Native schema `native-0.3.0` (kernel version `0.3.0`) adds a persistent,
reusable native search engine: repetition-safe transposition table, iterative
deepening, exact node budgets, a monotonic time budget and native atomic
cancellation. Python Core stays the correctness oracle; the engine is
experimental and is not the production SearchBackend (no UI integration).

## Phase 2C-0 boundary cleanup

* Dropping at the maximum hand count (256) works; only a capture that would
  exceed 256 reports `GC_STATUS_HAND_OVERFLOW`.
* The legality filter no longer silently skips a failed trusted make: it
  records `GC_MOVE_ERROR_TRUSTED_MAKE` + the original `GC_STATUS` and the
  failing packed action, and the Python layer raises a `RuntimeError` with
  packed/status/ply/side/hand counts/fingerprint.
* All fixed-depth and iterative entries enforce `0 <= depth <= GC_MAX_PLY` in
  both layers; allocations use `gc_checked_size_add/mul`.
* The C extension search paths use one cleanup label (all Python-API results
  checked); terminal roots report `nodes == 1`.
* The fixed-depth root uses a shared root alpha; canonical tie-break compares
  packed actions numerically so ordering cannot change the result.

## Repetition context

`GCPosition` now carries `repetition_context_lo/hi` — a deterministic 128-bit
fingerprint of the `{position_hash -> occurrence_count}` mapping over the
whole history — plus `history_complete`. `gc_repetition_count_token` hashes a
`(position hash, count)` pair with deterministic splitmix; make updates the
fingerprint incrementally before appending the child hash, unmake restores it
from the undo record, and `gc_repetition_context_rebuild` recomputes it from
the history. Full history replay (`root_hash_count == 0`) marks the position
complete; the legacy perft pack marks it incomplete. The production iterative
search rejects incomplete history.

## Transposition table

`native_tt.h/c` implements a fixed 4-way set-associative table. Keys include
the 128-bit position hash, the 128-bit repetition context, ply and
history_len, so two states with the same board but different histories never
share an entry. `tt_megabytes` is validated (0 = off, 1–1024); the bucket
count is floored to a power of two so the allocation never exceeds the
request. Entries store mate-normalized scores (`gc_score_to_tt/from_tt`),
generation-tagged replacement (exact key → empty → older generation →
shallowest depth → fixed way), and fail-soft bounds. TT actions are only used
for ordering after exact re-validation against the current legal list.
Shallow entries never produce score cutoffs.

## Iterative deepening + budgets + cancellation

`NativeSearchEngine` (Python) is created once per (rules, evaluation, TT
size); `engine.search(session, SearchLimits(...), cancel_token=...)` replays
the full session history natively, then makes one `native_iterative_search`
FFI call (GIL released). Only fully completed iterations are published;
early aborts return the last complete depth with the real
`node_limit`/`time_limit`/`cancelled` reason, and a depth-1 failure returns a
deterministic canonical fallback (`used_fallback=True`).

* Node budget is exact (checked before visiting each node; `nodes <=
  max_nodes`).
* Time uses `QueryPerformanceCounter` / `CLOCK_MONOTONIC` (never wall or CPU
  clocks) with saturating deadlines, checked at search start, iteration
  boundaries, root child boundaries and every 128 nodes.
* Cancellation is a C11 atomic flag written once from Python (via the
  extended `CancellationToken.register_callback`) and only read inside the
  recursion — no per-node Python callbacks. Aborts always unwind make/unmake,
  and the root position (board/hands/side/ply/history/hash/context) is
  verified restored before returning.

## Differential evidence

`python -m generic_chess.native.phase2c_differential` (and the pytest suite)
verify TT-off == reference minimax == TT-on for score, canonical best,
returned-action-in-reference-best-set and PV legality; iterative depth N
equals fixed depth N; same-board/different-history states stay isolated in a
warm TT; node/time/cancel aborts restore the root.

## Not implemented (next phases)

No qsearch, no production dynamic evaluator, no PVS/aspiration, no
killer/history/countermove, no production SearchBackend or UI integration.
