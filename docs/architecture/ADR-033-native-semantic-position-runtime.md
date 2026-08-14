# ADR-033: Native Semantic Position Runtime Foundation

## Status

Rejected for retention in F16; audit-only foundation recorded.

## Context

F15 proved semantic correctness for an immutable Native child-capsule mirror, but its lifecycle overhead failed the F15 retention gate. F16 therefore measured the existing exact C `gc_semantic_runtime_make_trusted` / `gc_semantic_runtime_unmake` primitive and trialed a C-owned mutable stack with one current position and O(depth) full-position undo frames.

## Evidence

`GCSemanticPosition` and `GCSemanticUndo` are each 27,296 bytes. The existing trusted primitive computes a checked local child, copies the parent into the undo frame, and assigns the child; unmake copies the saved parent back. The estimated push/pop copy traffic is 109,184 bytes before Python/C boundary costs.

Precomputed exact semantic action maps passed the lossless packing differential and measured 8.84× faster than the F15 rebuild-every-call helper. The temporary mutable runtime push/pop measured 23.89 µs median against 38.61 µs for the F15 immutable lifecycle. This was an improvement, but failed G1 because it exceeded the 20 µs absolute ceiling and was above half the F15 median (19.31 µs).

## Decision

Do not retain the mutable runtime or opt-in AlphaBeta shadow integration in F16. Do not implement delta undo, copy-on-write state, or a history redesign as an emergency fallback. Keep Python `SearchPathRuntime` and Python semantic truth authoritative. Preserve the H16A size, copy-cost, action-pack, and differential evidence for a separately authorized phase.

## Consequences

F16 closes as:

```text
F16_RESULT = AUDIT_ONLY_PASS
H16B_RETAINED = false
FULL_POSITION_UNDO_NOT_ECONOMIC
SELECTED_NEXT_BOUNDARY = NATIVE_DELTA_POSITION_RUNTIME
```

The selected boundary is not started by F16. Existing F13/F14 semantic attack/check APIs and F15 audit-only mirror history remain unchanged.
