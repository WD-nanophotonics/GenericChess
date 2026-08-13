# ADR-028 — Post-F10 runtime re-baseline and Python-local boundary

## Decision

Close F11 as `AUDIT_ONLY_PASS`. F10 materially changed the semantic source-dispatch
cost structure, so earlier F4/F6 hotspot rankings are not selection authority. A fresh
whole-search audit was required and was performed on the current production tree.

## New ranking

The post-F10 ranking is led by exact semantic attack/check work, followed by checkpoint
dispatch and runtime push/terminal/hash work. Geometry enumeration, source-index residual
work, and evaluator work are smaller or necessary. Source-index construction is already
covered by F10 within legality operations; cross-query reuse would be F7-style architecture.

## Single-winner result

No allowed Python-local family was both clearly dominant and supported by a safe material
end-to-end probe. Attack memoization, target-directed geometry, general caches, identity
redesign, native migration, and search/evaluator policy changes are explicitly outside F11.
No H11B production change was created.

## Python-local headroom

`PYTHON_LOCAL_RUNTIME_HEADROOM = LIMITED`. The remaining dominant work is exact semantic
attack/check and runtime safety work. The next boundary is exactly
`NATIVE_SEMANTIC_EXECUTION_AUDIT`; F11 does not start it.

## Consequences

F4–F10 accepted optimizations remain intact. The F11 corpus, cProfile reports, structural
counts, hotspot ranking, candidate matrix, and explicit no-candidate records are preserved
under the F11 evidence directory. Full pytest and fresh supported Zig build pass.
