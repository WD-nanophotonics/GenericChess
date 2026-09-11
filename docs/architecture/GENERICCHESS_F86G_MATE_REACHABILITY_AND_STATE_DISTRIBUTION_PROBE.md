# GenericChess F86G mate reachability and state-distribution probe

Status: bounded reachability probe complete. No Anchor or placement changes,
new rulesets, new random seeds, learned evaluator, teacher/search compute,
Heavy, ladder, training, C2, F85 acquisition, admission thresholds, or
default-generator rewrite were used.

## Frozen cells and tapes

The probe uses only the four current cells, loaded from tracked serialized
artifacts:

| sample | ORTHO4_CURRENT | FULL8_CURRENT |
|---|---|---|
| V4-3 | `ea993a6147595b1ce740cc91ad426a96395edcb6de479c95c23ecc88800a0e17` | `7511327e944c195de71de536f818e8a2028136d4b04123937596f4dce46bda62` |
| V5-3 | `1a256a4fcc763cb6f4e5ca1037a77b72885d4e85a4d5e46ccf88c69f552b266d` | `8d77e9671449b2d6952aa7c80c898d7e390eff0fa534ac8be6d55e7f055ec1d8` |

The exact F86E-R1 common tapes were reused from
`artifacts/f86e_r1_common_policy_replay/policy_tapes.json`:

```text
algorithm = python_random_mt19937_random_floor_index_v1
V4-3: A=8624301, B=8624302
V5-3: A=8625301, B=8625302
```

Each cell ran A/B and B/A, max ply 32: 8/8 replay trajectories. HOME cells
were not used.

## Per-state trajectory probe

Every inspected state records side to move, ordinary material remaining by
owner, legal action count, current check, legal checking-move count, legal
mate-in-one count, enemy Anchor-zone size, ordinary-only attacked squares and
coverage, ordinary attack on the enemy Anchor, capture occurrence, and
coverage delta across captures. Legal checking and mate-in-one counts come
from real Core child transitions and terminal results; pseudo-attacks are not
used to declare a legal child.

The shared legal-child probe cap was 4,096. It inspected 788 children and did
not truncate. The eight trajectories inspected 230 states in total:

| cell | states | current-check states | legal checking moves | mate-in-one moves | captures | max ordinary-zone coverage | capture coverage deltas |
|---|---:|---:|---:|---:|---:|---:|---|
| V4-3 ORTHO4_CURRENT | 63 | 0 | 0 | 0 | 4 | 0.25 | 0, 0, 0, 0 |
| V4-3 FULL8_CURRENT | 57 | 2 | 3 | 0 | 5 | 0.25 | -0.167, -0.222, 0, 0.056, -0.25 |
| V5-3 ORTHO4_CURRENT | 66 | 3 | 7 | 0 | 3 | 0.25 | -0.2, 0, 0 |
| V5-3 FULL8_CURRENT | 44 | 1 | 3 | 0 | 1 | 0.333 | -0.167 |

No common-tape trajectory reached a legal mate-in-one. Capture deltas are
mixed in FULL8 and non-positive in the listed ORTHO4 paths; this bounded
sample does not support the stronger `CAPTURE_INDUCED_MATE_CAPACITY_COLLAPSE`
route.

## Cooperative shallow reachability

For each current cell, a generic BFS starts at the real generated opening,
expands all legal actions for both sides, retains full `GameState` and path
semantics, uses canonical legal-action order, performs no unsafe Position-only
deduplication, and stops at the first checkmate or at depth 8 / 8,192 state
expansions.

| cell | first check depth | first checkmate depth | expansions | deepest completed depth | frontier | node truncated |
|---|---:|---:|---:|---:|---:|---|
| V4-3 ORTHO4_CURRENT | 7 | — | 8,192 | 7 | 0 | yes |
| V4-3 FULL8_CURRENT | 5 | — | 8,192 | 5 | 22,391 | yes |
| V5-3 ORTHO4_CURRENT | 2 | — | 8,192 | 7 | 0 | yes |
| V5-3 FULL8_CURRENT | 2 | — | 8,192 | 5 | 24,820 | yes |

Total state expansions were 32,768/32,768, with every cell node-truncated
before a checkmate was found. No cell result is interpreted as a global
unreachability proof.

## Routing

The current evidence is:

```text
MATE_REACHABILITY_UNRESOLVED_DUE_TO_STATE_CAP
```

The state cap prevents deciding whether a shallow cooperative mate exists.
The trajectory layer shows some checks and zero mate-in-one opportunities, but
that is not enough to distinguish a missed state distribution from a deeper or
blocked legal path. Capture coverage is retained for the next bounded
diagnostic, without attributing a causal collapse from this sample.

## Exact validation and resource accounting

```text
\.venv\Scripts\python.exe -m pytest tests/test_f86a_minimal_game_benchmark.py tests/test_f86b_quality_calibration.py tests/test_f86c_generator_viability.py tests/test_f86d_mobility_ablation.py tests/test_f86e_anchor_placement_ablation.py tests/test_f86e_r1_common_policy_replay.py tests/test_f86f_ordinary_mate_capacity_census.py tests/test_f86g_mate_reachability_probe.py tests/test_f85_lane_scaling_calibration.py tests/test_f85_c2_train_teacher_acquisition.py tests/test_benchmark.py --tb=no
```

Result: **52/52 PASS**. Replay trajectories: 8. Real new random seeds: 0.
Legal-child probes: 788/4,096. Cooperative expansions: 32,768/32,768.
Teacher/learned search compute: 0. F85 actual compute: 0. The default
generator and frozen rulesets remain unchanged.

## Durable evidence

- `artifacts/f86g_mate_reachability/trajectory_probe.json`
- `artifacts/f86g_mate_reachability/cooperative_reachability.json`
- `tests/test_f86g_mate_reachability_probe.py`
