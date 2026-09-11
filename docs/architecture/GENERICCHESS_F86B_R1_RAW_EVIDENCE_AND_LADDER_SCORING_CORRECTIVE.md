# GenericChess F86B-R1 raw evidence and ladder-scoring corrective

Status: corrective closure candidate using only the frozen F86B sample. No
new ruleset, seed, budget, Heavy job, C2 fit, or large scan was added.

Baseline: `efe782c52b859c4dc430e36ff38b2dc4f7af2521`.

## Corrections

The ladder runner now receives `stronger_name` explicitly. Seat swapping only
changes player assignment; it never changes which named agent receives the
stronger-player score. The existing six ladder games were rerun with the same
G4-A ruleset, pair seeds, and budgets. The corrected stronger mean scores
remain 0.5 for all three adjacent pairs because these short games terminate
as draws/stalemates; this is an honest calibration result, not a skill claim.

The quality measurement path now aggregates both games in every policy pair.
Each ruleset therefore has `paired_game_count=2`, `played_game_count=4`, and
`metric_game_count=4`. `results.json` durably stores all 12 raw quality-game
records, including sample ID, pair index, policy A/B seeds, seat assignment,
plies, terminal status, winner, first-player score, and branching sequence.

## Frozen sample and exact counts

The rulesets and fingerprints are unchanged:

- G4-A / board 4 / seed 860401 / ordinary 2 /
  `a67e1fef5ff9e5d8e3aea778f7dbe40a71dc80844707264247ac9ddd5affe6be`;
- G4-B / board 4 / seed 860402 / ordinary 3 /
  `0a83a730e02343439f3926c6e86564fc48a8ba2b1437cced54d667ea43531750`;
- G5-A / board 5 / seed 860501 / ordinary 3 /
  `a3ef34cad53f9908e95827e80af3f83d53c29ca724049a15cc1b48092c24ee6e`.

The rerun contains 12/12 durable quality-game records, 6 policy pairs, and
6/6 durable ladder-game records. All three rulesets remain dominated by
stalemate in this fixed sample; the profiles remain `UNRESOLVED`, and no seed
was changed in response to that result. Tactical probes remain 3 positions,
526 actual nodes total, with depth ≤4 and per-probe cap 256. Ladder actual
search nodes remain 183. F85 actual compute remains 0.

## Exact evidence

```text
\.venv\Scripts\python.exe -m pytest tests/test_f86a_minimal_game_benchmark.py tests/test_f86b_quality_calibration.py tests/test_f85_lane_scaling_calibration.py tests/test_f85_c2_train_teacher_acquisition.py tests/test_benchmark.py -q
```

Result: **34/34 PASS**. Wall time is not promoted as evidence. The artifact
files are `artifacts/f86b_quality_calibration/rulesets.json` and
`artifacts/f86b_quality_calibration/results.json`.

The fixed sample shows strong stalemate/draw pathology and no shallow solve;
it does not justify changing the generator or declaring benchmark admission.
The next route is F86C minimal-generator viability population probing to
separate unlucky seeds from a generator-distribution problem before any
formal threshold calibration. F85 remains HOLD.
