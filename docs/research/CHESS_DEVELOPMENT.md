# Runnable Chess development comparison

The initial implementation combines the existing material candidates with the
production `run_root_search`; rules and search are unchanged. `geometric_half`
is the declared default candidate, `unit` and `linear_mixture` the controls.
This entry is Chess only; generic-rule strength remains an open objective.

The first batch uses all24 Bratko-Kopec cases in original order with their
existing `bm` answers, converted by the already verified python-chess1.11.2
parser before any candidate run. Source and raw-file SHA256 are in the suite.
Source: https://github.com/niklasf/python-chess/blob/3516d7c6c0879af724c2855fac5a304a4ef40949/examples/bratko_kopec/bratko-kopec.epd
No fitting, candidate-based filtering or independent-holdout claim.

These include positional questions. A reference-answer miss is not automatically
a proven tactical mistake: the source best-move set may not enumerate every
acceptable alternative. The first batch reports reference agreement and paired
candidate-only/control-only hits; exact errors need case-specific evidence.
Execution failures (including incomplete depth) are separate. Record actual
nodes, wall/CPU time and selected moves; unlike internal scores, these are
comparable observations. Source answers and ties are never changed after results.

Initial shared configuration: depth2, q0, no TT/ordering/root-tactical fallback,
2048 total-node fuse and1second/move. These are finite development conditions,
not claims that deeper search is unnecessary. A later changed condition must
be declared and run for all methods, preserving this result. Do not extend
this batch until it happens to favor a candidate.

```
.venv/Scripts/python.exe -m scripts.chess_development compare --suite docs/research/data/chess_development_suite.json --output .local_agent/chess_development_compare_01.json
.venv/Scripts/python.exe -m scripts.chess_development play --suite docs/research/data/chess_development_game_starts.json --output .local_agent/chess_development_games_01.json --max-plies 40
```

The short-game starts were declared before comparisons: native initial position,
BK.01 and BK.19. Each candidate/control pairing plays both colors, using the
same search config. A40ply cutoff is unfinished, never silently scored as a
draw. A legal fallback may be played, but incomplete search is flagged.
No pass-all prerequisite to games. These small games do not establish Elo or
amateur strength. Outputs refuse overwrite and retain progress per case/move;
Ctrl-C preserves a partial record. No network/model calls occur in the runner.

Observed failure-driven followup, declared after the original results: BK.01
geometric Black plays Bd7-a4 and loses to Qa7+, Kc8, Qb7# in the actual game.
Check one existing quiescence config (depth2/q2,8192nodes/2seconds) across all24
original cases and all12 original short games, rather than cherry-picking a
successful root. The old q0 producer/results are retained. This is development,
not a new holdout; compare costs and incomplete searches, not only hits.
Qsearch's known en-passant classification limitation remains disclosed; this
test does not certify every descendant or fix it. Do not change coefficients.
First q2 run coupled the check-evasion hard limit to2;23/24 per method failed
to complete (mostly hard-limit aborts), rather than providing valid price errors.
Preserve that result. Set the independent check-evasion hard limit to the
existing SearchLimits default8 and repeat the declared batch, then the games;
do not waste12 game runs on the demonstrated unusable hard2 configuration.

Restored the already installed Zig0.16 toolchain's supported native build;
q0 native legality gives exact action/score parity on all72 original searches
and reduces aggregate search wall from16.87 to10.26seconds. It is a throughput
change, not coefficient improvement. Native tests34pass/1blocked by existing
cshogi Application Control; do not bypass that system restriction.
The q2/hard8 Python/native batches still have many unfinished searches at2sec.
A BK.01 feasibility check with existing common ordering and a fresh TT reaches
depth3 but not4 at2seconds for all methods. Next declared playing config is
depth3/q0/native, shared frozen geometric capture-order prices, fresh65536entry
TT,32768nodes/5seconds. Run all original24 cases and12 short games unchanged;
report actual completion/cost and mate behavior, not just favorable examples.
No search-feature throughput gain is attributed to material coefficients.

External reference followup: use the official fixed Stockfish17.1 Windows
generic x86-64 archive (65,440,867bytes), not a model/worker. The existing verified
python-chess1.11.2 UCI module communicates with one local process: Threads1,
Hash16MiB, fresh game/hash for each analysis,50,000nodes per unique selected
move/reference answer. Analyze all24 original cases' depth3 selections/answers,
without changing either. These limited standard-Chess child scores are noisy
independent proxies, not exact regret/WDL or the project's finite-goal semantics.
Do not fit/select coefficients from them. Acquisition and full outputs stay local.

Observed initial-game wandering motivates one shared-dynamic ablation. Keep
the full depth3/native/TT/common-order condition fixed and add only the existing
Evaluator mobility2 and anchor-escape5/check terms to all methods. Disable its
separate material/hand/promotion-gain profile with zero tables; material prices
stay exactly the frozen candidates. Multiply the residual by100 to align its
Queen1000 units with this candidate's Queen100000 scale. This explicit provisional
scale is not label-fitted or a new theoretical claim. Run all24 unchanged cases
and12 same short games once; preserve worse and equal results too. No coefficient
or residual-weight search. Existing raw-material results remain the control.

After the shared-dynamic comparison, run its12 predeclared internal games.
Additionally declare6 paired-color games from the initial position against
the same Stockfish17.1 process, Threads1/Hash16, UCI_LimitStrength true and
UCI_Elo1320,50,000nodes/1second per opponent move. Local methods all use the
same depth3/q0/native/TT/shared-order/dynamic configuration,32768nodes/5sec,
with80ply truncation. The strength setting is not a calibrated rating at this
budget;6 games provide failure feedback, not an Elo estimate. Stockfish's
stochastic weak-move choice and standard-Chess draw/search assumptions are
limitations. Keep board/actor alignment and the local authoritative terminal;
do not tune any price/weight from the result. No pass-all or dot-reply gate.

## Observed development results,2026-10-06

One portable result file, `data/chess_development_results_20261006.json`, preserves
all declared conditions/summaries, selected moves, finite child references and
all48 actual game move lists. Full search statistics, histories and original
producer versions remain in ignored local records; raw-file hashes bind them.
No production search/rule/price source was changed. The common runner now also
checks UCI board, actor, raw EP target and castling-right alignment.

| Fixed24-case condition | Geometric hits | Linear hits | Unit hits | Completed searches | Aggregate search wall |
|---|---:|---:|---:|---:|---:|
| Depth2/q0/Python |0|0|0|72/72|16.87s|
| Depth2/q0/native |0|0|0|72/72|10.26s|
| Depth3/q0/native/shared order/TT |4|3|1|72/72|54.06s|
| Same depth3 plus shared dynamic residual |2|2|3|72/72|104.52s|

The depth3 material candidate/unit paired reference hits are3:0, linear1:0.
Dynamic candidate/unit paired hits instead1:2. These are answer agreements,
not certified error rates or independent validation. Do not promote the richer
dynamic combination automatically. Its unchanged existing weights cost nearly
twice as much here and have mixed finite-reference changes: geometric8better,
9worse,7equal versus the material selections; linear9/6/9, unit10/8/6.
No coefficient or dynamic-weight fitting followed these exposed results.

Fixed Stockfish17.1 full-strength child references used62 unique material
analyses, then33 new dynamic children and36 identical cached references, each
under the same50,000-node condition. Examples establish useful distinctions:
BK.12 geometric Bf5 has+18cp versus unit Qxc3 -822cp; BK.14 geometric Qe1
+536cp versus unit Bxc3 -19cp. But BK.09 candidate Bb5 has+265cp versus the
declared answer f5 +242cp. Therefore a nonmatching move is not automatically a
blunder. Scores are finite standard-Chess proxies, not exact regret/WDL.

Internal games: initial q0 condition3mates/9unfinished; deeper material
1mate/11unfinished; shared dynamic4mates/8unfinished, each12 games/40ply.
The deeper and dynamic batches have no incomplete searches. These games reveal
behavior and actual mate, without a statistically justified ranking.

Six external games use the predeclared limited-strength setting and80ply cutoff:

| Local method | White | Black | Full local searches |
|---|---|---|---:|
| Geometric |unfinished80ply|win76ply|78/78|
| Linear |win71ply|unfinished80ply|76/76|
| Unit |loss48ply|win72ply|60/60|

All48 games/2008played moves replay with identical author-library legal sets,
boards, raw EP and castling rights. Actual terminal mates agree. Unfinished
games are not draws. The weak engine's stochastic choices, two games per method
and node/time setting prohibit an Elo/amateur-strength claim. Full-strength
postgame analysis covers all214 Agent moves, preserving bad decisions in wins
as well as losses. E.g. geometric Black f7f6 has a529cp finite-reference drop;
winning a game does not excuse that failure.

BK.01's source-suggested Qd1,Kxd1,Bg4+,Kc1,Rd1# line legally reaches local
mate at ply5. This is one verified line, not a complete defense certificate.
A shared10second/131072node/depth5 probe on this observed failure completes
pure-material unit in8.88seconds and chooses Qd1; geometric/linear complete
only depth4, and all dynamic runs fail to finish depth5. This points to horizon
and cost, not automatic coefficient superiority. Keep the unfinished results.

One actual played EP opportunity (external game2, ply27, h4g3) is omitted by
the current qsearch noisy classifier. A local off-target enemy-removal prototype
includes it and preserves the complete root/history identity. On this particular
q1 material state the score stays28539; correctness coverage is not a proven
utility gain. Main games use q0, so the omission did not invalidate their search
condition. Repair both ordinary and runtime paths together before relying on q.

A local delayed-generation feasibility hook avoids generating noncheck qnode
legal moves before stand-pat/qdepth cutoffs. All18 shared completed searches
retain action/score; the72-search timed probe completes6/5/10 versus6/5/7.
Timed completion is observational and some other local jobs overlapped. A separate
alternated fixed1024-node BK.01 control retains321 main+703 qnodes, the same move,
score and node-limit reason, while generation calls fall703to209 and observed
wall~1.37to1.21seconds. This hook is not a production patch or strength improvement.

Next work is driven by these actual failures: integrate a minimal correct capture
classification/performance repair with focused regressions, then compare a useful
fixed search horizon through this same entry. Keep the exposed suite and game
results; do not grow a proof/admission framework or refit prices to its answers.

