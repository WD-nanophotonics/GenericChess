# F63-R1 game-atomic Arena hardening closeout

Status: implementation checkpoint complete; candidate Arena execution is not
authorized or started.

Parent checkpoint: `99c3fc276a946f0a751d9e2ad47bb0791238fad2`

Implementation checkpoint: `ef4b99f429b9cd7213b7c67db2d7f1abcc066bf4`

## Delivered

- Added versioned `generic-chess-arena-game-progress-v1` files while leaving
  the existing pair-v1 reader and writer unchanged.
- Persisted each completed child-owner game with an atomic replace and an
  identity covering stage/Arena/opening, pair, owner, both checkpoints and
  role budgets, depth, TT, telemetry, and hard caps.
- Added replay, legality, terminal/declaration, final-position, telemetry, and
  stale-identity validation before reuse.
- Made a game the scheduling unit with deterministic exact-once aggregation;
  partial pairs remain resumable and never contribute pair statistics.
- Enforced the bounded game-lane formula and explicit per-game/stage caps,
  pause/resume, and `PAUSED`/`INCOMPLETE` states. A cap hit cannot become a
  draw.
- Added conservative `arena_decision_bound`, including the F63 7/8 result:
  completed total `4.75`, worst mean `0.59375`, worst classes `4/2/2`,
  decision sufficient but strength estimate incomplete.

## Verification

The focused bounded command passed 27 tests:

```text
tests/test_learning_arena_integrity.py
tests/test_f63r1_game_atomic_arena.py
tests/test_learning_selfplay_arena.py
tests/test_f63_champion_loop_causal_triage.py
```

The published sandbox SHA is exactly
`ef4b99f429b9cd7213b7c67db2d7f1abcc066bf4`, with a clean worktree. No
candidate Heavy, teacher rerun, promotion, or master write was performed.

Next authorization boundary: prepare the exact candidate-resume compute plan
for three-party Chat/Supervisor review. Do not approve or execute that plan in
this closeout.
