# Conservative late quiet reduction: closed quality study

All frozen producers are CLOSED:1,177 new Player returns and7,543 literal PV
steps qualified. The fixed LMR prototype shows **no observed WDL benefit** and
some additional cost. Do not integrate it or expand/tune its parameters from
these results. PURE LEAPER remains the scope; default/UI/AUX are unchanged.

## Actual results

Both arms use the same default dynamic evaluator, PVS and Q4/hard8. The baseline
is PVS-enabled, not the product's default PVS-off tuning. Quality uses actual
returned actions and source-attributed full-history WDL, never score/depth.

| Cohort/budget | Baseline/candidate correct | Repairs/regressions | Query seconds, baseline → candidate | Target-node time censors |
|---|---:|---:|---:|---:|
|19 histories,50k/10s|19/19 →19/19|0/0|180.765 →186.199 (+3.01%)|11/13|
|same19,200k/30s|19/19 →19/19|0/0|570.005 →570.218|19/19|
|same19,existing1.5s|19/19 →19/19|0/0|28.504 →28.659|not a node target|
|p47/p49/p53 controls,1.5s|1/3 →1/3|0/0|4.500 →4.526|not a node target|

The50k events are885,684 →852,492;200k events2,671,564 →2,516,407.
Fewer events do not establish lower total cost: per-event work and reduction/
re-search/patching overhead change. All200k returns hit30s; desired node
attainment stays UNKNOWN although actual chosen WDL is known. Fixed-time stops
are the intended consumer boundary, not missing game outcomes. This is not
evidence of policy equivalence.

The19-witness bundle has9 complete RuleSets,13 WDL-fork histories across5 rules,
9 rootWIN/10DRAW and one structural-draw history. Nine rules are not nine
independent sensitive families. The corpus is previously selected/exposed by
AUX, not a holdout or a newly solved census.

The first batch completes24colorpaired games on6existing rules/12full-history
roots, configured2s/search and original maxply96. All24 end in actual ruleDRAW;
20 meet the benchmark's timing eligibility. This shows no observed strength
benefit, not equivalence. Some trajectories repeat early, others reach the clock.
Game-query totals1041.438/1043.470s are not identical-query paired cost trials.

The service clock includes AST/Player work, recording and PV replay. Two early
flags are2.108/2.125s: one reports search2.089872s; another reports search2.000105s
but query2.117336s. Residual locations differ; exact OS/atomic-work cause is
UNKNOWN. All four timing-ineligible games and their actual DRAW outcomes stay.
Shared load/recording overhead limit interpretation; no such slot is rerun.

## Prototype, registration and controller boundaries

The research-only reversible transform reduces one ply at nonroot nonPV nodes,
depth>=3/moveindex>=3, for noncapture/nonpromotion board moves outside check.
Checking/terminal children refuse reduction. An alpha-raising null probe requests
original-depth/window re-search. No labels choose actions, prices, parameters
or stopping depths. TT history/clock identities remain; arm-specific Player/TT
state stays isolated.

This is selective search: nominal depth, TT EXACT and mate bands do NOT certify
the original full-width tree/forced WIN. Raw result-source fields are provenance,
not proof. The any-win option remains false. Re-search counters count requests,
not guaranteed physical expansion past a TT hit. Quiet threats/zugzwang can fail.
Accepted-fail-low counters include unreduced checking/terminal-child probes;
actual reduced_calls is distinct.

Disabled-transform real Core action/value/PV/work/TT parity, exception restore,
immediate cancellation and cancellation INSIDE an actual reduced branch pass.
The pilot requestsD6/100k/5s:4x4 completesD6;6x6 retainsD5 under the safety guard.
It triggers164 actual reductions, qualifying activation rather than quality.

The76-slot quality batch was frozen before queries. After its first11 correct
returns a NEW38-slot existing1.5s-limit follow-up was frozen before its own
calls. It reuses the desktop allocator's LIMIT SHAPE; both arms still use PVS.
It is not original76-slot preregistration, independent validation, an arbitrary
threshold scan or refill of censored targets.

Saturation is budget-specific: the older64-history default was perfect at50k/
200k, but62/64 at1.5s. Its actual misses are p49/p53; p47 is an adjacent sensitive
correct control. The NEW6-slot control preserves H64/5x5 full histories and
converts global seat0 labels to mover perspective. Both current PVS arms still
miss p49/p53. Historical PVS-off default results cannot be credited as LMR gains.
No old FirstQ/singleton/anchor experiment/cap was resumed or rewritten.

## Supplied reference evidence actually checked

Pinned AUX d485c487ba6c3503a7d5af9d8bba465746dfb9a1 supplies horizontal3x3
root137. PRIMARY replays22 all-defenseWIN nodes, including every literal defender
branch. Other actionDRAW labels remain source-graph attribution. Fresh default-
dynamic/PVS D1/2/4/6/8 calls select WIN/DRAW/WIN/WIN/WIN in BOTH arms. D2 cannot
activate reduction. Older AUX material-price/tie behavior is a different caller.

