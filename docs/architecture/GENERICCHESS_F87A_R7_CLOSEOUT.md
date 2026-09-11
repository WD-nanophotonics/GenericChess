# GenericChess F87A-R7 Calibration Closeout

- Baseline: `7cf67307e66abe79f4cac92b5ddcf7985ac07365`
- Scope: cheap T0/T1 calibration only; no training, weight update, Arena, or external engine.
- Frozen samples: two small generated rulesets (`R7-A`, `R7-B`).
- Policies: `random_legal`, `low_node` (64 nodes/depth 4), and `medium_node` (256 nodes/depth 6).
- Bounds: 8 short paired games, 24-ply horizon, 100,000 total internal search-node cap, 600-second wall cap.

## Result

The calibration completed all 8 games in 0.14 seconds using 930 internal search nodes. All 8 games and all 4 seat-swapped pairs were resolved; no game was horizon-censored. Both paired matchups scored 0.5:

| Matchup | Paired score | Result |
| --- | ---: | --- |
| `low_node_score_vs_random_legal` | 0.5 | no repeatable improvement signal |
| `medium_node_score_vs_low_node` | 0.5 | no repeatable improvement signal |

The pre-registered route is `RETURN_T1_ACTION_SPECTRUM_REGRET`. No weight-update route is authorized by this calibration. Pair scoring is fail-closed: a matchup can contribute only when both seat-swapped games resolve. The result is diagnostic only: the tiny short-horizon sample did not establish capability growth, and no external engine score was used.

## Evidence

- Manifest SHA-256: `0ff828845c1da500d9a00c5a789880bedb1af9c73e175da67c9671ac045b881d`
- Results SHA-256: `34519462119a8627c93006a6164d5896a838ae2f66abaac84d603bf76ef4ece2`

R7 does not alter the F87A promotion decision. Western termination remains deferred and the calibration does not authorize training or promotion.
