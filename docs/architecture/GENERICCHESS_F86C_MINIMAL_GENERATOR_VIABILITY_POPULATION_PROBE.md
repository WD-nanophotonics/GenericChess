# GenericChess F86C minimal-generator viability population probe

Status: bounded viability probe complete. No admission thresholds, ladder
tournament, training, Heavy job, C2 fit, or F85 work was run.

## Frozen eight-seed sample

The exact preregistered seeds and serialized rulesets are retained in
`artifacts/f86c_generator_viability/rulesets.json`; no seed was replaced:

| sample | board | seed | ordinary/side | fingerprint |
|---|---:|---:|---:|---|
| V4-2 | 4 | 861401 | 2 | `1b8547501a45ebc1344f7134319ed215de09a51dfb001270dc127e77528698ac` |
| V4-3 | 4 | 861402 | 3 | `7e2ff9e15c2a0d1be5faa8c6697f22e488976a2d2ae9f077b85c6e71f95ff400` |
| V4-4 | 4 | 861403 | 4 | `864e9aaf0f36b0a94024454a357e6787b3edd9cfd81898d1bea76dfc591b08d0` |
| V4-5 | 4 | 861404 | 5 | `9a5f3de7a492fa4fa01ca1b4c2e7a11b24403cde87b79761b26e212d13221f24` |
| V5-2 | 5 | 861501 | 2 | `ddacec0f6b6fbffeb9135fbbbb658093d92ce0e5bce28665a87022b702d815d6` |
| V5-3 | 5 | 861502 | 3 | `d6e47a6fe19ab20538a1ec9539597b5765d0211cb608b15c262613a86e635297` |
| V5-4 | 5 | 861503 | 4 | `580475d4c25b8d5bb9d796902d383ac673bd00c3565e4609d07443bcc338ad04` |
| V5-5 | 5 | 861504 | 5 | `c3fa844c61ea944f9fd11560f00878337389f427a59d84958c312e38d5494d31` |

All 8 seeds generated successfully. Each ruleset ran exactly one policy pair
(A/B and B/A), max ply 32: 16 real games total, with every raw game saved in
`artifacts/f86c_generator_viability/results.json`. Each ruleset also ran one
bounded terminal-only probe (depth ≤4, nodes ≤256): 8 positions and 1,331
actual probe nodes total, under the 2,048-node ceiling.

## Observed viability

The terminal distribution was **16 stalemates, 0 decisive games**:

- decisive fraction: 0.0;
- stalemate fraction: 1.0;
- repetition fraction: 0.0;
- max-ply unresolved fraction: 0.0;
- all eight quality profiles remain `UNRESOLVED` by admission policy.

Per-sample game lengths were V4-2: 15/17, V4-3: 12/12, V4-4: 2/4,
V4-5: 9/6, V5-2: 12/13, V5-3: 15/12, V5-4: 16/15, and V5-5: 14/15.
Opening legal counts ranged from 2 to 8. Branching-collapse fractions ranged
from 0.0 to 1.0. These are raw viability observations, not threshold claims.

The evidence supports the routing label
`GENERATOR_DISTRIBUTION_STALEMATE_DOMINATED` for this fixed 8-seed probe.
It is not sufficient to claim that every possible seed is pathological, but
it is sufficient to stop expanding population or running a ladder tournament
before inspecting the generator mechanism. In particular, deleting the
stalemate rule or hand-picking winning seeds would invalidate the probe.

## Exact evidence

```text
\.venv\Scripts\python.exe -m pytest tests/test_f86a_minimal_game_benchmark.py tests/test_f86b_quality_calibration.py tests/test_f86c_generator_viability.py tests/test_f85_lane_scaling_calibration.py tests/test_f85_c2_train_teacher_acquisition.py tests/test_benchmark.py -q
```

The F86B scorer preflight directly covers stronger wins/losses from seat 0 or
1 and draws. The F86C artifact tests cover all eight frozen seeds and budget
accounting. Result: **37/37 PASS**. F85 actual compute is 0; wall time is not
promoted as evidence.

Routing after this probe should inspect the generator distribution and its
causes (placement, occupancy, anchor mobility, atom mixture, and capture
mobility) before any formal admission thresholds. F85 Standard Shogi teacher
acquisition remains HOLD.
