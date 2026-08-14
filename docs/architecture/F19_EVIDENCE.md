# F19 Evidence — Native Position-Key Architecture Reassessment

F19 closed as `ARCHITECTURE_DECISION_PASS` on the locked sandbox baseline. The external canonical identity remains `SHA-256(canonical semantic position JSON)`. The audit used the F17 H17A transactional delta journal only as a temporary H19A probe, then removed all probe entrypoints before E19 closure.

## Decision summary

- `S0_S4_HISTORY_INDEPENDENT = true`.
- State, attack/check, legality, nested-reply, and fail-closed differentials all reported zero mismatches.
- Exact-history delta push/pop median: `36.38 us` in the final recorded run.
- `TRANSIENT_NONE` delta push/pop median: `14.29 us` in the final recorded run.
- Historyless saving: `22.08 us`; exact/transient speedup: `2.55x`.
- G1, G2, G3, and G4: `PASS`.
- Conservative end-to-end Profile A/B routing gain was not evidenced at `>=10%` for both profiles; fine-grained attack/check routing is therefore not selected.
- Selected next boundary: `NATIVE_LEGALITY_KERNEL`.

## Authority split

`semantic_position_key` remains the public/external identity and is unchanged. Exact terminal, repetition, perft, probe search, and fixed-depth search remain full-history authorities. Attack/check and S0–S4 transition semantics do not read repetition history; key/history work is post-transition bookkeeping.

The transient prototype marked the child inexact and exposed only push/pop, attack/check, snapshot, and depth conceptually. Direct use of terminal, history occurrence, perft, probe, and fixed-depth APIs rejected the transient child. The final architecture requires a distinct future capability/capsule type; no such production type was retained in F19.

## Differential and regression evidence

Machine-readable evidence is under `artifacts/f19_position_key_architecture/`:

- `capability_dependency_matrix.json`
- `s3_s4_history_dependency.json`
- `transient_state_differential.json`
- `transient_attack_check_differential.json`
- `transient_legality_differential.json`
- `nested_s3_reply_differential.json`
- `transient_fail_closed_runtime.json`
- `external_key_196_regression.json`
- `performance_gate.json`
- `attack_routing_economic_model.json`
- `probe_cleanup.json`

The frozen 196-row external key corpus remained at zero mismatch. Old evidence manifests contained 525 entries before and after F19 and were byte-identical. The cleaned production semantic sources match the F17-closed baseline commit `4999be31b6fc91655d7d0df9c948ef3bbdb43408`.

## Verification

Focused regressions: 62 passed. Full suite: 917 passed. Final cleaned Native build: `C:\Users\icywo\AppData\Local\Temp\generic_chess_native_f19_final.pyd`, 335360 bytes. No F20 work was started.