Dot identified canonical data at c5e6d667a8f00f8e0c421e41cabae96752e54a13;
original capsule SHA256:
8af501fffbf8428e4393efe167c4b772d0be45ade4fffaf9b214fd62eeb10ddb.
PRIMARY binds adb75...'s actual17ply H128/repeat4 history, actor1. The bad K
move permits opponent0WIN, checked by2664 literal all-defense nodes. The safe B
capture enters the supplied4264-position/18720-Core-edge region with no decisive
terminal. Plain-Leap/remove/no-promotion/drop/history-policy scope is checked;
repetition/clock only add draws. Fresh graph vertices are NOT reconstructed
played histories; actual root/safe-child records stay intact. Wrong action/proof
binding is rejected; this finite reader closes in18.418s.

Two additional strategies exactly match19-bundle roots and verify78 nodes. They
prove specified winning actions, not unlisted alternatives. No AUX solver, full
graph census, learner or checkout was executed. Other all-action labels retain
original complete-graph provenance, not independent census reproduction.

## Next useful step already begun: a concrete draw-cost opportunity

The new paid games include132 root queries with only two ordinary King anchors:
264.755s, about12.70% of2084.908s game-query time. Name-only counting is an
opportunity measure, not proof or measured savings. A changed policy can change
future trajectories/frequency.

A separate zero-Player check rebuilds all six FULL rules from a minimal
constructor: ordinary8-offset anchors, capture removal, no promotion/drop/extra
policy, H96/repeat4DRAW/stalemateDRAW. Across every nonadjacent King placement/
both turns,6608 fresh Positions and33344 literal Core transitions stay closed
without decisive terminals; ply advances/side alternates. Twelve incompatible
loss/geometry admissions are rejected. Its90s/60k-edge plan closes in12.527s.
One accidentally repeated invocation is refused at exclusive mkdir BEFORE work;
the original single result is authoritative.

The finite invariant and checked draw-only history/clock policies support a
SCOPED FUTURE cutoff. It is not implemented/timed as a cutoff, not general
all-Leaper proof, and never changes Core terminals. The latest autonomous review1792912079.322259 instead prioritizes a real
nonroot-hit/terminal/TT/classifier-cost survey BEFORE cutoff implementation.
Offline artifact audit confirms those exactinternal fields are not retained;
rootcounter/PV cannot replace a bounded trace. Only after consumer/payback and
scope qualification should a reversible research cutoff begin. Replacing a finite heuristic with trueDRAW can still change choices
at non-draw parents: quality controls remain necessary. No type-name shortcut,
clock change, AUX-competing solver, worker or default activation follows.

## Cost, communication and delivery

The LMR chain begins2026-10-25T05:36:42UTC, including engineering/recording/all
phases. The76-slot batch requires parentCLOSED/start<70 cumulative minutes;
1600s cap plus20minute review reserve stays below120. New deadline phases keep
90s/30s caps and the original origin, not new quotas. The tiny invariant is a
distinct next-step feasibility question using paid observations; its measured
cost and prior preparation must carry into continuation. Expected>=120minute
runs still need USER confirmation; contrary Dot advice was explicitly rejected.

Fresh request GC-SLACK-20261025-143549-d40632c7 is verified at root
1792906576.977249. One five-minute check reads Dot1792906749.584589. Adopted:
alternate pinned sources, proof plus actual games, selective TT/mate distinction.
Follow-up1792907766.581369 is verified and checked once about five minutes later,
with no reply; five minutes is not expiry. Latest/relevant older Chat threads
are rechecked before delivery. No remote reviewer is claimed to have run this.

Both schedules now use60minutes: PRIMARY ACTIVE; existing AUX PAUSED and chat
bindings preserved. Stale AUX automation-only Dot bans are replaced by fresh
AGENT_REQUEST/comment-check/five-minute rules. No AUX checkout/state/research
files are edited. Public-manifest LF formatting was repaired without altering
frozen capsules; original diagnostic retained.

[Immutable originals, executed sources and results](data/leaper_lmr_20261025/manifest.json)
are lossless gzip copies with hashes. Capsules are DATA ONLY. All producers close;
no missing slot is filled or failure hidden. Negative LMR and positive finite-
invariant feasibility are not class-wide strength/success or mixed/NNUE expansion.


Latest review adoption: newChatroot1792912079.322259 was discovered during the
single final delayed check, then its complete one-post thread was privately
saved/read. It independently reviews published445c613e without rerunning code.
Adopted survey-first order; executed only the offline observability audit, not
new trace/cutoff/unknownroot experiments. No newresearchtime claimed from reading
this review. No extra Slack acknowledgement loop; next meaningful request will
report actual follow-through. Original report/results and frozen caps unchanged.