Before ending this segment, declare an additional six external material-only
controls: same initial root, all3 methods both colors, same depth3/native/q0/TT/
common-order32768nodes/5sec, same weak-opponent1320/50knodes/1sec and80ply cap.
This fills the missing raw-material counterpart; it does not rerun/overwrite the
dynamic games or change prices. Opponent weak-choice randomness prevents matched
move streams or strong causal/strength inference. Preserve all six outcomes.
Completed material-only counterpart: geometric White loses34ply/Black unfinished80;
linear White unfinished80/Black loses47; unit White loses50/Black loses37.
All163 local searches complete. Thus material4losses/2unfinished versus dynamic
3wins/1loss/2unfinished; this limited observation favors retaining the shared
activity playing option despite worse tactical-reference agreement. Keep both
conditions explicit, rather than tune prices or claim statistical superiority.
The dynamic sample alone supplies the214-move finite postgame analysis above.

## Followup declared2026-10-06 q repair

Production qsearch now conservatively recognizes enemy board removals, including
off-target captures, in immutable/runtime paths. Capture the parent count before
the mutable push. Noncheck qdepth/stand-pat exits avoid unused legal generation;
in-check nodes retain all legal evasions. Focused regressions cover the actual
EP fixture, positive material score/full root restoration and zero unnecessary
generation. Net enemy-board decrease is a conservative additional signal; it
does not certify every compound removal/spawn or custody effect in arbitrary
rules. Old frozen reports retain their original source hashes/results;
two original producer files are compressed as inert byte evidence under
docs/archive/development_before_20261006_qfix. Historical tests validate those
bytes explicitly, not a claim that the current search is the old producer.

First full24-case same2sec/depth2/q2 native condition after repair completes
6/5/8 versus original6/5/7; no reference hits. This small repair does not by itself
make q2 usable as a default. Before observing the next batch, declare practical
depth3/q1/hard8, native/shared-order/TT/shared-dynamic,65536nodes/10sec across all
24 original cases/all3 methods. Unknown: can repaired q1 provide concrete useful
choices with affordable complete searches? Outcomes inform whether to try q1
games or keep q0 while diagnosing cost. Maximum12min/single local process;
save every incomplete/worse result, without price/label tuning. Old caps stay.

Completed repaired q1 batch: geometric/linear/unit complete6/6/14 of24, with
zero reference hits;46 time-limit failures are separate. Aggregate588.780sec,
324617 main+q nodes and1559123 runtime pushes. Both classifiers also now include
the actual played h4g3 EP opportunity, retaining score28539 and full root/history.
Keep q0 as the practical playing condition; a broader q default is not supported
by these observations. Old18 jointly complete q2 action/score pairs are unchanged.

Next declared failure probe: reconstruct external dynamic geometric Black game1
through its first9 actual plies, preserving history, then compare all3 methods
at depth3/4/5,q0,native/shared-order/TT/shared-dynamic,65536nodes/20sec.
The played f7f6 has an exposed finite reference drop529cp; the question is
whether deeper search changes it affordably, not fitting prices to that reply.
Nine searches at most3min, sequential after the full-suite q1 batch.

This complete probe reproduces f7f6 for geometric/linear atdepth3; unit instead
chooses b4c3. Allthree complete depth4 and choose f7f6. Allthree depth5 runs time
out20sec, retaining completed depth4. Independent finite played-history child
scores at50knodes give b4c3 -114cp and f7f6 -599cp from Black's perspective.
This is a real exposed horizon/evaluation problem even in an eventual won game,
not an argument for tuning the candidate to that move or claiming exact regret.

The runner also exposes the existing PVS switch without changing defaults.
Declare a separate full24-case depth4/q0/native/shared-order/TT/shared-dynamic
comparison at65536nodes/10sec, PVS off then on, all3 methods unchanged. Its
decision is whether the existing search feature makes completed deeper searches
cheaper/useful. Report search effects separately from price effects and preserve
incompletes. Two interruptible72-search batches at most24min; do not extend the
same condition on unfavorable results. This is exposed development, not holdout.

Completed PVS comparison: off17/19/24 complete versus on19/23/24; source hits
remain3/3/2. All60 shared completed actions/scores are identical. Their main
nodes fall592841to500632 (~15.6%) and observed wall343.758to300.291sec (~12.6%).
Six additional searches complete, none lose completeness. Full-batch wall
463.690to413.809sec; cost evidence supports the explicit PVS playing option,
not a price improvement or a global default change. Both runs bind identical
producer hashes/conditions except the declared switch. Finite deeper misses
remain, and alternate acceptable source moves are not automatically errors.

Observed played-history overhead supplies a further changed premise: the runner
uses explicit default auxiliary slots in the fresh initial FEN, whereas Core's
canonical initial position omits them. Stable public identity is equal, but
exact reconstruction from canonical setup fails; played imports therefore use
opaque historical SHA bridges and lose TT eligibility. Never drop those records.
Here eligibility refers to the runtime history flag, not a claim that every
ordinary Western-Chess TT probe is disabled; its applicable probes still run.
Declare the same9 played-depth probes with Core-produced position witnesses
retained from each actual prefix transition via the existing private search
entry. Verify every witness/public identity, history/root preservation and
zero opaque child hashes. Same methods/depths/nodes/time; maximum3min. This tests
the runner's history handoff, not a price change or a broader Core rewrite.

Witness probe completed: all6 complete depth3/4 rows keep exactly the same
actions/scores/main-node counts and full root. All3 depth5 runs still time out
at20sec. Opaque child SHA calculations fall122376to0 and all10 actual prefix
witnesses are available, but complete-row wall is slightly slower, not faster
(geometric depth4,7.627to8.017sec; linear7.206to7.643; unit5.381to5.688).
Retain the matching GameSession-style handoff as correct information reuse,
without a performance claim or weakened repetition/terminal rules.30 relevant
runner/tuning/history-context tests pass. Intermediate PVS runner/pre-LF patched
q source bytes also reside inertly in the same archive for exact raw bindings;
their provenance is a working snapshot, distinct from the original9ff920e files.

Declare the ensuing playing check, after the search/handoff regressions:
same initial root, all3 fixed methods both colors, existing shared dynamic
terms, native/common-order/TT/PVS,q0,depth4,65536nodes/5sec,80ply limit, same
limited-strength Stockfish1320/50knodes/1sec opponent. Six games, at most20min
local Agent-search time, one interruptible local process. Unknown: does the
repaired history handoff plus supported deeper configuration produce affordable
actual play, or frequent incomplete choices/tactical losses? Preserve all wins,
losses, unfinished games and fallback searches; no Elo/causal comparison with
the earlier stochastic3ply games. Do not tune prices or require pass-all tactics.

Completed six4ply playing cases: geometric White loses78/Black unfinished80;
linear White wins63/Black loses75; unit White unfinished80/Black loses71.
One local win/three losses/two unfinished,447 played plies, all author pushes
and board/side/rights/raw-EP align.223 local choices include104 complete4ply
searches and119 time-limited searches whose last complete iteration is3ply.
Local search wall911.759sec; every runtime restores balance and has zero missing
witnesses/opaque child hashes. This condition does not justify replacing the
cheaper3ply playing option: its depth target is often unmet and observed outcomes
are mixed. Different stochastic opponent lines/preexisting3ply samples do not
identify a causal strength effect. Preserve these unfavorable results.

Failure-driven local trace explains the f7f6 horizon: after Whiteg3,40 of41
legal Black replies admit an immediate legal capture of its Queen. The exception
Bxc3+ is a checking intermezzo; Whitebxc3 leaves36 Black replies, all admitting
a Queen capture.176 actual public transitions preserve the complete prefix.
This supplies a scoped White Queen-removal strategy within6 halfmoves from the
original root, not a full material/WDL certificate. It explains why the complete
4ply PV (f6,e5,Bxc3,bxc3) can prefer a shallow alternative to the trap; no missing
move or price fitting has been established.189 prefix/branch/capture states
match independent python-chess and native/public legal sets and boards. The
short mechanical audit overlapped part of the playing batch; game latencies
remain observational, not an isolated hardware performance comparison.

Declare a targeted descendant check after the six games: reconstruct the actual
f6,g3 prefix with all12 Core-produced witnesses. Compare shared native/order/TT/
dynamic/PVS under (main4,q0),(main3,q0),(main3,q1),(main3,q2), all3 prices with
65536 total nodes/20sec/hard8 each. At most12 searches/4min, all results retained.
Unknown: does an extra ordinary ply or tactical q extension expose the delayed
Queen removal affordably here? The earlier full-suite q failure does not forbid
this changed-premise diagnostic; no return to unexposed validation or price
tuning. Different horizon types are resource/result observations, not matched
price superiority. Reference each unique returned child at the existing finite
50knode condition, keeping disagreement/incompleteness visible.

One final finite-reference followup uses the same24 original cases and the
completed PVS-on choices, reusing only identical engine/condition/FEN/child cache
entries from the existing dynamic3 report. Unknown: are newly completed deeper
choices useful or just complete? All source children remain finite standard-
Chess proxies; keep all cases, original answers and misses, no requalification.

The targeted12 searches all complete. Main3/q0 picks Bxc3+ and still reports
positive material scores; ordinary main4 and main3/q1 expose large negative
geometric/linear scores and select Qg5. Q1 costs6.045/5.429sec versus ordinary
4ply5.585/4.900sec here, no clear saving. Unit selects Qxh2 at4ply/q1; the finite
child proxy is -717cp versus Qg5 -611cp. Q2 selects Bxc3 for geometric/linear and
Nc6 for unit, with finite proxies -645/-685cp; all are losing-score proxies,
not exact utility. This confirms a meaningful horizon effect without certifying
a globally better q setting.24 new PVS-child references reuse41 identical cached
analyses; BK01 unit retains the source mate line while geometric/linear retain
negative finite alternatives. Cost/completeness gain does not imply tactical gain.

One portable followup file data/chess_development_qfix_results_20261006.json
retains all declarations/outcomes/selected moves, full game move streams and
raw hashes. Per-move game telemetry stays in the untouched local raw run;
the portable file uses per-game aggregates rather than duplicate private counters.

## Capture-risk development continuation2026-10-06

Before outcomes: test a fixed half-discount of material that is semantically
pseudo-attacked and not pseudo-protected. This is an explicitly approximate
leaf residual, not legal exchange value or a calibrated loss probability.
Use the existing semantic attacked-square API, without changing side/history;
legacy movement-atoms omit Western Pawn capture rules. Native/Python semantic
agreement and Pawn/pin/EP scope controls precede the first search. Pins, checks,
recapture sequences, off-target removals and postconditions are omissions.
All three inventory candidates receive the same declared law; no Queen-specific
condition, human-price tuning, answer fitting or new holdout is introduced.
Measure native packing/query overhead on the actual played trap and selected
declared controls. If feasible, compare risk off/on at shared3ply/q0/native/
ordering/TT/PVS/dynamic conditions on the original24 cases, plus the exposed
actual prefix. Keep every failure and finite source-proxy limitation. This is
development, not a requirement that every prototype first prove exact WDL.

