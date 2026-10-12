# Q0 canonical reconstruction and immediate-win caller policy

Production base: `c5396cbe8f2c524002461b06068ced561ad2119c`.
This segment separates two actual costs: materializing the canonical search
continuation, and repeatedly deepening after a chosen action already wins.
Both concern the existing supported semantic q0 backend. The q4/general-domain
target, legacy/default/UI policies and frozen older experiments remain.

## Canonical reconstruction

The preceding naive TT experiment retained root score/action but shortened gen0
PV4→2 and changed the Shogi PV despite its length staying4. Cached values are
not a trace. This changed-premise candidate keeps canonical encoded action
order, evaluates child scalar bounds through ordinary search/TT, and recursively
rebuilds ONLY the finally selected child with a full canonical window at every
canonical node. It does not substitute a TT action chain for a continuation.

At a canonical node, the first ordinary candidate supplies an exact incumbent;
a neutral declaration supplies a preferred equal-score incumbent. Later normal
child searches use the narrowed negamax window. A fail-high child supplies only
an upper bound at the parent, which cannot displace the earlier smaller action
at equality; an improving child is exact. Recursing on the selected child then
reconstructs the continuation under the same finite horizon/history/evaluator.
The actual completed selected-pass value is checked against its parent's value.
Mismatch produces `internal_error` before committing an incomplete iteration.
This is source reasoning plus finite measurements, not a whole-domain proof.

Private fixedD4, cold1MiBTT/min2, fullhistory, both execution orders:

|Saved root|Baseline visits|Reconstruction visits|Full output|
|---|---:|---:|---|
|gen1091 turn0|35219|14699|same value/action/four-action PV|
|gen1091 turn2|342036|281094|same value/action/PV|
|Shogi middle turn0|25518|17236|same value/action/PV|

TT0 repeats also preserve all6 cross-arm full tuples:35219→22615,
342052→283701,25666→19432. The local improvement is not conditional on TT.
Seven existing complete generated-rule/history roots atD2/D3 give56 queries,
28 fulltuple comparisons, all requested depths complete. Relevant39 private
product/development regressions pass. A new16000-node regression has actual
sensitivity: old full replay fails atD3; naive TT reachesD4 but fails its two-action
PV; reconstructed search passesD4 with the complete frozen four-action PV.
These are three real search queries, not implementation-mirroring assertions.

Five deterministic marker+64 node-budget calls target refinement and canonical
pass. Both publish the prior wholeD3 tuple;61 new valid descendant TT stores
exist before the refinement abort. Retrying with the SAME persistent TT matches
coldD4 full output in both cases. Valid completed descendants need no rollback.
The source/counter records distinguish this node-budget check from external
thread cancellation. The existing public cancellation regressions are separate.

Equal64s/max_nodes=None,12 queries, six reverse fulltuple pairs agree:

|Root|Baseline depth/value|Reconstruction depth/value|Attempted visits, first order|
|---|---|---|---|
|gen1091 turn0|D5/-221|D6/-2619|2153112→1003493|
|gen1091 turn2|D5/-221|D5/-221, whole tuple same|1474470→1020968|
|Shogi middle turn0|D4/0|D5/200|1983548→922984|

Counts include the unfinished next iteration. Distinct completed horizons may
have distinct values; that is not a claim of better game play. Ordinary concurrent
local work, including owned diagnostics, occurred; no exclusive-machine,
noise-free, equal-primitive or Elo claim follows. Original resource planes remain
immutable/exposed. No new PVS kernel or position patch is introduced.

## Actual immediate-win policy, kept separate

Private candidate after a COMPLETE depth1 exact-root iteration rebuilds its
selected ordinary child with `make_checked`, executes the actual terminal policy
with full history, and confirms winner==root mover. Declaration decisions are
excluded. It returns `proven_immediate_win` and actual completed_depth1, never
labels the result as requested_depth12. This is a caller goal, not replacement
for fixed-horizon evaluation/training labels or default/UI behavior.

