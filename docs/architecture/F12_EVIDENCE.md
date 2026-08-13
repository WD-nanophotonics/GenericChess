# F12 — Native Semantic Execution Capability Audit

Status: `AUDIT_PASS` / H12A audit-only. No production native migration was performed.

## Scope and authority

The certified Standard Shogi semantic ruleset is fingerprint `5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345`. Python `SemanticEngine.is_square_attacked` and `in_check` remain the semantic authority. The native legacy attack map is not treated as an equivalent implementation.

## Build and capability result

The fresh Zig native build passed on Python 3.13.2 and produced `native_f12_core.pyd`. The existing native semantic corpus (10 frozen fixtures) compiled and passed position, guarded-action, terminal, and fixed-depth smoke/differential coverage. Native semantic execution currently exposes position/key/action, candidate/guarded traversal, checked make, terminal, perft, and a bounded fixed-depth probe.

Standard Shogi does not compile to an executable native semantic capsule. Lowering fails closed on the `action_delivers_check` S3 postcondition in `sem_00_standard_drop_contract`; this is a capability gap, not an evidence failure.

## Attack/check boundary

The Python contract requires owner/current-type dispatch, target-enemy filtering, type/geometry compatibility, owner-relative geometry, path predicates, state guards, slot guards, and S4-to-S0/S1 projection without S3/S4 recursion. Native C contains internal `semantic_attacked_by` and `gc_semantic_runtime_in_check`, but no public semantic attack/check entry point. Legacy native attack maps matched the initial positions of the toy corpus; Standard Shogi comparison was correctly not run because its legacy native compiler rejects the history policy before a common executable surface exists.

## Boundary decision

The only selected future boundary is `NATIVE_CAPABILITY_GAP_CLOSURE`: first add a semantics-preserving lowering for `action_delivers_check`, recompile Standard Shogi, and complete differential coverage. Attack/check slice, mirrored native position ownership, native search-path ownership, and full native production search remain deferred.

## Evidence index

All new evidence is under `artifacts/f12_native_semantic_audit/`. Important files are `standard_shogi_compile.json`, `native_capability_matrix.json`, `semantic_gap_matrix.json`, `legacy_vs_semantic_attack.json`, `boundary_microbench.json`, `position_ownership_matrix.json`, `search_readiness_matrix.json`, `selected_future_boundary.json`, and `failure_model.json`.

Focused native tests passed: 100 tests across the Phase 19C contracts, semantic position/runtime/differential suites, probe/fixed search, history/TT, kernel, and readiness suites. Full-suite and final-build results are recorded by the closing audit evidence.
