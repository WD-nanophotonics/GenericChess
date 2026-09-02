# H50B1-R6 final certification and provenance closure

R6 is a record-only checkpoint.  Native production is byte-frozen at
`a2ce9048bd336d5dbe3d359e3da93aa0f9e8ab63`; the R5-to-R6 production diff is
zero.  The executable audit is
`scripts/audit_h50b1_r6_final.py`, and its machine-readable result is
`tests/fixtures/h50b1_r6_final_certification.json`.

The audit binds every Western 24-cell and Standard Shogi 21-cell matrix entry
to an executable lockstep witness, including the real history, imported
history, declaration, attack/check, and 500-ply automatic-adjudication paths.
It directly compares declaration boundaries and controls for both owners,
zone membership/aggregation/owner/type filters, and all shared spatial
selectors.  It also records the canonical generic Native v4 payload hash,
actual compiler-measured `sizeof(GCSemanticPosition)` values, an isolated
H50A regression, the historical repair ledger, and the cumulative production
diff inventory.

The isolated H50A run is exactly 1506 passed, 2 skipped, and 13 failed: 11
historical candidate-only provenance failures plus the established F24F
Kiwipete 45-vs-48 residual and unavailable external AlphaSho input.  The
inherited post-H50B1 description of 15 historical drifts/17 failures is
retained as historical context, not substituted for the isolated result.

F50B2 remains `NOT_STARTED`; promotion remains `HOLD` pending independent
review.
