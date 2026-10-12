# Public q transfer and restored Shogi attribution — 2026-10-12

Science is OPEN. Source base: `4f3aa32bb587a670b5560c881a685340d6136706`.
This segment records212 completed primary physical search calls, plus one
unconfirmed interrupted attempt. Independent replay checks286 public PV actions.
Tests and pre-search protocol/refusal checks are separate. No AUX training is
launched, no UI/default flag changes. `data/public_transfer_20261012.json` binds
frozen producers/results, corrections, failures and the evidence archive.

## Decision-changing defect and repair

The actual existing whole-C q0 material caller supplied dynamic coefficients
`(0,0,0)`. C still computed the dynamic feature vector at each scored leaf.
The same mathematical leaf with an omitted dynamic term avoided that work.
Eight reversed completeD2 controls establish exact action, score, PV, nodes
and separately returned leaf features, before making a cost interpretation:

|Root|Nodes|Explicitzero before, two orders|Omitted before|Explicitzero after|Omitted after|
|---|---:|---|---|---|---|
|Shogi middle|1709|2.066/2.069s|0.058/0.058s|0.058/0.058s|0.058/0.058s|
|Shogi hand/drop|20165|33.516/33.567s|0.401/0.399s|0.396/0.400s|0.393/0.402s|

The narrow C guard skips scoring-feature extraction when all three coefficients
are zero. Nonzero coefficients, compact/spatial terms, input validation and
separately returned leaf metadata remain in their existing paths. The normal
Zig build succeeds; local binary434688bytes is hashed, excluded from Git. Two
new real-search regressions cover promotion and hand/drop roots, full legal PVs,
root preservation, equal decisions/work and reported leaf features. Existing
binding, nonzero/spatial/compact/ordering and root-mode tests also pass.

This fixes an observed caller cost; it does not claim all Native interfaces are
fast or that a Cq4 kernel exists. Actual q4 request to SemanticSearchEngine still
raises `ValueError: SemanticSearchEngine does not implement qsearch` before
recursion. Omitting a neutral term was already a caller remedy; the source fix
also makes explicitzero scoring avoid the unnecessary computation.

## Existing root-window option, not a new search implementation

After that repair,12q0 delivery calls with TT0 retain middleD3/handD2 at16s,
versus old explicitzeroD2/D1. Eight paired fresh0/1MiBTT controls give the same
support. TT1 allocates720896bytes with88-byte entries; middle300hits/hand84hits
and zero score cutoffs, despite about436k/820k probes. This particular cold TT
comparison does not justify a larger cache or an inference about warm engines.

The already repaired public exact-root-window option is advertised by the
current binary. No compatibility guard is bypassed.24 new paired OFF/ON curves
use fresh1MiBTT, the same neutral material profile, caps1M/maxD12, budgets
0.25/1/16s and both root orders. At16s ON completesD4 on both roots in both
orders; OFF retains middleD3 and handD2. These are q0 support curves, not
comparisons with a fullq4 evaluator. All have legal Core-replayed PVs.

Eight separate completeD2 controls establish equal action/value/PV before cost:

|Root|OFF nodes / seconds|ON nodes / seconds|Actual raw C tie refinements|
|---|---|---|---:|
|Shogi middle|1788 /0.061,0.060|348 /0.018,0.018|2 per ON call|
|Shogi hand/drop|20468 /0.392,0.395|769 /0.025,0.025|0|

No fixedD2 tie-refinement abort occurs. The public dataclass does not expose
these two raw counters; the finite producer transparently captures the actual
C return rather than interpreting absent fields as zero. Raw C counters are not
claimed for the earlier24 delivery rows. Their time-limited unfinished iteration
is distinguished from the last completed D4. Defaults remain full root windows.

## Public tuple q ordering is not universally beneficial

On predeclared generated1090 with actual auxiliary history, fourD2 controls
keep action/PV/value-3641/main1727. Existing weighted q ordering increases
q33120 to35504 and cost18.007/17.951 to19.703/19.715s. Four paired16s calls
retainD1/q0/value10 for both arms. The old positive1091 result does not transfer
as a universal option recommendation.

Moving the same proved quiet exclusion before sorting also fails: four complete
controls keep the ordered value/PV/main/q, but cost19.727/20.594 becomes
43.994/44.701s. Ordered actions drop944505 to151045 and ordering cost falls,
while mechanical action trials grow142632 to901845. Eager classification pays
for actions that the late traversal would never reach. Reject that route.

A q-only order-price ablation fixes leaf prices and main ordering. Returningzero
for q capture-order value keeps captured-category-first and lexical capture ties,
using the existing orderer. On1090 q35504 becomes28024 and19.87 becomes14.77/14.86s;
on1091 q12263 becomes14659 and4.70/4.73 becomes5.91/5.70s. Each root retains the
same exact completeD2 action/PV/value/main. Reject a global unweighted switch and
an exposed-root-ID selector; this is a genuine cross-rule priority tradeoff.

The original S4 fixture has empty hands and cannot establish active pawn-drop
prohibition coverage. A separate declared active hand position has69 candidates,
61 legal actions,54 legal drops and a real forbidden mating pawn drop. Core public
membership matches Native. FourD2 lexical/ordered calls give1928/main194/q95,
16 checking-drop q actions, no Native fallback/error and exact root restoration.
Four full-Core shadow controls validate748/719 proposed quiet exclusions percall
without changing the complete decision/work. This is finite S4/drop coverage,
not a complete Shogi/generated-domain certification.