Followup declared before game outcomes:12 short external games, all three
unchanged inventory policies, both colors, risk off/on. Shared3ply/q0/PVS/
native/order/TT/dynamic,32768nodes,5sec,80plies; Stockfish17.1 configured1320,
50000nodes/1sec,Threads1/Hash16 and original initial position. Weak-choice
randomness and only one game per cell prevent causal strength/Elo inference.
Keep terminal versus unfinished, completed search depth and all move streams.
No answer-agreement pass gate is imposed before playing. This costs at most
2400 local-search seconds plus bounded opponent/transport, normally much less;
single local process, progress saved, interruptible. The decision is whether
the residual merits further playing development rather than default promotion.

Check-only followup declared before its searches: preserve qdepth0 default,
add opt-in entry to the existing bounded qsearch only when a static leaf is
in semantic check. It searches all mandatory evasions (including quiet ones)
and stops at the first noncheck static leaf; no ordinary captures are added.
Existing hard check depth, node/time, cancellation and terminal gates remain.
Test checking and nonchecking leaves, terminal priority and hard-limit aborts.
Compare all24 at identical3ply/q0/PVS/native/order/TT/dynamic32768nodes/5sec,
risk off/on, with the earlier no-extension records retained. No selective
answer changes. Then compare ordinary4ply versus check-only4ply on all24 under
the same32768node/5sec condition to learn depth/completeness/cost tradeoffs,
risk off in both. This is a resource curve and new explicit feature, not an
extension of old frozen failed q1 experiments or changed success criterion.

The advisor's same-thread followup is adopted: primary interpretation is risk
OFF ordinary q0 versus risk OFF check-only, one changed search feature. The
already declared combined risk-on observations are exploratory, not a common
repair or prerequisite. Five discrepant selected PV leaves do not estimate
the incidence across search nodes. Dot reviewed reported evidence, not local
code execution. No new attacker interface is required for this next action.

Playing followup declared before outcomes: six check-only/risk-OFF external
games, original initial start, all three policies and both colors. Keep the
same3ply/q0/PVS/native/order/TT/dynamic32768nodes/5sec/hard8/80plies and pinned
1320-limited Stockfish50knodes/1sec/Threads1/Hash16 opponent. The earlier six
risk-OFF games are retained as descriptive comparison, without rerunning them
or claiming stochastic opponent choices are paired. Unknown: do mandatory
evasions expose new practical failures or reduce those already observed?
All outcomes, incomplete searches and full histories remain; no Elo/default
promotion claim. Expected a few minutes, worst1200 local-search seconds;
single process, interruptible progress, no external worker/model/cost.

One deterministic playing complement is declared before outcomes: existing
`play` entry, initial start only, geometric versus linear and versus unit,
both colors (four games), check-only ON/risk OFF, otherwise identical3ply
conditions above,80plies. This changes the search premise of older internal
games. Unknown: do price-dependent trajectories survive the common evasion
search, and do terminal/repetition paths remain aligned? Report all outcomes
and moves, not a rating or proof from winning against another weak candidate.
The geometric/linear pair and color reversal help distinguish unequal prices
from a single stochastic external-opponent trace. Expected several minutes;
maximum1600 local-search seconds with saved interruptible progress. No result-
driven retry or escalation of a frozen test is involved.

The risk experiment completes144/144 paired3ply searches. Hits change2/2/3
to4/2/2 (geometric/linear/unit), while observed aggregate time rises84.711
to102.114sec. Finite50knode child-score pairs are mixed: geometric8 improve,
6 regress,9 equal; linear5/8/10; unit9/7/7, plus one mate-valued pair each.
BK12 geometric regresses559cp and BK14 geometric/linear549cp. The actual
prefix changes geometric/linear from f6(-599cp finite Black child) to Ng6
(-152cp), but unit changes Bxc3(-114cp) to Qxh2(-690cp). A concrete legal
Ng6,g3,a6,gxh4,Nxh4 trace still trades Queen for Pawn: Boolean protection
misses exchange magnitude. This is a mechanism counterexample, not a forced
opponent strategy or exact utility. Risk remains an optional approximation.

All12 risk off/on games complete their declared horizons: off2 local wins,
1 loss,3 unfinished; on0 wins,1 loss,5 unfinished. All837 played steps match
author/public complete legal sets, board, rights, raw EP and final Core state.
Every local move's3ply search completes; outcome difference remains a tiny
stochastic observation, not evidence of a causal strength decrease.

Primary risk-OFF3ply check-only result (all24 complete for every policy):

| Policy | Finite cp improved / regressed / equal | Sum delta cp | Time off / on sec |
| --- | --- | --- | --- |
| geometric | 4 / 4 / 16 | -427 | 29.672 / 34.550 |
| linear | 3 / 4 / 17 | -950 | 29.272 / 33.935 |
| unit | 6 / 0 / 18 | +938 | 25.767 / 30.220 |

Original answer hits stay2/2/3. Paired sums are descriptive finite engine
proxies, not a new pass threshold, calibrated regret or WDL. Combined risk-ON
check-only comparisons show geometric0/2/21,linear1/0/22,unit2/1/20 cp changes
plus one mate pair each; no universal common fix appears. Actual played prefix
all three policies choose Bxc3 with check-only, either risk setting.

Under the SAME five-second4ply curve, ordinary completion is8/9/13 versus
check-only5/5/9 (30to19/72); all19 jointly completed choices are identical.
Observed total time is314.615 versus325.497sec. All incomplete time-limit records remain, without
counting their shallower results as completed4ply. Threeply remains the cheap
playing condition. Fourply incompleteness is a resource observation, not a
universal prohibition on future higher-information calculations.14 new finite
child references reuse91 identical engine/conditions/cache entries; answers
and exposed status are unchanged. No default search or material price changes.

The six check-only/risk-OFF external games finish: geometric White mates
at57plies; the other five reach80plies unfinished. All229 local searches
complete3ply; observed local-search time324.572sec, not an isolated performance
test. Earlier stochastic risk-OFF2W/1L/3unfinished versus this1W/0L/5unfinished
does not establish either improvement or loss of strength. Retain all outcomes,
not only the one mate. The deterministic candidate games and full semantic
replay provide the next practical checks; no rating claim or price tuning.

Cost followup declared before running: turn ONLY existing PVS OFF for the
check-only/risk-OFF3ply condition on all24 original cases/allthree policies,
same32768nodes/5sec/native/order/TT/dynamic. Compare with the saved PVS-ON
check-only result; no rerun of the latter. Unknown: is the existing PVS saving
enough work at this new shallow evasion condition to offset part of its cost?
Report score/action parity, completeness, actual main+q nodes and time; if
scores differ, preserve the disagreement before considering a search change.
No new sample, price, feature, API or increased comparison budget is needed.

The four deterministic check-only games finish: geometric White mates unit
at49plies, reverse colors and both geometric/linear games remain unfinished80.
Final full-move audit corrects the preliminary completeness summary:287/289
internal local searches complete3ply. Two geometric Black turns (absolute
plies43and53 in the last linear/geometric game) hit the five-second limit
and legally retain completed2ply results. These are preserved incomplete3ply
searches, not full-depth successes. All ten new games/746plies replay with zero
complete legal-set, board, rights, raw-EP or final Core-state discrepancies.
Combined with the twelve risk games this is22 games/1583 actual played plies;
the internal win shows only a difference between these specific weak players.
It is neither a human rating nor proof of performance against all responses.

One cost-attribution diagnostic is also declared before execution: profile a
single geometric/check-only/risk-OFF3ply search on the already exposed actual
nine-move played prefix, all Core history witnesses retained. Same32768node
condition,20sec profiling safety fuse (not a strength-comparison extension).
Unknown: are repeated check queries, leaf dynamics or state/transition work the
largest actionable cost? Use cProfile call/cumulative/self costs to select one
next bottleneck, not its instrumented wall time as an optimization speedup.
Save outcome and profiler output; no new implementation/API follows merely
from profiling. No unchanged outcome trial or old frozen result is overwritten.

The new check-only3ply PVS comparison completes all72 on both sides; every
paired action and score matches. PVS reduces main+q nodes179998to146439
(-18.6%) and observed time122.018to98.704sec(-19.1%). The short746ply replay
overlapped part of PVS-off execution, so wall improvement is observational;
node parity/savings do not depend on isolated hardware timing. This supports
retaining existing PVS, without a new price or global default promotion.

The single actual-prefix profile completes3ply in7.667 instrumented seconds,
choosing Bxc3. Existing dynamic evaluation consumes3.133 cumulative seconds,
anchor escape1.884 within it, repeated pseudo-attacks2.925 across callers;
the new checking-leaf gate itself0.494sec. These categories overlap and cannot
be added as disjoint shares. Prefer one existing dynamic/attack bottleneck
investigation over a new attacker API merely to chase one risk failure.

Source inspection gives a NEW semantic concern in the shared residual:
`Evaluator` uses legacy movement-atom pseudo-attacks for mobility, escapes
and its check penalty; Western Pawn capture rules are omitted. Two explicit
minimal Pawn controls demonstrate missed actual check and an unsafe empty
King escape, with256 native/semantic square-query agreements and unchanged
states. Diagnostic unscaled dynamics9versus-45 and35versus26 show a concrete
difference; these are counterfactual values, not a tested replacement or error
rate. Initial audit mistakenly compared all King moves (including a capture)
to an empty-square count; it was corrected to the matching empty-target subset.
Core legality/search checking remains semantic and was not changed. All old
dynamic comparisons retain their actual legacy residual and cannot be relabeled
as semantic. Next qualify a cheap semantic shared residual separately, keeping
prices and search fixed and testing actual usefulness/cost before replacement.

One portable record data/chess_capture_risk_results_20261006.json contains all
504 full-suite searches (including incomplete4ply), actual-prefix results,
22 full move streams, finite references, replay, cost and approximation limits.
Raw local output and failed reference transport remain untouched and hashed.
Exact intermediate runner/search/tuning bytes are inertly preserved alongside
the older producer snapshots; positional SearchTuning compatibility is retained
by appending the new option.115 current regressions and39 historical pin checks
pass. No default, Core rule, human holdout, extra worker or public push changes.

## Cached versus semantic shared dynamics (2026-10-06 continuation)