56 saved-root queries:28 reverse fulltuples and14 commonD1 comparisons agree.
Three actual one-ply wins return in roughly2–5ms instead of continuing16s at
D8/D9/D5, with the same chosen action/score. Four non-immediate roots retain
complete tuples and budget causes, including a five-ply win that continuesD8.

A real private defect was found: injecting `gc_cancel_flag_request` during the
extra proof caused the first prototype to report proof instead of cancellation
on the three winning roots. Corrected private checks force budget/cancel before
and after proof.35 boundary calls retain the same completedD1 tuple, report
cancelled on all7 roots, and guarded persistent-TT retries match cold results.
The first prototype's data stay frozen and are never relabelled as corrected.

112 corrected direct-entry calls cover root-offset0/1,TT0/1,legacy/exact modes:
56 rawtriplets agree,28 legacy depth/cause pairs remain unchanged. A private
explicit-opt-in consumer executes28 actual GameSession calls:21 submitted
moves,7 cancelled calls not submitted,7 node-budget fallbacks submitted as
predeclared,3 proven winning submissions re-adjudicated from session rules.
It logs requested/actual depth and kernel/caller cost. The extra proof rebuild/probe
are not added to the original search node/transition counters; total caller/kernel
time includes them. Do not infer equality of primitive work from those counters. This is private consumer
closure; existing public UI/self-play integration is not claimed. Self-play source
records actual depth, but its handling of a new termination reason is not a
universal verified contract. No small training was launched by this segment.

Dot1791798325 reviewed the published baseline output code independently, not
unpublished candidates or local measurements. Adopt its explicit-caller boundary,
actual-submit outcome check and truthful depth/cost/abort reporting. Source-only
advice is not independent experimental reproduction. The dispatched16-seed
prospective comparison was already declared; it completes unchanged, without
expanding rules again for the separate consumer check.

## Completed broader checks and delivery

Prospective16 fixed seeds yielded40 natural ongoing roots at plies0/8/16:
160 queries,80 reverse fulltuple pairs. Ten roots have actual immediate winners;
private proof returns in1.3–7.0ms while the original runs roughly8.25–16s.
The30 non-immediate roots retain whole value/action/PV/depth tuples. The entire
producer ran2314.631seconds (38.577minutes), without a cap extension. This
cohort uses the FIRST prototype with no external cancel supplied; its performance
is not relabelled as a test of the corrected cancellation variant. Eight later
roots are naturally absent because the predeclared uniform legal walk ended
sooner. Walk-only coverage records their actual terminal states, validates all40
saved roots and does not rerun/resample search.

Six fixedD5 Shogi calls compare reconstructed Native, TTfree/unordered CorePlain
and existing ordered/TT CoreAB (all noPVS/root tactical, same fixed material leaf,
q0/fullhistory,64s/no node limit). All3 reverse fulltuple pairs agree. Native
completesD5/200 in9.651/9.678s,181699visits; CoreAB in20.574/20.686s,73764visits.
CorePlain uses63.984/63.987s,449988/451507visits, completing ONLYD4/0. Its
independentD5 value is UNKNOWN. CoreAB remains an optimized reference, not
independent TTfree confirmation. Different node meanings and work/order costs
prevent a primitive-speed claim. Preserve the incomplete cells, not rescue them.

Production adopts only the existing optional exact-root q0 canonical
reconstruction; no terminal earlyreturn/default/UI/result-enum policy changes.
All owned calculation processes exited before replacing the staged DLL. Its
SHA matches the installed product.40 relevant production regressions pass;
39 earlier private checks and the three regression-sensitivity searches are
separate evidence, not an inflated independent test count. Publisher repeats
these40 production targets as required. Final remoteSHA is verified separately.
The source adds the selected-pass scalar consistency check and retains existing
control-before-completed-iteration commit. No diagnostic counters are shipped.

