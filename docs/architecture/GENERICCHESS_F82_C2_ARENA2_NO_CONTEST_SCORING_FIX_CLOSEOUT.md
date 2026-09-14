# F82 C2 Arena2 no-contest scoring-fix closeout

Date: 2026-09-14  
Mode: Courier  
Sandbox commit: `9a4210bcf77485742e902a957dbaa84d71c4c455`

## Work order

The v6 Arena2 pair exposed a measurement defect: `NO_CONTEST/restart` was
being treated as a draw because every winner-less game returned `0.5` child
points. Chat directed the minimum mainline repair: keep no-contest explicit,
exclude any role-swapped pair containing it from strength statistics, and add
regression coverage before obtaining another scorable Arena2 pair.

## Implemented contract

- `ArenaGameResult.child_points` returns `None` for `result == "no_contest"`.
- `ArenaPairResult.child_pair_score` returns `None` when either role-swapped
  game is no-contest; such pairs are not scoring pairs.
- Arena summaries and decision bounds consume only scoring pairs, so a
  no-contest cannot become a draw, a half-point, or a strength decision.
- Empty scoring sets produce a zeroed summary instead of invoking bootstrap on
  an empty sample.

## Verification

The published focused suite passed (`35 passed`):

```text
tests/test_learning_arena_integrity.py
tests/test_f63r1_game_atomic_arena.py
tests/test_f82_c2_parent_anchored_repeatability.py
```

No Heavy run, Arena4/Arena8 expansion, or promotion was attempted. The next
Arena2 run must use the already registered corpus/search parameters and obtain
a pair whose two role-swapped games are both scoring results.
