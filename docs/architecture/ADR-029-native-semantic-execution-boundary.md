# ADR-029: Native Semantic Execution Boundary

Status: Accepted for F12 audit conclusion; implementation deferred.

## Decision

Select `NATIVE_CAPABILITY_GAP_CLOSURE` as the single next boundary. Do not migrate SemanticEngine attack/check, Position ownership, or production search in F12.

## Context

The native semantic runtime can execute a certified toy corpus through position packing, exact identity/history, candidate and guarded actions, checked make, terminal detection, and bounded fixed-depth search. The production search contract is broader: Standard Shogi semantics, interruptibility, complete history authority, evaluator integration, and differential evidence must all be preserved.

The certified Standard Shogi IR has 155 patterns and includes an S3 `action_delivers_check` postcondition. Native schema `native-0.5.0` does not lower that postcondition and rejects the ruleset fail-closed. The native module also has no public semantic `is_square_attacked`/`in_check` entry point; its legacy `native_attack_map` consumes a different movement-atom contract.

## Consequences

- Python semantic execution remains authoritative.
- The next implementation task is a semantics-preserving native lowering/capability closure for `action_delivers_check`.
- A future attack/check slice is conditional on Standard Shogi native compilation and a targeted differential corpus.
- Native search ownership is not ready: the semantic fixed-depth probe has no production node/time budget, cancellation/checkpoint contract, TT, qsearch, or dynamic evaluator.
- Unsupported rules and incomplete history continue to fail closed to Python.

## Rejected boundaries for now

Option A (per-call packing) has low correctness risk but low speedup ceiling. Option B (mirrored native frame) introduces ownership and exact-history lifecycle risk before the target ruleset is executable. Option C (native search path with Python shadow) and Option D (full native semantic backend) exceed the current certified capability and interruptibility surface.

## Exit criteria for reconsideration

1. Standard Shogi lowers and executes without unsupported semantic postconditions.
2. Native/Python differential coverage includes attack/check, S3/S4 behavior, history/repetition, terminal, and checked make.
3. A public semantic attack/check API has an explicit owner, geometry, guard, checkpoint, and fail-closed contract.
4. Production search budgets, cancellation, evaluator, and history ownership are proven at the selected boundary.