The counter-only follow-on measures ALL canonical-phase visits independently of
the old pv_replay flag; otherwise moving scalar probes into normal search would
misclassify cost. Its final measurements and source hashes are in the evidence
index, with a remaining-bottleneck decision after the four actual queries.
Private prototype sources, declarations, complete results, input closure and
hashes are archived after outgoing privacy review. Raw Slack/account records,
compiler logs, binaries and private inputs are excluded. Every project run is
under one hour; the Agent segment is a separate60–90minute unit. Science remains
OPEN and all finite/exposed/q0/ordinary-concurrency limitations remain.

## Actual phase accounting and root-only ordering follow-on

Four counter-only D5 calls match the counter-free complete outputs. Visit origins
sum exactly to total; both execution orders have identical counts. Gen2 uses
347112visits:main61292, root tie confirmation267696, canonical phase18124;
the root canonical interval is1.77–1.78s within16.5s caller time. Shogi uses
181699:main113754, refinement7094, canonical60851;2.20s within9.6s. Each has
only15 visits with the old replay flag. That flag therefore does NOT measure
complete canonical-phase work after the algorithm change. Phase time excludes
parent child-rebuild/context setup outside the recursive call; nested intervals
are not double counted. Ordinary concurrent work still limits timing inference.

This selects a new premise: canonical order ONLY at the root, preserving lower
level min2 material ordering and the new recursive reconstruction. Earlier global
lexical/min2 and failed TT-first tests are not rerun/relabelled. No root hint is
supplied. Eight gen2D4/D5 calls keep four complete output pairs and eliminate all
267696 refinement visits. D4 visits281094→58778,11.7→2.74s;D5 347112→219403,
16.6→11.8s. Four ShogiD5 calls keep full output, eliminate7094 refinement visits,
but total181699→183030 (+1331),9.69→9.81s. This small cost loss is preserved,
with load limits; uniform production adoption does not follow.

A derived verifier initially assigned comparison roles by row list order, so
reverse execution tested baseline against the candidate's zero-refinement
assertion. It failed before writing its verification file; the following
checkpoint already quoted correct first-order measurements but prematurely
referenced that missing file. Named `arm` selection now verifies all pairs and
repairs earlier derived reverse-cost labels. Original raw results are unchanged,
failed verification and repairs retained. Source-preparation substring/PowerShell
quoting failures for counter instrumentation were also corrected before search;
no hidden execution blocker or user intervention remains. The outgoing record
includes these limits rather than claiming flawless verification.

A final56-query factor on the existing seven roots atD3/D4 is recorded separately.
It is exposed development, no new rule sample or default/UI adoption. Root-only
order remains private pending the measured transfer/decision, whereas the tested
canonical reconstruction alone is the production change.

Final root-order finite factor:56 actualD3/D4 queries on all7 existing generated
roots complete every requested horizon;28 named-arm fulltuple pairs match.
Across14 root/horizon cells, candidate visits are lower5, higher7, equal2.
The largest gain is seed1204-root0 D4 28530→18788; a loss there atD3 is2268→3111.
Seed1202-root0 D4 31617→33852 also worsens. Thus eliminating root refinements
alone does not guarantee total-work savings, even within one rule/root at different
horizons. Keep this candidate private and measure actual caller resource curves
before adopting a fixed general policy. Do not select methods by exposed root ID.

Next-step source inspection also finds root hints applied AFTER the ordering
block. A caller's explicit legal hint can therefore override canonical root
order and bring late-smaller confirmations back. All current root-only controls
supply hintNone; zero-refinement is limited to that declared condition. No
root-hint metadata or public caller policy is changed by the production patch.

Segment67.654minutes/11 research stages, UTC09:25:06.755593–10:32:45.996482;
accepted `session finish safe_checkpoint`, Science OPEN.566 actual scientific
queries and3 regression-sensitivity queries. The109-member1877347-byte archive
passes every member SHA reread/privacy review. Final delivery uses the tested
sandbox publish entry and verifies exact remote SHA; publication evidence is
reported separately from local commit/test success.
