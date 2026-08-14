# F14 Evidence — Public Native Semantic Attack/Check API

F14 certifies two public Python functions over an already-packed Native semantic position capsule:

```python
generic_chess.native.semantic.is_square_attacked(native_rules, position, square, by_owner)
generic_chess.native.semantic.in_check(native_rules, position, side)
```

Both wrappers require an executable Native semantic rules capsule, validate bounds/owner/side, enforce the rules/position fingerprint match, and reuse the single C semantic attack authority. The Native implementation does not use legacy movement-atom attack, caches, bitboards, or production search integration.

The first differential run exposed and fixed two authority mismatches: Native now filters `target_enemy` patterns exactly like Python, and pseudo-attack does not require the queried square to be occupied. After correction, all 648 Standard Shogi attack queries (81 squares × 2 owners × 4 prefixes) and all eight `in_check` queries match Python with zero mismatches. The curated generic semantic corpus also has zero attack/check mismatches.

Packed-capsule calls measured approximately 9.19× faster for attack and 8.47× faster for check than Python on the measured Standard Shogi query set. The separate exact-history per-query pack benchmark makes `PER_QUERY_PACK=REJECT`; therefore the single selected next boundary is `NATIVE_MIRRORED_POSITION_FRAME`. That boundary is not implemented in F14. `FULL_NATIVE_SEARCH_READY` remains `false`.

H14A: `163284a`. H14B: `37b49db`. E14 is the final evidence commit.
