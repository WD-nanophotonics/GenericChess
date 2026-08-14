# ADR-034: Native Delta Semantic Position Runtime

## Status

Rejected for retention in F17; H17A audit-only prototype recorded.

## Context

F16 showed that full-position undo copying was the Native mutable-runtime cost center. F17 evaluated a bounded delta journal over the frozen Semantic IR v2 effect model. The journal used first-write capture for board, hand, and auxiliary cells, restored scalar/history-tail state transactionally, and used a pre-view overlay for parent-dependent auxiliary references, triggers, and invariants.

## Evidence

The H17A probe passed the frozen Standard Shogi prefixes and Generic IR-v2 fixtures with zero raw differential mismatches. Nested push/pop restored exact state; invalid packed actions left depth and position identity unchanged; underflow failed closed. The delta frame was 656 bytes, with bounded capacities of 9 board, 10 hand, and 24 auxiliary entries.

The action-pack speedup was 8.84× against the F15 rebuild reference. However, the measured delta push+pop median was 31.39 µs with p90 32.09 µs. This exceeded both the absolute 18.0 µs gate and the F16-relative 17.92 µs gate.

## Decision

Do not retain the delta runtime or integrate it into production search. Keep Python `SearchPathRuntime` and Python semantic truth authoritative. Preserve the H17A prototype and its evidence only for audit traceability. Select `NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION` as the next authorized boundary; do not implement it in F17.

## Consequences

```text
F17_RESULT = AUDIT_ONLY_PASS
H17B_CREATED = false
H17B_RETAINED = false
G4_DELTA_LIFECYCLE = FAIL
SELECTED_NEXT_BOUNDARY = NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION
```

F4–F16 source, evidence, and ADR history remain unchanged. No F18 work is started.
