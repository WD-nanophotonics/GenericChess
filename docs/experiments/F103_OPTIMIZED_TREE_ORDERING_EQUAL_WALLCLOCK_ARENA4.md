# F103 optimized tree ordering equal-wallclock Arena4

Work order: `GENERICCHESS_F103_CHESS_OPTIMIZED_TREE_ORDERING_EQUAL_WALLCLOCK_ARENA4`

F103 evaluated the exact F102 optimized learned full-tree ordering unchanged:
4096-entry direct-mapped Native ordering cache, exact structural collision
validation, and exact dynamic-feature reuse. No scorer, cache capacity,
ordering semantics, depth gating, top-k policy, or model was changed.

Frozen gates:

- Parent baseline commit: `08fd1f6b243b7e2ca408d2ec70510bbf4df9ef1e`.
- Frozen Western ruleset: `A_CANONICAL_WESTERN_CHESS`.
- Leaf/value checkpoint:
  `55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`.
- Ordering checkpoint:
  `68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f`.
- Ordering model:
  `855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`.
- F102 24-root parity remained 24/24; direct leaf parity, cache-enabled versus
  cache-disabled parity, and the fixed-node reference-versus-optimized action,
  score, PV, node, and depth gate all passed.

Arena4:

- Fresh opening seed `634701`, four deterministic openings, target opening
  plies 2--6, disjoint from F97--F102 corpora, and four role-swapped pairs
  (eight games).
- One-second per-move budget, depth 12, TT 8 MiB, one worker, root-window
  pruning enabled, and 1,000,000-node safety ceiling. Fresh engine per game.
- All 8 games completed. Pair scores were `[0.5, 0.75, 0.25, 0.5]`, with
  mean pair score `0.5`: one better pair, two tied pairs, and one worse pair.
  Overall results were 1 win, 6 draws, and 1 loss.
- Timing remained credible: candidate search wall mean `1.01105 s` versus
  parent `1.01034 s`; maximum wall-budget overshoot was `0.037982 s`.
- Candidate averaged `931.60` nodes/search versus parent `2077.76`.
  Ordering telemetry recorded 2,769,842 cache hits, 3,031,785 misses, a
  `0.477425` hit rate, 5,777,609 ordering actions, and 3,137,860 ordering
  nodes. Cache capacity was 4096 entries with 2712-byte entries.
- The arena validity record was structurally valid and had no hard execution
  timeout, but `no_contest_or_truncation` was false because the max-ply
  termination occurred in multiple games.

Classification:
`OPTIMIZED_LEARNED_TREE_ORDERING_EQUAL_WALLCLOCK_ARENA4_REJECTED`.
The required survival condition failed because mean pair score was not greater
than 0.5 and better pairs did not exceed worse pairs. No Arena8, Shogi, or
promotion was authorized.

Runtime evidence is retained under the ignored
`.generic_chess_flow/f103-chess-optimized-tree-ordering-equal-wallclock-arena4/`
directory.
