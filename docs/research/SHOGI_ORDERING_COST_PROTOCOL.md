# Fixed-leaf ordering cost, no outcome comparison

Reuse the complete geometric_half no-ordering row from frozen
shogi_static_search_20261006.json (49 pushes/51 nodes/44 evaluations).
Do NOT rerun that control. One NEW run changes only legacy MoveOrderer on;
depth2/qdepth0, no TT/PVS/native/tactical/fallback and evaluator remain fixed.
Require same full saved reference score/tie membership and all visited physical
positions. Capture heuristic ranks by captured current board weight plus
declared base hand weight minus mover current weight; ignores royals as anchors.
It is a sorting hint only, never a leaf score or extra goal measurement.

Use separate subclass of frozen StaticInventory, no production or old helper
edit. Whole paired cap128 pushes including49 saved baseline pushes,5000
enumerations conservatively including the old whole220+910 enumeration,
15sec including old0.125sec. One candidate search only; no staged picker,
alternate ranking or repeats after outcome. Persist partial result on failure.

Compare deterministic nodes, pushes and evaluations; legacy capture/promotion,
killer/history tie ordering is bundled as the ONE intervention. Old semantic
candidate counts were aggregated across two laws, so no precise per-run
candidate-cost improvement can be asserted. Report full NEW cost separately,
and sorting calls/time; wall timings are not a statistically reliable speedup.
No claims of material strength, full AlphaBetaPlayer adoption or WDL gain.
