# ADR-021: Safe history-aware transposition reuse

Status: ACCEPTED for F3

## Context

F2 made `RuntimeSearchKey` collision-safe for position, runtime repetition
counts, and ply.  That key was still insufficient for
`continuous_check_loss`: perpetual-check adjudication also depends on the
ordered actor/check evidence in the relevant occurrence cycle.  Two legal
histories can therefore have the same exact position, ply, and repetition
counts while differing in `gave_check` evidence.

The pre-F3 regression in `tests/test_search_path_runtime.py` demonstrates this
with two legal routes through the generic 4x4 rook fixture.  Their accepted
F2 key projection is equal, while their history adjudication contexts differ.

## Decision

Add a private `RuntimeHistoryContext` to the Core runtime.  It is a persistent
parent-pointer chain containing, for every imported or pushed history record:

* exact runtime identity;
* runtime hash discriminator;
* actor;
* `gave_check`;
* chain length and a compact digest.

The digest is never authoritative.  Context equality first compares length
and digest, then walks both parent chains and compares exact identities and
actor/check evidence.  Forced digest collisions therefore cannot conflate
history contexts.

Every push appends one context node and every pop/exception restores the
parent pointer.  No public history tuple or full context is copied per child.

## TT eligibility

Ordinary `draw` rules retain their existing TT behavior.  For
`continuous_check_loss`, TT probe/store is enabled only when the runtime has
complete exact history evidence: complete history, zero witness misses, no
unresolved opaque imported keys, and a non-null exact context.  Opaque or
incomplete roots skip TT conservatively; they are never enabled merely because
their current position matches.

The effective runtime key is therefore the existing ruleset/position/hash/
repetition/ply key plus the exact history context for eligible continuous
check nodes.  Qsearch remains outside this new TT enablement.

## Safety property

Equal eligible keys imply equal evaluator-visible position, legal moves,
absolute ply/max-ply state, repetition multiplicities, terminal precedence,
and ordered actor/check evidence for all future continuations.  Existing TT
bound semantics and mate-score normalization are unchanged.

## Evidence and limitations

Focused tests cover the legal F2 insufficiency witness, exact context equality,
forced context digest collision, opaque-history skip, session-witness reuse,
TT-on/off parity, and continuous-check parity.  The certified semantic Shogi
initial Session path produces nonzero safe TT hits at fixed depth.  Opaque
custom-root paths remain intentionally non-TT-eligible until exact evidence is
available.

## Corrective R1 Closure

The closure corpus exercises the actual persistent `AlphaBetaPlayer` /
`GameSession` path across two successive moves, bounded generic draw and
`continuous_check_loss` prefixes, reachable nonempty Semantic Standard Shogi
prefixes, ordinary repetition, and an opaque custom root. TT-on/off results
are compared at fixed depths with legal PV and runtime-balance checks.

The runtime-cost audit distinguishes four layers: history-context append is
one parent-pointer/digest update per child; snapshot fast-discriminator update
uses the existing `RuntimeHash` plus count; effective `RuntimeSearchKey`
construction is measured separately; TT probe/store timing remains a search
table concern. The snapshot keeps exact identity/count entries for equality,
so the RuntimeHash discriminator is not authoritative and forced collisions
remain safe. The public SHA/fingerprint boundary is unchanged.
