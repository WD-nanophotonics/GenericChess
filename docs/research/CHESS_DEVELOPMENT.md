# Runnable Chess development comparison

Current objective: useful play with a cheap rule-derived material prior, a fixed
supported search and one comparison entry. This is development, not generic
amateur-strength certification, independent holdout evidence or human-price fitting.

## Run and interpret

```powershell
.venv/Scripts/python.exe -m scripts.chess_development compare --suite docs/research/data/chess_development_suite.json --output .local_agent/compare-new.json
.venv/Scripts/python.exe -m scripts.chess_development play --suite docs/research/data/chess_development_game_starts.json --output .local_agent/games-new.json --max-plies 40
```

Use --help for supported configurations. The preserved entry defaults describe
its original finite depth2/q0 development batch, not the latest isolated native
pilot. Do not silently replace those settings or reproduce frozen evidence with
new defaults. Output refuses overwrite; interrupted/failed records remain evidence.
Source BK answers are exposed reference agreement, not complete tactical/WDL proof.

Full Core history, legal sets, board/rights/EP, terminal states and PV replay must
agree with the executed adapter. Compare methods under the same declared resource
condition or report curves; unfinished is never silently scored as draw. Timed
bestmove is not complete fixed-depth search. Negative outcomes and changed budget
conditions stay visible. Development budget is justified by information per cost.

## Latest actual-play evidence

| Fixed configuration | Observed development result | Evidence |
|---|---|---|
| Native material+4/Pawn208 nonroyal coverage, SinglePV1 |12direct wins; all6strong-reference cells lose | data/chess_activity_games_20261007.json |
| Coverage, MultiPV3 |10W1L1Udirect;24strong-reference losses | data/chess_allocation_20261007.json |
| Restored human-engineered classical leaf, same gc prices/search |22W2Ldirect;10L2Ustrong; ordinary native control1L3U | data/chess_classical_20261007.json |
| Fixed4 royal-zone-pressure pilot |36cells:6W2L4Uactivity,2W10Lclassical,11L1Ustrong reference | data/chess_royal_20261007.json |
| Native old half pseudo hanging-risk plus coverage |36cells:4W1L7Uactivity,1W11Lclassical,11L1Ustrong reference | data/chess_exchange_20261007.json |
| One fixed supported reference option2400, SinglePV1 |exchange4W1L7U;activity6W1L5U;24streams, no established candidate advantage | data/chess_feedback_20261007.json |
| Same half-risk leaf; only8fast SEE arithmetic price reads changed |12direct:2W2L8U;geometric2W2U,linear4U,unit2L2U; no established improvement | data/chess_see_price_20261007.json |
| Arithmetic-only repair vs fresh original at fixed2400 |first24:7W0L5U vs5W2L5U; new6ply-prefix24:8W2L2U vs10W1L1U; signal reverses | data/chess_see_feedback_20261007.json; data/chess_see_opening_20261007.json |
| Half-risk candidate vs classical, equal1sec SinglePV1/MultiPV3, explicit Chess draw policy |24cells:1W9L2D vs3W7L2D; both geometric groups0W4L | data/chess_candidate_allocation_20261007.json |

Classical is a diagnostic benchmark, not the rule-derived candidate. Native human
SEE/pruning thresholds remain a disclosed coupling in material/coverage pilots.
Direct wins, survival and small exposed samples do not establish Elo or isolate
price quality. The classical40streams retain4359played+160prefix plies, zero
replay differences. Verified raw/source packages are linked from each JSON index.

Retained adverse linearBlack root chooses g6g5 despite a finite mate reference;
activity1/4sec retains it, while forced root/child searches and MultiPV avoid it.
The royal and half-risk pilots are optional approximations, not tuned laws or
exact safety. Latest half-risk formula adds (hangingBlack-hangingWhite)/2 to
material+4nonroyal coverage delta, with symmetric integer truncation. Kings
attack/defend but are not discounted; pseudo pins/King legality/EP/exchange limits
remain.37Core/semantic+144native mirror/turn checks pass,4201played+144prefix
replayzero.8exposed roots6same2finite worse, with trace/root overlap disclosed.
Old bad root selects c6c5 at1/4sec; equal finite references mate-16forg6g5 versus
cp-866forc6c5 do not certify safety. No default promotion or coefficient fitting.

Completed fixed2400 feedback uses identical two prefixes/three tables/colors and
local search resources. Its3217played+96prefix plies replay with zero differences.
Stockfish's label is not measured Elo; weakened play can be stochastic. Neither
method saturates the predeclared threshold, and no candidate advantage is shown.
Do not hunt for a tier where it wins. The next isolated contrast fixes only SEE
arithmetic's8price reads, leaving LVA order/capture ordering/thresholds and leaf
unchanged.36fixture predicates and6identical leaf trace pairs pass;8actual roots
2changed. Retained c6c5->g6f5 finite references remain poor. Direct12paired games
finish2W2L8U with1825played+48prefix replayzero; no improvement/default or generic
SEE claim. Both complete evidence packs retain all unfavorable/unfinished cells.

Shogi reachable neighbor q0/q2 often chooses identically at3.3-12x cost, while
some old checked controls differ. Keep targeted q2 optional; Chess/Shogi semantic
boundaries and Xiangqi human holdout remain intact. Science remains OPEN.

## Optional Chess match adjudication

