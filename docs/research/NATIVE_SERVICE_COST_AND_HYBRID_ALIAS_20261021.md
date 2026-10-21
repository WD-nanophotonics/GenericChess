# Native service cost, actual utility and hybrid action aliases — 2026-10-21

PRIMARY_SANDBOX; base d2da9705bb7993e41d7920aad4439e5156059ede.
Science remains OPEN. No evaluator/search defaults, sampler, rule semantics or
AUX files were changed. This is exposed development evidence, not a holdout.

## Decision

Existing Native availability/check services reduce execution cost on the tested
explicit semantic carrier. Comparable search work requires aligned ordering;
otherwise representation-induced tie/order differences confound that comparison.
More completed depth under time limits did not establish outcome improvement.
Retain existing candidates and defaults. Next compare the existing q1 horizon
against q4 on the exact published hybrid inputs, without extending frozen panels.

## Evidence and reproduction

The compact [technical packet](data/semantic_probe_20261021/summary.json) retains
full rules, canonical input histories, 16 outcome slots, eight deduplicated game
records, selected query/provenance fields and repeat timings. Identical repeated
decisions are factored once with all measurements retained. It explicitly marks
one missing observation and scope exclusions; it is not the full raw query log.
Exact raw results and ad-hoc producers remain in ignored local artifacts. Only
one maintained [cost probe](../../scripts/semantic_probe_cost.py) is added.
It supports frozen complete records via --input, or explicitly declared generated
sampling, existing service/order switches and q depth. Old ad-hoc stages are not
claimed turnkey reproductions. Setup cost and choose_action cost are separate.

Next bounded comparison (not yet executed):

```powershell
.venv/Scripts/python.exe scripts/semantic_probe_cost.py --input docs/research/data/semantic_probe_20261021/summary.json --seed-count 4 --variants all ordered --qdepth 1 --nodes 5000 --seconds 1.25 --total-seconds 60 --output artifacts/hybrid-q1-next.json
```

The existing hard check extension cap remains8. Input/q1 parameter plumbing was
smoked on one frozen root with zero nodes; that is not a q1 comparison result.
Report returned q depth, reserve/abort, work and complete cost. Retain all failed,
missing, terminal and censored slots. Do not infer usefulness from depth alone.

## Mixed promotion/drop continuation

Three full roots at plies4/5/6 were replayed, then nine D2q0/protected capture-q1/
ordinary-q1 queries run. Chosen actions agree. At ply5 capture-q1 gives -5800
versus -5900 for ordinary/D2. The actual continuation contains Kf8-g8, checking
R@a8 and mandatory g8-h7: hand900 becomes board1000 without a capture or auxiliary
loss. This explains the 100 surrogate shift; it is not a demonstrated win gain.
An81-query service control gives matching decisions/work/PV and zero fallback.
Provider metrics on reused players are cumulative; saved metric deltas, rather
than cumulative readings, support per-query interpretation.

## Generated carrier and service costs

Eight fixed seeds2026102121..2128 use n8, three cyclic presets, attempts30 and
prefixes0/12. The original generator uses the legacy carrier. The diagnostic uses
existing compile_legacy_ruleset_for_semantic_execution explicitly; this does not
change generator defaults. The first default-carrier support lookup and a wrong
semantic compiler both failed before queries; failures are preserved.

The192-query service assay has D2 completion, matching decisions on all16 roots,
zero fallback, and three repeats/four service settings. Native-all/legal median
query ratios range0.489..0.834 (median0.720). Check-only can cost more;
availability plus check can share an import. These are measurements, not a
promise for arbitrary rules or concurrent loads.

The legacy baseline planned48 observations but retained47. One query completed
and was lost before persistence through a diagnostic-action parse mistake; it
remains missing, not rerun or silently replaced. Scores agree, but ordering/ties
and work differ (one root3982 versus510 nodes), so raw carrier timing confounds
execution and search work. A separate96-query process-local ordering intervention
aligns complete physical PV, scores, depth and nodes on all16 roots. Full semantic
aliases remain. Native-all/legacy warm median ratios range0.346..0.611
(median0.513). The intervention is restored after the assay, not a product patch.

Separate fresh setup/replay measurements show roughly6–12ms extra IR setup.
Composing their medians with query medians predicts break-even after one query
for14 roots and two for2; those two first-query ratios are1.024 and1.030.
This is arithmetic composition, not an observed process-cold pipeline. A profile
locates costs in existing attack/generation and Core availability/check paths;
it does not justify an unrelated micro-optimization project.

## Actual consumer, q ordering and finite outcomes