Decision before measurement: repair the observed shared-residual Pawn omission
without fitting prices or changing search. Three optional backends isolate two
questions: original legacy, cached legacy (exact same definition), semantic
pseudo-attacks cached within one leaf. No cross-state cache or history/side flip.
The existing native dynamic vector is NOT reused: source inspection shows legal
candidate counts, side views and legal anchor moves, a different feature law.
The chosen existing native square queries instead preserve the attacked-square
definition, including semantic Pawn captures and guards. Pins, S3 own-anchor
safety, S4 postconditions and anchor-source-vacancy effects remain outside the
residual. Empty-target pseudo-escapes are not legal King mobility; a new checking
rook control explicitly preserves and labels that approximation.

Before search comparison, two Pawn controls match the author semantic attack
counts/checks and yield unscaled residuals -45/26 versus legacy9/35. On those
two states and the actual nine-ply prefix, cached legacy preserves material and
total scores exactly.200 evaluations per method/state find legacy/cached/semantic
costs approximately51/18/231,69/20/216 and342/101/272 microseconds, respectively.
These are selected microcosts, not a population or whole-search speedup claim.
Semantic correction is slower in simple controls, so correct coverage alone
does not establish practical usefulness.

Declared comparison: all original24 cases/answers and three inventory policies;
3ply,32768 shared nodes, five seconds, qdepth0/qhard8, native legality, common
ordering, fresh TT65536, PVS and mandatory check-only ON, capture-risk OFF.
Interleave three backends within each case; include the same actual nine-ply
prefix with Core-produced history witnesses. Keep all completions, finite
reference gains/losses/magnitudes and costs. Require cached legacy score/move
parity before recommending it; assess semantic repair separately without
requiring BK12/14 or any other named failure to improve. Existing frozen results
remain legacy and their exact producer bytes are archived inertly before edits.
No Core/default/price/human-holdout/worker/publication change.

New cost hypothesis after the first microprobe: traverse each semantic capture
pattern/source/geometry once and reuse the author's exact binding/path/guard
predicates, rather than query all128 owner/squares. A26-state probe matches all
3328 native/author square booleans and measures17-204 microseconds per map pair.
It is a separate optional `semantic_bulk` backend; no native build/API or Core
rewrite. Independently qualify all22 previously recorded actual game histories
before recommending it. Its current-occupancy escape limitation remains unchanged.

After complete3ply/cache parity, a NEW4ply resource curve is declared: legacy,
cached legacy and semantic bulk; all24 original cases and the actual prefix,
same32768 nodes/five seconds/q0/check-only/PVS/order/TT, risk OFF. This is a new
development curve, not an extension or revision of the old frozen4ply failures.
Question: does equivalent faster legacy evaluation improve completion within
the same wall budget, and does semantic coverage have a cost/completion tradeoff?
Compare all shared completed scores/moves, count partial searches separately;
do not interpret different incomplete retained iterations as score-parity errors.
Worst-case single-core aggregate216 suite calls times five seconds is18 minutes;
each search is interruptible and bounded, no extra worker. This cost can change
which existing playing option is useful, unlike another non-discriminating proof.

Declare the practical playing followup before results: the original initial
position only, each of three unchanged inventory policies in both colors,
cached legacy versus semantic bulk interleaved within policy/color,12 games
maximum80plies. Same fixed4ply iterative player/node32768/five-second fuse,
check-only/PVS/common-order/TT, risk OFF; the same pinned Stockfish17.1 weak
1320 setting/50000nodes/one-second fuse/Threads1/Hash16, fresh game per cell.
Retain played partial-depth fallback moves, losses and unfinished games; replay
all moves with the author legal sets/board/rights/rawEP. One stochastic game per
cell is a development feasibility sample, not a causal/rating comparison.
Worst-case local search cost40 minutes on one core, normally lower; no external
model/worker or fee. Outcome/completion/move traces can decide whether semantic
coverage belongs in the next practical player, rather than tune to old answers.

The first216 suite searches all complete3ply. Legacy/cache72 pairs preserve
both main/q node counts, scores and moves exactly; total observed97.314 versus
77.053seconds (-20.8%). Semantic correction changes11 selections but original
answer hits stay2/2/3. Query/bulk144 separate searches preserve all72 scores,
moves and main/q nodes, with observed97.668 versus88.551seconds (-9.3%). Timing
is interleaved observation, not isolated hardware or future speed guarantee.
All22 old game streams are reconstructed through Core, preserving full histories
and final recorded states;1583 pre-move states preserve legacy/cache scores and
semantic query/bulk terms, with202624 exact native/bulk square booleans agreeing.
This is played-sample consistency, not every-position/variant proof.

Five additional fixed50000-node Stockfish child references plus67 matching cached
references cover every selected/accepted root action. All24 finite paired values
per policy: geometric2improve/1regress/21equal (+114cp sum), linear1/1/22 (+75),
unit2/4/18 (-466). Unit changes BK22 (-281cp) and BK23 (-183) are retained, with
actual selected PV traces. Correct attack coverage alone does not imply a useful
residual law, strength gain or permission to fit coefficients to these labels.
Keep semantics and practical evaluation as distinct questions.

Important interpretation correction for the earlier capture-risk5/144 diagnostic:
these are SAVED PV ENDPOINTS, not necessarily actual scored leaves. TT exact/bound
returns omit continuation; mandatory checking quiescence returns only a scalar.
The current72 legacy outputs contain12 PVs shorter than completed main depth
and8 checked endpoints; semantic has8 short/8 checked (these sets may overlap).
Even a full main-depth PV can omit a checking extension. This does not itself
show a wrong root score, but removes any claimed leaf-incidence or check-extension
coverage inference. Original output stays intact. Dot explicitly agrees with
the narrowed interpretation and identifies just one decision-changing check:
finite reference must start at the real root child. The reference source copies
the root board and pushes the selected root move; a new intercepted transport
test verifies exact one-move child state, root-player score perspective and fresh
game identity, using a deliberately longer saved PV. No path recorder is built.
Dot's report-based advice was not independent code/result reproduction.

The NEW4ply curve completes15/72 legacy,25/72 cached legacy,18/72 semantic bulk;
all15 shared legacy/cache completions preserve actions/scores/main+q nodes, with
10 additional cache completions. Observed totals329.660/315.850/324.920seconds.
Brief source/PV analysis and regression calls overlapped a few earlier searches,
so this is an observed interleaved resource curve, not isolated hardware or a
guaranteed future completion count. Every incomplete is retained as time_limit.
On the two original actual played roots,43/53 (not initially in check), new3ply
five-second calls give: legacy both retain2ply; cache completes root43 in4.363sec
but not53; semantic bulk completes53 in4.074sec but not43. Different finite-depth
choices are not price changes. Original old timeouts stay unchanged.

Observed recording friction during live games: at10:04:43UTC a reader hit the
empty interval of truncate/rewrite and JSON decoding failed; a later read was
complete. Repair `write_record` with same-directory temporary file, flush and
closed-handle atomic replacement. JSON encoding/bytes stay unchanged; failures
leave the previous complete frontier and clean the temporary. Four serializer
tests pass, including reader-at-replacement and injected replacement failure.
The already-running frozen game batch retains its initially imported old writer;
do not restart/reload it or relabel its producer. The fix applies to subsequent
processes; read this batch at completed checkpoints/after exit. Exact old writer
bytes are inertly archived with their original hash; no new protocol or daemon.

The declared12 games complete in1745.950seconds wall: cached legacy has
0wins/3losses/3unfinished across413plies; semantic bulk1win/2losses/3unfinished
across394plies. Unfinished is not draw. All807 played moves replay through the
author legal sets, board, rights/rawEP and final state with zero discrepancies.
Of403 local turns,168 complete4ply and235 retain3ply after time_limit; none
retain1/2ply. Cached/semantic local wall877.121/820.064seconds, main+qnodes
1308529/1119947, evaluation calls983361/836098, native legality246609/220736,
zero native fallbacks. One stochastic game per cell cannot establish causal
strength or Elo; mixed evidence does not promote semantic residual or defaults.

Actual full-history finite root-child references separate depth from quality:
at old timeout43, cached Nc6 scores-1cp versus old retained d6+81cp (root best
b6+336); at53, semantic b6+241 versus retained Ne5-434. More completed depth
does not guarantee a better choice. In the first new loss, White's42nd-ply Qg4
allows actual Queen removal, but its fixed50000-node child proxy is-966cp
versus the root reference's f2-900cp. Already severely losing; the66cp difference
does not identify the initiating blunder or justify another risk framework.
Next locate earlier deterioration in the actual trace. Stockfish17.1/Threads1/
Hash16 finite proxies are standard-Chess references, not exact Core WDL/regret;
actual child history/board transport is checked.

One portable record `data/chess_shared_dynamic_results_20261006.json` preserves
22 raw reports/summaries with hashes,576 suite searches,24 actual-prefix calls,
six timeout-root calls,12 full game streams and replay. Exact producers and10
drivers are inertly archived.43 relevant current and39 historical pin checks
pass. Final thread reread includes two additional user/dot status posts; they
add no technical objection and are not independent reproduction or newly
authenticated request replies. No routine acknowledgement sent.

## Earlier loss diagnosis and bounded capture search (2026-10-06)

The next segment executes all memo-selected actual White roots16/20/24/26/30/
32/36/38/40/42 before the first Queen loss. Fresh50000-node root/selected-child/
best-child references preserve actual full history, Core/author child alignment
and every point. The conspicuous negative finite differences are20Qh4(-460cp),
26Bc6(-399),40Kf3(-348). Earlier checkpoint incorrectly called e2f3 a Bishop
capture; it is a King move. Later corrected explicitly, raw checkpoint retained.
These are finite reference differences, not certified regret/blunder incidence.

At20 the legal saved continuation Qh4 g5 Qxg5 permits hxg5 removing White's
Queen. Direct author qsearch on that legal endpoint gives Black-perspective
static-19917 versus capture-only q1+83083/q2+65666 (all complete,~0.00024/
0.0140/0.0260sec). This is a diagnostic control, not proof the original search
visited/evaluated that endpoint; saved PV omits TT/q continuations. Ten original
root comparisons under4ply/32768nodes/five seconds find ordinary q1 mostly
retains1/2main layers versus q0mostly3/4 and often keeps the same bad choices.
Extra nominal extension alone does not guarantee a longer effective horizon.

First predeclare a new2x2 resource curve: ordinary q0/check-only versus q1;
lexical q traversal versus reusing existing shared-price move orderer. All24
original cases/three prices,4ply/32768nodes/five seconds, cached legacy residual,
PVS/root ordering/TT unchanged.288 searches at most24minutes on one core,
interruptible, every partial result kept. The exact initially loaded source is
archived; later lazy-classification/capture-only changes do not relabel it.
Brief tests and actual-root probes overlap some cells, so timings are observed
interleaved cost, not isolated hardware or guaranteed completion counts.

