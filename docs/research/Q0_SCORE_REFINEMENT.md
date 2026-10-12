# Exact q0 score refinement and canonical PV cost

Science remains OPEN. This record measures the optional exact-root q0 path;
legacy root-window mode and UI policies are separate. The fixed source base is
62b1d208b4ffc0ac2b358b1a2448c8265281bca1. Old archives and resource conditions
remain immutable; fresh controls do not restore blind validation status.

## Origin and candidate

Four counter-only cold gen2 D3/D4 calls, repeated in opposite order, match the
previous frozen full score/action/PV and node counts exactly. The D4 total
1,085,033 consists of 9,629 non-replay visits, 1,010,693 root tie-refinement
replay visits and 64,711 final selected-root replay visits. There are36 root
refinements and zero other replay visits. The expensive source is observed.

The private candidate keeps the full +/-INF exact-score confirmation with
pv_node=1, but uses normal search there instead of pv_replay=1. The final
selected-root canonical pass keeps encoded action order and suppresses TT score
probes. Root encoded tie choice, history, finite-depth TT score reuse, terminal
semantics and complete-iteration commitment are retained. Provisional candidate
PV is replaced by the final selected-root pass; losing candidates need no trace.

Eight paired D3/D4 cold calls preserve the whole tuple. D3 stays5,522 visits;
D4 goes from1,085,033 to342,036, about27.5 to13.1 caller seconds. Final replay
stays64,711. Non-replay includes the newly normal refinement work, so its
increase is a classification change as well as changed execution. Material
ordering nodes355 to2,841 and scored actions29,702 to225,221 increase actual
ordering time roughly0.60 to4.38 seconds. Fewer visits are not equal scoring
cost or a primitive-speed claim. Ordinary concurrent computer load is normal.

## Saved consumer delivery and resource plane

48 declared cold paired cells use six preselected full-history saved states,
min2 ordering,1MiB TT, maxdepth12,1M nodes and16/64seconds. No arm follows newly
selected actions. All24 reverse-order fulltuple pairs agree; all20 same-depth
between-arm comparisons agree. Onlygen2 changes:16s D3 toD4 and64s with1M D3
toD5 in both orders. Otherfive saved states have unchanged depth and tuple.
All returned PVs replay legally, roots restore and qnodes remain zero. Caller
search seconds sum1,269.364; this is compute cost, not the Agent segment time.

A separate predeclared eight-cell64s plane has max_nodes=None for both arms.
Gen2 both completeD5/-221; candidate about1.49M versusbaseline2.19M visits.
Shogi0 both completeD4/0, about2.02M visits. The previous1M depth gain depends
on the declared resource condition; this repair does not close the entire
Core/Native gap. Total counts include attempted incomplete next iterations.
Shogi's final canonical pass accounts for about1.9M visits, identifying a
different remaining cost. Do not infer that normal PVS alone solves it.

## Semantic value and abort checks

Dot's source-only review agrees with separating exact score confirmation from
PV generation, conditional on valid TT/context and complete-iteration commit.
Its useful objection: the final pass currently discards its returned value,
so legal PV alone cannot prove equality to the authoritative root score.

A counter-only private candidate verifies root best == -final branch whenever
an exact-root final pass completes. Gen2's independent fullD4 run gives four
checks, zero mismatch, identical342,036 visits and fulltuple. FirstD4 refinement
begins at node8,212 and ends22,714; final pass begins278,747. Before observing
abort outcomes, choose node budgets8,276 and278,811. They actually interrupt
refinement/final respectively and both return the previous complete coldD3
whole tuple. The refinement interruption has61 newly completed descendant TT
stores beyond earlier iterations. Retaining that same TT and retryingD4 without
clearing it gives the independent coldD4 whole tuple in both cases. Five calls
supply17 completed final-value checks with zero mismatch; full marker adds4.
This targets node-budget aborts; it does not claim phase-targeted actual cancel.
Existing cancellation regressions are separate evidence. No TT rollback layer
or new public API is introduced. Final-value equality uses search returns,
never substitutes literal material for terminal/history semantics.

The original38 relevant regressions pass on the private candidate. A new full-
history gen2 min2 integration regression requiresD4/-2619 within1M nodes and
matches all four canonical actions. Actual sensitivity executions: baseline
FAIL atD3, candidatePASS atD4. This is a node-completion/semantics regression,
not a wall-time speed threshold. The earlier old/new literal-PV correction
stands: both recorded literal leaves were-2514; -4912 was the old third action's
best-opponent residual value. Old evidence is not rewritten.

