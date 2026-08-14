# ADR-036: Native Position Identity Capability Split

## Status

Accepted as an F19 architecture decision; implementation deferred to a separately authorized phase.

## Context

F18 showed that another implementation-level SHA-256 optimization was insufficient: the candidate reached only 1.19x against a 1.67x gate. F19 therefore reassessed whether every transient Native child needs externally canonical SHA/history identity.

## Decision

Keep the external canonical SHA-256 position key frozen. Keep exact full-history authority mandatory for repetition, terminal, perft terminal cutoffs, probe search, and fixed-depth semantic search. Treat S0–S4 legality, attack, check, action witness, promotion, effects, triggers, and auxiliary lifetimes as history-independent transition semantics.

A future transient runtime may maintain exact current board/hands/side/ply/aux state without child SHA/history append, but it must be a distinct capability/capsule type. It may expose push, pop, attack/check, snapshot, and depth only. It must be rejected by exact-history authority APIs. A stale exact-history flag is not an acceptable design.

F19 used a test-only F17 delta journal plus `TRANSIENT_NONE` policy to validate this boundary. The probe was removed at E19 closure. The public `make_checked`, external key, history semantics, search APIs, and production runtime were not changed.

## Evidence

The transient state differential, attack/check differential, legality differential, nested S3-reply differential, and fail-closed misuse tests all passed with zero mismatches. Nested S3 reply probes performed zero canonical child-key computations in the transient path. The final recorded historyless delta lifecycle measured 14.29 us median versus 36.38 us exact-history delta, a 2.55x separation and 22.08 us absolute saving.

## Economics and next boundary

F14 packed attack/check speedups remain 9.19x/8.47x. F15 shadow overhead references remain 9.28% Profile A and 6.25% Profile B. F19 did not claim unavailable end-to-end precision; both profiles were not conservatively proven to clear the required 10% net gain. The selected next boundary is therefore `NATIVE_LEGALITY_KERNEL`, which can amortize a broader S0–S4 call boundary before any fine-grained attack/check routing decision.

## Consequences

The canonical external identity and Python repetition authority remain stable. Any future transient implementation must be separately reviewed, must use a distinct capability type, and must not be accepted by terminal or search authority APIs. F20 is not started or authorized by this ADR.
