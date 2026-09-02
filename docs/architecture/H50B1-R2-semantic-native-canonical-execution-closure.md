# H50B1-R2 semantic Native canonical execution closure

- Checkpoint: `H50B1-R2_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION`
- Work order: `GENERICCHESS-F50B1-CORRECTIVE-R2-PAYLOAD-VERSION-AND-CERTIFICATION-EVIDENCE-CLOSURE`
- Parent: `336822394e63667fa1a757c9ad5f46e3c6c71bd6`
- Promotion: HOLD; no master mutation

## Outcome

R2 establishes the explicit payload transition `2 -> 3 -> 4`. H50A v2 and
H50B1 v3 remain historical interpretations. The current declaration,
full automatic-adjudication, and expanded history-event contract is v4.
The Native parser accepts a legacy v3 shape only when v4-only fields are
absent; a v3 payload carrying those fields fails closed.

## Certification evidence

The complete Western 24-cell and Standard Shogi 21-cell matrices, witnesses,
generic compiler witness fingerprint/IR/payload hashes, API inventories,
history contract, automatic-adjudication contract, historical repair ledger,
and exact regression totals are frozen in
`tests/fixtures/h50b1_r2_semantic_native_execution.json`.

The final Native build is 354816 bytes with SHA-256
`43ed107f1a3bcbc2a9aae7277af3cf476c7aa53548d6dffb3a7022c05a1c9dbe` and
reports semantic payload version 4.

Full regression: `1531 passed, 3 skipped, 2 failed`. The only failures are
the established F24F Kiwipete depth-1 mismatch (`45 vs 48`) and the missing
external AlphaSho `evaluation_positions.jsonl`. No F50B2 behavior, search,
TT, budget, cancellation, learner, F49 restart, or production routing was
started.

F50B2 remains `NOT_STARTED`; this checkpoint stops for independent review.
