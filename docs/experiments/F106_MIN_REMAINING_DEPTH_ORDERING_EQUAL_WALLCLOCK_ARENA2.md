# F106 minimum remaining-depth exact ordering

Work order: `GENERICCHESS_F106_CHESS_MIN_REMAINING_DEPTH_ORDERING_EQUAL_WALLCLOCK_ARENA2`

Baseline: `926dd3147a7414884c560d9f1308010484460999`

Frozen inputs were the parent leaf/value checkpoint
`55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e` and
nonlinear ordering checkpoint
`68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`, with
ordering model SHA256
`855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`.

The exact frozen learned legal-action sort is now gated by
`ordering_min_depth`. The historical/default value is 1; F106 uses 2, so
remaining-depth 1 nodes use ordinary Native ordering while remaining depths
2 and above retain the exact learned sort. `ordering_max_ply` remains -1.
The bound and remaining-depth telemetry are included in engine results,
ArenaConfig, and resumable progress identity. Sorting arithmetic, tie-breaks,
TT/PV semantics, and the parent leaf evaluator remain unchanged.

Diagnostic: 24 frozen F61R4 roots, fresh engine per arm/root, 2,000 nodes,
depth 12, TT8, root-window pruning true. A was ordinary parent ordering, B
was `ordering_min_depth=2`, and C was historical `ordering_min_depth=1`.

- B skipped learned ordering at remaining depth 1 on 2,383 nodes and had
  learned ordering active at remaining depths >=2.
- Ordering elapsed B/C ratio: `0.0764121047` (gate <= `0.50`).
- Total fixed-node wall B/C ratio: `0.3873190248` (gate <= `0.75`).
- Action agreement: A/B 15/24, A/C 17/24, B/C 15/24.
- Principal-line agreement: A/B 15/24, A/C 16/24, B/C 15/24.

The predeclared equal-wall-clock Arena2 used seed 637701, two disjoint
openings, two role-swapped pairs/four games, one second per move, depth 12,
TT8, one worker, root-window pruning, fresh engines, and a 1,000,000-node
ceiling. Pair scores were `[1.0, 0.5]`, mean `0.75`, with candidate
better/tied/worse pairs `1/1/0`. Arena validity was true and the result was:
`MIN_DEPTH_EXACT_LEARNED_ORDERING_EQUAL_WALLCLOCK_SURVIVES`.

Raw evidence is retained outside Git at
`.generic_chess_flow/f106-chess-min-remaining-depth-ordering-equal-wallclock-arena2/summary.json`.
Per Supervisor direction, this is the final Chess ordering micro-variant in
this sequence; no automatic Arena4 or further depth tuning is authorized.