With the actual default evaluator, TT, main ordering, root tactical scan and
q4/hard8,32 fixed-node service queries preserve decisions/work/provenance:
6 roots complete D2,9 retain node-censored D1,1 has an immediate winning root
at depth0. The latter is not failure. Sixteen existing ordered-q queries reduce
work on complete roots but add zero D2 completions under5000 nodes. A separate
common1.25s/5000-node32-query cohort completes3 D2 with ordered-q versus0 ordinary
(plus the same immediate win). All3 agree in score/action with saved completed
q4 references. Every full input record/rule matches the fixed-node cohort.
Deadlines are cooperative, not hard preemption. Enabling ordered evasions in16
further fixed-node queries adds zero D2 completions, with some extra overhead;
no wider unchanged evasion campaign is selected.

The actual16-game panel fixes the opponent, both candidate colors and four
natural rules. Candidate D2q0 has10000 nodes/50ms; the fixed opponent uses IR-all
D2q0/10000 nodes/1s. Unit board1000/hand900, TT/order/root scan off, observation
cap64 and rule max_ply512 remain frozen. All16 slots were observed with zero
fallback; query times meet the declared requested+2ms qualification. Outcomes
are2 wins,6 losses,8 UNKNOWN; each service arm has1W/3L/4U. All8 paired game
records agree. Native-all completes D2 in61/132 candidate queries versus50/132,
without an observed outcome gain. Unresolved games remain UNKNOWN, not draws;
paired utility difference bounds remain[-1,1], even when observed prefixes agree.
Fresh public Core replay checks all16 records and530 action edges against actual
terminals/winners. No fitness slots or caps were extended.

## Hybrid alias and sampling controls

Four new hybrid seeds2026102141..2144 retain complete typed actions/history.
An initial legacy-uniform preflight is distinct from the later semantic-uniform
cost cohort. At2142, legacy versus semantic legal counts are38/42 at root and
70/72 at prefix12. Benign aliases reach equal physical states/terminals/repetition
counts but distinct literal histories. Existing runtime search keys already
coalesce those benign cases. A negative witness with the same coordinates/board
and different auxiliary effects retains distinct keys: board-only deduplication
would be wrong. No new coalescer is needed on this evidence.

Exact one-step pushforward total variation is34/399 and17/630 on the two2142
roots; other preflight roots are zero. Same RNG seeds nevertheless diverge at
ply1 in all4 physical walks, because action ordering also changes coupling.
Never equate same seed with matched states. Earlier carrier comparisons use
matched full histories and remain valid. A separate Ray plus redundant first
Leap control preserves raw static capability2.345256493555175; only its movement
signature differs, so there is no pending static-value fix from this witness.

The actual semantic-uniform hybrid cohort runs24 queries on8 full roots with
legal/all/ordered services,1.25s/5000 nodes and q4/hard8. All and ordered each
complete2 D2 roots; legal completes none. All3 recognize one immediate win.
Across24 queries there are4 check-hard aborts,13 time-censored,3 immediate wins
and4 D2 completions. Faster execution can reach hard8 and return a D1q0 reserve
where another arm times out: that is not q4 success. Do not extend that cap.
Fresh public Core applies all24 root choices and29 literal main-PV edges;
this does not certify the unrecorded q tail or all-domain equivalence.

## Observed recording defect and validation

Generic dataclass dumps of GameRecord omitted canonical action kinds and emitted
nullable version-specific fields rejected by strict replay. Five new tests fail
before the fix. research_record now delegates GameRecord to the existing public
serializer; canonical schema1/2/3 and actual promotion/drop/aux/history roundtrip
pass. Invalid records cannot replace old evidence. Standalone diagnostic actions
and PlayerDecision retain their existing shapes. Historical snapshots are not
rewritten; canonical copies were reconstructed and validated separately.

The affected record/session tests first pass28; the later focused record/session/
reserve/provenance run passes54 tests. Required publication-gate results and the
full remote SHA are recorded in the local delivery receipt, not invented here.

## Incoming advice and literature limits

Claude's new17:48JST message and complete empty-reply thread were saved privately
before assessment. Adopt actual consumer cost versus utility, compact evidence
and branch-specific interpretation. Reported AUX learning evidence remains
message-sourced, not independently rerun or merged by PRIMARY. No outbound reply,
AUX write, worker or repeated Chat poll occurred.

The [2001 publisher abstract](https://journals.sagepub.com/doi/abs/10.3233/ICG-2001-24205)
and author-hosted1998 sections on
[strength/depth](https://people.csail.mit.edu/heinz/dt/node49.html) and
[best-change behavior](https://people.csail.mit.edu/heinz/dt/node58.html) motivate
separating work/depth from measured decision utility. Full2001/2003 papers were
inaccessible; no full-paper verification or universal per-ply strength claim is
made. These tiny exposed cohorts do not settle search versus learning priority.