Observed continuation cost motivates one changed algorithm hypothesis: outside
check retain captures, promotions and terminal actions, omit quiet checks;
in check keep every legal evasion and existing hard abort. Off-target removals,
including EP, retain the actual child enemy-board-count signal. No SEE/price
fitting, automatic tactical pruning, changed Core/defaults or native API.
Optional ordered traversal classifies each candidate on demand before search,
so a beta cutoff avoids probing the unused remainder. First capture-q1/q2/q3
pilot is fixed to20/26/40; all12 partial searches remain. Capture q2 selects
bxa5/Bd2/Qd4 with finite child proxies-331/-235/-823 versus-634/-633/-924.
q3 is mixed (26Qxf6-665). No general-strength claim or coefficient calibration.

Declare the q2 followup before broad results: all24 cases/three unchanged prices,
same4ply/32768nodes/five seconds, cached legacy, existing common ordering/TT/PVS;
72 cells at most6minutes. Then twelve playing cells: three prices, both colors,
q0check-only versus capture-only q2, both new lazy qordering. Original initial
position;120ply ceiling to reduce the earlier80ply unfinished censoring. Same
Stockfish17.1 weak1320 setting/50000nodes/one-second fuse/Threads1/Hash16;
fresh game each cell. At most60minutes local search, interruptible each move;
all losses, incomplete searches and unfinished games retained. One stochastic
cell per condition is practical development, not Elo or isolated q2/price cause.
No adverse-result budget extension or human-holdout access.

Dot supports this scoped player comparison and asks one essential contract check:
interrupted iterations must not replace the last complete root. Existing
run_root_search only assigns returned complete negamax results; injected
time/node/qbudget interruptions preserve exact prior move/score/PV/depth for
q0/q2. Reaching a finite q boundary is normal completion, actual interruption
is recorded separately. Advice was report-based, not independent reproduction.

Completed ordering-only curve: q0 lexical/ordered each finishes4ply on33/72,
retaining3ply on39. Ordinary q1 lexical/ordered each finishes4ply on3/72,
retaining3/2/1ply on7/57/5. All33 shared complete q0 and3 shared complete q1
actions/scores match. Observed aggregate wall308.261/307.862sec for q0 and
348.375/348.198sec for q1; total main+qnodes606473/604111 and189132/176611.
Original answer agreement8/72 for q0 and6/72 for q1. Ordering alone does not
recover useful completion depth or wall time in this curve; do not promote it
as a measured speed improvement. Preserve partial searches rather than counting
only returned records as completed4ply searches.

The separate capture-only/lazy q2 suite finishes all72 records, with3 searches
completing4ply,33 retaining3ply and36 retaining2ply; zero1ply results. Original
answer agreement12/72, observed wall347.328sec and392599 main+qnodes. This is a
practical tradeoff against the q0 and ordinary q1 conditions, not evidence that
more extension always improves a move or that answer agreement is an error rate.
The exposed three-root pilot and full-suite sample retain distinct scopes.

Existing counters offer a concrete next cost question, not a causal profile:
ordered q0/q1/capture-q2 suites make592631/952599/1009089 runtime pushes versus
573049/66128/153019 recorded searched successors. Full semantic diff fallback
counts592646/952637/1009123 track those pushes closely. Measured ordering time
6.341/0.820/3.804sec is small against aggregate308/348/347sec; evaluation and
native-legality timers are scoped and not necessarily a disjoint wall-time
partition. Profile classification/state updates before adding nominal depth or
discarding semantic/history guards. No runtime optimization is claimed here.

All selected q0ordered/capture-q2 suite children, including interrupted-search
choices, receive finite50000-node references:24 new analyses plus43 matching
cached analyses under the same exact engine/hash/threads/nodes conditions.
Across23 cp-valued pairs geometric improves9/regresses5/equals9, sum+169cp;
linear6/9/8, sum-47cp. Their remaining BK.01 pair changes d6d4 to d6d1 with
reference mate2 instead of a cp result; do not convert mate to an arbitrary
scalar or silently omit it. Unit's24 cp pairs improve7/regress9/equal8, sum+1198.
These sums are descriptive finite proxies, not certified regret or fitted
selection criteria. Explicit negatives include linear BK.11-554cp, geometric
BK.20-215, unit BK.17-305. More answer hits do not imply every choice improves.
References here use supplied BK FEN history, unlike actual-loss full histories.

All twelve declared120ply playing cells finish their records in2397.806sec wall:

| Profile | Local wins | Local losses | Unfinished | Played halfplies | Complete4ply local turns | Retained3ply | Retained2ply |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| q0 check-only | 1 | 3 | 2 | 591 | 162 | 133 | 0 |
| capture-only q2 | 2 | 1 | 3 | 524 | 44 | 162 | 56 |

q0/q2 local search wall1080.570/1233.697sec and main+qnodes1524865/1235571.
All351 incomplete local searches are time_limit and retain the last completed
iteration. Longer nominal q extension spends more wall while reducing main
depth. Geometric q0 loses White and leaves Black unfinished; q2 leaves White
unfinished and wins Black. Linear q0 leaves White unfinished and loses Black;
q2 wins White and leaves Black unfinished. Unit q0 loses White/wins Black;
q2 leaves White unfinished/loses Black at61halfplies. This last regression is
retained, not hidden by the aggregate. Winner/color are checked explicitly:
an earlier spoken Black q2 result was reversed, then corrected from raw winner1.
Unfinished is not draw. One stochastic cell per condition, one initial position
and weak opponent do not establish Elo, independent price quality or isolated
causal q2 strength. Keep capture-only as a useful development option; do not
promote prices/defaults from this small mixed batch.

All1115 moves replay through public/author full legal sets, board/rights/rawEP
and exact final Core state/history with zero discrepancies.82 relevant current
and39 historical source-pin tests pass; no full-repository test claim. One
portable record `data/chess_qcapture_results_20261006.json` contains13 exact
raw reports/summaries with hashes,360 suite searches,32 actual-root q calls,
twelve games and full replay. Exact earlier/order-only/capture producers and11
drivers are inertly archived; original manifest bindings remain unchanged.
Latest full advisor thread read has15 posts and no further technical supplement;
the interruption objection was adopted without turning remaining risks into
a backlog or waiting for approval. The next practical question is classification/
state-update cost; the actual unit Black q2 loss supplies a separate error check.

## Runtime terminal cost continuation (2026-10-06)

The next memo Main profiles the fixed actual root20 at equal2ply/32768nodes/
30seconds. Both complete: q0 observed profiled wall0.306sec/157 runtime pushes;
capture-q2 2.552sec/1865pushes. q2 classification cumulative1.499sec, terminal
1.156sec and attack queries1.424sec overlap; do not sum them or treat profiled
times as operational performance. Source inspection locates a redundant query:
`terminal_from_search_runtime` asks in_check after discovering a legal action,
but only uses that answer when no action exists. Move this query inside the
no-action branch. Keep terminal precedence, legal-action existence, repetition,
history gave_check, automatic adjudication and all history/identity guards.
No evaluation, q law, native API, budget, prices or search defaults change.

69 relevant tests pass, including all four legal-existence/check combinations,
actual checking-child history, runtime path contracts, q value parity and aborts.
Two test-only mistakes (import location and per-instance mock of a freshly made
engine) were corrected; no experiment record was overwritten to hide a failure.
All1115 prior played transitions match exact baseline terminal status, immutable
position/ply, preserved check-history and final state with zero discrepancies.

Predeclare the resource curve before results: all24 cases/three prices/q0 and
capture-q2/baseline and deferred terminal,288 cells at4ply/32768nodes/five seconds;
cached legacy/PVS/common root and q ordering/TT fixed. Alternate version order by
case/model/q. Exact archived baseline function body is loaded inertly and its
result/enum aliases share canonical identities, necessary for runtime `is` tests;
the old decision code is unchanged. One sequential local job, at most24minutes
search, interruptible, all partials retained. Timing comparisons require matching
complete work; same-budget completion counts are a separate practical measure.

Then run twelve newly declared deferred-terminal playing cells: three prices,
both colors and q0/q2, initial position,120ply ceiling, same weak1320-setting
Stockfish17.1/50000nodes/one-second fuse/Threads1/Hash16. Per local move fixed
4ply/32768nodes/five seconds, at most60minutes local compute. Old stochastic games
are contextual observations, not paired causal measurements. No adverse-result
extension, human-price/holdout read, extra worker or default promotion.

The prior unit Black capture-q2 loss is separately diagnosed at prospectively
chosen actual plies9/17/25/33/41/49/53/55/57/59, fresh50000-node roots and selected/
best children under full actual history. This is finite standard-Chess evidence,
not certified regret. It can identify an error worth testing without a new proof
framework. A distinct Shogi control uses existing full13-board-mode affine
inventory and an explicit held point h(base)=one-half normalized board(base),
shared across leaves. Two new synthetic full-stock roots permit unequal capture
and R/B drop choices; neither is claimed reachable/heldout. Four equal2ply/2048node/
10second calls plus one-ply tie diagnostics are practical feasibility, not a
certified held law, exact WDL or generic strength. No data-driven price selection.

The full resource curve retains all288 searches. q0 completes4ply33→39/72;
capture-q2 completes4ply3→3,3ply32→42 and retains2ply37→27. On all36 shared
complete4ply pairs, move/score/main nodes/qnodes/runtime pushes are identical.
q0 shared work takes111.558→101.284seconds (about9.2% lower observed wall);
q2's three small complete pairs2.947→2.734seconds. These are a single sequential
development observation, not a repeated statistical speed guarantee. Fixed
q2 wall remains essentially347seconds because69/72 calls hit the time limit;
extra exploration raises main+qnodes384277→448635. Answer agreement12→11/72
retains an adverse outcome: faster equivalent mechanics need not make every
budget-dependent choice better. q0 remains8/72 answer agreement. No price or
qsearch default promotion. Operational timings exclude later compilation.

All twelve playing records finish in2239.940seconds,983 moves; q0 has two local
wins/three losses/one unfinished, q2 one/four/one. Neither unfinished120ply cell
is called a draw. q0 local turns complete4ply105 and retain3ply114; q2 completes
4ply29, retains3ply155/2ply88. All357 interrupted searches are time limits.
All983 moves pass author/Core full legal sets, board/rights/rawEP and exact final
state/history. Old stochastic results are contextual, not paired counterfactuals.
The single source cost repair is useful without treating these mixed results as
causal strength evidence.69 earlier plus32 additional relevant tests pass.

All ten preselected earlier-loss references finish with full actual history.
At ply9 the selected child already has finite Black-664cp versus alternative
-601; at17 -958 versus-945,25 -841 versus-798,33 -860 versus-873,41 identical
-845,49 -1184 versus-1100. The last four points retain mate-valued references,
not arbitrary converted cp. Do not blame a late Rook/Queen loss for an already
bad position or assume the root's finite best stays best after independent
child analysis. These references are descriptive50000node proxies.

