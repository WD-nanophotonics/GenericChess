# F63-R1-R2 corrective closeout

Status: corrective implementation complete; candidate Arena execution remains
unauthorized and was not started.

Corrective parent: `db363323a0befb2e68f643f8aa03a3d36c39b5b9`

Corrective checkpoint: `c0c5eeeac7d2a72a211666537ee2c2290963143a`

## Corrections delivered

- A hard per-game wall budget and any remaining stage-wall budget are now
  reduced to the minimum positive deadline and passed into the actual
  `SearchLimits.max_time_seconds` call while retaining the node bound.
- Deadline/time-limited search results are rejected before applying a fallback
  move; elapsed checks remain as an explicit coarse-overshoot backstop.
- `arena_decision_bound` now accepts a predeclared simple mean criterion or the
  F63 mean-plus-`better_pairs > worse_pairs` criterion and emits
  `PASS_LOCKED`, `FAIL_LOCKED`, or `UNRESOLVED`.
- Existing game-v1 identity, replay, exact-once aggregation, lane cap,
  pause/resume, hard-cap behavior, and pair-v1 compatibility are preserved.

## Verification

The bounded focused command passed 29 tests:

```text
tests/test_learning_arena_integrity.py
tests/test_f63r1_game_atomic_arena.py
tests/test_learning_selfplay_arena.py
tests/test_f63_champion_loop_causal_triage.py
```

The sandbox is clean and both local and remote refs are exactly
`c0c5eeeac7d2a72a211666537ee2c2290963143a`. No teacher rerun, candidate
game, Heavy job, promotion, or master write was performed.

Next authorization boundary: prepare the exact candidate-resume compute plan
against this new SHA for Chat and registered-Supervisor review. The plan must
be approved by both before any Heavy launch; this closeout does not approve or
launch it.
