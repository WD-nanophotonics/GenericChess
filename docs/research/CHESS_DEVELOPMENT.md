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
