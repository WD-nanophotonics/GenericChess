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
