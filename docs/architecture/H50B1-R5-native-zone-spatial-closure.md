# H50B1-R5 Native zone-spatial selector closure

Status: PASS pending Courier closeout

Work order: `GENERICCHESS-F50B1-CORRECTIVE-R5-ZONE-SPATIAL-SELECTOR-NATIVE-PARITY-CLOSURE`

Parent checkpoint: `8a1306645b43e642da732272c866f6654cea018c`

R4 exposed a Native/Python declaration mismatch at weighted score 23. The
cause was the shared Native `spatial_holds()` helper reading `refs[0]` before
handling a zone selector. A zone selector has no square references, so valid
board pieces were excluded and only the hand witness remained. R5 handles the
zone primitive before the reference-based selectors and preserves the generic
owner/type filtering contract.

The R5 differential harness is executable and compares exact public action
identity, packed actions, state/key/aux/ply parity, checked make/unmake,
attack/check queries, ordinary and continuous-check history, imported exact
history, declarations at scores 23/24/31 for both owners, zone inside/outside
guards, and a compiler-produced generic witness. It passes the exact 24-row
Western and 21-row Standard Shogi matrices. A real 500-ply legal Standard
Shogi history reaches `no_contest` at ply 500 with Native/Python exact history
and event metadata parity.

Durable evidence is frozen in
`tests/fixtures/h50b1_r5_semantic_native_execution.json`; the executable
coverage is guarded by `tests/test_h50b1_r5_native_differential.py` and
`tests/test_h50b1_r5_zone_spatial_differential.py`. R5 changes production only
in `generic_chess/_native/native_semantic_runtime.c`; payload version remains
4 and F50B2 remains `NOT_STARTED`.
