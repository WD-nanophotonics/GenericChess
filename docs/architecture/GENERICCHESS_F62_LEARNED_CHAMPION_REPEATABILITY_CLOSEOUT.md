# GenericChess F62 learned-champion repeatability closeout

Status: complete, negative repeatability result.  This closeout records the
formal F62 run for `GENERICCHESS-F62-LEARNED-CHAMPION-REPEATABILITY`.

## Immutable run identity

- Implementation commit: `5051a71f6f3f7fbc201db832a8fe08d3fcd6c7a9`.
- Parent closeout SHA: `750b0617f925cf7dd3c233330c18cd96327410a2`.
- Formal stage identity: `e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70`.
- Gen1 accepted D0: checkpoint `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`, model SHA `d63f5061a80ff016fd8eb1848f85a1308d0c9bc457b939c3aae1cae39c24b5a5`.
- Gen2: checkpoint `43cdecedb6e6a46cc0543648d8745ec95d3e4a73d08213a668ecf0407655dec1`, model SHA `9a80088c0d220699381cd28ff0b46d5de0bd1382a4af383ff92b4e5bf70789f9`.
- Fresh records SHA: `b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61`.
- Raw formal result: `.generic_chess_flow/f62-learned-champion-repeatability/f62_results.json`; SHA-256 `31B25F0A1DDE0E3BFE1E7A68155CC798CA9123C27FFEB2F07B2DFB07EBB11238`. The raw result remains outside Git.

## Frozen mechanism and decision repeatability

F62 reused the accepted F61 D0 Shogi mechanism: standard semantic Shogi,
generic encoding, width-32 tanh compact residual, `successor_root_q`
perspective, pairwise ranking, seed `59012`, and equal-budget parent/child
Arena. Fit, development, and final source groups were disjoint. Gen2 was
persisted before Arena.

Fresh deterministic decision validation produced 8 roots and 4 changed
search decisions. The changed-decision count is diagnostic of learning
effect; equal-budget Arena is the strength authority.

## Formal Arena outcome

| Stage | Games W-L-D | Pair scores | Mean pair score | Bootstrap interval | Classification gate |
|---|---:|---|---:|---:|---|
| 4 pairs | 2-5-1 | 0, 0.25, 0.5, 0.5 | 0.3125 | [0.125, 0.5] | Not catastrophic; continue |
| 8 pairs | 1-12-3 | 0, 0, 0, 0.25, 0.25, 0.5, 0.25, 0 | 0.15625 | [0.03125, 0.28125] | Stop; below 0.5 |

The 8-pair owner-role split was symmetric in exposure: each child-owner
role played 8 games. Child owner 0 scored 0 wins, 1 draw, 7 losses (0.0625);
child owner 1 scored 1 win, 2 draws, 5 losses (0.25). Search telemetry was
present for every decision and replay validation succeeded. Termination modes
were `node_budget` for 3,740 searches plus one completed search in the 8-pair
stage. Aggregate NPS was 134.09 for Gen2 and 134.37 for Gen1; completed
depth medians were 2 and 1 respectively, with maxima 2 and 12.

Because the 8-pair mean was below 0.5, the frozen stopping rule correctly did
not start the 32-pair confirmation stage. The formal result classification is
`GEN2_NOT_POSITIVELY_COMPETITIVE`.

## Integrity and regression gates

- Re-read the completed 4-pair and 8-pair progress directories through
  `run_arena_resumable`; opening identity, game replay, pair completeness,
  and requested telemetry all validated successfully.
- Verified 4/4 and 8/8 pair counts, swapped child-owner role symmetry,
  decision-change count `4/8`, result SHA, and absence of a 32-pair stage.
- Regression suite passed: `95 passed`.
- `origin/sandbox` was synchronized to the closeout commit; `master` was not
  changed or promoted.

The negative F62 result means this fresh Gen1 -> Gen2 continuation did not
show a monotonic next-generation improvement under the frozen mechanism. It
does not invalidate the separately accepted F61 Gen0 -> Gen1 Shogi gain.
