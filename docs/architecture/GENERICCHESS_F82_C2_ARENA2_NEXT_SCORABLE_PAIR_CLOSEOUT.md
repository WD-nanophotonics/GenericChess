# F82 C2 Arena2 next scorable pair closeout

Date: 2026-09-14  
Mode: Courier  
Sandbox commit: `2c8d8f6035e3f61aff56242c1c9cb386485d9c7c`

## Approved execution

- Plan: `f82-c2-arena2-next-scorable-v1`
- Plan SHA-256: `1cb2d9a2522c0ca20728c7afed5acb77b5c1ed8d12c29c880fc49a1ec4e7954a`
- Normalized resource-envelope SHA-256: `5a0934eb4f332851ad3aafb8958276c754490187e69f45967c4f1afcf983e972`
- Registered Arena2 corpus: `6eca12faa0981e1c71f637eae7f66ee4a053193a752fbe592d2b0edafbdffd2a`
- Registered opening index: `1`
- Search: 512 nodes/move, depth 12, TT 8 MiB, fresh TT each move, two workers
- Caps: 262144 nodes/game, 512 plies/game, 7200 seconds/game and stage

The tracked runner used the existing candidate/parent identity gates and an
isolated progress/result directory. The first bounded invocation left two
valid partial checkpoints; the same approved command resumed them without
changing candidate, corpus member, or search parameters.

## Pair result

Result artifact: `.generic_chess_flow/f82-c2-arena2-next-scorable/result.json`

- Status: `COMPLETE`
- Completed games/pairs: `2` / `1`
- Pair score: `0.5`
- Game aggregates: 1 child win, 0 draws, 1 child loss
- Owner-0: 352 plies, `checkmate`, winner `1`; artifact SHA-256
  `61d717ae5a924044b1c6a7c36e777f1a6dd91bccbb98009b054954bf362251ea`
- Owner-1: 292 plies, `checkmate`, winner `1`; artifact SHA-256
  `cb0d6fdeed413e057435e4f3e1cfb0af51df4ce95c1a336049359a3404dc4a44`

Both role-swapped games are scoring results; neither is `NO_CONTEST`. This is
the first valid direct strength pair after the v6 no-contest pair was excluded.
The result is descriptive only: no Arena4/Arena8/final-confirmation run or
promotion was attempted. Any enlargement remains subject to Chat's next order
and a new exact compute approval.
