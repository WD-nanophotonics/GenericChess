# F123 Reverse Benchmark: Identifiability and Optimizer Diagnosis

## Scope and immutable inputs

F123 diagnoses the F122 known-evaluator benchmark without changing production
evaluator, search, rulesets, or teacher paths. It reuses the exact F122 corpus
generator, feature basis, oracle, train/dev/holdout counts, and seeds.

- Baseline checkpoint: `4bce37cccad7d0891dd90888f28a88c4b53624dd`
- Implementation checkpoint: `f6de114c1e5f2a957dc9e673d6f643ab3bc56a54`
- Corpus counts: train 3000, dev 750, holdout 750
- Scalar gate: holdout normalized RMSE <= 0.05, R2 >= 0.99, Pearson >= 0.995
- Adam: full-batch, normalized train design/target, learning rate 0.01,
  weight L2 `1e-6`, 2,000 steps for the F122 reproduction and zero-init
  control, 20,000 steps for the longer convergence run
- Conditional action gate: unchanged F122 ranking thresholds; action ranking
  is run only when ZERO_INIT_2K or F122_RANDOM_20K passes the scalar gate.

Heavy run `f123-ident-v2-4c589f438857` completed with exit code 0 in
113.600276 seconds. Its argv digest was
`a0b209563d9c3a108a8e2e5e0ee6c32c84e41b731e67a9cc57f6302c8b1469cb`, and the
transient result SHA-256 was
`bb751d0babe14ab1e7d4138811f372863460d5d6903a872dbd93deaa9029ea78`.

## Matrix and coverage diagnostics

| Ruleset | Raw features | Train-active features | Train constants | Design shape | Numerical rank | Nullity | Condition number |
|---|---:|---:|---:|---|---:|---:|---:|
| Western chess | 332 | 311 | 21 | 3000 x 312 | 307 | 5 | 32.1033 |
| Standard shogi | 1086 | 664 | 422 | 3000 x 665 | 652 | 13 | 452.4134 |

The exact material dependencies hold in train, dev, and holdout for every
material type: `material_diff:type` equals the sum of its square occupancy
differences. The train-constant feature contribution is far below the F123
coverage limit of normalized RMS 0.05:

| Ruleset | Dev normalized RMS | Holdout normalized RMS | Holdout features becoming variable |
|---|---:|---:|---:|
| Western chess | 0.00001512 | 0.00006315 | 2 |
| Standard shogi | 0.00005431 | 0.00005037 | 44 |

Therefore `F122_TRAIN_COVERAGE_IDENTIFIABILITY_LIMIT_SUPPORTED` is not
supported by this run.

## Scalar results

The matched ridge solves the Adam objective exactly: mean squared normalized
loss plus `1e-6` weight L2, with the intercept excluded from regularization.
The historical closed form retains F122's raw Gram matrix and weak `1e-8`
ridge. The min-norm model is the SVD pseudoinverse solution.

### Western chess

| Model | Holdout RMSE | Normalized RMSE | R2 | Pearson | Scalar gate |
|---|---:|---:|---:|---:|---|
| Matched ridge 1e-6 | 25.6045 | 0.032966 | 0.998913 | 0.999486 | pass |
| Historical closed form | 25.6028 | 0.032964 | 0.998913 | 0.999486 | pass |
| Min norm | 25.6044 | 0.032966 | 0.998913 | 0.999486 | pass |
| F122 random-init 2K | 54.1045 | 0.069660 | 0.995147 | 0.997743 | fail |
| Zero-init 2K | 58.4789 | 0.075292 | 0.994331 | 0.997372 | fail |
| F122 random-init 20K | 52.8413 | 0.068034 | 0.995371 | 0.997849 | fail |

### Standard shogi

| Model | Holdout RMSE | Normalized RMSE | R2 | Pearson | Scalar gate |
|---|---:|---:|---:|---:|---|
| Matched ridge 1e-6 | 211.2056 | 0.049286 | 0.997571 | 0.998823 | pass |
| Historical closed form | 211.0792 | 0.049256 | 0.997574 | 0.998825 | pass |
| Min norm | 211.1880 | 0.049282 | 0.997571 | 0.998823 | pass |
| F122 random-init 2K | 354.7130 | 0.082774 | 0.993149 | 0.996676 | fail |
| Zero-init 2K | 350.3293 | 0.081751 | 0.993317 | 0.996727 | fail |
| F122 random-init 20K | 348.4695 | 0.081317 | 0.993388 | 0.996779 | fail |

The matched ridge and historical closed form both pass in both rulesets, so
the requested regularization-bias classification is not supported. The
longer Adam run improves the F122 reproduction but still fails the unchanged
scalar gate in both rulesets.

## Convergence and null-space evidence

The final F122 random-init 20K optimizer states were close in training-row
space but retained large parameter null-space components. The 2K and 20K
trajectories were recorded at steps 0, 10, 100, 500, 1000, 2000, 5000,
10000, and 20000 for the long run; the 2K runs recorded the first six.

| Ruleset / model | Objective at final checkpoint | Gradient L2 | Null-space parameter norm | Null-space fraction |
|---|---:|---:|---:|---:|
| Chess random-init 2K | 7.748956e-6 | 0.0162714 | 0.676135 | 0.999998 |
| Chess random-init 20K | 5.997466e-6 | 0.0136907 | 0.644056 | 0.999997 |
| Shogi random-init 2K | 1.815287e-6 | 0.0051435 | 0.136442 | 0.969581 |
| Shogi random-init 20K | 3.969349e-7 | 0.0004975 | 0.132399 | 1.000000 |

The 20K run does not pass, and zero initialization does not pass or remove
the failure. The matched ridge does pass, while Adam remains separated from
that optimum in holdout predictions (Chess 27.3232 RMSE units for random 20K;
Shogi 155.7768). This isolates optimizer dynamics / convergence, rather than
train coverage or a broad basis inability, as the supported diagnosis.

## Classification and next-step boundary

Both rulesets classify as:

`F122_ADAM_OPTIMIZER_DYNAMICS_FAILURE_SUPPORTED`

Not supported:

- `F122_FAILURE_REGULARIZATION_BIAS_SUPPORTED`
- `F122_FAILURE_INSUFFICIENT_ADAM_CONVERGENCE_SUPPORTED` (20K still fails the
  scalar gate)
- `F122_FAILURE_INITIALIZATION_NULLSPACE_TRANSIENT_SUPPORTED`
- `F122_TRAIN_COVERAGE_IDENTIFIABILITY_LIMIT_SUPPORTED`

Neither conditional action model passed the scalar gate, so no action-ranking
or search-teacher stage was run. Per the F123 order, no next search-teacher
stage is authorized until direct scalar supervision passes.
