# F124 Reverse Benchmark: Stable Convex Solver

## Scope and frozen inputs

F124 closes the F122/F123 direct-supervision layer with a deterministic
benchmark-local PCG solver. It reuses the exact F122 basis, oracle weights,
corpus generator, splits, normalization, one-ply roots, and search roots. No
production evaluator, ruleset, or search code was changed.

- Baseline: `341e1a895c8b57321086819ba9095634ced3b7ea`
- Implementation checkpoint: `956b3738a24be750206fef12863a876c69ca4384`
- Western Chess corpus identity:
  `79625a972c980c607eb6a9a1b930ebaba2fd447bbe320c52b3ec62ae510b91ac`
- Standard Shogi corpus identity:
  `a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b`
- Heavy run: `f124-stable-v1-3c6e81a7280e`
- Heavy argv digest:
  `e203d2585608c6c7aba527bb13ed314f964971f4a719767746bc469363a965b2`
- Runtime: 3201.625820 seconds
- Transient result SHA-256:
  `028387bdbde91930f5d172d4971c01e066461b547f6a7e81c898681722b50c3b`

The solver is `PCG_DIRECT_LEARNER`: zero initialization, NumPy-only
Jacobi-preconditioned conjugate gradient on

`H theta = b`, where `H = X^T X/n + 1e-6 D`, `b = X^T y/n`, and the intercept
entry of `D` is zero. The stopping criterion is relative residual <= `1e-10`,
with a maximum of `4 * parameter_dimension` iterations. F122 Adam and random
baseline values are retained as report references and were not rerun.

## Numerical gate

| Ruleset | PCG iterations / max | Relative residual | Objective excess vs matched ridge | Parameter distance | Holdout prediction difference (normalized) |
|---|---:|---:|---:|---:|---:|
| Western Chess | 139 / 1248 | 8.70452e-11 | 8.87267e-20 | 2.32667e-09 | 1.52997e-09 |
| Standard Shogi | 771 / 2660 | 9.71837e-11 | 2.41669e-19 | 7.84638e-09 | 6.59503e-09 |

All PCG parameters were finite, Jacobi diagonals were finite and positive,
and both rulesets passed the numerical gate. The matched-ridge reference was
computed analytically only for comparison; PCG independently reached the same
objective.

## Scalar identification

The unchanged F122 scalar gate is holdout normalized RMSE <= 0.05, R2 >= 0.99,
and Pearson >= 0.995. PCG passes it for both rulesets.

### Western Chess

| Split | RMSE | Normalized RMSE | R2 | Pearson | Spearman | Sign agreement | Max absolute error |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 0.002099 | 0.00000270 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.009595 |
| Dev | 23.535149 | 0.03030181 | 0.998556 | 0.999312 | 0.999567 | 1.000000 | 92.084310 |
| Holdout | 25.604509 | 0.03296614 | 0.998913 | 0.999486 | 0.998903 | 0.994667 | 92.175393 |

### Standard Shogi

| Split | RMSE | Normalized RMSE | R2 | Pearson | Spearman | Sign agreement | Max absolute error |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 0.034889 | 0.00000814 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.248609 |
| Dev | 202.291531 | 0.04720554 | 0.996421 | 0.998216 | 0.998337 | 0.994667 | 1169.321427 |
| Holdout | 211.205589 | 0.04928567 | 0.997571 | 0.998823 | 0.997302 | 0.989333 | 663.178577 |

For comparison, the F122 Adam 2K holdout results were Chess RMSE 54.1045,
normalized RMSE 0.0697, R2 0.9951, Pearson 0.9977; and Shogi RMSE 354.7130,
normalized RMSE 0.0828, R2 0.9931, Pearson 0.9967. The F122 random baseline
was far outside the gate in both rulesets.

## Action-ranking recovery

The exact F122 256-root enumeration and unchanged action thresholds were used.

| Ruleset | Top-1 agreement | Pairwise agreement | Mean normalized regret | Median regret | P95 regret | Mean normalized oracle top-2 gap | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| Western Chess | 0.996094 | 0.996690 | 0.00004895 | 0 | 0 | 0.184499 | pass |
| Standard Shogi | 0.972656 | 0.978874 | 0.00000003 | 0 | 0 | 0.179090 | pass |

The original F122 Adam action results were Chess top-1 0.9688 / pairwise
0.9838 and Shogi top-1 0.9414 / pairwise 0.9546; PCG improves both while
preserving the frozen basis and roots.

## Search-recovery diagnostic

The exact F122 64-root, 2,000-node, depth-12 diagnostic was rerun for PCG.
There was no pass threshold for this diagnostic.

| Ruleset | Top-action agreement | PV-head agreement | Mean oracle score gap when different | Node parity | Completed-depth parity |
|---|---:|---:|---:|---:|---:|
| Western Chess | 0.984375 | 0.984375 | 53.9973 | 1.000000 | 1.000000 |
| Standard Shogi | 0.656250 | 0.656250 | 665.8728 | 1.000000 | 0.968750 |

The search result remains diagnostic and does not alter the direct scalar or
action gates.

## Classification and interpretation

Both rulesets, and the overall run, classify as:

`KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES`

This demonstrates that the frozen corpus contains sufficient information, the
handcrafted basis represents the known evaluator, normalization and value
serialization are consistent, and a deterministic direct learner recovers the
scalar and one-ply decision surface. It specifically isolates F122's failure
to the fixed-lr Adam optimizer configuration. It does not establish that
self-play works, that search is an improving teacher, or that the current
generic representation is sufficient.

The next authorized layer is the known handcrafted representation plus known
oracle search teacher. No self-play or production promotion is authorized by
this result.
