# F101: Learned tree ordering equal-wall-clock Arena2

## Result

F101 completed the fresh two-opening, two-pair/four-game equal-wall-clock
Arena2 with the frozen evaluator and learned full-tree ordering. The timing
extension was implemented in `generic_chess/learning/arena.py`; it adds an
explicit `ArenaConfig.move_time_seconds`, binds timing mode and budget into
game progress identity, passes the budget through `SearchLimits.max_time_seconds`,
and records wall time around the complete `engine.search()` call.

- Baseline: `d808fdcf31b410b7580425e8a1054f93f15ac6cc`
- Ruleset: `A_CANONICAL_WESTERN_CHESS`
- Leaf/value checkpoint: `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`
- Ordering checkpoint: `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`
- Ordering model SHA256: `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`
- Policy identity SHA256: `ef31e45b2279f2cd053b781db514f72a546639b59f476a168c9c5678ebe08287`
- Policy implementation identities: `generic_chess/native/semantic_engine.py` = `5c5619577becbafcd181be6243abd6a4ceff231fe2ec5f74771f37391ed42f50`; `generic_chess/_native/native_module.c` = `47a1ed0349f7a7d51b90f92cc199b31226ce8eec893f58028e701585e793016e`
- Timing implementation identity: `generic_chess/learning/arena.py` SHA256 is recorded in the raw summary.

Pre-Arena checks passed: frozen identities exact, leaf bindings identical,
frozen root parity `24/24`, direct leaf parity exact, and the two final
opening identities were disjoint from F97, F98, F99, and the preserved F100
opening corpus.

## Equal-wall-clock Arena2

Configuration was a 1.0-second intentional per-move search budget for both
arms, a non-binding 1,000,000-node safety ceiling, max depth 12, 8 MiB TT,
one worker, fresh engine per game, and opening plies 2--6 with seed `632701`.

Opening position identities, in order:

1. `2d3f956ec0b6302844a51fed710bbfd1834e7ada7f63ba329aac18698c0f27b2`
2. `c3f8226386e1efcf5fde66885efc0817ba34e284ee3a705dc086727472188c3e`

Pair scores were `[0, 0.25]`, mean pair score `0.125`, with 0 better, 0 tied,
and 2 worse candidate pairs. Game W/D/L was `0/1/3` and all games completed:

| Pair | Child owner | Terminal result | Winner | Plies |
|---:|---:|---|---:|---:|
| 0 | 0 | checkmate | 1 | 62 |
| 0 | 1 | checkmate | 0 | 45 |
| 1 | 0 | checkmate | 1 | 127 |
| 1 | 1 | max_ply | — | 997 |

The comparison was valid: every action was legal, no hard execution timeout,
no no-contest/truncation, and no search reached the node ceiling. Requested
time termination counts were parent `615` and candidate `614`. Maximum wall
budget overshoot was `0.02394730001105927` seconds; the per-role wall-time
means were parent `1.008476349837264` seconds and candidate
`1.0083550325198274` seconds, with p95 values `1.0157272999931592` and
`1.0160268000036012` seconds respectively.

Search-node totals were parent `1,309,776` and candidate `338,703`, or
`2,126.2597402597403` and `550.7365853658537` nodes per search. Completed
depth aggregates were parent `{2: 596, 3: 19, 12: 1}` and candidate
`{1: 70, 2: 536, 3: 7, 4: 1, 12: 1}`. Learned-ordering overhead was
`431,733` evaluations, `34,751` ordering nodes, `431,733` ordered actions,
and `448.7837838` seconds.

Classification: `LEARNED_TREE_ORDERING_EQUAL_WALLCLOCK_REJECTED`. The frozen
ordering did not retain practical strength when both arms received the same
per-move wall-clock budget. No timing sweep, equal-node confirmation, transfer
run, or promotion was performed.

Focused F101 contract tests passed: `tests/test_f101_equal_wallclock_arena.py`.

Raw Heavy summary: `.generic_chess_flow/f101-chess-learned-tree-ordering-equal-wallclock-arena2/summary.json`.
