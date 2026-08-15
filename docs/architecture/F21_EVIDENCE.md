# GenericChess F21 Evidence

## Verdict

```text
F21_RESULT = PRODUCTION_ROUTING_PASS
NATIVE_LEGALITY_DEFAULT_ON = true
F22_STARTED = false
```

The complete machine-readable evidence is under
`artifacts/f21_native_legality_routing/`.

## Boundary and routing

- Core Native imports: 0.
- Core stores only a neutral legal-binding callback; no Native capsule/rules object.
- `SearchPathRuntime.legal_actions()` is the single production boundary for
  normal negamax, PVS, aspiration, qsearch, root tactical, and root fallback.
- Python remains authoritative for push/transition, terminal, repetition,
  history, runtime identity, TT, evaluator, and search policy.

## Differential and safety gates

- Standard Shogi: 84/84 rows, zero order/identity mismatch.
- Generic IR-v2: 10/10 rows, zero order/identity mismatch.
- Binding/child-transition parity: PASS.
- Setup fallback, injected operational fallback, cancellation, root fallback,
  repeated-search TT/history behavior: PASS.
- Full pytest: PASS.
- Final Native `-O2` build: PASS, 338,432 bytes.

## Performance

| Profile | Aggregate gain | Retention |
|---|---:|---|
| A | 31.73% | PASS |
| B | 33.25% | PASS |

All four frozen semantic cases passed exact search parity in both profiles;
all cases gained at least 10% and none had a stable regression over 3%.

## Provenance

The authoritative Gmail record is persisted at
`inbox/2026-08-15_GenericChess-F21_Production_Native_Legal-Action_Routing_Fail-Safe_Search_Integration.md`.
The final evidence manifest and before/after old-evidence SHA-256 manifests
are in the F21 artifact directory. No F4–F20 evidence was modified.