One unchanged ordered1091 q4/hard8 call captures the first hard-limit path at
65.055s, preserving completedD3/value-230. Independent Core replay confirms all
12 actions, actual full history, final check with10 legal evasions and maximum
repetition count1. This is an intended finite check-extension boundary, not an
observed legality/restoration defect. Do not extend hard8 merely to finish D4.

## Restored mature Shogi entry and defined decision utility

A clean preserved official Fairy-Stockfish source revision
`9f778da667f6e07dae1e85d3e2ea204fc6dee94d` supplies LARGEBOARDS/ALLVARS.
The first build omits the upstream default PRECOMPUTED_MAGICS and times out at
the10s handshake. Inspecting Makefile/initialization identifies the normal flag;
a separately rebuilt binary starts and actually searches full9x9Shogi. USI uses
USI_Variant/USI_Hash, not the guessed UCI option name. Eight250ms existing-root
searches return legal bestmoves and replayable PVs, including promotion/drop and
played history. Owned engines close. No repeated old unsupported launch or user
security-setting intervention is needed. Binary/source/archive hashes are bound.
[Fixed official build source](https://github.com/fairy-stockfish/Fairy-Stockfish/blob/9f778da667f6e07dae1e85d3e2ea204fc6dee94d/src/Makefile).

This mature reference uses classical evaluation with NNUE disabled and its own
pruning/draw/declaration policies. It is not the shared arbitrary material leaf.
Nominal tacticdepth245 has seldepth2/mate1; middle repeats differ in bestmove and
one upper-bound score. Do not treat nominal depths as genericq4 work or compare
its scalar scores as material-only controls.

A60-cell two-root0.25/1/16s bridge separates identical bare minimal AB on Core,
Native-legality Core and cshogi from actual public PVS q0/q4. The common fixed
Material coefficients are arbitrary controls, not fitted human prices. Minimal
and public algorithms/node definitions/TT/order differ. At16s middle minimal
Core D4 versus cshogiD5; public q0/q4D4. On handroot, public q4 retainsD1/q0
king5i4i/value700 while publicq0 completesD3/R*1g/value900. cshogi can hit1Mnodes
before16s; actual termination/work limits are reported, not renamed equal-time.

Six8192-node diagnostic controls isolate that handroot: raw/quiet both stop at
node_limit, main537/q7655, retaining the sameD1/q0 king700. Quiet reduces about
5.1 to3.45s but does not completeD2. Existing capture-onlyq4 changes inclusion
policy and completesD2/main1091/q2576/R*1g900 at2.81/2.76s. No checking move/drop
continuations are included in that arm; it is a behavioral ablation, not an
identical-support speed gain or a production recommendation.

Twelve independent forcedD3/q0 branches use identical full-window minimal AB
and full histories on Native-legality Core/cshogi: king5i4i scores700; R*1g and
R*1a score900. Another twelveD4 branches agree in values, work and trace hashes:
king5i4i=500, R*1g=900, mature reference R*3b=500. These are restricted branch
values under this defined shallow material criterion, not a whole-root optimality
certificate or WDL/strength judgment. Native exact-windowD4 delivery selects the
900 rook action; its conditional advantage over the retained king is400 atD4.
The mature move's lower shallow score does not establish that its deeper,
different evaluation chose incorrectly.

## Failures, declaration corrections and next selection

The original bridge exits1 after24 completed cells without a returned diagnostic
traceback. Cause remains unknown. One isolated16sq4 cell with faulthandler/full
logs succeeds, then35 remaining declared cells complete with attempt records.
The60 unique cells are covered, plus one unconfirmed interrupted attempt; this
is not an uninterrupted same-batch timing experiment. Original partial output
and source are preserved, not rewritten or presented as a clean first run.

Source-derived declaration copying retained some contradictory top-level fields:
fixed neutral/root controls say maxdepth12 although the actual call fixes2;
TT/root ablations retain TT0/windowOFF prose although actual calls and result
fields specify their paired modes. Original declarations remain immutable;
corrections.json pins the exact mismatch and actual source/result evidence.
These exploratory controls are not blind holdout data. Producer import/type,
verification and sandbox-WAL/Git failures and successful remedies are recorded;
no security block or scientific completion is inferred from them.

Select the corrected neutral-term caller and already-supported exact-root q0
option for further scoped consumer comparison. Fullq4/checking-branch support
remains a different problem: transport alone fails to complete this handroot,
and q-only prices have opposed cross-root effects. Keep UI/default policy frozen.
Next use one explicit consumer/q-support requirement to distinguish bounded
checking continuation from existing q0 material service before proposing a Cq4
kernel or new API. AUX retains its independent training/validation lane.
The next checking-support step has actually begun: one additional instrumented
8192-node call captures a real nonterminal rook checking drop at parentply2.
Independent Core full-history replay validates that full noisy classification
retains it while capture-only excludes it. This is an inclusion witness, not a
score/strength gain. Its equal-context continuation-value check is the next memo
Main, rather than an assumption that either profile solves the whole problem.