## Finite action projection and boundaries

At gen2 root/selectedchild Native canonical and cold Core generic order share
exactly the same77/116 legal-action semantic multisets, but different sequences.
This rules out missing-action projection only there; different order is not a
speed proof or permission to change required canonical tie semantics.

Sixteen fixedD4 gen2 factors preserve every fulltuple. With TT0, lexical
visits711,685 to708,676 but min2 goes1,085,033 to342,052. With coldTT1,
lexical697,244 to692,832 and min2 to342,036. Permitting existing material
ordering during score confirmation explains most of this local benefit;
TT score reuse contributes little here. No global min2 default follows.

The four prospectively declared generator seeds supply seven ongoing roots
at plies0/8: seed2026101201 naturally ends in checkmate atply1, with no
resampling.84 D2/D3 Native baseline/candidate/plain Core queries all complete.
All Native fulltuples agree across arms/orders;70 candidate root-final-value
checks have zero mismatch. Core nonmate values agree; mate sign/distance
agree after SOURCE-DEFINED unit comparison: Native terminal constant1e8 and
Core1e9. Raw scores remain unchanged; this is not raw-all-score equality or a
fitted scale. The reconstructed declared RNG walk adds no new search/game.

Eight cold Core flags-only64s calls isolate existing use_pvs. Both CoreAB and
CorePVS completeD5/-221 ongen2 andD5/200 onShogi0; reverse fulltuples agree.
Gen2 bothabout277-279kvisits; ShogiAB229k versusPVS240-244k. Actual Native
legality fallbacks are zero. Defer a new NativePVS kernel: this does not show
PVS required for the observedD5 reference. Native/Core order/cache/counters
still differ, so this is not an aligned primitive comparison.

A separate twelve-call PRIVATE naive replay-TT control retains encoded order,
but permits same-depth TT score probes on nonPV replay nodes. Root score/action
and final scalar checks agree in both orders, yetgen0 PV shrinks4 to2 actions;
Shogi0 retains length4 but changes its canonical line. Gen2 retains its tuple.
Reject this naive optimization despite fewer nodes: score equality alone does
not materialize or canonicalize a continuation. This negative control is
separate from the adopted score-only confirmation change; production final
replay still suppresses all TT score probes. No new public interface is added.
No human-price fit, strength claim, extra worker, default/UI change or q4 support
is inferred. The generic target still includes the complete generated rule and
state domain. These are finite, qualified diagnostics of a specific cost defect.


## Actual unfamiliar-rule caller budget

42 cold16s/1M cells on all seven saved prospective roots preserve21 reverse
fulltuples and14 same-depth Native between-arm fulltuples. No Native completed-
depth gain occurs in this cohort. Caller seconds sum549.980. Native/Core work
counts and output sources remain separate. Three roots have actual one-ply
terminal wins: independently replaying six Core choices confirms childcheckmate
and the mover aswinner. Core returns in about0.001-0.002s with reporteddepth0;
Native spends16s repeating deeper winning horizons on these roots. That depth
number is not a gain over a verified terminal action. A5ply win on another
savedroot is distinct and not classified immediate. Roots/method are exposed;
this is not statistical strength or full generated-domain validation.

The next cheap discriminator is whether Native's completed first iteration
already has the exact selected-child terminal proof needed for a safe scoped
early return. Check actual terminal/history/declaration semantics and caller
termination metadata before implementing it; score alone is not a general
certificate. Proper canonical trace reconstruction remains a separate question:
naive TT score reuse already fails, and a length check alone misses Shogi's
same-length canonical mismatch. No default/UI change follows from either idea.

## Delivery evidence

The optional exact-root production change uses normal full-window score
confirmation and keeps the existing final canonical pass.39 relevant production
regressions pass, including the observed node-budget completion test. Original
38 private checks and actual two-call sensitivity remain distinct; publisher
repetition is not independent validation. Source/archive closure:
[data/q0_score_refinement_20261012.json](data/q0_score_refinement_20261012.json),
236 scientific calls and two sensitivity calls,72 SHA-verified archive members.
Explicit Agent-only whitelist excludes binaries, compiler/private diagnostics,
raw Slack/account records and stop/session files. Fixed-revision collaboration
summaries are reviewed separately. Science remains OPEN.
