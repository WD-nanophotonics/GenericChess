# Actual UI search diagnostic and fixed-trigger cost

2026-10-10; exposed development evidence, not Elo/WDL or an original user-game
reproduction. Direction and operating policy remain in LOCAL_MAINLINE.md and
AGENTS.md. Source/raw records: data/ui_product_20261010.json and its archive.

## Actual product path

Pin remote ui-test99c97bb87474c44af94c76571f326ef8a41eb898. The original
ced72 handoff differs: the later UI adds the teaching material profile. An
isolated tracked export and locked dependencies execute actual WebGame capture,
AI choose and final controller commit. All243 generic_chess source files match
Git archive bytes. Publish only these hashes and Agent-produced records;
user-authored UI source/dependencies/raw Slack/account records stay local.
This tests service/controller, not rendered browser, HTTP or event latency.

Two predeclared start-position games, exchanged UI colors,32plies or terminal;
one-second requests. The actual Core-only UI keeps a persistent player/TT,
root tactical scan, ordering, ordinary q4/hard8 and dynamic evaluator terms.
Its recorded teaching table is P1000,N/B3000,R5000,Q9000; this diagnostic does
not fit the rule-only formula to that human table. The bare python-chess
alpha-beta comparator uses the same material but no dynamic terms/TT/q/order;
backend and algorithm differences are explicit, not a strength control.

The games finish28plies/checkmate and32plies/external cut. All30 returned UI
actions equal committed actions;24 complete onlyD1. Two queen captures take a
pawn then lose the queen to a bishop, net8000. Captured complete-history parents
have an independently complete finite materialD2 alternative; chosen queen
captures have regret7000 under that deliberately limited oracle. Direct-loss
flags on later already-lost boards are not all classified as avoidable errors.
The original user's missing game record is not substituted by these games.

## First-completion mechanism and candidate boundary

The source temporarily sets ordinary qdepth to0 before the first complete
main iteration, then restores configured q. If deeper iterations time out, the
selected completeD1 may retain this approximate greedy result. Changing q4 to
q1 alone preserves both queen losses at1second on frozen and current backends.
Complete q0D2 avoids them in0.136/0.190seconds frozen; q4D2 takes3.476/5.004.
The earlier indexed sandbox reduces q4D2 to2.393/3.391seconds but retains the
one-second failure. State/evaluation/commit are distinct from completion.

An isolated diagnostic changes only the first ordinary limit to min(1,q).
Across all30 captured cold parents, finite material regret improves8, worsens1,
ties21; means966.7->166.7. The adverse1000 row remains. First-completion latency
means18.8->114.6ms, maximum250ms; original depths21/7/2 versus20/8/2 forD1/2/3.
Four capped5second q4D2 references remain UNKNOWN;26 complete. Original warm
UI records remain separate from cold replays. First-q4 checks on the two known
loss parents also avoid them but do not establish affordable general coverage.

Dot recommended retaining first-q1 as diagnostic-only and checking starvation.
One highest legal-frontier root among eight existing controls is Shogi-drop;
one existing generated4x4seed21 root adds unfamiliar coverage. Two reversed
one-second pairs each retain a completed iteration; the generated root endsD2
at the unchanged qsearch_check_hard_limit. Four deterministic cancellations
beforeD1 return legal incompleteD0 fallback and restore root/history. Selection
by legal-frontier count was initially only a proxy. A later exact generic noisy
selector instead chooses Shogi-tactic21noisy versusdrop18. The corrected four
one-second calls also finishD1 and both cancellations restore state/returnD0;
original proxy results and the initial archived-path error remain. These finite
passes do not guarantee arbitrary-rule safety.

A changed-budget check is decisive: on the two same saved parents, at50/100ms
baseline completesD1 but first-q1 completesD0 in both; at25ms one baseline still
completesD1. Returned fallback is not relabeled completedD1. Thus no unconditional
first-q change is installed, even though one-second exposed regret improves.
Next ask how limited tactical coverage can respect a completion reserve; keep
configured q0 semantics, generic actions and one total live budget. No Chess
position patch or additional proof/Elo gate follows.

## Mechanical trigger dispatch

Profiled q4D2 spends overlapping time in legal generation, terminal probes,
trial transitions, identity and checkpoints. Two roots perform62851/42005
transitions and754212/504060 trigger predicates. Profiled wall is about2.8x
ordinary wall; cumulative times overlap and are not disjoint attribution.

An engine-owned fixed-square event index regresses ordinary fixed cost16-21%:
plans rebuild73611/55347 times. Preserve this failed ownership attempt, including
two constructor-bypass fixture failures. Exact compiled-object amortization
changes the premise and yields11-13% local reduction with identical completed
choices/scores/PVs/main/qnodes. The installed version derives metadata once on
CompiledSemanticRuleset; replacement rebuilds it. No global position/rule cache.
The western metadata has24 entries and about5174 recursive Python bytes.

Fixed event/square/owner filters now dispatch matching clears directly; dynamic
square references and compile-only carriers keep original traversal. Static
and dynamic trigger writes all clear slots and commute; explicit auxiliary
writes still execute afterwards in declared order. Events/entries keep live
cancellation checkpoints; the empty-trigger route avoids a no-op helper call.
No game name, piece-specific exception, evaluator change or Native ABI change.

Eight builtin root audits retain1394 child states/40 legal frontiers. A separate
remaining generated semantic lowering retains30/5: total1424/45. The inspection
IR was not executable; no capability flag was bypassed. Shogi-drop stays capped
atD1 under the same q2D2/5second limits; generated and completed controls retain
finite signatures. Independent owner/scope/relative-coordinate, dynamic fallback,
replacement, explicit write-after-clear and cancellation tests pass. Full1897
active regressions pass; final publisher checks validate current source.

Two installed fixedD2 repetitions retain work and take about2.89/2.08-2.13seconds
versus3.31-3.34/2.35-2.37 controls. On the fixed30 cold1second indexOFF/ON cohort,
D1/2/3 changes21/7/2->18/10/2. One material-loss choice improves,29 tie, none worsen;
mean finite material regret966.7->900. Both queen failures remain. This supports
scoped useful execution savings, not claiming the basic-error policy is fixed,
engine parity or broad playing strength. UI branch remains unmodified.

## Recovery and limitations

Retain initial runner root-bookmark error, empty-profile success-looking attempt,
missing-test target, constructor-bypass probe failures, temp permission/missing
parent failures, read-only session property and inspection/generated-lowering
errors. Corrected harnesses complete their declared populations; failures are
not rewritten. Earlier checkpoint arithmetic is corrected explicitly by later
checkpoints. Old caps are not expanded.

The archive retains exact actual UI runner, profile/full-first-q and final source
versions. A few earlier replay/population version bytes were overwritten before
capture: their recorded original hashes/outputs remain, but exact source closure
is incomplete. No claim of byte-exact old recovery. Paths in JSON are normalized;
original local hashes and transformed member hashes distinguish this operation.
Use the current three CLI diagnostics in scripts/ for new declared checks;
failed and amortization prototype code belongs in the archive, not product imports.
