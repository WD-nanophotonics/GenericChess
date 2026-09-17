# F98: Frozen learned tree move ordering Arena4

## Result

F98 completed the fresh four-opening, four-pair/eight-game Arena4 on the
published sandbox baseline `57b1eb3cdab672fee340a497a811f0f3a77c848e`.

- Classification: `RETAIN_FOR_SEPARATE_ARENA8_AUTHORIZATION`
- Ruleset: `A_CANONICAL_WESTERN_CHESS`
- Frozen leaf/value checkpoint: `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`
- Frozen ordering checkpoint: `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`
- Frozen ordering model SHA256: `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`
- F97 policy identity SHA256: `ef31e45b2279f2cd053b781db514f72a546639b59f476a168c9c5678ebe08287`
- Policy implementation identities: `generic_chess/native/semantic_engine.py` = `5c5619577becbafcd181be6243abd6a4ceff231fe2ec5f74771f37391ed42f50`; `generic_chess/_native/native_module.c` = `47a1ed0349f7a7d51b90f92cc199b31226ce8eec893f58028e701585e793016e`

Pre-Arena frozen checks passed: ordinary ordering-disabled path repeatable,
leaf bindings identical, F97 policy identity exact, root-order parity `24/24`,
and direct leaf parity exact.

## Arena4

Configuration was equal AlphaBeta node budget `2,000` per move, max depth 12,
8 MiB TT, one worker, root-window pruning enabled, fresh engine per game, and
opening plies 2--6 with seed `629701`.

Opening position identities, in order:

1. `d246e71cbde6c696d0a892df1950b3c52ecebcedafc94dbfe4eedf27c9fcbe03`
2. `77d94ad0081a8a7c67d33ea18580bcb7dac7d8effa97b824e3283a8bd641e538`
3. `64fac34393cb884c712bbf2bc5f753f63e57a6325bf14d32368340c95e58be5a`
4. `165aaabbe59ea36648707197a2ff8db35cf0085b978a008db895535656d4f8dd`

Pair scores were `[0.5, 1.0, 0.75, 1.0]`, mean pair score `0.8125`, with
3 better, 1 tied, and 0 worse candidate pairs. Game W/D/L was `5/3/0` and
all 8 games completed without no-contest or truncation:

| Pair | Child owner | Terminal result | Plies |
|---:|---:|---|---:|
| 0 | 0 | max_ply | 995 |
| 0 | 1 | max_ply | 995 |
| 1 | 0 | checkmate | 49 |
| 1 | 1 | checkmate | 38 |
| 2 | 0 | checkmate | 45 |
| 2 | 1 | max_ply | 996 |
| 3 | 0 | checkmate | 60 |
| 3 | 1 | checkmate | 79 |

Search totals were 3,251,789 parent nodes and 3,256,361 candidate nodes.
Completed-depth aggregates were parent `{2: 1611, 3: 13, 11: 1, 12: 2}` and
candidate `{2: 1614, 3: 13, 12: 3}`. Beta cutoffs were parent 0 and candidate
0. Learned-ordering overhead was 8,234,825 evaluations, 268,068 ordering
nodes, 8,234,825 ordered actions, and 13,261.5977434 seconds; it is reported
separately and is not treated as equal-wall-clock performance.

F97 Arena2 mean `0.75` is prior-stage context only and is not pooled with this
Arena4 result. The result authorizes consideration of a separately authorized
fresh Arena8; it does not authorize Arena8, promotion, scorer changes, or a
second Arena4 corpus.

Raw Heavy summary: `.generic_chess_flow/f98-chess-learned-tree-move-ordering-arena4/summary.json`.
