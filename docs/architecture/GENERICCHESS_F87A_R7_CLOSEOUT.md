# GenericChess F87A-R7 Calibration Closeout

- Baseline: `7cf67307e66abe79f4cac92b5ddcf7985ac07365`
- Scope: cheap T0/T1 calibration only; no training, weight update, Arena, or external engine.
- Frozen samples: two small generated rulesets (`R7-A`, `R7-B`).
- Policies: `random_legal`, `low_node` (64 nodes/depth 4), and `medium_node` (256 nodes/depth 6).
- Bounds: a 4-root T1 action-spectrum probe (4,096 nodes/10 seconds), followed by 8 short paired games, 24-ply horizon, 100,000 total internal search-node cap, and 600-second wall cap. The game caps are coarse stop points checked before the next ply or game.

## Result

The bounded T1 probe used 842 internal search nodes across 4 roots. Low- versus medium-node action selection disagreed on 1 of 4 roots, but the candidates were re-evaluated with the same 128-node/depth-5 reference budget and the bounded regret proxy was 0.0; this selected short seat-swapped validation as the only next step. The subsequent calibration completed all 8 games in 0.14 seconds using 930 internal search nodes. All 8 games and all 4 seat-swapped pairs were resolved; no game was horizon-censored. Both paired matchups scored 0.5:

| Matchup | Paired score | Result |
| --- | ---: | --- |
| `low_node_score_vs_random_legal` | 0.5 | no repeatable improvement signal |
| `medium_node_score_vs_low_node` | 0.5 | no repeatable improvement signal |

The pre-registered route is `RETURN_T1_ACTION_SPECTRUM_REGRET`. The positive route is fail-closed on a complete T1 probe followed by short seat-swapped validation; an incomplete probe cannot pass the gate. No weight-update route is authorized by this calibration. Pair scoring is fail-closed: a matchup can contribute only when both seat-swapped games resolve. The result is diagnostic only: the tiny short-horizon sample did not establish capability growth, and no external engine score was used.

## Evidence

- Manifest SHA-256: `4dc01978f579dcec844b3f30caabaa35887298e3764dfcddd8947dbb696886f1`
- Results SHA-256: `e38915f8a6098f3de5b6ae2b8c3d4aa82fa267a524ca1372cfa2add312571408`

R7 does not alter the F87A promotion decision. Western termination remains deferred and the calibration does not authorize training or promotion.
