# task2636 all-in cost completeness

Frozen design values (do not change): 6,600s lifetime hard cap; stage caps 1,200s preparation/audit/reporting, 2,400s training and 3,000s evaluation. The plan charges 542.632s for prior preparation/audit work, leaving 657.368s in that reserve and 6057.368s future total allowance. Source-bound projection is 2110.568s training + 691.419s evaluation + 1,200s reserve = 4001.988s (66.70 min), with a 110-minute hard cap.

The inherited 66.70-minute projection is not a runtime guarantee. Its training component is derived from the slowest 80k-node task2621 cost-scan arm with a1.5× margin; its evaluation component reuses task2609's measured1,536-slot run for the planned1,024 slots. The later task2625 run's own elapsed-time receipts are separate comparator data, not the formula inputs. The projection still does not include measured development/validation costs for the candidate-index training/evaluation runners, partial history/query auditors, stop/deadline tests, write-once registration, or final source-bound analysis. Those are required engineering/preflight work, not evidence that can be absorbed by an unexamined reserve. The current657.368s reserve is explicitly allocated to remaining replay/audit/reporting; the plan provides no measured margin for the missing adapters.

Decision: preserve the 6,600s/110-minute cap and 120-minute Chat-assessment threshold unchanged. Do not launch or register based on 66.70 minutes alone. First estimate the missing implementation and validation work from bounded receipts; if that work is charged to this study, stop within the existing reserve and hard cap, and report partial evidence rather than extending. Count engineering effort separately in the study's information-per-cost comparison. The run remains below 120 minutes by the current projection, but the all-in scope is not yet closed because adapter work is unpriced.

No experiment started and no cap or frozen input changed.

## Continuation engineering-cost checkpoint — 2026-10-21

The same DEV_AUX session ledger rose from 2,074.554978s to 2,715.371352s
confirmed effective work during this continuation: +640.816374s. This work
implemented and adversarially tested only a source-bound per-slot replay
prototype, reviewed receipt composition, and documented the remaining gates; it
did not implement the candidate-index runner, registration, training or
evaluation. It is Agent engineering/research overhead, not elapsed runtime from
a registered experiment timer (no registration exists).

As a conservative information-per-cost allocation, charging that work against
the remaining 657.367934s preparation/audit/report reserve would leave
16.551560s. That is not enough for whole-result integration, actual-terminal
fixtures, stop-safe writes, final audit or reporting. Therefore the frozen
66.70-minute projection is still not an all-in project estimate, and no
registration/launch is justified. Preserve the existing 1,200/2,400/3,000s
stage allocations, 6,600s lifetime cap, 110-minute hard cap and 120-minute
assessment threshold. Any future cost estimate must separately expose
engineering overhead and actual registered-process time; do not imply this
research time was charged to a nonexistent run timer.

A bounded source-context smoke took31.7ms to read/hash the 6,962,023-byte root
pool and index,34.9ms for first candidate compilation plus one query replay,
and24.0ms median for ten cached one-query replays. It confirms context reuse is
cheap for the tested single root; it does not measure multi-query slots, a full
1,024-slot audit, durable writes, or actual-terminal handling. It does not
justify reclaiming the remaining reserve or change the no-registration decision.
See `results/dev_aux/task2636/replay-context-cost-smoke.json`.

## Frozen-root branching cost diagnostic — 2026-10-21

A source-pinned, outcome-blind legal-action census replayed all task2636 frozen
roots and task2625 reference roots without running search. task2636 means were
38.17 training / 38.63 evaluation legal actions per root; task2625 means were
10.84 / 10.94 (3.52× / 3.53×), with p90 73 / 71 versus 19 / 20. This is direct
evidence that the old panel is a weak complexity proxy for the new candidates,
but root legal branching does not yield a linear wall-time multiplier. It
therefore weakens the 66.70-minute projection as a guarantee and does not close
the cost estimate. Keep task2636 unregistered and preserve the 6,600-second
cap. Full data, pins and interpretation limits:
`results/dev_aux/task2636/ROOT_BRANCHING_COST_REVIEW_20261021.md` and
`root-branching-cost-audit.json`. No outcomes, search or training were read or
run.
The training projection implies1,895 nodes/s against a 1,667 nodes/s minimum
to complete within the2,400s stage cap, only12.1% projected throughput margin.
Evaluation's3,000s cap has much wider arithmetic headroom for its projected
1,254,951 nodes. These sensitivities do not predict realized candidate speed.

## Estimate-root basis audit — 2026-10-21

A follow-up read-only audit compared legal actions at the exact root manifests
behind the training and evaluation cost references, rather than treating the
later task2625 completed run as the projection's root basis. Task2621's
80k-node-per-arm cost-scan registration points to only8 already-exposed roots
(two per rule; mean10.125 legal actions), while task2609's frozen evaluation
manifest has64 roots (mean8.938). Task2636's frozen roots average38.166 across
1,920 training starts and38.629 across256 evaluation starts: 3.77× and4.32×
the respective reference means. The task2621 sample is very small, and legal
actions at a root do not predict descendant branching, pruning, query count or
node throughput. This diagnostic further limits confidence in the projection
without yielding a replacement runtime number. Task2625 remains a separate
later runtime comparator. Keep all frozen budgets and inputs unchanged and do
not register until runner, durability, result-binding and estimate gates close.
Source pins and distributions:
`cost-basis-root-branching-audit.json` and
`ROOT_BRANCHING_COST_REVIEW_20261021.md`.

