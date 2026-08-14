# F20 Evidence — Native Transient Legality Kernel + End-to-End Routing Boundary Audit

Status: `F20_RESULT = LEGALITY_KERNEL_PASS`

## 1. Provenance and baseline

The authoritative Gmail body and complete attachment are preserved in [the F20 inbox record](../../inbox/2026-08-15_GenericChess-F20_Native_Transient_Legality_Kernel_End_to_End_Routing_Boundary_Audit.md). The task was found by fuzzy GenericChess/F20 Gmail matching, read in full, and persisted before code work.

Frozen baseline:

```text
origin/sandbox = f2992ce07272a0b8ccee87ddf7a5595e67e1f8ed
origin/master  = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat    = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
Standard Shogi = 5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

## 2. Authority and boundary

Python `SemanticEngine.iter_legal_action_bindings()` remains the legality/binding authority. Native returns the complete canonical ordered S0–S4 packed action sequence. Python decodes stable pattern/geometry/type IDs, projects public actions, and calls `_make_binding_from_action(...)` before the existing Python transition.

The retained API is a packed-capsule transient boundary: it consumes one state-only packed position, performs all S0–S4 work, returns packed actions, and does not expose a transient child position. It excludes history, repetition, terminal, evaluator, TT, and search authority. Production `SearchPathRuntime` and AlphaBeta routing are unchanged.

## 3. H20A baseline

The existing `guarded_actions` path was instrumented without changing its public semantics. Across 84 Standard Shogi states (four frozen prefixes with deterministic depth-1/depth-2 samples), Python and exact-history Native action count/order mismatches were both zero. The baseline performed 2,354 candidate/S3 trials, 2,354 child canonical-key computations, and 2,354 history appends.

## 4. H20B correctness gates

All H20B authorization gates passed:

- Standard Shogi ordered legality: 84 rows, zero count/order/identity mismatches.
- Generic IR-v2 corpus: 10 rows (`cannon`, `castling`, `en_passant`, `nifu`, `uchifuzume`, `weird_0`–`weird_4`), zero count/order mismatches.
- Packed action decode and stable ID mapping: zero mismatches.
- Exact binding reconstruction: zero mismatches.
- Python child transition using reconstructed bindings: zero mismatches.
- Transient child canonical-key computations: zero.
- Transient history appends: zero.
- Fail-closed wrong-fingerprint, malformed-board, and invalid-side checks: pass.
- F13/F14/F19 and exact-history/public Native focused regressions: pass.

## 5. Performance gates

On the same packed states, transient Native legality had an aggregate speedup above the 1.50x/50-us H20B threshold; the four frozen root rows were 1.24x–3.21x faster, with no stable regression class above the allowed limit.

The realistic one-shot route included state-payload construction, capsule packing, one Native call, direct packed-action decode, public action projection, and exact binding reconstruction. Across 40 Standard Shogi states, median speedup was `4.7933x`, median absolute saving was `4,127.98 us`, and 100% of measured states were faster. The one-shot routing gate passed.

Atomic transient calls had median `466.13 us`, p90/p99/max `584.04 us`, below the 10-ms interruptibility threshold.

The test-only search shadow preserved the chosen action, score, PV, termination reason, node/TT/runtime counters, and legal-action order exactly. End-to-end median gains were:

```text
Profile A: 33.50%
Profile B: 32.31%
```

All four semantic cases gained in both profiles. The shadow did not alter production routing.

## 6. Retention and next boundary

`H20B_RETAINED = true`. The Native transient legality-kernel API is retained as an independently certified Native capability. Since the one-shot and shadow gates passed, the selected future boundary is:

```text
SELECTED_NEXT_BOUNDARY = NATIVE_LEGAL_ACTION_ROUTING_DIRECT
```

That future phase is not started in F20. Production search remains Python-routed.

## 7. Regression and immutability evidence

The full suite passed with the final extension, and the final Zig Native build passed. The canonical normalized-content before/after manifest covers 561 F4–F19 evidence files and is equal. New evidence is confined to `artifacts/f20_native_legality_kernel/`.

See [ADR-037](ADR-037-native-transient-legality-kernel.md) and the machine-readable files in `artifacts/f20_native_legality_kernel/` for row-level, benchmark, gate, manifest, and final-verdict data.

F20 stops here; no F21 work was started.
