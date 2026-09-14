# F82 C2 Arena4 next scorable pair closeout

Date: 2026-09-14  
Mode: Courier  
Sandbox commit at execution: `bedf235aa7b96994e5442155bb7648872cd36d81`

## Approved execution

- Plan: `f82-c2-arena4-next-scorable-v1`
- Plan SHA-256: `8390f4f43c04d2d57320e26a7987d073839ee5d62f3a2c3044ede43fc46b034e`
- Normalized resource-envelope SHA-256: `df2eda86c79c52f32b652ff2a65788203e3e9dc86a7d28173bd3857a907f8803`
- Registered Arena4 corpus: `593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1`
- Registered opening index: `0`
- Search: 512 nodes/move, depth 12, TT 8 MiB, fresh TT each move, two workers
- Caps: 262144 nodes/game, 512 plies/game, 7200 seconds/game and stage

The tracked runner reused the candidate/parent identity gates and isolated the
one-pair progress/result path. No remaining Arena4 pair or later funnel stage
was scheduled.

## Pair result

Result artifact: `.generic_chess_flow/f82-c2-arena4-next-scorable/result.json`

- Status: `COMPLETE`
- Completed games/pairs: `2` / `1`
- Pair score: `0.5`
- Game aggregates: 1 child win, 0 draws, 1 child loss
- Owner-0: 178 plies, `checkmate`, winner `1`; artifact SHA-256
  `c5ffed23851757518e5dacd91bd50b8df2a025562051b5c99e1eac05f027ca4b`
- Owner-1: 166 plies, `checkmate`, winner `1`; artifact SHA-256
  `56f51e138a7f6fad0fe5186e15635c3dbf0fa195ec8c85c69f73478f254eb245`

Both role-swapped games are scoring results; neither is `NO_CONTEST`. Together
with the valid Arena2 pair, this provides two valid direct-strength pairs, both
scoring `0.5`. The result remains inconclusive and descriptive: no remaining
Arena4 pairs, Arena8/final-confirmation run, or promotion was attempted. Any
further enlargement requires Chat's next order and a new exact compute approval.
