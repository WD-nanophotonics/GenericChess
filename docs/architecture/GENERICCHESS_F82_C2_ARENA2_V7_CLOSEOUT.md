# F82 C2 Arena2 v7 closeout

- Published implementation SHA: `7afd51bbb41751364268aed7376869de55ef174d`
- Heavy run: `f82-c2-arena2-v7-df3c30d50cd3`
- Plan: `f82-c2-arena2-v7`, SHA `b3810f720f48f572d4fc9f04637e9a9f8dc30c0faed4d0e3c5620a47568691c6`
- Resource envelope SHA (normalized): `b1adaebe92bc54bd9c9b0da076d45fc66ab4d01ac8971b195324fe48ff687912`
- Approved command argv digest: `b4aa892aac76ec746459a2ed187b6c477bc86934db6baf53c8f459b6db2933cb`

## Outcome

The approved continuation reused the existing atomic `game-000000-owner-0.json` checkpoint and held candidate, parent, opening corpus, seed, 512 nodes/move, depth 12, TT 8 MiB, one lane, and the effective one-game workload fixed. The Heavy monitor completed successfully within the 130-minute outer bound, but the Arena result remained `INCOMPLETE`: `completed_games=1`, `completed_pairs=0`, `reason=stage_wall_seconds`. No owner-1 terminal checkpoint was written, so no complete role-swapped pair or C2 playing-strength observation was obtained.

The run's execution caps were `per_game_wall_seconds=7200` and `stage_wall_seconds=7200`. The v6 identity-only failure was corrected before v7 by separating semantic progress identity from operational execution caps; the existing owner-0 manifest remains bound to its original 3600-second identity while v7 executes with the approved extended wall bound. No candidate, corpus, search, resource-lane, or promotion state changed.

## Verification

Focused regressions passed before publication:

```text
tests/test_f63r1_game_atomic_arena.py
tests/test_f82_c2_parent_anchored_repeatability.py
16 passed
```

The result is insufficient for a strength conclusion. Further continuation requires a new Chat work order and a newly bound compute approval if the wall-time boundary is changed again.
