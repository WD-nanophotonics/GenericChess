# GenericChess F87A-R7 Calibration Closeout

- Baseline: `7cf67307e66abe79f4cac92b5ddcf7985ac07365`
- Scope: cheap T0/T1 calibration only; no training, weight update, Arena, or external engine.
- Frozen samples: two small generated rulesets (`R7-A`, `R7-B`).
- Policies: `random_legal`, `low_node` (64 nodes/depth 4), and `medium_node` (256 nodes/depth 6).
- Bounds: a 6-root T1 action-spectrum probe on two additional frozen rulesets (4,096 nodes/10 seconds), followed by 8 short paired games, 24-ply horizon, 100,000 total internal search-node cap, and 600-second wall cap. The game caps are coarse stop points checked before the next ply or game.

## Result

The expanded T1 probe used 1,663 internal search nodes across 6 new roots from two additional frozen rulesets. Low- versus medium-node action selection disagreed on 2 of 6 roots; with the same 128-node/depth-5 reference budget, the bounded regret proxy mean was 1.4. Terminal candidates use explicit mate-scale/draw values, and an incomplete reference budget defers the probe. This selected short seat-swapped validation as the only next step. The subsequent calibration completed all 8 games in 0.14 seconds using 930 internal search nodes. All 8 games and all 4 seat-swapped pairs were resolved; no game was horizon-censored. Both paired matchups scored 0.5:

| Matchup | Paired score | Result |
| --- | ---: | --- |
| `low_node_score_vs_random_legal` | 0.5 | no repeatable improvement signal |
| `medium_node_score_vs_low_node` | 0.5 | no repeatable improvement signal |

The pre-registered route is `RETURN_T1_ACTION_SPECTRUM_REGRET`. The T1 signal class is `BUDGET_SENSITIVE_ACTION_SPECTRUM`, but T1 remains diagnostic-only and has no standalone admission threshold. The positive route is fail-closed on a complete T1 stage followed by short seat-swapped validation; an incomplete probe cannot pass the stage. No weight-update route is authorized by this calibration. Pair scoring is fail-closed: a matchup can contribute only when both seat-swapped games resolve. The result is diagnostic only: the tiny short-horizon sample did not establish capability growth, and no external engine score was used.

## Evidence

- Manifest SHA-256: `4a02236de1c7531a6406c8b2467636f81337ae405e5e1b99fd10d9c023b4382a`
- Results SHA-256: `d466b6865d8bcf3d5072c92668ae9de57aa3fd1c3b251044d18360c90686e077`

R7 does not alter the F87A promotion decision. Western termination remains deferred and the calibration does not authorize training or promotion.
