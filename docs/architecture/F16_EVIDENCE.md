# F16 Evidence — Native Semantic Position Runtime Stack

Status: `AUDIT_ONLY_PASS`.

F16 followed the Gmail/inbox protocol. The authoritative attachment is preserved in [the F16 inbox record](../../inbox/2026-08-14_GenericChess-F16_Native_Semantic_Position_Runtime_Stack.md), with message/thread provenance and complete-authoritative-attachment state.

## Baseline and boundary

The locked refs matched exactly:

```text
origin/sandbox = 1182d98f3c4efe1de1b4049049f73ba6c47e0199
origin/master  = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat    = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Core remained Native-unaware. No production attack/check, legality, terminal, evaluator, or search path was routed to Native. F4–F15 evidence and ADR-022 through ADR-032 were hash-identical before and after this task; the manifests contain 410 unchanged tracked entries.

## H16A findings

The fresh temporary Native build measured:

```text
sizeof(GCSemanticPosition) = 27296 bytes
sizeof(GCSemanticUndo)     = 27296 bytes
make_trusted copy model    = 81888 bytes
unmake copy model          = 27296 bytes
push+pop estimate          = 109184 bytes
```

Undo storage would therefore consume 436,736 bytes at depth 16, 873,472 bytes at depth 32, 1,746,944 bytes at depth 64, and 13,975,552 bytes at depth 512. This is O(depth), but the full-position copy is the measured cost center.

On the same Standard Shogi environment, using 100 warm-up calls and 5,000 measured repetitions:

```text
F15 immutable child-capsule lifecycle median = 38.61 us
temporary C-owned mutable runtime push+pop    = 23.89 us
```

The mutable trial improved over the immutable lifecycle but failed both G1 authorization alternatives: it was not <= 0.50 × 38.61 us (19.31 us), and it was not <= 20 us. The precomputed exact action pack measured 8.84× faster than F15 rebuild-every-call maps and passed G2. Four frozen Standard Shogi prefixes had zero action-pack or raw make/unmake mismatches.

Because G1 failed, H16B was not authorized. The temporary probe and AI shadow bridge were removed before closure; only diagnostic measurements remain in `artifacts/f16_native_position_runtime/`.

## Closure

H16B-only artifacts explicitly say `NOT_RUN_NOT_AUTHORIZED`; they are not fabricated runtime certification. The selected next boundary is `NATIVE_DELTA_POSITION_RUNTIME`, because full-position undo copying is the measured blocker. F16 does not implement that boundary.

See [ADR-033](ADR-033-native-semantic-position-runtime.md) and the machine-readable evidence under `artifacts/f16_native_position_runtime/`.
