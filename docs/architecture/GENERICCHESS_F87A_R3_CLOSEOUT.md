# F87A-R3 Layer-C dynamic playability calibration closeout

This checkpoint records the signed order `GENERICCHESS-F87A-R3-LAYER-C-DYNAMIC-PLAYABILITY-CALIBRATION`.
It is bound to PREP baseline `b424b4795f075e50b8171f0f8f52791fda62f038`, target
`PLAYABILITY`, and the required Layers A-C. F87A-R2 negative and boundary
Common-Tape trajectories were inherited as compact evidence; R3 did not rerun
those 16 games.

## Runtime authority

The positive calibration uses the production semantic runtime:

`compile_semantic_ruleset` → `semantic_engine_for` → `initial_state` /
`apply_action`, with public `SemanticBoardMove`/`SemanticDropMove` projection
sorted by canonical `action_to_dict` JSON. Direct contract checks passed for
legal-action generation, canonical ordering, action application, side-to-move
switching, terminal authority, and position identity on both built-ins.

The legacy `GameSession` adapter remains limited to inherited R2 evidence. No
second rules runtime was introduced.

## Positive calibration

| Ruleset | Policies | Games | Max ply | Dynamic result |
| --- | --- | ---: | ---: | --- |
| Western Chess | canonical Common-Tape random; deterministic material/capture-greedy | 4 | 64 | Layer C PASS |
| Standard Shogi | canonical Common-Tape random; deterministic material/capture-greedy | 4 | 64 | Layer C PASS |

Each policy/ruleset used one opening role-swapped pair. All eight games were
`CENSORED` at the 64-ply cap, so outcome scores are null and excluded from side
bias. Both policies on both rulesets showed captures or checks and material
reduction; neither triggered immediate stalemate collapse, an almost-all
forced-line collapse, or a deterministic short repetition. Opening sensitivity
is `UNMEASURED` because each ruleset has one opening identity. The very-shallow
fixed-evaluator search policy is explicitly `DEFERRED_SCOPE` with zero search
nodes.

## Result status and compute

- Layer A: `PASS`.
- Layer B: inherited mixed negative `FAIL` / boundary and semantic structural `DEFER`; no universal lattice gate was applied.
- Layer C: positive semantic calibration `PASS` for both built-ins; inherited legacy/boundary Layer C remains `DEFER`.
- Layers D/E: `DEFER`.
- Overall report: `CALIBRATION_MIXED_OUTCOMES`; individual built-in reports remain `DEFER` because the shared structural Layer-B admission state is not being redefined by R3.
- New positive games: 8; max ply: 64; search nodes: 0; Arena/training/Heavy/C2/F85/QD/MAP-Elites: 0.

Ignored generated evidence was produced from the committed implementation and
has these SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| `artifacts/f87a_ruleset_qualification/manifest.json` | `11dddf4855f61b7b32a323268acdbd7f4b40ab6f8deec03dfa73c0c6968e7ef5` |
| `artifacts/f87a_ruleset_qualification/summary.json` | `8cad229ffc7d334ac1da689995c836b3f359b1b4deb8fe33d154c0e9b672f367` |
| `artifacts/f87a_ruleset_qualification/reports.json` | `1e6baf2f973cb4a500dcb4d6f5ac2b7630b5fe6f326daed4c85187688c450762` |

No promotion is authorized by this closeout.
