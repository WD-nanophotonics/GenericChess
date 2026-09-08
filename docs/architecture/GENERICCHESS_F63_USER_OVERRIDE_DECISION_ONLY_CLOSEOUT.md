# GenericChess F63 user-override decision-only closeout

Status: user-stopped at a safe external process boundary; decision-only evidence
retained. This report records the superseding user instruction and does not
claim a complete teacher-8 result.

## Immutable authority and run identity

- Work order: `GENERICCHESS-F63-CHAMPION-LOOP-CAUSAL-TRIAGE`.
- Implementation checkpoint: `66fcaf55b793c461511322a2a90691b2c70873ea`.
- `origin/sandbox`: `66fcaf55b793c461511322a2a90691b2c70873ea`.
- `master`: `44fce4f9dfeee0ef9480597c7ab34195db984100` (unchanged).
- Durable Heavy run: `f63-champion-loop-causal-triage-5c67cf3cd996`.
- Durable state SHA-256: `C12F1665C928755612A3AD2CEF9C87EB07773A735E289D2BDD8D2C615171F3CC`.
- The user superseded the earlier Chat Decision A because the final teacher pair had run for pathological cost without game-level checkpoint visibility. The unique Heavy process tree was terminated only after exact PID/parent verification; its durable state is `failed` with termination exit code `4294967295`.
- No second F63 Heavy, replacement Courier request, seed change, budget change, or master write occurred.

## Preserved teacher evidence

The teacher-4 stage remains complete at 4/4. The teacher-8 stage is explicitly
decision-only at 7/8: pair files `pair-000001.json` through
`pair-000007.json` are present, and `pair-000000.json` plus the eighth pair are
absent. Each preserved pair contains both swapped child-owner games with
`child_owner=0` and `child_owner=1`; the files were atomically written by the
existing pair-level runner.

Teacher-8 preserved evidence summary (7 complete pairs, 14 games):

| Evidence | Value |
|---|---:|
| Child W/D/L | 9/1/4 |
| Child game score rate | 0.678571428571429 |
| Pair-score mean | 0.678571428571429 |
| Better / tied / worse pairs | 4/2/1 |
| Pair files | 7/8 |

This is sufficient for the user-requested decision-only teacher-gate direction,
but it is not an 8-pair estimate and must not be reported as one. The missing
pair's two in-memory games were not represented as evidence when the process
was stopped.

Evidence hashes:

- Teacher-8 manifest: `42DAA12BB32329B209E9313E480DCDAF33A8D81092295F95B1F440F006C89CA8`.
- `pair-000001.json`: `39D13FF7DF8E16183A32F06BF9CF629BFF108DFDFDD733B650BC68620AA292D9`.
- `pair-000002.json`: `24CAD60B256D347DDE98488113084BFB5E1CDA4EC7148379F1C58ABC49C69535`.
- `pair-000003.json`: `52E7705D8D7945ECED74E9D01433669AF4A42B32039F1AAB90F6840FB5B32DB2`.
- `pair-000004.json`: `DBE80953D3DFA6251DFC78D24D7452C1B06A282DC45DA615A9FACFD6D6B25334`.
- `pair-000005.json`: `53FC06A813F2C1C200E0A36D18817DEBB8BEA426206EF23FC6AFE1B09695C28D`.
- `pair-000006.json`: `895CDEE39CF23BC6DAC0CE1293D5D4730A10DEA27730B019342FC4971A35A5C0`.
- `pair-000007.json`: `364FE6DD1E81595736CF87A6E32211B35ED1D751075034445594002FA2862D01`.

`candidates.json` and `f63_results.json` are absent. Therefore the three
candidate 4-pair stages, selected 8-pair stage, and selected 32-pair stage did
not start and have no evidence.

## Courier decision lineage

The same-work-order decision request was submitted once:

- Request: `GENERICCHESS-20260908-110229-730c204b`.
- Submission count: `1`.
- Request fingerprint: `7092d068459f486e81619c984d56ae660bd8a4d10befed3aa623b2d0d5188c64`.
- Captured Chat response SHA-256: `fd16b97312ef3817bf492f3746004287ad09410db18d2515943741e95c78f551`.
- The initial Chat Decision A was later superseded by the explicit user override recorded above. No Courier retry or replacement request was sent.

## Required next work order

The next explicitly approved work order must first implement and test the small
Arena execution controls that F63 exposed, without changing the scientific
mechanism: per-game atomic checkpoints; deterministic exact-once pair
aggregation; game-level scheduling capped by available CPU (no more than 8 or 16
lanes for 4- or 8-pair stages, respectively, and never above the declared
logical-CPU cap); strict identity/replay/role validation; crash/resume,
out-of-order completion, partial-pair, color-swap, exact-once, and result-
equivalence tests; explicit wall-time, node, and game caps; stage pause; and a
predeclared decision-aware early-stop rule that distinguishes “enough to stop or
continue” from “enough to estimate strength.”

Every future Heavy must have an upfront CPU-time/wall-time estimate and a hard
ceiling for wall time, nodes, games, and concurrency before launch. No Heavy is
authorized when those bounds are absent. The infrastructure work itself should
be validated with bounded focused tests before any new expensive arena run.

