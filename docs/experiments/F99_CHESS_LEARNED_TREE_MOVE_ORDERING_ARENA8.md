# F99: Frozen learned tree move ordering Arena8

## Result

F99 completed the fresh eight-opening, eight-pair/sixteen-game Arena8 on the
published sandbox baseline `76aa21964d69c969713afdbd8a084975c4ca2722`.

- Classification: `RETAIN_FOR_SEPARATE_FINAL_CONFIRMATION`
- Ruleset: `A_CANONICAL_WESTERN_CHESS`
- Frozen leaf/value checkpoint: `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`
- Frozen ordering checkpoint: `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`
- Frozen ordering model SHA256: `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`
- F97 policy identity SHA256: `ef31e45b2279f2cd053b781db514f72a546639b59f476a168c9c5678ebe08287`
- Policy implementation identities: `generic_chess/native/semantic_engine.py` = `5c5619577becbafcd181be6243abd6a4ceff231fe2ec5f74771f37391ed42f50`; `generic_chess/_native/native_module.c` = `47a1ed0349f7a7d51b90f92cc199b31226ce8eec893f58028e701585e793016e`

Pre-Arena frozen checks passed: policy identity exact, implementation
identities exact, root-order parity `24/24`, and direct leaf parity exact.

## Arena8

Configuration was equal AlphaBeta node budget `2,000` per move, max depth 12,
8 MiB TT, one worker, root-window pruning enabled, fresh engine per game, and
opening plies 2--6 with seed `630701`.

Opening position identities, in order:

1. `23832aa31e3b3f1c45844cea1e2be3bc101b2e7e444ae2f67e460bb444cc35e8`
2. `89ed5ce0fe2c81afe04351bafc08f1b372d94c614e3cc39681397d4b00c209b5`
3. `dd6202f0f9cf29968ca338a173863e3f918c9b6462db0b7be01c6af994b8f28e`
4. `3f076990fc83fde035487659ce909787e76b38fe681b06898fb9b642be3bfb13`
5. `884cb25ae533f71cc0c26e05230ecdb98cd4faee7e9f95d486a26a4eeb491656`
6. `182ac66d6bfbe2130c6c393f30609002f97706a40008a80e7117fc8ff6ec83aa`
7. `8b29951e48aef050e074d0a4a74c0b046a06a5f213aad562c8f24004f3aee397`
8. `f1b173c0f9b73e6f04d96724d4b98745355624f58a92401fcd47e5f20f443353`

Pair scores were `[0.75, 1.0, 0.75, 0.75, 0.75, 1.0, 0.5, 1.0]`, mean
pair score `0.8125`, with 7 better, 1 tied, and 0 worse candidate pairs.
Game W/D/L was `10/6/0`; all 16 games completed without no-contest or
truncation:

| Pair | Child owner | Terminal result | Plies |
|---:|---:|---|---:|
| 0 | 0 | checkmate | 57 |
| 0 | 1 | max_ply | 994 |
| 1 | 0 | checkmate | 98 |
| 1 | 1 | checkmate | 41 |
| 2 | 0 | checkmate | 59 |
| 2 | 1 | max_ply | 996 |
| 3 | 0 | checkmate | 64 |
| 3 | 1 | max_ply | 997 |
| 4 | 0 | max_ply | 997 |
| 4 | 1 | checkmate | 49 |
| 5 | 0 | checkmate | 84 |
| 5 | 1 | checkmate | 63 |
| 6 | 0 | max_ply | 997 |
| 6 | 1 | max_ply | 997 |
| 7 | 0 | checkmate | 73 |
| 7 | 1 | checkmate | 74 |

Search totals were 6,628,103 parent nodes and 6,637,682 candidate nodes.
Completed-depth aggregates were parent `{2: 3289, 3: 22, 12: 6}` and
candidate `{2: 2374, 3: 941, 4: 1, 5: 1, 12: 6}`. Beta cutoffs were parent
0 and candidate 0. Learned-ordering overhead was 13,034,138 evaluations,
511,767 ordering nodes, 13,034,138 ordered actions, and 18,386.5963348
seconds; it is reported separately and is not treated as equal-wall-clock
performance.

F98 Arena4 mean `0.8125` is prior-stage context only and is not pooled with
this Arena8 result. The result authorizes consideration of a separately
authorized fresh final confirmation; it does not authorize final confirmation,
promotion, scorer changes, or Shogi.

Raw Heavy summary: `.generic_chess_flow/f99-chess-learned-tree-move-ordering-arena8/summary.json`.
