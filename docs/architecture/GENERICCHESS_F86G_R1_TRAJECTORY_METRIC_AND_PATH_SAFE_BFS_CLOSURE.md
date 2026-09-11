# GenericChess F86G-R1 trajectory metric and path-safe BFS closure

Status: bounded corrective closure. F86G's primary routing remains valid, but
the original capture-delta field and truncated-frontier accounting were
retired. This R1 reuses the exact F86G scope and closes those implementation
defects without increasing any scientific or compute bound.

## Frozen scope

The four CURRENT cells and their exact fingerprints were reused unchanged:

| sample | ORTHO4_CURRENT | FULL8_CURRENT |
|---|---|---|
| V4-3 | `ea993a6147595b1ce740cc91ad426a96395edcb6de479c95c23ecc88800a0e17` | `7511327e944c195de71de536f818e8a2028136d4b04123937596f4dce46bda62` |
| V5-3 | `1a256a4fcc763cb6f4e5ca1037a77b72885d4e85a4d5e46ccf88c69f552b266d` | `8d77e9671449b2d6952aa7c80c898d7e390eff0fa534ac8be6d55e7f055ec1d8` |

The exact F86E-R1 common policy tapes were reused:

```text
algorithm = python_random_mt19937_random_floor_index_v1
V4-3: A=8624301, B=8624302
V5-3: A=8625301, B=8625302
```

The probe used A/B and B/A for each cell: 8/8 trajectories, max ply 32,
with no new random seeds. The legal-child cap stayed at 4,096; no Heavy,
ladder, teacher, training, C2, F85 acquisition, generator rewrite, new
ruleset, or admission-threshold work was performed.

## Corrected trajectory metrics

Actions are ordered by the canonical JSON representation of `action_to_dict()`
before both tape selection and child probing. Each state now records ordinary
Anchor-zone coverage for both owners. A capture records the captured owner and
piece type, that owner's pre-capture coverage, post-capture coverage, and the
same-owner post-minus-pre delta. The enemy-Anchor attack flag explicitly tests
the enemy Anchor square rather than the minimum index in the Anchor zone.

The eight trajectories inspected 215 states and 867 legal children, with no
probe truncation:

| cell | states | current-check states | legal checking moves | mate-in-one moves | captures | max ordinary-zone coverage | same-owner capture deltas |
|---|---:|---:|---:|---:|---:|---:|---|
| V4-3 ORTHO4_CURRENT | 40 | 0 | 0 | 0 | 6 | 0.25 | 0, 0, 0, 0, 0, 0 |
| V4-3 FULL8_CURRENT | 47 | 1 | 1 | 0 | 6 | 0.25 | 0, 0, 0, 0, 0, 0 |
| V5-3 ORTHO4_CURRENT | 62 | 1 | 7 | 0 | 3 | 0.5 | 0, 0, 0 |
| V5-3 FULL8_CURRENT | 66 | 2 | 3 | 0 | 4 | 0.333 | 0, 0, 0, 0 |

No trajectory reached a legal mate-in-one. The corrected same-owner capture
data does not support capture-collapse routing.

## Path-safe cooperative BFS

Before deduplication, all four cells explicitly asserted:

```text
repetition_policy == "draw"
no continuous-check history dependency
semantic_actions == ()
automatic_adjudications == ()
```

Only this probe uses the guarded reachability key
`(Position, ply_count, repetition_counts)`. On a duplicate key, the retained
and candidate history representatives must have identical terminal status and
canonical legal-action signatures. A mismatch fails closed and reruns with
deduplication disabled; the key is not promoted to a global transposition
contract. The dedicated tests cover both equivalent representatives with
different history labels and the mismatch fail-closed path.

The depth cap remained 8, each cell cap remained 8,192 expansions, and the
total remained 32,768:

| cell | generated children | unique enqueued | duplicate-pruned | expansions | completed depth | unexpanded current frontier | generated next frontier | exact truncation reason |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| V4-3 ORTHO4_CURRENT | 26,491 | 26,491 | 0 | 8,192 | 7 | 18,300 | 0 | state cap with unexpanded current frontier |
| V4-3 FULL8_CURRENT | 36,321 | 36,321 | 0 | 8,192 | 5 | 3,921 | 24,209 | state cap with unexpanded current frontier |
| V5-3 ORTHO4_CURRENT | 8,523 | 8,515 | 8 | 8,192 | 7 | 324 | 0 | state cap with unexpanded current frontier |
| V5-3 FULL8_CURRENT | 38,157 | 38,157 | 0 | 8,192 | 5 | 7,386 | 22,580 | state cap with unexpanded current frontier |

All four cells remained node-truncated with no checkmate witness. The real
unexpanded frontier is now retained in the artifact; no truncated result uses
the former ambiguous `frontier=0` convention.

The routing remains fail closed:

```text
MATE_REACHABILITY_UNRESOLVED_DUE_TO_STATE_CAP
```

Because all cells still hit the unchanged node cap, this R1 does not claim
either mate unreachability or a baseline-distribution miss. No larger BFS cap
is authorized by this closure; the next permitted diagnostic, if ordered, is
the static F86F mate-template optimistic kinematic analysis.

## Validation and accounting

```text
\\.venv\\Scripts\\python.exe -m pytest tests/test_f86a_minimal_game_benchmark.py tests/test_f86b_quality_calibration.py tests/test_f86c_generator_viability.py tests/test_f86d_mobility_ablation.py tests/test_f86e_anchor_placement_ablation.py tests/test_f86e_r1_common_policy_replay.py tests/test_f86f_ordinary_mate_capacity_census.py tests/test_f86g_mate_reachability_probe.py tests/test_f85_lane_scaling_calibration.py tests/test_f85_c2_train_teacher_acquisition.py tests/test_benchmark.py --tb=no
```

Result: **53/53 PASS in 4.58s**. The R1-specific focused tests
cover corrected capture fields, exact frontier accounting, guarded dedup
preconditions, canonical action ordering, and duplicate-representative safety.
New random seeds = 0; teacher/learned search compute = 0; F85 actual compute =
0; default generator unchanged.

## Durable evidence

- `artifacts/f86g_mate_reachability/trajectory_probe.json`
- `artifacts/f86g_mate_reachability/cooperative_reachability.json`
- `scripts/f86g_mate_reachability_probe.py`
- `tests/test_f86g_mate_reachability_probe.py`
