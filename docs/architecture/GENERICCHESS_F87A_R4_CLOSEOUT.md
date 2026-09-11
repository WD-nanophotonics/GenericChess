# F87A-R4 termination-viability calibration closeout

This checkpoint records the signed order
`GENERICCHESS-F87A-R4-TERMINATION-VIABILITY-CALIBRATION`, bound to PREP
baseline `4b26e51f4a5dfcace639cb5a1572a90a4c80632e`. R3 semantic runtime and
nondegeneracy evidence is inherited; R2 controls and R3 random/greedy games
were not rerun.

## Control and authority

The only new policy is `deterministic_semantic_shallow_search`, a deterministic
depth-2 terminal-aware evaluator using the production semantic runtime,
canonical public-action ordering, exact `position_identity_key` recurrence,
and a strict 256 search-node cap per game. The horizon is 128 plies. Two
role-swapped pairs per ruleset produce exactly eight new games.

Recurrence/return counts use the full semantic position identity, including
auxiliary state. Terminal status, repetition, and `CENSORED` are reported as
separate categories; censored games never receive draw scores.

## Results

| Ruleset | Terminal result | Termination viability | Recurrence | Search nodes |
| --- | --- | --- | --- | ---: |
| Western Chess | 4/4 `CENSORED` at 128 plies | `DEFER` (`ALL_TRAJECTORIES_CENSORED`) | 220 returns; max multiplicity 3 | 1,024 |
| Standard Shogi | 4/4 `repetition` at 22 plies | `PASS` | 36 returns; max multiplicity 4 | 1,024 |

No abnormal recurrence or legal-action collapse predicate fired. The Western
Chess result remains `DEFER` because all trajectories were censored; interaction
alone does not upgrade termination viability. Standard Shogi supplies a
reproducible terminal trajectory without abnormal recurrence/collapse. The R4
Layer-C result is therefore mixed: Western Chess `DEFER`, Standard Shogi
`PASS`.

Compute was limited to 8 new games and 2,048 total search nodes. Arena,
training, Heavy, C2, F85, and generator work were not run. No promotion is
authorized by this closeout.

Ignored generated evidence SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `artifacts/f87a_r4_termination_viability/manifest.json` | `0c1f522b3efcd97235cd6ecedd1fb474b47936ce22509bfb18f6dda512ed9f13` |
| `artifacts/f87a_r4_termination_viability/summary.json` | `49c3c88bf6820bd4c86a50b132fdfff41dd6f184ce2fc3d01461bbf038ab02de` |
| `artifacts/f87a_r4_termination_viability/reports.json` | `45f56b2ea10c89fd6c29c23f16e3e8684b72410bf10590bef58f57d12c62faaa` |