A newly observed earlier premise is tested separately without changing those
ten points: actual7Bxa3/8bxa3 trades Bishop for Pawn. Four same-resource full-history
controls yield unitq0 Bxa3 at3ply, unitq2 Bd6 at3ply, geometricq0 Bxa3 at3ply and
geometricq2 Ke7 retaining2ply. Finite children Bxa3/Bd6/Ke7/Qb6 are-610/-209/-228/
-115cp for Black. Thus this failure is not simply unit prices or q2 machinery.
The q0 returned PVs end in Qxc3 before a legal ordinary Queen recapture; absence
from PV still does not prove search never examined it. This concrete horizon
problem motivates the mature actual-history control rather than price fitting.

Both synthetic full-stock Shogi capture calls complete2ply in0.387/0.343sec:
geometric selects Re5xh5 (Rook capture), unit Re5xe6 (Pawn capture with check).
One-ply maxima have one/two ties respectively. For the drop root, geometric
retains1ply at node limit in1.485sec, choosingR@a2; unit completes2ply in1.525sec,
choosingR@e7. One-ply43/86-way ties expose weak placement discrimination, not a
proof of hand prices or generic ability. All chosen children retain public/runtime
position/terminal parity and conserved base inventory. The declared half-board
held coefficient remains an approximation, not a certified deployment law.

### Mature search testbed decision

