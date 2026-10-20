# Task2628 rules15 TDLeaf evaluation

## Result

The registered four-seed TDLeaf training reached all four 250,000-node caps.
Its independently replayed training audit passed: 1,000,000 paid nodes,
56,061 search queries, 1,471 episodes, 1,377 actual terminal outcomes and 94
UNKNOWN episodes. Training took 1,277.23 seconds, below its 1,800-second cap.

The original trainer exited with code 1 while assembling its final summary
because it read `rule_index` from records keyed by `rule`. That failure is
preserved. A separate recovery artifact was reconstructed from durable run
logs; the full-history, terminal, node-cap and TD-update audit passed. The
source-pinned evaluation binder also failed before writing due to undefined
`RULES`/`SEEDS`; that failure is preserved, and a plan-derived supplemental
binder passed the registered source, recovery and audit checks before the only
evaluation launch. Neither failure changed the frozen plan, samples, training
or evaluator source.

The single registered evaluation completed all 256 slots in 243.78 seconds:
10,399 queries and 191,464 nodes, with 239 actual terminals and 17 UNKNOWN
endpoints. The independent full-history audit passed slot identity, legal
replay, actor/prefix consistency, actual terminal/reward semantics, UNKNOWN
retention and combined per-game node caps. Result SHA-256:
`a7009533fbfc5be49439a7580e2b00c47dda3831e762312017b01ff1af36496a`.

| Endpoint | Wins | Draws | Losses | UNKNOWN |
| --- | ---: | ---: | ---: | ---: |
| Initial weights | 60 | 1 | 57 | 10 |
| TDLeaf weights | 60 | 1 | 60 | 7 |

Of 128 paired strata, 113 have both endpoints known and 15 contain at least
one UNKNOWN. Treating every UNKNOWN endpoint independently over `[-1,+1]`
gives a TDLeaf-minus-initial sum bound of `[-20,14]`, or mean bound
`[-0.15625, 0.109375]`. These are finite-panel completion bounds, not
confidence intervals. They include both signs, so this panel does not establish
a strength gain or loss. No UNKNOWN was labeled a draw.

## Mechanism and limits

Descriptive exposure checks passed after fixing the supplemental script's
missing repository-root import path. All five trainable feature channels were
exposed in every seed's learner-turn searches; the fixed board-P coordinate
remained at 1.0. The hand-R unlock action executed 124 times for TDLeaf and 126
times for initialization in the evaluation. As an explicitly post-hoc,
non-causal diagnostic, the four trained seeds moved board-N, board-R and hand-R
weights upward, hand-N downward, and hand-P slightly upward. This verifies
parameter updates and action exposure, not that a feature caused a W/L result.

The registered panel covers one generated 4x4 semantic-action ruleset. Its
freshness audit establishes exact full-record disjointness only against the
enumerated history inventory; it does not establish descendant,
transposition, distributional or population independence, nor full-Generic
transfer. The pinned analyzer was left unchanged; its stale 512-stratum
assertion conflicts with this frozen 128-stratum plan. The supplemental
plan-derived analyzer passed without changing slots or inputs.

The latest Chat mailbox review is preserved in
`results/dev_aux/task2627/CHAT_REVIEW_20261021.md`. Its outcome-blind
sampleability/cost recommendation was adopted because task2627 already passed
that gate; it did not call for expanding or rescanning the panel. The optional
task2625 censoring analysis remains deferred, PRIMARY-owned suggestions remain
outside this checkout, and the transport-only note was rejected as
non-actionable. No additional sample or cap extension was made.

## Verification and artifacts

- `audit_training.py`: PASS; result and audit receipts remain under `run/`.
- `audit_evaluation.py`: PASS, 256 slots, 10,399 queries, 191,464 nodes.
- `analyze_corrected.py`: PASS; audit, plan, registration and output hashes
  are bound in `run/corrected-analysis.json`.
- `feature_exposure.py`: PASS; descriptive only, gated on both audits.
- Five task2628 test modules: 12 passed; `git diff --check`: PASS.
- Frozen plan SHA-256: `beeb7aa73a1c184ff9e34451c81ec524d02f596bdc663976a187132756a46187`.
- Root-pool SHA-256: `03f7184d843bcd7c2f90ff84204516a739125ff26a538f2655078841bd98c17c`.

Follow-up: a separate fresh-root H=256 evaluation using the frozen task2628
models is recorded in `results/dev_aux/task2629/REPORT.md`. It retained its own
registration and analysis; the two panels are not pooled. Neither finite panel
establishes a strength gain or broader learner transfer. Do not reuse either
panel's exposed roots or extend either cap.
