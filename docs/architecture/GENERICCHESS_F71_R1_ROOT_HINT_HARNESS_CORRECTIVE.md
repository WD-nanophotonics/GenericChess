# F71-R1 Root-Hint Harness Corrective Closeout

Date: 2026-09-11  
Work order: `GENERICCHESS-F71-R1-ROOT-HINT-HARNESS-CORRECTIVE`  
Baseline: `1f378782db9c1b1c314abdf863d4a94d37294cd4`

## Correction

The original F71 result is revoked as a causal classification. Native
iterative search enters the root as a PV node, while the existing TT-action
ordering branch is guarded by `!pv_node`. The original F71 TT capsule entry
therefore produced TT hits but did not execute the requested root move-ordering
hint; its `ROOT_HINT_CAUSAL_NEUTRAL` result was a harness mismatch.

R1 adds a narrow optional `root_order_hint` channel. After root candidate
generation, and only when `ply == 0`, a legal matching action is moved to the
front of the root list. The channel does not alter score, bounds, evaluation,
node accounting, child ordering, or TT writes. An absent hint preserves the
existing call path and behavior. The experiment harness no longer accesses
native TT memory.

## Regression coverage

`tests/test_f71_r1_root_hint_harness.py` verifies that a deterministic legal
hint different from the default is searched first at each attempted iteration,
that an illegal packable hint fails closed, that the hint channel is root-only,
and that no-hint repeatability preserves score, action, nodes, qnodes,
completed depth, and root-first telemetry.

Targeted result: 7 tests passed, including the existing F62 repeatability
checks.

## Bounded rerun

The exact twenty stable F62 development roots were rerun with the frozen Gen1
D0 evaluator, a fresh runtime and fresh 8 MiB TT per arm, `max_nodes=2000`,
`max_depth=12`, and `qsearch=0`. No fit, final holdout, Arena, self-play, seed
sweep, Heavy job, or promotion was started.

| Measure | Result |
| --- | ---: |
| stable development roots | 20 |
| baseline cached F62 root_2k reproduction | 20/20 |
| baseline/deep agreement | 1/20 |
| hinted/deep agreement | 1/20 |
| decision changes | 0 |
| toward deep | 0 |
| away from deep | 0 |
| lateral | 0 |
| unchanged | 20 |
| legal root hints | 20/20 |
| attempted iterative-deepening iterations | 59 |
| root-hint applications | 59/59 |
| first-action mismatches | 0 |
| contract failures | none |

Classification: **NEUTRAL**.

The raw ignored result is `.generic_chess_flow/f71-r1-root-hint-harness-corrective/f71_results.json`, SHA-256
`88e031fdca54f902ede99c879652445af0ad7513672da3f9f4effa0069084540`.

This neutral corrective result does not authorize
`final_holdout`, Arena, or promotion; the next work order controls any
independent confirmation.
