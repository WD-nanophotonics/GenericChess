# ADR-019: Canonical State Identity and History Authority Boundary

- Status: Accepted for F1
- Date: 2026-08-12
- Scope: GenericChess Core, Session, UI stale-result checks, Python AI search, diagnostics, and parity adapters

## Decision

F1 owns one internal authority in `generic_chess.core.identity`.  Consumers do
not choose between legacy and semantic key functions locally.

The authority exposes five deliberately separate concepts:

1. **Position identity** (`PositionIdentity`) is the compiled-ruleset-aware
   identity of a position.  It includes the ruleset fingerprint, side to move,
   board, hands, and all canonical rule-relevant auxiliary state.
2. **Repetition identity** (`RepetitionIdentity`) is the key stored in
   `GameState.repetition_counts`.  For the currently certified engine it is
   the same external key as position identity, but it has a separate API so a
   future ruleset-defined equivalence cannot be smuggled in by a caller.
3. **Search-state identity** (`SearchStateIdentity`) contains the position
   identity, the complete current repetition-count tuple, `ply_count`, and the
   existing continuous-check adjudication context.  This makes path
   dependence explicit; it does not make Standard-Shogi TT reuse safe.
4. **External stable key** (`ExternalStableKey`) is the deterministic,
   serialization-safe SHA-256 string used by records and evidence.  The
   existing legacy and semantic encodings remain byte-for-byte unchanged.
5. **Runtime hash** (`RuntimeHash`) is only a named future process-local
   performance boundary.  F1 does not construct or persist one.

Dispatch is based on the compiled ruleset type.  A
`CompiledSemanticRuleset` uses the certified semantic key and its canonical
logical auxiliary slots; all other compiled rulesets use the legacy-compatible
key.  Semantic slot defaults canonicalize to the same identity as an omitted
physical entry, while unknown/foreign physical auxiliary entries remain
identity-relevant.  Ruleset fingerprints always isolate otherwise identical
positions.

## Ownership and compatibility

`core.identity` is the only owned production boundary for position,
repetition, and search-state identity.  Core transition/repetition code,
Session records, UI root validation, AI TT construction, diagnostics, learning
corpora, and Native differential adapters call it directly.

`core.keys.position_key` and `core.keys.semantic_position_key` remain as
documented compatibility primitives for historical fixtures and parity tests.
They are not a dispatch API and migrated production callers must not select
between them.  The Native semantic exact-key function remains the native
parity implementation; F1 does not migrate the production backend to Native.

## History and search boundary

The existing `continuous_check_loss` adjudication and the existing safety
rule that disables Standard-Shogi TT are preserved.  F1 does not compress,
bound, reinterpret, or redesign history; it does not add make/unmake or
incremental/Zobrist hashing.  A lazy child key may be passed back to the
authority only after Core issued it, and the state repetition/path context is
still included in the search identity.

## Explicit non-goals and handoff

- F2 may redesign the History/Repetition Runtime and introduce an optimized
  process-local runtime hash, but must keep the external key contract.
- F3 may define a safe Semantic TT policy after path dependence is addressed;
  F1 does not enable Standard-Shogi TT or change replacement policy.
- Evaluators, search heuristics, UI product behavior, rulesets, AlphaSho, and
  Native production-backend selection are outside F1.
