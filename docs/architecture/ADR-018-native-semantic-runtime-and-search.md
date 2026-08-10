# ADR-018: Native Semantic Runtime and Fixed-Depth Search

Status: Accepted successor to the C-1 compile-only boundary

## Context

ADR-017 remains authoritative for the semantic payload ABI: deterministic
type/pattern/geometry identity, C-owned `GCSemanticRules`, the exact 64-bit
semantic action layout, closed enum codes, fail-closed size/domain limits,
legacy-structure non-aliasing, and the prohibition on using high-level
`RuleSet` or game names as Native execution authority.

The C-1 compile-only/public-surface restrictions in ADR-017 are superseded by
this record after the accepted prerequisite chain:

- payload ABI hardening at `38c554a...`;
- standard build closure at `d2faa66...`;
- runtime publication candidate at `9779d5d...`;
- publication authorization in `native-semantic-c1-supersede-audit-001`.

This supersession does not rewrite ADR-017 history. It authorizes the next
runtime contract only after its gates and differential tests are green.

## Decision

Native semantic positions are independently packed, fingerprint-bound, and
validated before every `(rules, position)` operation. Exact four-word
SHA-256 history is authoritative for repetition; two-word history remains a
legacy transport projection and is not terminal-eligible.

This successor runtime publishes Native ABI/runtime version `0.5.0` with
schema `native-0.5.0`. The semantic payload version remains `2` because its
numeric payload layout is unchanged; the public runtime surface and capability
contract are not the frozen C-1 `0.4.0` contract.

The public semantic runtime exposes terminal status and a fixed-depth
AlphaBeta search. Search uses Native S0-S4 action generation, C action
buffers, trusted make/unmake, exact terminal precedence, deterministic
packed-action tie-breaking, and a stable profile keyed by compiled type IDs.
Board material is valued by current type; hand material is valued by base
type.

`semantic_position_state`, `semantic_s0_s4_executor`, and
`CompiledSemanticIR.capabilities.native_executable` are fail-closed gates.
The first two become true only after their focused runtime suites pass. The
last is computed per ruleset from the supported lowered primitives; unsupported
or malformed/future primitives remain false or fail closed.

The semantic-specific capability keys are `semantic_terminal`,
`semantic_fixed_depth_search`, and `semantic_material_evaluator`. Broader
`production_dynamic_evaluator` and `production_search_backend` flags remain
false because this contract does not claim integration with the product-wide
evaluator or SearchBackend.

## Consequences

Legacy Native structures and APIs remain unchanged. The old probe API remains
available as a lower-level compatibility control, while production callers
use the fixed-depth semantic search API and direct terminal API.
