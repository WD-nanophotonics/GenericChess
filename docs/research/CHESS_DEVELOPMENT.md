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

## Historical detail

The full preceding guide, old protocols and failed attempts are preserved in the
[verified cleanup snapshot](../archive/repository_cleanup_20261007/README.md),
original path docs/research/CHESS_DEVELOPMENT.md. Recover the matching source/data
there only when a concrete question needs it; historical suggestions are not a
new branch backlog. [LOCAL_MAINLINE.md](LOCAL_MAINLINE.md) owns current direction.
