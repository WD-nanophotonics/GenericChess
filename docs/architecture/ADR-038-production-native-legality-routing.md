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

