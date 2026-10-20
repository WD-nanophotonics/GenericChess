# Task2612 — shared-receipt learner cost scan

Status: cost path complete; research OPEN. No fitness evaluation, terminal W/L label, or learned parameter was analyzed or emitted.

## Fixed scope

Four deterministic identifier-only seeds were paired across TreeStrap and TDLeafEpisode. Each arm started from the same eight-ply random legal opening for its seed, used the same task2492 `AlphaBeta`/`Receipt` implementation, and routed a fixed uniform foe on the other color. Candidate and foe nodes both counted toward each 100,000-node arm cap. The global wall cap was 900 seconds. There was no held-out evaluation or finite-WDL arm.

## Result

Attempt4 completed eight arms and used 800,000 total search nodes in 111.982 seconds. Each arm reached its 100,000 combined-node cap and had one incomplete final budget-limited search; those records remained censored. TreeStrap processed 36,903 internal-bound samples; TDLeafEpisode observed 2,208 complete candidate receipts and received `None` at every game end. The final record contains timing, nodes, search counts and sample counts only; it stores neither W/L nor weights.

- TreeStrap: four 100k-node arms, mean 14.132 seconds per arm (range 12.814–15.215), 4,341 complete and 4 incomplete searches.
- TDLeafEpisode(.95): four 100k-node arms, mean 13.861 seconds (range 12.998–14.946), 4,416 complete and 4 incomplete searches.

The observed difference is small and order-confounded: TreeStrap was run first for each seed. Treat this as path feasibility, not a robust update-overhead comparison or a learning/strength result.

## Preserved attempt history

Attempt1 stopped before the first search because the new runner called a nonexistent `ChessEnv.restore`; this was a script/API error, not an environment fault. Attempt2 used the same inputs but stopped at its 64-ply limit well below the node cap; its `ending` field was inaccurate and is corrected in its interpretation note without rewriting raw output. Attempt3 used one game per arm and ended at a terminal state before reaching the node cap; terminal labels were censored. Attempt4 continued paired games under the same 100k-node and 900-second caps and reached the node cap. All attempts and failures are retained.

## What this establishes

The same frozen AlphaBeta/Receipt path can drive both learner interfaces, and a fixed-foe runner can charge both actors under a bounded node budget. It does not establish how either learner changes W/L. Cost remains to be measured for the common held-out evaluation path and the finite-WDL proposal-selection arm before a complete protocol is registered. The earlier `task2492/run.py` remains unsuitable unchanged because it uses the candidate model for every actor (self-play).

See `attempt-4/plan.json`, `attempt-4/registration.json`, `attempt-4/started.json`, `attempt-4/cost_scan.py`, `attempt-4/arms.jsonl`, and `attempt-4/result.json`; exact raw attempt outputs remain preserved.
