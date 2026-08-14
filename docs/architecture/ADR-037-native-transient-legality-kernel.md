# ADR-037: Native Transient Legality Kernel

Status: Accepted for retained Native capability; production search integration deferred to a separately authorized phase.

## Decision

Retain one Native transient S0–S4 legality-kernel API that returns ordered packed semantic action identities. The API may use a packed state capsule at this boundary, but it returns no transient child capsule and has no history or terminal authority.

Do not change Core, `SearchPathRuntime` production legal generation, AlphaBeta routing, external SHA identity, repetition, TT, evaluator, qsearch, move ordering, or schema/action layout.

## Context

F19 established that S0–S4 legality is history independent and selected `NATIVE_LEGALITY_KERNEL`. The existing Native `guarded_actions` implementation still ran exact child key/history bookkeeping for each trial. F20 audited that cost and tested a single `TRANSIENT S0–S4 LEGALITY KERNEL` family using the same semantic transition and no-history policy.

## Authority and exact bridge

Python `SemanticEngine.iter_legal_action_bindings` remains authoritative for reference correctness and binding semantics. Native preserves canonical action order and all identity fields: kind, pattern, geometry, actor current/base type, source, target, and promotion target.

The bridge is:

```text
ordered packed Native action
  -> direct integer bit decode and frozen ID maps
  -> internal SemanticAction
  -> SemanticEngine._make_binding_from_action(position, action, exact_pattern)
  -> existing Python authoritative transition on push
```

The binding reconstruction uses exact pattern/geometry identity and exact geometry path reconstruction. It does not first-match or coordinate-only fallback.

## Transient safety boundary

The transient kernel parses/uses only current semantic state: ruleset authority, side, ply, board, hands, and auxiliary state. It deliberately ignores history, repetition counts, external canonical SHA, terminal status, evaluator, TT, and search. Candidate child transitions and nested S3 reply probes use the transient history mode, so child key computations and history appends are both zero. The local child state is not returned to Python.

## Evidence

H20A observed 2,354 child key computations and 2,354 history appends in the old guarded path across 84 Standard Shogi states. H20B produced zero transient child key/history operations, exact ordered parity across 84 Standard Shogi states and the 10-case generic corpus, zero binding/child-transition mismatches, and fail-closed input validation.

The packed-state performance gate passed. The full one-shot route, including state packing, Native entry, kernel, direct decode, public projection, and binding reconstruction, achieved median `4.7933x` speedup and `4,127.98 us` saving over Python authoritative legal-action plus binding generation; all 40 measured Standard Shogi states were faster. Atomic max latency was `584.04 us`.

The test-only AlphaBeta shadow preserved exact search outputs and counters. Profile A gained `33.50%`; Profile B gained `32.31%`; all four semantic cases gained in both profiles. These measurements authorize selection of the future direct-routing boundary but do not implement it.

## Consequences

The retained Native capability removes unnecessary child SHA/history work for callers that explicitly request transient legality while preserving the exact-history authority contract. A future direct search-routing phase must be separately authorized and must retain the Python push, terminal, history, TT, evaluator, qsearch, and ordering boundaries.

F20 final verdict:

```text
F20_RESULT = LEGALITY_KERNEL_PASS
H20B_RETAINED = true
ONE_SHOT_ROUTING_GATE = PASS
SELECTED_NEXT_BOUNDARY = NATIVE_LEGAL_ACTION_ROUTING_DIRECT
PRODUCTION_SEARCH_ROUTING_CHANGED = false
```
