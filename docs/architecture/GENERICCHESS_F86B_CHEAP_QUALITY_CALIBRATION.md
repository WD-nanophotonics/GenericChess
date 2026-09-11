# GenericChess F86B cheap quality calibration

Status: bounded calibration complete. This is calibration evidence, not an
admission decision. F85 Standard Shogi teacher acquisition remains HOLD.

## Frozen sample

The sample was frozen before quality results were inspected and retained in
`artifacts/f86b_quality_calibration/rulesets.json`:

| sample | board | seed | ordinary pieces/side | ruleset fingerprint |
|---|---:|---:|---:|---|
| G4-A | 4 | 860401 | 2 | `a67e1fef5ff9e5d8e3aea778f7dbe40a71dc80844707264247ac9ddd5affe6be` |
| G4-B | 4 | 860402 | 3 | `0a83a730e02343439f3926c6e86564fc48a8ba2b1437cced54d667ea43531750` |
| G5-A | 5 | 860501 | 3 | `a3ef34cad53f9908e95827e80af3f83d53c29ca724049a15cc1b48092c24ee6e` |

No seed was replaced because of observed behavior.

## Bounded run

Each ruleset used two deterministic policy pairs (A/B and B/A), four played
games per ruleset, and max ply 32. Totals were 3 generated rulesets, 6 policy
pairs, and 12 random/legal games. Each ruleset contributed one bounded
terminal-only probe at depth ≤4 and ≤256 nodes: 3 probe positions and 526
actual probe nodes total (ceiling 768).

The measured profiles are in `artifacts/f86b_quality_calibration/results.json`.
All three profiles remain `UNRESOLVED`; the observed side-bias magnitude was
0.0 in this tiny paired sample. This is not evidence that the ruleset family
is generally unbiased.

The G4-A adjacent ladder smoke used the existing generic alpha-beta path and
the same evaluator configuration:

- `very_shallow`: max 16 nodes, depth 2;
- `low_node`: max 64 nodes, depth 4;
- `medium_node`: max 256 nodes, depth 6.

It ran three adjacent seat-swapped pairs (random/legal vs very-shallow,
very-shallow vs low-node, low-node vs medium-node), six games total, and
reported stronger mean score 0.5 for each resolved pair. The actual search
node total was 183. This is a plumbing/calibration result, not a strength
claim; the sample is too small to freeze skill or admission thresholds.

## Exact evidence

Command:

```text
\.venv\Scripts\python.exe -m pytest tests/test_f86a_minimal_game_benchmark.py tests/test_f86b_quality_calibration.py tests/test_f85_lane_scaling_calibration.py tests/test_f85_c2_train_teacher_acquisition.py tests/test_benchmark.py -q
```

Result: **34/34 PASS**. F85 actual compute was 0. Wall time was not promoted
as scientific evidence. No Heavy job, C2 fit, large scan, or search-trained
agent run occurred.

The next decision is population calibration (F86C): determine how many
rulesets are needed to freeze explicit side-bias, shallow-triviality,
forced-line, search-explosive, draw-dominated, and skill-discrimination
thresholds. F86B does not produce `QUALIFIED_GENERAL`.
