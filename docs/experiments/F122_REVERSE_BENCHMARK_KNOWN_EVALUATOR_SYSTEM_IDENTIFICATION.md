# F122 reverse benchmark: known evaluator system identification

Date: 2026-09-19  
Baseline: `98eb06c8af40c22282a31c976cd84eb253c72854`  
Implementation checkpoint: `742f4a26fdf6dc38a633e2a8e9ad99e0ce931347`  
Heavy run: `f122-known-eval-v2-da1f83a45850`  
Heavy argv digest: `329896c47a987ae96144686f5fffd265a045728dd833a72eb9682e894ff3b5fa`

## Result

The final classification is:

```text
overall:       REVERSE_BENCHMARK_DIAGNOSTIC_REQUIRED
western chess: REVERSE_BENCHMARK_LEARNING_PIPELINE_FAILURE_SUPPORTED
standard shogi:REVERSE_BENCHMARK_LEARNING_PIPELINE_FAILURE_SUPPORTED
```

The benchmark is diagnostic-only. It does not modify the production evaluator,
Arena, self-play, AlphaBeta, MCTS, teacher, or ruleset-generation paths.

## Frozen protocol

The benchmark uses a separate deterministic handcrafted feature extractor and
direct oracle labels `V*(s) = w* · phi(s)` for canonical Western Chess and
Standard Shogi. It collects 3,000 train, 750 dev, and 750 holdout reachable
positions per ruleset using seeded legal random playouts with trajectory lengths
8, 24, 64, 128, 192, and 256. The corpus is deduplicated by canonical position
identity.

| ruleset | corpus seed | identity SHA-256 | features | oracle-weight SHA-256 | constant train features |
| --- | ---: | --- | ---: | --- | ---: |
| Western Chess | 1220101 | `79625a972c980c607eb6a9a1b930ebaba2fd447bbe320c52b3ec62ae510b91ac` | 332 | `77cfc280d9108a461629e9de492b71d8257213fc8088ce69c1584232c2668ec9` | 21 |
| Standard Shogi | 1220201 | `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b` | 1086 | `dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316` | 422 |

Features are standardized using train-only means/scales, constant train
features are dropped deterministically, and targets use train-only mean/std.
Adam is full-batch, 2,000 steps, learning rate 0.01, L2 1e-6; the closed-form
ridge solution is diagnostic only. Random baselines use a deterministic
untrained normalized linear model (seeds 1221111 and 1221211).

## Scalar identification

RMSE is in oracle units. Normalized RMSE is divided by the holdout oracle
standard deviation. Metrics are shown for train/dev/holdout RMSE and holdout
normalized RMSE, R², Pearson, Spearman, nonzero-sign agreement, and maximum
absolute error.

### Western Chess

| model | train RMSE | dev RMSE | holdout RMSE | holdout nRMSE | holdout R² | Pearson | Spearman | sign agreement | max abs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| random | 13158.7266 | 15686.8653 | 15533.7819 | 19.9999 | -398.9978 | -0.0084 | -0.0079 | 0.4933 | 65885.6161 |
| Adam | 2.8367 | 51.1402 | 54.1045 | 0.0697 | 0.9951 | 0.9977 | 0.9963 | 0.9853 | 201.0109 |
| closed form | 0.0000 | 23.5311 | 25.6028 | 0.0330 | 0.9989 | 0.9995 | 0.9989 | 0.9947 | 92.1525 |

Adam scalar gate: fail. Closed-form scalar gate: pass. Adam action gate:
pass. Classification: `REVERSE_BENCHMARK_LEARNING_PIPELINE_FAILURE_SUPPORTED`.

### Standard Shogi

| model | train RMSE | dev RMSE | holdout RMSE | holdout nRMSE | holdout R² | Pearson | Spearman | sign agreement | max abs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| random | 86439.9888 | 94560.3013 | 89908.5214 | 20.9805 | -439.1820 | 0.0522 | -0.0512 | 0.4333 | 365528.3078 |
| Adam | 6.8285 | 296.2092 | 354.7130 | 0.0828 | 0.9931 | 0.9967 | 0.9934 | 0.9760 | 1102.2141 |
| closed form | 0.0000 | 202.0722 | 211.0792 | 0.0493 | 0.9976 | 0.9988 | 0.9973 | 0.9893 | 662.2047 |

Adam scalar gate: fail. Closed-form scalar gate: pass. Adam action gate:
pass. Classification: `REVERSE_BENCHMARK_LEARNING_PIPELINE_FAILURE_SUPPORTED`.

## One-ply action ranking

Each ruleset uses 256 fresh scalar-holdout roots and complete legal actions.
Regret is normalized by holdout oracle standard deviation.

| ruleset | model | top-1 | pairwise | mean regret | median regret | p95 regret | mean oracle top-2 gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Western Chess | random | 0.1328 | 0.5343 | 0.3779 | 0.1638 | 1.2149 | 0.1845 |
| Western Chess | Adam | 0.9688 | 0.9838 | 0.0001 | 0.0000 | 0.0000 | 0.1845 |
| Standard Shogi | random | 0.0977 | 0.4998 | 0.3720 | 0.2240 | 1.3738 | 0.1791 |
| Standard Shogi | Adam | 0.9414 | 0.9546 | 0.0000 | 0.0000 | 0.0000 | 0.1791 |

Adam passes the specified action gates in both rulesets.

## Search recovery diagnostic

The shared fresh-transposition-table negamax uses 2,000 nodes and maximum
depth 12 for 64 roots per ruleset. This probe has no pass/fail threshold.

| ruleset | model | top-action/PV-head agreement | mean oracle score gap if different | node parity | depth parity |
| --- | --- | ---: | ---: | ---: | ---: |
| Western Chess | random | 0.1406 | 11019.6825 | 1.0000 | 0.5156 |
| Western Chess | Adam | 0.8281 | 54.2072 | 1.0000 | 1.0000 |
| Standard Shogi | random | 0.0469 | 54216.1077 | 1.0000 | 0.5469 |
| Standard Shogi | Adam | 0.6406 | 951.5525 | 1.0000 | 0.8906 |

## Interpretation

The closed-form scalar fit passes the holdout gate in both rulesets, while the
fixed 2,000-step Adam fit misses the normalized-RMSE threshold in both. Action
ranking nevertheless passes for Adam in both rulesets. Under the prescribed
classification, this supports a learning-pipeline-specific failure rather
than a corpus/basis underdetermination. The next investigation should isolate
the fixed Adam optimization configuration and its interaction with the large
Shogi feature basis; it should not begin generic self-improvement.

The raw JSON result and Heavy runtime logs are transient ignored evidence at
`.generic_chess_flow/f122-reverse-benchmark-result.json` and
`.generic_chess_flow/heavy-runs/f122-known-eval-v2-da1f83a45850/`.