The formula was separately reconstructed and its exact upstream plan,
registration, result and root-manifest hashes checked in
`estimate-basis-receipt-verification-v2.json`. It confirms the 4,000,000-node
training estimate is `50 × 1.5 × 28.1409069s = 2,110.568s`, and the
evaluation estimate is task2609's1,536-slot 691.419s result. The root-action
comparison does not provide a corrected runtime estimate or close the missing
implementation/validation cost.

A fixed, outcome-blind depth-two legal-action census over8 of120 roots per
candidate found mean full-expansion edge counts 12.69× (training) and19.35×
(evaluation) above the small direct cost-reference root sets. The candidate
group means are heterogeneous and the census does not execute AlphaBeta,
measure visited nodes or provide a runtime multiplier. See
`depth2-legal-action-expansion-audit.json` and the interpretation limits in
`ROOT_BRANCHING_COST_REVIEW_20261021.md`.

The separate fixed-root D2 no-search upper-bound screen compared full-width
walk-call counts with the frozen2,048-node training-query limit:34/128 roots
in the first8 families per candidate exceed it, versus0/8 task2621 reference
roots. This is not an observed cap-hit rate because AlphaBeta pruning and
terminal short-circuits were not run. It adds a concrete load mismatch but no
runtime multiplier; preserve UNKNOWN for incomplete searches and keep the
registration gate closed. See `query-cap-screen.json`.

The same upper-bound count across the entire frozen training pool is549/1,920
(28.59%), close to the first-eight-family subset's34/128 (26.56%). Candidate
rates are heterogeneous (0–112 of120 roots), and the direct task2621 roots
remain0/8 above the bound. This confirms a structural mismatch in the frozen
input set but still does not measure AlphaBeta node visits, actual cap endings,
UNKNOWN frequency or elapsed time. Full results:
`query-cap-fullpool-audit.json`.

## Confirmed preflight effort checkpoint — 2026-10-21

The active DEV_AUX segment `9e97f96e-1a97-4cdd-994c-6f2b2cedc337` has now
confirmed 2,715.517 effective research seconds through the candidate-aligned
train/evaluation node-bound analysis. This is Agent research/engineering time,
not task2636 process runtime: there is still no registration, start receipt or
`run-v1`. The frozen source-bound training/evaluation projection remains
2,801.988 seconds; the design had allocated 542.632 seconds of prior work to
the 1,200-second preparation/audit/reporting reserve, and the earlier
checkpoint conservatively charged another 640.816 seconds of Agent work
against its 657.368-second remainder.

Under that same conservative information-per-cost convention, charging the
current segment's confirmed 2,715.517 seconds would put the remaining reserve
2,698.965 seconds below zero and the projected sum at 6,700.953 seconds, which
is 100.953 seconds above the frozen 6,600-second total. This is not an actual
process-budget overrun because the Agent intervals are not registered-run wall
time; it is evidence that the existing all-in allowance cannot honestly absorb
the observed preflight effort plus the inherited execution projection. The
candidate-index runner, integrated auditor, terminal fixture and stop-safe
writer are still missing and unpriced. Keep the 6,600-second cap unchanged and
do not register or launch on the 66.70-minute projection. No extension or
relabeling of these costs is justified by the negative reserve.

## Cost-ledger correction — 2026-10-21

The preceding 6,700.953s scenario double-counted the 640.816s increment. That
increment was the increase in the same active segment's cumulative session
ledger from 2,074.555s to 2,715.371s; it is already included in the later
2,715.517s and 2,883.287s totals and must not be added separately. The plan's
542.632s preparation charge is a mixed budget allocation, not one measured
duration: 227.998s observed inventory, 4.762s observed prefix audit, 165.872s
projected pool preparation, and 144s projected full-source audit. At the
00:06:34Z checkpoint, 3,313.414s confirmed Agent research + 542.632s allocated
prior preparation + 2,801.988s projected training/evaluation = 6,658.034s,
58.034s above 6,600 under this mixed-cost scenario. This is not process-wall
time or an actual cap hit. The active plan defines its cap in cumulative
process wall seconds, and no task2636 run is registered or started. Keep
Agent effort, measured process time and projections separate. Unpriced
candidate-index runner/auditor, terminal-fixture, stop-safe lifecycle and
reporting work still prevents a closed all-in estimate; retain the no-run
decision and do not change frozen caps or inputs. Detailed source recheck:
`results/dev_aux/task2636/PIN_AND_COST_SCOPE_RECHECK_20261021.md`.

The allocation components have now been reconciled against the frozen root
plan and prefix-audit receipt. Only 227.998s inventory and 4.762s prefix audit
are observed; 165.872s root preparation and 144s full-source audit are
projections. The 144s has no matching completed runtime receipt in this task's
records. Exact component arithmetic and evidence classes are in
`PREPARATION_CHARGE_COMPONENT_CHECK_20261021.md`. This clarifies the 542.632s
charge without changing the no-registration decision or converting the mixed
scenario into process runtime.
