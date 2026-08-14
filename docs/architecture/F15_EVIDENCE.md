# F15 Evidence — Native Mirrored Semantic Position Frame

## Status

`F15_RESULT = AUDIT_ONLY_PASS`.

The Native mirror is correct as an opt-in audit frame, but its immutable
child-capsule/action-pack lifecycle fails the retention economics gate. Python
remains the only production authority and the H15B AlphaBeta shadow plumbing
was removed before E15 closure.

## Baseline and provenance

- Gmail authority: `inbox/2026-08-14_GenericChess-F15_Native_Mirrored_Position_Frame.md`
- `origin/sandbox = 4e6bff47c4d30d926d5d8aa3e810afa968849bff`
- `origin/master  = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d`
- `origin/chat    = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4`
- Standard Shogi fingerprint: `5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345`

## Architecture boundary

`Core Native imports = 0` and `Core Native-specific state = 0`. The mirror is
implemented in `generic_chess/native/mirror.py`; it is not imported by Core,
`SearchPathRuntime`, `semantic_executor`, or `terminal`. The temporary H15B
AI-layer shadow hook was exercised for certification, then removed because G5
and G6 failed.

## Root/history/action contracts

The root pack carries fingerprint, side, ply, board base/current/owner/promoted
state, hands, auxiliary state, and full four-word SHA-256 history. Certified
history is accepted; opaque/imported history fails closed to Python-only.

Public semantic board/drop actions are packed directly from pattern, geometry,
type, source, target, and promotion identity. No guarded-action enumeration or
coordinate-only fallback enters the push path. Four frozen Standard Shogi
prefixes reported zero missing actions, duplicates, or field mismatches.

## Lifecycle and correctness

Root, depth-1 DFS, bounded generic semantic sync, exception rollback, Python
push failure, mirror push failure, sibling isolation, and O(depth) capsule
lifetime all passed. Native snapshot parity covers board, hands, side, ply,
auxiliary state, and exact history transport. F13/F14 regression remains pass:
648 attack queries, 8 in-check queries, action-delivers-check witnesses,
checking/non-checking drops, and uchifuzume.

## Shadow parity and performance

The temporary opt-in AlphaBeta shadow mode matched action, score, PV, node/qnode
counts, termination, TT/runtime counters, and legal ordering for Profiles A/B
across all four prefixes. Timing-only fields were excluded from logical parity.

Measured aggregate mirror-only overhead:

- Profile A: `9.28%` (gate `<= 7%`: FAIL)
- Profile B: `6.25%` (gate `<= 7%`: FAIL; single-case maximum `12.07%`)

Projected net attack/check routing headroom:

- Profile A: `6.85%` (gate `>= 8%`: FAIL)
- Profile B: `14.13%` (gate `>= 8%`: PASS)

Because both profiles are required, `H15B_RETAINED = false`. No F15 speedup
claim is made.

## Final report

1. Status: `AUDIT_ONLY_PASS`.
2. Baseline: frozen and unchanged.
3. Gmail/inbox provenance: complete authoritative attachment persisted.
4. Environment/initial build: temporary Zig build pass; evidence records SHA.
5. Architecture boundary audit: PASS.
6. Root semantic pack contract: PASS.
7. History transport/fallback: PASS.
8. Lossless semantic action packing: PASS.
9. H15A provenance: commit `bc4042b`.
10. H15B implementation: commit `4dba42f`, exercised then not retained.
11. Standard Shogi DFS mirror sync: PASS.
12. Generic semantic mirror sync: PASS.
13. Push/pop/exception/sibling isolation: PASS.
14. Capsule lifetime: PASS, O(depth).
15. F13/F14 regression: PASS.
16. AlphaBeta shadow search parity: PASS.
17. Interruptibility: PASS; no stable Native make over 10 ms.
18. Mirror cost microbenchmark: recorded; lifecycle cost is the failed gate.
19. Shadow-mode overhead: G5 FAIL.
20. Projected Native routing headroom: G6 FAIL for Profile A.
21. Retention gate: FAIL for retained foundation; audit-only closure.
22. Selected next boundary: `NATIVE_POSITION_RUNTIME`.
23. Tests: focused 32 passed; full 917 passed.
24. Evidence/manifest: `artifacts/f15_native_mirrored_position/`.
25. Git: H15A/H15B pushed; E15 cleanup follows on sandbox.
26. Deferred: Native attack/check routing, legality, terminal, evaluator, and F16.
27. Final verdict: `F15_RESULT = AUDIT_ONLY_PASS`.

## Required verdict fields

```text
F15_RESULT = AUDIT_ONLY_PASS
H15B_RETAINED = false
CORE_NATIVE_UNAWARE = PASS
ROOT_NATIVE_MIRROR = PASS
LOSSLESS_SEMANTIC_ACTION_PACK = PASS
MIRROR_PUSH_POP_SYNC = PASS
MIRROR_EXCEPTION_SAFETY = PASS
MIRROR_SIBLING_ISOLATION = PASS
CAPSULE_LIFETIME = PASS
SEARCH_SHADOW_PARITY = PASS
INTERRUPTIBILITY = PASS
MIRROR_OVERHEAD_GATE = FAIL
PROJECTED_NET_HEADROOM = FAIL
SELECTED_NEXT_BOUNDARY = NATIVE_POSITION_RUNTIME
FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```