A new advisor supplement and user question prioritize a mature material testbed.
Adopt this useful direction, not every theory branch. Official pinned
[Fairy-Stockfish source](https://github.com/fairy-stockfish/Fairy-Stockfish/tree/9f778da667f6e07dae1e85d3e2ea204fc6dee94d/src)
supports a small standard-Chess pure-material `Eval::evaluate` hook and inherited
variant piece-value configuration. This does not establish arbitrary GenericChess
rule transplantation. YaneuraOu's official MATERIAL_LEVEL1 is a real alternate
pure-material mode; Chess first reuses this existing suite and UCI/replay entry.

Direct source inspection corrects an initial local inference: normal Chess SEE
in position.cpp2502/2506/2607 and capture ordering movepick.cpp136/152 retain
`PieceValue`; variant overrides create `EvalPieceValue`/`CapturePieceValue`, the
latter used by atomic/blast exchange paths. Fixed pruning/nonPawnMaterial and
old ordinary SEE remain common across the first three leaf candidates. Results
will concern material leaves inside this fixed mature search, not an entirely
price-neutral search or evidence that these mismatches are optimal.

The complete19-post thread includes a new verified shared-account response with
the matching request/FOLLOWUP_ID. Explicitly review/adopt its one concrete issue:
internal Pawn=100 is not UCI100cp. Pinned types.h has PawnMg126/PawnEg208, and
uci.cpp divides internal score by208 for centipawns. Adopt internal208 per Pawn
before any mature outcome; static one-Pawn difference in both side orientations
must show1.00Pawn=100cp. This is a gauge convention, not data fitting or proof
of ideal pruning thresholds. Earlier100/126 drafts are superseded pre-execution.
No advisor reproduced local tests/games; the separate bot's broader direction
is independently source-checked, without changing identity configuration.

The optional sequential build uses existing Zig0.16, pinned official source with
local GPL/AUTHORS and patch, no installation/new worker. Build/static controls
precede a tiny same0.25sec/Threads1/Hash16 exposed24case×3model feasibility probe.
Keep raw failures and all candidates; no compile during the operational batch.

The build is now runnable. First compilation fails on upstream __DATE__ under
Zig's reproducibility warning; fix the banner to the source-commit date before
resuming. One local resume accidentally omitted the cache environment and failed
against an unwritable default cache; restore project-local cache arguments, with
both failures retained. Successful remaining compile/link takes36.116sec, no
system settings/install or source/search change beyond the experimental leaf.
Run upstream shallow Chess bench and official/custom configuration checks; all
return0. Official broad config diagnostics retain unsupported8x8-build entries,
so this is not all-variant qualification. All six static controls show1.00Pawn
from White's perspective for either actor. The three internal tables are:

| Candidate | Pawn | Knight | Bishop | Rook | Queen |
| --- | ---: | ---: | ---: | ---: | ---: |
| geometric_half | 208 | 605 | 549 | 1071 | 1194 |
| linear_mixture | 208 | 483 | 394 | 767 | 855 |
| unit | 208 | 208 | 208 | 208 | 208 |

All72 equal0.25sec exposed-suite calls produce legal choices. Answer agreements
are7/24 geometric,9/24 linear,4/24 unit; not proven-error rates, training or price
promotion. Reported nodes total17.728/17.378/18.950million; reported depths include
one245 maximum-depth mate case per model, not245 fully examined plies. Engine
depth/node definitions and selective pruning are not cross-engine equivalents.

At the exact actual ply7 history, all three mature models chooseQb6 at reported
28/29depth in0.258–0.261sec. Its exactly matched finite root-child proxy is-115cp,
versus the earlierBxa3-610. This supports runnable feedback and this one improved
selection, not a theorem of price advantage or isolated search cause; old SEE
still contains original values and the own-engine residual is different. Six
prospectively declared standard-start playing cells now use the existing UCI/
Core transport,120ply ceiling,0.25sec local, same weak opponent condition. Count
recording time/written bytes separately; no adversarial-result extension.

All six cells finish records in90.293sec: geometric/linear each two local wins,
unit one win/one120ply unfinished, zero local losses. All515 moves replay through
author/Core full legal sets, board/rights/rawEP and exact final state/history
without discrepancies. These are one weak stochastic opponent and one start,
not amateur Elo, independent price ranking or an isolated search effect. Own
and mature players differ in residuals/heuristics/budgets; their node/depth counts
cannot be equated. The practical next priority is to reuse this working material
testbed and obtain broader declared feedback, while keeping GenericChess Core
as its separate rule/legality foundation.

Per-action persistence is measured rather than assumed free:527 writes serialize
163714268bytes and take5.335sec (final summary write excluded), about5.9% of
the observed game-chain wall. Current recording overhead does not justify a new
protocol. Preserve complete records and revisit only if a concrete larger use
makes it dominant.101 current-relevant and38 historical-binding tests pass;
six independent C++ static controls and upstream smoke are separate observations.
`data/chess_runtime_cost_results_20261006.json` contains nine own-runtime reports
plus nine mature acquisition/build/probe/play/replay records. Raw local profile/
compiler path labels are normalized explicitly in portable bodies; original raw
hashes remain bound. Exact producers/drivers and material patch/config are inertly
archived; original baseline records and failed builds remain unchanged.

## Reuse

The supported deeper material comparison (choose a new output path):

```
.venv/Scripts/python.exe -m scripts.chess_development compare --suite docs/research/data/chess_development_suite.json --output .local_agent/compare-next.json --depth 3 --nodes 32768 --seconds 5 --native-legality --ordering --tt
.venv/Scripts/python.exe -m scripts.chess_development play --suite docs/research/data/chess_development_game_starts.json --output .local_agent/games-next.json --depth 3 --nodes 32768 --seconds 5 --native-legality --ordering --tt --max-plies 40
```

`--dynamic` is the explicitly labeled shared-residual ablation. Optional
`play-uci`/`reference` require a local official UCI executable and python-chess;
`--uci-python` accepts the pinned local author import root. Neither mode accesses
an account/model/worker. A native build is optional: omit `--native-legality`
to use the slower legal reference. Output refuses overwrite and preserves errors.

Optional `--dynamic-backend cached_legacy` preserves the old residual with per-leaf reuse; `semantic_bulk` selects semantic pseudo-attacks and requires `--native-legality`. Legacy remains default. Use `--pvs --check-only --qdepth 0` for the fixed practical condition above.

Optional `--qordering` requires `--ordering`; `--qcaptures-only` requires positive `--qdepth`. Both default OFF. For the prospective capture-only player use `--qdepth 2 --qcaptures-only --qordering --pvs --dynamic --dynamic-backend cached_legacy --native-legality --ordering --tt`; omit `--check-only` for positive qdepth.


### Reusable mature-material entry and useful budget feedback (2026-10-06)

The existing `compare` and `play-uci` entry now accepts a qualified pure-material
UCI engine plus its exact frozen config, with no new interface or default price.
Each case may specify `opening_uci` from its original FEN. Both engines and Core
retain that full history, including repetitions/rights/raw EP; child references
never use fresh-FEN cached values for a nonempty prefix. Legal sets are checked
before each material-player move. Reported UCI nodes/depth/time/PV are retained;
a legal time-bound best move does not certify a complete fixed-depth search.
Native CPU/cache/scored-leaf counts remain unknown, not zero. Production TT and
ordering flags are not controls over the external search.

Only the pinned standard-Chess pure-Eval build is qualified here: official
Fairy-Stockfish source9f778da667f6e07dae1e85d3e2ea204fc6dee94d, binary SHA256
477628ae141c6e5fb7dcb562e31e3bc40eab95b20c8b966ece131a1dbf090999.
Original SEE/ordering/pruning remain fixed. Pawn208/report100cp and frozen
geometric(208,605,549,1071,1194), linear(208,483,394,767,855), unit(all208)
were fixed before results. The config guard alone cannot certify a pure Eval
binary. Qualification and six static gauge controls are in
`data/chess_runtime_cost_results_20261006.json`. This is a standard-Chess testbed,
not a full GenericChess rules transplantation or independent price validation.

Thirty-six prospectively declared games used two four-move legal prefixes:
e4/e5/Nf3/Nc6 and d4/d5/c4/e6; three tables, both colors and three local resource
points. Each game had at most160 *subsequent* plies, fresh Hash16/Threads1,
against1320-configured Stockfish17.1,50000nodes with1sec fuse. The initial save
callback launch failed before games; its record remains intact. A separate
resume changed the callback argument only, not conditions or source.

| Local seconds/move | Wins / losses / unfinished | Batch wall seconds |
| --- | --- | --- |
| 0.25 | 12 / 0 / 0 | 148.795 |
| 1 | 11 / 0 / 1 | 542.508 |
| 4 | 12 / 0 / 0 | 1593.479 |

The4sec batch costs about10.7times the0.25sec batch without extra winning cells
on this weak comparator. Stochastic trajectories and capped games prohibit a
causal strength conclusion or universal budget cutoff. Saturation is a reason
to change the decision question, not to repeat easy games or fit prices.

A separately declared direct12-game comparison used all unordered table pairs,
both colors and the same starts at0.25sec each side. Unit lost all eight games
against geometric/linear. Geometric versus linear produced one linear Black
win and three160ply unfinished games. These are not draws or an Elo ranking.
A further single1800-configured comparator batch, keeping local0.25sec and
reference50000nodes/1sec, produced geometric3wins/1unfinished, linear4wins,
unit2losses/2unfinished. The1800 setting is not a calibrated rating claim.
All60 games replayed5527 new played moves and240 opening-prefix moves with
zero full legal-set/state/history discrepancies. No defaults are promoted.

The sole1sec unfinished linear White game was already deteriorating before its
late endpoint. Five preselected full-history points0/40/80/120/158 gave limited
strong-reference actual-child proxies-34/-227/-541/-543/-653cp. At40, current
geometric/unit h3h4 scored-347 versus actual/current linear g4g5-227; retain this
adverse alternate. At0, Nc3+26 versus actual c5-34 is only finite proxy feedback.
It does not prove WDL or original examined leaves. Next inspect the actual0–40
interval rather than assuming a winning-endgame finish defect or tuning prices.

The separate checked full-stock Shogi control had8 legal evasions. Under the
existing2ply/2048node/10sec conditions geometric/unit both completed2ply,
choosing R@e2/B@e2 at421/261nodes and0.531/0.278sec. Static placement ties remain
2/4. Held values equal half normalized board values, an explicit approximation;
neither certified held-price law nor historic reachability is claimed. A draft
Bishop/Rook identity error was corrected before execution, with old records kept.

The1800 batch measured1441 writes,1,427,552,225 serialized bytes and35.366sec
recording within258.106sec wall. A small corrective change makes only per-action
progress compact; completed reports keep the prior pretty default and same
schema/conversion/atomic replacement. Four alternating offline final-frontier
write pairs retained equal parsed values:8,209,772→5,218,812bytes and
0.177→0.105sec. This is not measured game-chain acceleration. Replacement-failure
tests preserve the old frontier and clean temporary files in both modes.
28 targeted adapter/development/record checks pass; actual six2ply CLI transport
games also complete. A formatting indentation error was found by collection and
fixed before the benchmark. No experiments ran under changed source conditions.

`data/chess_mature_entry_results_20261006.json` preserves16 complete raw records
and hashes (SHA25667dd4d6e9d322c26d3659ac032565d83b8dd558ddfc246111900385f29efed1f).
The exact60-game source SHA2561472c03f88e7ea06f464eeea68e1afac301f99feddada7e47c9dcdf1fcb240b6
is in `../archive/development_mature_entry_20261006/frozen_entry.zip`.
`sources.zip` holds13 inert producers/test sources before the final formatting
repair; `recording_format.zip` separately holds final writer/entry/tests/benchmark.
Each archive has a hash/size manifest and was read back byte-for-byte. Offline
format results are in `data/chess_recording_format_20261006.json`. No binary,
credential, local username path or Slack record is in these portable archives.

Example with an already qualified local build (output must be new):
```
.venv/Scripts/python.exe -m scripts.chess_development compare --suite .local_agent/mature-openings/suite.json --output .local_agent/next-material-compare.json --material-engine .local_agent/mature-search/build/fairy-material.exe --material-config .local_agent/mature-search/material-variants.ini --uci-python .local_agent/certificate_source/python-chess --seconds 0.25
.venv/Scripts/python.exe -m scripts.chess_development play-uci --suite .local_agent/mature-openings/suite.json --output .local_agent/next-material-play.json --material-engine .local_agent/mature-search/build/fairy-material.exe --material-config .local_agent/mature-search/material-variants.ini --engine .local_agent/stockfish-reference/stockfish/stockfish-windows-x86-64.exe --uci-python .local_agent/certificate_source/python-chess --seconds 0.25 --opponent-nodes 50000 --max-plies 160
```
These runs are development measurements, not independent held-out validation.
No human-label fitting, Xiangqi holdout read or general amateur-strength claim.
The objective remains OPEN. Public publication remains on its existing hold.


### Stronger-comparator time, operational recording and Shogi horizon (2026-10-07)

The prior1800-configured comparator was kept fixed:50000nodes/1sec fuse,
Threads1/Hash16, two unchanged four-move opening prefixes, all three frozen
tables/both colors and160 subsequent plies. Twenty-four new games were declared
before outcomes,1sec and4sec local time. No source, compilation, tests or second
search ran alongside operational search; light Agent file inspection/preparation
continued. The optional additional direct batch was prepared but not launched;
actual-root feedback was the more useful next decision. No price/default change.

| Local seconds | Geometric W/L/U | Linear W/L/U | Unit W/L/U | Batch wall |
| --- | --- | --- | --- | --- |
| 0.25, prior descriptive batch | 3/0/1 | 4/0/0 | 0/2/2 | 258.106sec |
| 1, new batch | 4/0/0 | 2/0/2 | 1/3/0 | 711.373sec |
| 4, new batch | 3/0/1 | 4/0/0 | 4/0/0 | 2369.116sec |

U means unfinished, never an inferred draw. The4sec batch costs3.33times the
1sec batch, with useful unit/linear terminal feedback and a geometric regression.
This supports further targeted resource work, not a universal cutoff or minimum,
calibrated Elo, causal effect or intrinsic prior ranking. Opponent randomness,
different trajectories and exposed adaptive development scope remain. Frozen
failures and success criteria are unchanged. A requested-cost arithmetic typo
3840sec was retained and corrected separately to4800sec, without changing cases.
The raw report records pre-final-save costs:1sec1357writes/813804326bytes/21.152sec;
4sec1223writes/677827406bytes/17.888sec. Console counters after the final pretty
save include that last write and are slightly larger; batch wall excludes it.

The actual unfinished linear game has full-history finite references at8/16/24/32:
actual-child-22/-171/-197/-255cp. The36-choice0.25/1/4sec matrix shows root8 all e3;
root16 geom/linear Ra2(-109) and unit f3(-171) at all times; root24 linear g4(-192)
at0.25 but Kf2(-197) at1/4, unit f4(-334) at all times; root32 all Ke1(-321),
against actual Kg2(-255). Longer game wins do not eliminate fixed early errors.
The qualified leaf counts material only; static positional blindness is a narrow
source-backed hypothesis, not proof of sole cause. A single common positional
residual is a possible next pilot. Old Python2/5 terms used Queen1000 units;
this native comparison fixes Pawn208/report100cp. Direct transfer is not the same
old ablation; name a common scale and approximation before any pilot outcomes.

Twelve40ply actual instrumentation streams paired identical atomic records in
alternating pretty/compact order. All493pairs parsed identically. Pretty costs
182244905bytes/5.527sec; compact114246011bytes/3.871sec:37.3percent fewer bytes,
29.97percent less measured write time. Equality checks1.074sec and third support
frontier writes3.490sec are separate; total operational wall95.584sec includes
dual-writing/verification. This is not a measured production game-speed gain.
The compact per-action writer stays, with schema/atomicity/default final reports
unchanged. Original budget24games replay2554played+96prefixplies; instrumentation
12streams replay480+48. Combined36streams3034+144 have zero legal/state/history
differences. Instrumentation outcomes are excluded from strength comparisons.

Checked full-stock synthetic Shogi still uses held=half board as an approximation.
Originalq0 root has geometric unique finite R@e2 and unit four tied drops. A
declared relocation e5->e7/f3->f5 removes two captured Pawn targets while preserving
stock/file uniqueness/check/eight root actions. Its simple unit-tie prediction
fails underq0; it also uncovers Bishop routes, so no single-cause claim. A
nonchecking Bishop capture ends at static depth2 without the defended recapture.
Existing capture-onlyq2, with the same2ply/2048nodes/10sec per-case conditions,
keeps original geometric R@e2 and shrinks unit best ties to B@e2/R@e2. On the
relocated root it selects geometric B@e2(-58840), unit Kingd2(-100000), each
unique under the matching finite full-window diagnostic. Root choices/scores
match all four explicit depth1 child contexts at ply1, with ordinaryq2 active.
This is useful horizon feedback, not WDL/strength/default promotion.

An inspection error is preserved: fresh maxdepth1 iterative child calls reserve
ordinary qsearch during their first phase. Their configuredq2 labels cannot be
used as root2phase q2 rankings. The supplementary direct contexts explicitly
match phase/ply and retain the original caps; no production reserve policy/API
was changed. Detailed raw counters include node/qnode costs and balanced paths.

`data/chess_budget_continuation_20261007.json` is a small index/summary; ordinary
`../archive/development_budget_20261007/raw.zip` preserves exact raw reports,
with `sources.zip` and manifests verified by unpacked hashes. Do not duplicate
large record bodies into another summary. Its SHA256 is
3b46be945b95b6f3981d7f59de4f503543f9c40de82d291cec6108c357016896.
`data/shogi_capture_horizon_20261007.json` and `shogi_horizon.zip` separately keep
failed masking prediction, naive phase probes and corrected direct observations.
28 adapter/development/record tests pass again; no production code changes.
Native CPU/cache/leaf and exact model-token costs remain unavailable, not zero.
No human-label fitting, Xiangqi holdout read, extra worker, Goal or public push.

## Common activity and targeted time pilot20261007

Before outcomes, declare one nonroyal pseudo-attack union residual:4native
units per unique attacked square, at common Pawn208 (1.923cp/square), all
three frozen tables. It includes friendly occupied and pinned-piece attack
squares, excludes King attacks, and is not legal mobility or king safety.
An isolated Eval object links with original hashed search objects in2.025sec;
pure source/binary remain unchanged. Initial managed execution blocks the
new executable (WinError4551) before the first static control. Retain that
failure; subsequent approval-reviewed execution is reported below, without
changing machine policy or inferring playing strength.

Switch to the declared resource alternative:4sec on check or any legal capture,
otherwise1sec, same rule for all tables. Compare to fixed4sec on the same two
prefixes, colors and1800-configured reference, Threads1/Hash16/160ply maximum.
This policy is independent of scores/outcomes; preserve every positive/adverse
cell, no retuning or extra result-driven cells. On the exposed unfinished
linear history its first40plies would request56rather than80local seconds,
but it is not a positional-evaluation repair.

A recording failure interrupts the third cell after75persisted plies: a
concurrent long PowerShell read of the active single-line JSON holds a Windows
handle and os.replace receives WinError5, including the final save. Previous
evidence remains intact. Preserve the original report, skip that interrupted
cell, continue the remaining declared cells into a separate report. Outcomes
and cost comparisons must separate interrupted/unfinished; paired cost
summaries exclude both members of the interrupted pair. Do not hold an active
large report open during writes; stdout is sufficient progress monitoring.

After the timed batch, normal approval-reviewed execution runs the unchanged
activity build without modifying system policy. All60 independent python-chess
pseudo-attack count, mirror, side-to-move and table controls pass. At exposed
actual root16, activity selectsBa3 for all three tables: finite strong child
proxy-117cp, versus pure geometric/linearRa2-109 and unitf3-171. Thus it helps
unit on this root but preserves an adverse8cp geometric/linear difference.
At root32 all three changeKe1(-321) toKg2(-255). These two finite diagnostic
points motivate prospective small games, not WDL, strength or default promotion;
the coefficient remains the one declared before outcomes, no price tuning.

Declared time pilot retains23 complete game streams and one75ply recording
interruption. Targeted: geometric4wins, linear4wins, unit3wins/1unfinished.
Fixed4: geometric3wins/1recording interruption, linear3wins/1loss,
unit2wins/2unfinished. The interrupted sample is never counted as a draw/loss.
The11complete root/color/table pairs request2124/2236local seconds and measure
2037.102/2130.581search wall seconds: targeted4.387percent less measured local
search time, nodes6804276341/7025187485. Paths are independently stochastic,
small and exposed; not deterministic paired strength/price/Elo validation.
Strong adverse cells remain: open linearBlack249vs148requested seconds;
central geometricBlack243vs108; open unitWhite209unfinishedvs196win.
Targeting is an optional further-development policy, not a default replacement.
Continuation wall4138.920sec covers remaining21games only; its persisted
recording counter70.269sec/3138373051bytes excludes the final write. The first
failed batch's lost action/write cost is unknown; never report it as zero.
All24streams replay2561persisted played+96prefixplies: author/Core legality,
full final histories on23streams, and all budget predicates agree. The partial
stream has legal prefix validation, not a complete terminal-state certificate.

Standard Shogi now has a19ply legal cooperative capture/promotion/drop prefix
from initial full stock/history, ending in a Pawn-protected checking Bishop
drop and five evasions. This is a constructed development control, not a
representative game. At2ply/2048nodes/10sec q0geometric Gd9xd8(-44092) and
unit Rh8xd8(-200000) finish; unitq2 retains choice/score and finishes.
Geometricq2 instead returns a depth1 partial Rh8xd8(+993), time-limited,
with21406runtime pushes. A separately declared symmetric4096node/20sec
continuation retains that failure: depth1,42127pushes; q0andunit results remain.
No more blind extension or defaultq2 promotion. Candidate filtering cost is a
concrete next diagnostic; immediate terminal quiet actions cannot be blindly
excluded. All eight searches retain actual counters and balanced paths.

28related adapter/development/atomic-record tests pass. Production search,
price/defaults and old qualification records remain unchanged. Exact raw
records and inert producer sources are verified ZIPs under
../archive/development_targeted_budget_20261007; the compact data index is
`data/chess_targeted_budget_20261007.json`, SHA256
42b954cdbc1b4c969976d3f0a5f310a612093faf2e2745a00d39b6fa8d460e00.
Native CPU/cache/leaf and exact engineering/model-token costs remain unavailable.
No human fitting, Xiangqi holdout access, worker, Goal or public push.


## Unchanged native attack-union practical comparison20261007

The4-native-unit nonroyal pseudo-attack-union term is an optional standard
Chess development candidate, not a fitted coefficient/default or exact
mobility/king-safety model. Pawn208, all three tables, compiled search/SEE/
ordering/pruning, Threads1/Hash16 remain frozen. Two existing exposed prefixes,
reciprocal colors, pure/activity interleaved produce24fresh1sec games against
Stockfish17.1 limit-strength1800 setting/50000nodes/1sec fuse. Maximum160
subsequent plies is an unfinished frontier, never automatically a draw.

Exact first-cohort replay-derived aggregate: pure6wins3losses3unfinished;
activity10wins0losses2unfinished. Pure per table: geometric2W1L1U,
linear3W1L, unit1W1L2U; activity geometric4W, linear4W, unit2W2U.
Keep adverse central-d unit White: pure wins in71plies, activity reaches160
unfinished. Other same-cell move counts/costs also reverse. Same prefixes,
colors and tables do not ensure the same stochastic game path or deterministic
paired inference. The first session checkpoint hand-transcribed pure as7W3L2U;
the next documentation checkpoint corrects it without erasing that error.

All24streams replay2332played+96prefixplies: whole author/Core legal sets,
full history/final states and per-move binary/mode tags agree. Measured local
search wall593.128sec pure versus524.485sec activity; fewer game search calls
are not per-node efficiency. Total1258.919sec;2358writes,2.668GB cumulative
serialized bytes,58.856sec including final output. Raw persisted counters
exclude final save and are explicitly distinguished in the final index.
Native CPU/cache/leaf counts and exact engineering/model-token cost unknown.

Dot's complete10:06:35 same-thread advice was read among all24posts and
reconciled before adoption. It recommends a fixed early-root union to distinguish
same-root choice changes from different lost game trajectories; it did not
reproduce local controls or games. The fixed stronger-reference and direct
comparison conditions plus fixed sampling rule are in the retained prospective
analysis plan. No extra worker, Goal, coefficient fitting or public push.


Stronger condition was declared separately before execution: only central-d,
three tables, reciprocal colors, both leaves, unlimited Stockfish17.1 with
50000node/1sec fuse, same local1sec. All12games lost (six each leaf).
Replay1178played+48prefixplies zero differences. Total606.606sec. Activity
frequently survived longer, which is not a gain in win rate or independent
strength. Relative local/reference compute is not equal; the candidate/base
conditions are equal. This is an intentional harder opponent, not an Elo test.

Before this stronger batch, fixed sampling selected first local-to-move roots
at/after subsequent16/32 from each stream, with complete history.24roots,
48unchanged1sec leaf searches, fresh unlimited500000node/1sec child diagnostics:
14equal selections (exactly no action difference), eight positive finite cp
deltas, one negative, one separate mate/cp comparison. The8/1count is not an
error rate and a1cp difference is not reliable evidence of improvement.
Adverse unit White root16 chooses h3f4(-40cp) instead of e3f4(-30cp).
The important separate linear Black source-pure root33 comparison is activity
g6g5 with mate-16 reference versus pure g6f5 with-861cp. No conversion of mate
to cp, exact WDL claim or coefficient adjustment. Broader fixed games need not
wait for an all-defense proof; retain this root for focused failure diagnosis.

Reachable Shogi19-ply checked root now has12instrumented same-budget controls:
lexical/noTT, ordering+TT and ordering+TT+orderedq; q0/q2; geometric/unit;
2ply4096nodes20sec, identical approximate half-held inventory. Original lab
Point lacked capture_order_value: four lexical controls survived, first ordered
cell failed. The inert continuation supplies common constant990000 unit
capture priority, lexical capture ties, identical for all models; no human or
model-specific ordering prices. It continues eight unexecuted cells, retaining
original report and interface failure. Production code/defaults unchanged.

Geometric q2 lexical remains depth1/time_limit20.020sec;39747runtime pushes,
37211classification pushes and11.147sec classification. Existing ordering+TT
completes2ply Gold d9xd8 score-74850 in3.647sec,7503classification pushes.
Adding existing orderedq preserves full choice/score,1.804sec and1637classification
pushes (1966total versus7872). This combines q traversal and on-demand
classification; do not attribute all improvement solely to one operation.
Unit q2 complete score-200000 remains, tied root action changes with ordering;
orderedTT0.957sec/1919classification pushes, orderedTTq0.614sec/737pushes.
All paths balance and selected actions match immutable apply. No terminal quiet
moves removed, no new search filter or cap. One constructed root gives a concrete
supported-cost setting, not representative Shogi playing-strength evidence.

The retained linearBlack adverse root is
`r1bq1k1r/pp1nn3/2p2pp1/5P1p/P1BP4/B1P3QN/6P1/4RRK1 b - - 5 19`.
Pure captures the white f5Pawn with g6f5; activity pushes the same g6Pawn to g5.
Both local PVs begin the White reply a3e7; pure reports depth16/2644496nodes,
activity depth15/2410000nodes. Cross-leaf local cp(-437/-473) is not an
independent ranking. The independent finite children above retain the failure,
but the changed leaf can also alter pruning and reachable depth at fixed time.
A future prospectively symmetric root resource curve can distinguish a
persistent adverse choice from a1sec search-frontier effect; do not assert
that the union bonus directly caused the error or silently fix its coefficient.


Direct comparison was separately predeclared to remove the third-party-opponent
condition: same table on both sides, pure/activity reciprocal colors, both
existing prefixes,1sec/Threads1/Hash16/160plies. Activity wins all12games
(four each table);1252played+48prefixplies replayzero. Existing adapter's
uci_reference routing role here is an activity UciMaterial, not Stockfish;
explicit per-side and per-move leaf tags/binary hashes establish the transport.
First replay expected a single whole-game leaf tag and failed KeyError before
writing output; corrected per-move hash check passes, no game rerun. The failed
source and error remain. Total1207.163sec, console1266writes/926.1MB/22.235sec;
persisted pre-final counters are separate. Small exposed timed direct games
justify retaining an optional candidate, not default/Elo or price selection.

Separately declared exposed adverse-root1/4sec symmetric resource diagnostic
retains g6g5 for activity at both budgets (depth15/19); pure changes g6f5 to
c6c5(depth16/18). Fresh1million-node/2sec finite children report g6g5 mate-12,
g6f5-944cp, c6c5-866cp. The earlier500000node mate-16/-861 record is untouched.
No exact mate certificate or automatic coefficient fit. This specific failure
persists when activity reaches greater reported depth than pure; lack of a
single ply at1sec is not an adequate explanation. Investigate the native
search's existing safety/SEE/evaluation coupling on this root next.

Decision: retain the unchanged optional activity candidate and the existing
Shogi orderedTTq setting for further practical development; neither becomes
a production default. Reference1800, unlimited-strength reference and direct
play answer different questions; do not pool them into a strength rating.
All48game streams replay4762played+192prefixplies, zero mismatches;24same-root
pairs and12Shogi controls preserve adverse/partial results. Production source
unchanged. 28related entry/transport/atomic-record tests pass after the observed label
repair; full actual-game parity is the new semantic check.

Compact index: data/chess_activity_games_20261007.json, SHA256
7a2b7a52b49402c87d1892a57ca351c3c47c7b4c87816605d49e4037ba51bb76.
Exact raw records, declarations, failed/inert producers and hash-verified ZIPs
are in ../archive/development_activity_games_20261007. Source/build qualification
links to the preceding targeted-budget index. Native CPU/cache/leaf costs and
exact model-token cost remain unavailable. No public push or scientific completion.
