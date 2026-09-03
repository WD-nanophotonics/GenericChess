# H50B2A semantic Native iterative search core

F50B2A adds an experimental, no-transposition-table search entrypoint for the
compiled semantic Native runtime. It is not production search routing and does
not modify the legacy `GCPosition` engine.

## Contract

`generic_chess.native.semantic.semantic_iterative_search` binds one compiled
semantic rules capsule, one packed `GCSemanticPosition`, and an optional
immutable evaluator profile. It performs deterministic iterative deepening from
depth 1 through `max_depth`, retaining only the last complete iteration. The
result includes the exact packed action and PV, score, completed/selective
depths, node and transition counters, termination reason, and zero-valued TT
diagnostics. The package-level `generic_chess.native.iterative_search` export is
an alias for this semantic-only entrypoint.

The root position is never mutated. Each recursive level uses a heap-allocated
`GCSemanticPosition` slot and checked semantic runtime transitions; no complete
semantic state is placed on the C recursion stack. PV storage is also heap
allocated. A spare heap state slot is reserved for deterministic root fallback,
including `max_depth=0` and interrupted searches.

## Limits and fail-closed behavior

Node, monotonic-time, and cooperative cancellation checks occur at the root,
before every node, and before every child transition. If an iteration is
interrupted, the prior complete iteration remains authoritative. If none is
complete, the smallest checked root action is returned with `used_fallback=true`
and an explicit `node_budget`, `time_budget`, or `cancelled` reason. No TT, PVS,
null move, LMR, quiescence, or heuristic ordering is enabled.

Exact full history is required by the semantic position capsule. Terminal
evaluation delegates to the existing semantic terminal policy, including
winner-aware checkmate and continuous-check adjudication plus neutral
repetition, max-ply, and no-contest outcomes. Declaration-bearing rulesets are
explicitly rejected by this no-TT action-only entrypoint; declaration-aware
search remains a later capability rather than a silent second action model.

## Resource policy

The search is the deterministic single-worker baseline. It does not yet spawn
threads or share mutable TT/evaluator state. The resource preflight is therefore
bounded by one `GCSemanticPosition` per depth slot plus PV tables sized by the
requested depth, with checked allocation arithmetic and a hard
`GC_SEM_MAX_PLY` depth cap. Heavy workflow commands remain serialized; measured
CPU and memory can be used for independent external audits, but this core must
not trade semantic identity for parallel nondeterminism.
