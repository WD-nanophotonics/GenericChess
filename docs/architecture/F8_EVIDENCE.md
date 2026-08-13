# GenericChess F8 evidence

## 1. Status

`F8_RESULT = AUDIT_ONLY_PASS`  
`H8B_CREATED = true`  
`H8B_RETAINED = false`  
`reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED`

## 2. Gmail / inbox provenance

The authoritative Gmail task was captured in
`inbox/2026-08-14_GenericChess-F8_Runtime_Push_Terminal_Check_Deduplication.md`.
Message ref: `19ffbc34992f0fe4`. The complete body was persisted before work.

## 3. Diagnosis

The audit proved that semantic `_gave_check(child)` and the terminal-path check
are the same query for the same exact child Position, side, ruleset, board,
hands, and auxiliary state. Across the certified semantic corpus the exact
duplicate rate was 100% and boolean mismatches were 0.

## 4. Candidate and gate

H8A was committed first (`be7eb75`, with transport correction `0be57ea` and
trace corrections `9a9a5a0`, `eba10ea`). H8B temporarily forwarded the exact
boolean through an explicit `known_checked: bool | None` API (`6a3b852`).
Terminal, history, continuous-check, search, interruptibility, and rollback
parity passed. The authorization probe passed, but the final frozen gate did
not: Profile A was approximately `+1.81%`, Profile B `+8.76%`. H8B was
reverted by `990fd4f`; the production tree retains no optimization.

## 5. Validation and evidence

Full pytest passed 100% under the required elevated execution context, and the
fresh supported Zig build passed. Detailed evidence, traces, timings, parity
records, SHA manifests, and the final verdict are in
`artifacts/f8_push_terminal_check_dedup/manifest.json`.

The F4–F7 evidence directories, F4–F7 evidence documents, and ADR-022 through
ADR-024 were verified byte-identical before and after F8. No F9 work was begun.
