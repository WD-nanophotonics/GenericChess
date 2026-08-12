# ADR-020: Core-owned search-path history and repetition runtime

Status: ACCEPTED for F2

## Context

The public `GameState` is intentionally immutable and carries complete
history/repetition evidence for Session, replay, UI, and records.  Copying
that tuple at every AlphaBeta child is unnecessary search overhead, but
position identity alone is not a safe key for path-dependent adjudication.

## Decision

AlphaBeta receives a Core-owned `SearchPathRuntime` at the root.  It imports
the immutable state once, validates the ruleset fingerprint and imported
history, and then maintains the current `Position`, ply, occurrence counts,
history evidence, terminal result, and a persistent repetition snapshot.
Every explored action is enclosed by an exception-safe `push`/`pop` boundary;
the runtime is never serialized, shared with Session, or used by
`reference_minimax`.

The runtime hash is a process-local 128-bit XOR-delta hash over the same
ruleset/side/board/hands/semantic-aux identity inputs as F1.  The external
SHA-256 key remains authoritative for records and is retained as the exact
collision guard.  A runtime hash is never used as a Standard-Shogi TT key.
The existing TT policy remains unchanged: continuous-check paths are not TT
compatible, while ordinary draw paths include the exact persistent count
snapshot in the runtime search key.

The runtime owns terminal precedence in Core and preserves checkmate,
stalemate, ordinary repetition, continuous-check loss, max-ply, imported
history, and malformed-history fail-closed behavior.  Lazy/eager tuning,
PVS null/full re-search, aspiration, root tactical scan, both qsearch modes,
and cancellation all use the same push/pop boundary.

## Consequences

Search no longer constructs a public `GameState` for every explored child.
The reference minimax and all public transition APIs remain immutable oracles,
so differential tests can compare the runtime with the existing behavior.
Runtime counters expose balanced pushes/pops, incremental hash updates,
exact-key/collision checks, root import cost, and zero full history/repetition
tuple copies on the hot path.

## Rejected alternatives

* Replacing external SHA keys with a runtime hash would make records and
  cross-process artifacts unstable and would make collisions unsafe.
* Putting mutable history in `GameState` would violate Session/replay/UI
  ownership and the F1 public contract.
* Enabling Standard-Shogi TT was deferred; draw-policy path context remains
  explicit and collision-safe.
