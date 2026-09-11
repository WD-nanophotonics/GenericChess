# GenericChess F86H static-mate-template kinematic reachability

Status: bounded optimistic kinematic closure. This probe re-enumerated the
validated F86F stripped-defender mate positions under the same static census
contract, normalized them into templates, and tested only empty-board movement
graph reachability from the real generated opening. It used no games, policy
trajectories, BFS expansions, new seeds, teacher/search compute, Heavy, ladder,
training, C2, F85 acquisition, generator rewrite, or new rulesets.

## Frozen authority and census consistency

The four CURRENT ruleset fingerprints were reused unchanged:

| sample | ORTHO4_CURRENT | FULL8_CURRENT |
|---|---|---|
| V4-3 | `ea993a6147595b1ce740cc91ad426a96395edcb6de479c95c23ecc88800a0e17` | `7511327e944c195de71de536f818e8a2028136d4b04123937596f4dce46bda62` |
| V5-3 | `1a256a4fcc763cb6f4e5ca1037a77b72885d4e85a4d5e46ccf88c69f552b266d` | `8d77e9671449b2d6952aa7c80c898d7e390eff0fa534ac8be6d55e7f055ec1d8` |

The F86F static census was re-enumerated with its exact candidate contract:
2,048 candidate checks per cell and 8,192 total. The 1,593 checks were
untruncated and matched F86F exactly:

| cell | F86F validated positions | F86H validated positions | normalized templates |
|---|---:|---:|---:|
| V4-3 ORTHO4_CURRENT | 89 | 89 | 10 |
| V4-3 FULL8_CURRENT | 0 | 0 | 0 |
| V5-3 ORTHO4_CURRENT | 1,262 | 1,262 | 67 |
| V5-3 FULL8_CURRENT | 37 | 37 | 2 |

A template is one validated defender Anchor plus exact ordinary placements,
with the validated attacker Anchor squares merged into an allowed target set.
No F86F mate predicate was changed. V4-3 FULL8 has no validated static mate
template; that is retained as a direct negative result.

## Movement graph and symmetry

For each frozen ruleset, piece type, and owner, the graph has directed edges
from `compiled.empty_mobility[type_id][owner][source]` to each target.
All-pairs shortest paths and canonical shortest-path witnesses use this graph.
Occupancy, check legality, turns, captures, defender ordinary pieces, and
inter-player interference are intentionally ignored, so every result is only
an optimistic necessary-condition analysis.

The generated opening passed owner-swap plus 180-degree symmetry for all four
cells. The empty-mobility graph also passed the same symmetry check:

| cell | opening symmetry | mobility pairs checked |
|---|---|---:|
| V4-3 ORTHO4_CURRENT | pass | 128 |
| V4-3 FULL8_CURRENT | pass | 128 |
| V5-3 ORTHO4_CURRENT | pass | 150 |
| V5-3 FULL8_CURRENT | pass | 150 |

## Type-respecting reachability

Opening ordinary pieces were matched to template ordinary targets only within
the same type. Duplicate types were assigned by exact minimum-distance
permutation, with deterministic tie-breaking. The attacker and defender
Anchors were separately tested on their owner-relative graphs.

| cell | templates | ordinary assignment reachable | both Anchor reachable | joint reachable | min ordinary moves | min attacker Anchor moves | min defender Anchor moves | lower bound <=8 / <=16 / <=32 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| V4-3 ORTHO4_CURRENT | 10 | 0/10 (0) | 10/10 (1) | 0/10 (0) | — | 0 | 3 | 0 / 0 / 0 |
| V4-3 FULL8_CURRENT | 0 | — | — | — | — | — | — | 0 / 0 / 0 |
| V5-3 ORTHO4_CURRENT | 67 | 0/67 (0) | 67/67 (1) | 0/67 (0) | — | 0 | 0 | 0 / 0 / 0 |
| V5-3 FULL8_CURRENT | 2 | 0/2 (0) | 2/2 (1) | 0/2 (0) | — | 0 | 1 | 0 / 0 / 0 |

All 79 validated templates fail the ordinary-piece assignment layer. The
dominant recorded unreachable reason is
`ordinary_movement_graph_unreachable`: 89 validated positions for V4-3
ORTHO4, 1,262 for V5-3 ORTHO4, and 37 for V5-3 FULL8. The artifact retains
the associated type and target-square details. Anchor movement is therefore
not the limiting layer in these cells, but no joint lower bound can be formed
when an ordinary target is graph-unreachable. No canonical joint path witness
exists.

## Routing

The exact per-cell routing is:

```text
V4-3 ORTHO4_CURRENT:
STATIC_MATE_TEMPLATES_KINEMATICALLY_UNREACHABLE_FROM_OPENING

V4-3 FULL8_CURRENT:
NO_VALIDATED_STATIC_MATE_TEMPLATE

V5-3 ORTHO4_CURRENT:
STATIC_MATE_TEMPLATES_KINEMATICALLY_UNREACHABLE_FROM_OPENING

V5-3 FULL8_CURRENT:
STATIC_MATE_TEMPLATES_KINEMATICALLY_UNREACHABLE_FROM_OPENING
```

This is a strong optimistic necessary-condition result for the three cells
with validated templates: even the empty-board, occupancy-ignored movement
graph cannot route the opening ordinary pieces to any validated static mate
template. It does not claim a legal game path or justify changing the
generator yet. The fourth cell has no validated static template to analyze.

## Resource accounting and validation

```text
real games = 0
policy trajectories = 0
BFS expansions = 0
teacher/search compute = 0
F86F candidate checks = 1,593 / 8,192
F86H graph vertices <= 25 per type/owner
F85 actual compute = 0
default generator changed = false
```

Focused tests: **3/3 PASS**. The full bounded regression set passed **57/57 in
3.66s**.

## Durable evidence

- `artifacts/f86h_kinematic_mate_reachability/templates.json`
- `artifacts/f86h_kinematic_mate_reachability/results.json`
- `scripts/f86h_static_mate_template_kinematic_reachability.py`
- `tests/test_f86h_static_mate_template_kinematic_reachability.py`
