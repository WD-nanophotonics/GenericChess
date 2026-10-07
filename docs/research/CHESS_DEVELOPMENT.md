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
| Fixed4 royal-zone-pressure pilot | Original36cells unfinished verification; direct6W2L4U, classical2W10L replayzero | Private .local_agent/royal-20261007, pending final portable index |

Classical is a diagnostic benchmark, not the rule-derived candidate. Native human
SEE/pruning thresholds remain a disclosed coupling in material/coverage pilots.
Direct wins, survival and small exposed samples do not establish Elo or isolate
price quality. The classical40streams retain4359played+160prefix plies, zero
replay differences. Verified raw/source packages are linked from each JSON index.

Retained adverse linearBlack root chooses g6g5 despite a finite mate reference;
activity1/4sec retains it, while forced root/child searches and MultiPV avoid it.
The royal pilot checks one approximation, not a weight sweep or exact safety law.
Current formula: material+4*(nonroyalCoverageDelta-pressureWhite+pressureBlack),
King zone=current square+one-step pseudo squares, including occupied neighbors.
Current semantic checks25actual roots/children+108static controls pass; no default
promotion. Finish its declared reference, same-root and recording checks unchanged.

Shogi reachable neighbor q0/q2 often chooses identically at3.3-12x cost, while
some old checked controls differ. Keep targeted q2 optional; Chess/Shogi semantic
boundaries and Xiangqi human holdout remain intact. Science remains OPEN.

## Historical detail

The full preceding guide, old protocols and failed attempts are preserved in the
[verified cleanup snapshot](../archive/repository_cleanup_20261007/README.md),
original path docs/research/CHESS_DEVELOPMENT.md. Recover the matching source/data
there only when a concrete question needs it; historical suggestions are not a
new branch backlog. [LOCAL_MAINLINE.md](LOCAL_MAINLINE.md) owns current direction.