For new play/play-uci batches explicitly declare --claim-chess-draws and, when
needed, --uci-python <existing python-chess import root>. Omission retains the
old canonical Core fixture. The option uses full initial/prefix/played history,
automatic outcomes first, then immediate legal claims before search. A prospective
claim saves its legal witness without playing it. Automatic terminal detection
also runs after the last allowed halfmove; mate precedes the75move rule.
Match decisions and Core final_state are separate, with library version/hash.
Library insufficient-material detection is not proof of every dead position.
See [FIDE9.2/9.3/9.6](https://handbook.fide.com/chapter/E012023).
Do not retrospectively rescore old datasets. The latest48streams had no supported
automatic/claim draw, but the fixture's repetition100000/max1000 is not full
FIDE WDL. Price/search defaults remain unchanged; no stable SEE repair advantage.

## Current candidate diagnosis

Latest actual-loss diagnosis retains three full-history geometric roots and
28identical shared native link objects. At root28 MultiPV changes e5c6 to e5d3;
separate finite child references are cp-136/+145 from White, not WDL. Four
same-root forced-choice continuations use declared2sec native calls: e5c6 loses
and e5d3 draws by insufficient material against classical; both lose against
full reference500000nodes/2sec fuse. This does not isolate the loss cause or
establish broad allocation benefit. Root/static/game contexts and budgets differ.

All28newstreams replay2471played+276prefix plies with zero differences, including
four opening claim draws and one continuation automatic draw. Cost preserves
the lower MultiPV reported depth, actual node/wall/controller CPU counts and
unknown native CPU/cache/scored-leaf counts. No defaults change. Root28 and three
real children contain no protected nonroyal target attacked by a strictly cheaper
priced enemy. Therefore the proposed penalty is not justified by this root;
do not expand or fit it to classical threats after the negative predicate.
Static classical threats/rook/king/passed terms remain diagnostic clues, not new
coefficient targets. Exact records/source recovery are in the portable report
and [verified pack](../archive/development_candidate_allocation_20261007/README.md).
The matched activity/exchange root ablation selects h2h4 for both; preserve the
earlier e5c6 exchange call as timed-choice variability, not a cherry-picked
failure certificate. The104native hanging correction is a static contribution,
not a proven cause. data/chess_candidate_risk_ablation_20261007.json binds source.

## Fixed-prior feedback, 2026-10-07

Two existing6ply prefixes, all three frozen tables and both native colors give
24interleaved exchange/classical streams versus the same reference2400 setting.
Native SinglePV1/Threads1/Hash16/NNUEfalse uses1.5sec; reference500000nodes/1.5sec
fuse, Threads1/Hash16, UCI_LimitStrengthtrue. Fresh engines/hash per cell,
160subsequentplies, explicit immediate Chess claim policy. The reference label
is stochastic and is not measured Elo; old full-strength failures remain intact.

| Frozen table | Half-risk candidate | Classical diagnostic bundle |
|---|---|---|
| geometric_half |3W0L0D1U|3W0L1D0U|
| linear_mixture |2W0L1D1U|4W0L0D0U|
| unit |1W0L2D1U|0W3L0D1U|

The initial candidate-failure expectation is contradicted here:6W3D3U. Classical
7W3L1D1U is not universal improvement; its adverse unit cells are retained.
These differing resources/prefix/draw conditions are not a causal before/after
strength gain. No price choice, coefficient fitting or default admission follows.

A separate8cell direct comparison holds the classical executable/leaf/search
fixed, both players1.5sec, and changes only their configured fixed tables.
Geometric and linear each win4/4 versus unit across the same prefixes/colors.
This is useful fixed-prior deployment feedback within a supported human positional
bundle. Native PSQT/material/SEE/pruning remain price-coupled: not a pure prior
effect, a generic rule-derived position evaluator or independent holdout evidence.
Unit is now a weak/saturated direct control in these cells; the next useful test
must distinguish the unchanged rule priors without fitting or selecting a table.

The separate exposed root28 fixed-node curve uses1M/3M/10Mnodes, fresh hash,
SinglePV1/Threads1/Hash16, full history and10sec safety fuse. All9cells reach the
node budget. Exchange chooses h2h4/e5c6/e5d3, activity h2h4/h2h4/h2h4, classical
e5c6/e5c6/e5d3. This establishes leaf/allocation interaction, not single-term
loss causality. Reused child reference scores remain finite old observations.

Both game cohorts complete:3386played+192prefix plies, full Core/legal sets,
history/selectedPV/finalstate/draw-witness replayzero;19ZIPentries actually
extracted/rehashed. Cohort compute/recording wall3684.630sec; the24stream logger
records2625writes/109001617bytes/11.546sec before final save. Controller CPU,
native-reported nodes/time are separate; native CPU/cache/scored leaves unknown.
Different trajectory lengths prohibit interpreting total nodes as throughput.
Portable record: data/chess_positional_feedback_20261007.json. Exact raw/producers
and recovery index: ../archive/development_positional_feedback_20261007/.

## Historical detail

The full preceding guide, old protocols and failed attempts are preserved in the
[verified cleanup snapshot](../archive/repository_cleanup_20261007/README.md),
original path docs/research/CHESS_DEVELOPMENT.md. Recover the matching source/data
there only when a concrete question needs it; historical suggestions are not a
new branch backlog. [LOCAL_MAINLINE.md](LOCAL_MAINLINE.md) owns current direction.
