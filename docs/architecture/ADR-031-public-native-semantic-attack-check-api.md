# ADR-031 — Public Native Semantic Attack/Check API

## Decision

Expose `is_square_attacked` and `in_check` in `generic_chess.native.semantic` for already-packed, fingerprint-matched, `native_executable` semantic rules capsules. Add corresponding extension entrypoints `semantic_is_square_attacked` and `semantic_in_check`.

## Authority and fail-closed behavior

Python `SemanticEngine.is_square_attacked` remains the semantic authority. Native delegates to the existing `semantic_attacked_by` implementation. Only `target_enemy` patterns contribute; paths, target geometry, state guards, slot guards, owner-relative semantics, S4 projection, and no-recursion behavior remain unchanged. `in_check` resolves the requested side's anchor and queries the opposing pseudo-attack. Invalid capsules, mismatched fingerprints, invalid squares, and invalid owners/sides raise errors rather than silently returning false.

## Certification

The certified Standard Shogi fingerprint `5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345` passed 648 row-level attack comparisons and eight `in_check` comparisons across the four frozen prefixes. Curated generic semantic fixtures and the F13 witness/S4 regression also pass. Versions, fingerprints, action layout, position keys, history format, and game serialization are unchanged.

## Integration boundary

Packed-capsule Native attack/check is materially faster, but exact-history Python→Native repacking per query is uneconomic. The selected next boundary is `NATIVE_MIRRORED_POSITION_FRAME`: Python runtime authority with a synchronized Native capsule per frame. F14 does not implement that boundary, modify `SemanticEngine`, alter `SearchPathRuntime`, or route AlphaBeta/production search through Native.
