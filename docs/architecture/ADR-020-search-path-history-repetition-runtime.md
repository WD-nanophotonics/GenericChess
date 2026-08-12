# ADR-020: Core-owned search-path history and repetition runtime

Status: ACCEPTED for F2 Corrective R1

## Context

The public `GameState` is immutable and its SHA-256 position identity is the
boundary for Session, replay, UI, records, and imported history.  AlphaBeta
also needs path-local repetition and continuous-check evidence, but creating a
public child state and recomputing its external key on every DFS edge is
unnecessary work and makes the mutable search data plane too close to the
public data boundary.

## Decision

AlphaBeta owns one Core `SearchPathRuntime` per root search.  It imports the
immutable root once, validates the ruleset fingerprint and exact imported
history/count set, and then maintains the current `Position`, ply, terminal
result, linked history evidence, and collision-safe occurrence table.

After root import, legacy board/drop transitions update a process-local
128-bit `RuntimeHash` by XOR-delta tokens for only the changed side, board
cells, and hand components.  Semantic transitions use an exact component-map
delta fallback with stable addresses, including added/removed auxiliary
components.  Neither path computes a child SHA-256 key.

Each runtime-hash bucket retains exact in-memory `Position` identities.  A
hash collision therefore performs an exact guard comparison and cannot merge
two positions.  Imported historical positions that have no in-memory
`Position` remain opaque external identities; they are accepted only when the
history and repetition-count sets match exactly.

Repetition counts use a persistent parent-pointer snapshot with an
order-independent XOR digest.  The digest is only a fast discriminator;
equal digests are verified against the exact materialized map.  The snapshot
and runtime occurrence table are private search data and are never serialized
or used to change the public SHA contract.

Every explored action is enclosed by an exception-safe `push`/`pop` boundary.
Negamax, PVS re-search, aspiration, ordinary and in-check qsearch, root
tactical scans, lazy/eager paths, and cancellation use that same boundary.
Continuous-check adjudication reads runtime history evidence and remains
disabled when a legacy root has no complete imported history.

## Consequences

The search hot path no longer constructs public child states or child external
keys.  The immutable transition APIs and `reference_minimax` remain the
correctness oracle.  Runtime counters expose root SHA/import work, zero child
external-key work, legacy delta updates, semantic full-diff fallbacks, exact
collision comparisons, snapshot collision checks, and balanced push/pop
behavior.

## Rejected alternatives

* Replacing external SHA keys with `RuntimeHash` would break stable records and
  make collisions unsafe.
* Using only a hash bucket without an exact in-memory guard would allow false
  repetition adjudication.
* Materializing a complete component map for legacy board/drop moves would
  defeat the O(changed-components) requirement.
* Making `GameState` mutable would violate Session/replay/UI ownership.
* Enabling Standard-Shogi TT or changing TT semantics is deferred to F3.
