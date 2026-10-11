# ADR-038: Production Native Legal-Action Routing

Status: Accepted for F21

## Decision

`AlphaBetaPlayer` creates one `NativeSemanticLegalityProvider` per player when
the compiled semantic ruleset is executable. `SearchPathRuntime` receives only
the Core-neutral callback:

```text
provider(position, ply_count, checkpoint)
    -> tuple[(public_action, opaque_binding_payload), ...]
```

Core remains Native-unaware. It atomically validates provider output, fills its
existing `_legal_cache` and `_bindings`, and preserves the existing Python
transition, terminal, history, repetition, runtime hash, TT, evaluator, and
search-policy authorities.

## Provider lifecycle

Native semantic rules are compiled once at player construction. Type, pattern,
and geometry maps are precomputed. Each uncached position performs one
state-only payload pack, one `transient_legal_actions` call, direct decoding of
the frozen 64-bit action layout, and exact
`SemanticEngine._make_binding_from_action` reconstruction. No per-action FFI
unpack, child SHA, history append, or Native child transition is used.

## Failure and cancellation

Setup unavailability (missing extension, non-semantic rules, or unsupported
compile) selects the normal Python path. An operational provider failure
discards the complete partial result, disables the provider for the current
root search, and recomputes the node through Python. Strict provider mode may
raise for diagnostics. Checkpoints run before packing, after the Native call,
through bounded decode chunks, and before return; cancellation exceptions are
never converted into provider failures.

## Policy and evidence

F21 H21B makes the route default-on for eligible semantic rulesets while
`use_native_semantic_legality=False` remains the exact Python parity control.
84/84 Standard Shogi provider rows and 10/10 generic IR-v2 rows match ordered
public actions, semantic identity, bindings, and sampled child transitions.
Production search parity is exact. Profile A gain is 31.73% and Profile B gain
is 33.25%; both exceed the 20% retention threshold.

The reproducible F21 `-O2` extension is 338,432 bytes. F20 recorded 3,384,432
bytes for its final build without an optimization/section manifest; F21 records
this as a historical provenance discrepancy, not a correctness blocker.

## Per-state capability and terminal stage — 2026-10-11

The callback supplies complete frontiers after Core adjudicates the state as
ongoing. Empty Native frontiers are not pre-adjudication availability proofs:
Native checked transitions enforce max_ply before Core history/terminal rules.
An ongoing automatic checking continuation can exceed that cutoff, and S4
no_legal_reply probes can encounter it one ply earlier.

A provider may optionally expose supports_position(position, ply_count).
False selects normal Core generation for that state, increments fallback count,
does not increment operational failures, and does not disable the provider.
Strict mode also honors this capability miss. Callables without the optional
method retain their contract; callable objects and bound methods use the same
owner metadata. Native support excludes ply>=max_ply and also the preceding
ply when compiled patterns require no_legal_reply. This is conservative semantic
scope detection; no game name, native ply rewriting or new DLL is involved.

Evidence: RUNTIME_AUX_IDENTITY.md and the current boundary regression tests.
The earlier profile thresholds/build figures above remain historical results,
not current admission gates or new gains attributed to this repair.
