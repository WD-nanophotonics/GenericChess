# GenericChess F86A-R3 ladder score and symmetry closure

Status: narrow semantic closure candidate. No F85 acquisition, Heavy, C2,
random population scan, formal ladder tournament, or ruleset-family change.

Baseline: `92cdd2337b84f7c04224f5770de30112d8d111e2`.

## Changes

`AgentLadder.evaluate_adjacent_matchups` now accepts the explicit contract
`paired_scores[(weaker, stronger)] = stronger mean score in [0, 1]`. It emits
both raw `stronger_scores` and centered
`adjacent_advantages = stronger_score - 0.5`. `monotonic` requires every
stronger score to exceed 0.5; `skill_discrimination` is the mean positive
advantage only when all adjacent pairs are positive, otherwise zero. Missing
pairs return `None`. The separate `evaluate_ordered_scores` remains a
pre-check for global scores and is not paired evidence.

The owner-rotation diagnostic is renamed to
`swapped_opening_legal_count_equal`. It intentionally makes only the legal
opening-count claim; it does not claim canonical action-set correspondence or
quality evidence. The transformed opening remains available for this weak
symmetry smoke check without introducing a general action-transform layer.

## Exact evidence accounting

Exact focused command:

```text
\.venv\Scripts\python.exe -m pytest tests/test_f86a_minimal_game_benchmark.py tests/test_f85_lane_scaling_calibration.py tests/test_f85_c2_train_teacher_acquisition.py tests/test_benchmark.py -q
```

Result: **32/32 PASS**.

The profile test measures 1 generated ruleset, 3 policy pairs, 6 played
games, 1 tactical probe position, and at most 256 tactical nodes. The direct
probe contract test caps at 32 nodes. F85 actual compute is 0. Wall time is
not promoted as evidence. The clean published checkpoint and unchanged
authority refs are verified separately by the flow gate.

F86A is now closed at this foundation scope. The next route is F86B cheap
quality calibration: a few fixed-seed 4--4/5--5 games, measured first-player
bias, branching/collapse, shallow solvability, draw behavior, and real
adjacent ladder matchups before freezing any population thresholds. F85
Standard Shogi teacher acquisition remains HOLD.
