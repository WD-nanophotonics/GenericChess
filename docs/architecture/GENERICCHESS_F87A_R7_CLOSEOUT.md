# GenericChess F87A-R7 Calibration Closeout

- Baseline: `7cf67307e66abe79f4cac92b5ddcf7985ac07365`
- Scope: cheap T0/T1 calibration only; no training, weight update, Arena, or external engine.
- Frozen samples: two small generated rulesets (`R7-A`, `R7-B`).
- Policies: `random_legal`, `low_node` (64 nodes/depth 4), and `medium_node` (256 nodes/depth 6).
- Bounds: 8 short paired games, 24-ply horizon, 100,000 total internal search-node cap, 600-second wall cap.

## Result

The calibration completed all 8 games in 0.14 seconds using 961 internal search nodes. Both paired matchups scored 0.5:

| Matchup | Paired score | Result |
| --- | ---: | --- |
| `random_legal > low_node` | 0.5 | no repeatable improvement signal |
| `low_node > medium_node` | 0.5 | no repeatable improvement signal |

The pre-registered route is `RETURN_T1_ACTION_SPECTRUM_REGRET`. No weight-update route is authorized by this calibration. The result is diagnostic only: the tiny short-horizon sample did not establish capability growth, and no external engine score was used.

## Evidence

- Manifest SHA-256: `0ff828845c1da500d9a00c5a789880bedb1af9c73e175da67c9671ac045b881d`
- Results SHA-256: `5f48a331859743e9ad4ff500215ea16cabd43de5be84ffc458b88f0fedd8c52d`

R7 does not alter the F87A promotion decision. Western termination remains deferred and the calibration does not authorize training or promotion.
