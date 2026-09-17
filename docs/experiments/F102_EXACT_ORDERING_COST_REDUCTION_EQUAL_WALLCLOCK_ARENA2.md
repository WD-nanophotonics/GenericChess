# F102 exact ordering cost reduction and equal-wallclock Arena2

Work order: `GENERICCHESS_F102_CHESS_EXACT_ORDERING_COST_REDUCTION_EQUAL_WALLCLOCK_ARENA2`

F102 added a bounded Native-owned learned-ordering cache keyed by the maintained
exact semantic child state and profile generation. The cache uses 4096 direct
slots, retains the complete structural key for collision validation, and is
owned by the persistent `SemanticSearchEngine` capsule. Cache lookup now
precedes compact dynamic-feature construction, and the compact ordering path
shares the exact dynamic vector with the base ordering evaluator on misses.
Fresh capsules invalidate the cache on profile rebinding; fresh engines/games
do not inherit entries. Search and Arena telemetry expose cache hits, misses,
collisions, hit rate, capacity, and entry size.

Correctness and cost gate:

- Native rebuilt from the updated C source.
- F102 exactness tests passed for 100 deterministic reachable Western positions
  and cache-enabled versus cache-disabled search parity.
- Focused F58, F101, H50b2e, Arena, and F102 tests passed.
- Fixed-node benchmark: 24 positions, 2000 nodes, depth 3, no TT, 48,000
  search nodes per variant. Reference ordering elapsed 68.2422 s; feature
  reuse only 35.4578 s (0.51959x); optimized cache plus reuse 33.5507 s
  (0.49164x). Total wall was 71.2896 s reference versus 36.5928 s optimized
  (0.51330x). All 24 actions, scores, depths, nodes, and root-first-action
  sequences matched. The gate thresholds (ordering <= 0.50x, total <= 0.70x)
  passed.

Arena2:

- Fresh seed `633701`, two openings, target opening plies 2--6, four
  role-swapped games, disjoint from F97--F101 corpora.
- Parent leaf checkpoint:
  `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`.
- Frozen ordering checkpoint:
  `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`.
- 1-second per-move budget, depth 12, TT 8 MiB, one worker, root-window
  pruning enabled, 1,000,000-node safety ceiling.
- Results: pair scores `[0.75, 0.5]`, mean `0.625`; one better pair, one tie,
  zero worse pairs; 1 win, 3 draws, 0 losses. Timing validity passed with
  maximum overshoot 0.0351 s and no truncation.
- Arena ordering telemetry: 2,615,996 actions, 1,329,445 evaluations,
  1,297,539 cache hits, 1,329,445 misses, 1,313,271 collision probes,
  775.6050 s accumulated ordering time, 4096-entry capacity, 2712-byte entry.

Classification: `LEARNED_TREE_ORDERING_EXACT_COST_REDUCTION_SURVIVES`.

Runtime evidence is retained under the ignored
`.generic_chess_flow/f102-chess-exact-ordering-cost-reduction-equal-wallclock-arena2/`
directory.
