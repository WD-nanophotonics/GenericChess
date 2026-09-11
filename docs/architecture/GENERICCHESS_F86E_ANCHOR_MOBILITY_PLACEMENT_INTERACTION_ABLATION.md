# GenericChess F86E Anchor mobility/placement interaction ablation

Status: bounded placement-interaction probe complete. F86D artifacts were
preserved unchanged. The production/default generator was not modified. No
Heavy job, ladder, training, C2, F85 acquisition, or admission-threshold work
was run.

## Corrected static preflight

The F86D `forward_only_atom_fraction` label was not carried forward because it
counted horizontal atoms as forward. F86E uses these exact definitions:

- `has_backward_atom`: any atom has relative rank component `< 0`;
- `non_backward_atom_fraction`: atom rank component `>= 0`;
- `strict_forward_atom_fraction`: atom rank component `> 0`;
- `horizontal_atom_fraction`: atom rank component `== 0`;
- `far_edge_sink_fraction`: for owner 0, sink rank `n-1`; for owner 1, sink
  rank `0`.

Sink fraction, direct reversibility, largest SCC, nontrivial SCC, and
monotone-DAG calculations are otherwise unchanged. The preflight artifact
contains 10 rows: the two frozen samples across the two direct references and
the three new cells. Every row contains per-type, per-owner metrics.

All new placements compiled successfully. For even boards, the project's
lower center file (`n//2 - 1`) is the deterministic Anchor tie-break. The
three ordinary files are the nearest central files, sorted by center distance
then file; ordinary type assignment is stable by `(type_id, original rank,
original file)`. Owner 1 is an exact 180-degree rotation with corresponding
piece types.

## Frozen references and new rulesets

The exact F86C serialized V4-3/V5-3 rulesets were loaded directly without
regeneration or seed replacement. `LEGACY_CURRENT` uses the F86C placement and
legacy Anchor. `FULL8_CURRENT` is referenced directly from the accepted F86D
ruleset artifact and is not rerun.

The six new serialized rulesets and fingerprints are in
`artifacts/f86e_anchor_placement_ablation/counterfactual_rulesets.json`:

| sample | ORTHO4_CURRENT | ORTHO4_HOME | FULL8_HOME |
|---|---|---|---|
| V4-3 | `ea993a6147595b1ce740cc91ad426a96395edcb6de479c95c23ecc88800a0e17` | `b212a7b7eeb624a8765d046a9aea898f388357bc356657b6b1a225a7ae5a5f37` | `8bbf89abb06de37fd530893986daa2866e957176baace0b2b4c29cfcd2fb5b04` |
| V5-3 | `1a256a4fcc763cb6f4e5ca1037a77b72885d4e85a4d5e46ccf88c69f552b266d` | `a0ef1a7439137d344c72e56bd308dfaa31643ff60ff505c92efe11ef0db363e8` | `a97770ea9f685a9cfcbe257d57beb3b5272fd5af4e014d54396d0dc361abc204` |

`ORTHO4` is exactly the four cardinal LEAP offsets. `FULL8` is the accepted
F86D full eight-neighbor Anchor. Ordinary movement atoms, material, terminal
semantics, promotion/drop masks, and the frozen seeds remain unchanged.

## Game evidence

Legacy and FULL8 current results are direct references; only the three new
cells ran games. Each new cell used both frozen samples, one A/B plus B/A
policy pair per sample, and max ply 32: 3 cells × 2 samples × 2 games = 12
new real games. The six new rulesets each received one terminal-only probe,
depth at most 4 and nodes at most 256: 6 positions and 1,128 actual nodes,
under the 1,536-node ceiling.

| cell | games | decisive/checkmate | stalemate | ongoing @32 | repetition | median length |
|---|---:|---:|---:|---:|---:|---:|
| LEGACY_CURRENT reference | 4 | 0/4 | 4/4 | 0/4 | 0/4 | 12 |
| FULL8_CURRENT reference | 4 | 0/4 | 0/4 | 4/4 | 0/4 | 32 |
| ORTHO4_CURRENT | 4 | 0/4 | 0/4 | 3/4 | 1/4 | 32 |
| ORTHO4_HOME | 4 | 0/4 | 0/4 | 4/4 | 0/4 | 32 |
| FULL8_HOME | 4 | 0/4 | 0/4 | 4/4 | 0/4 | 32 |

The new-cell quality summaries also retain median branching, forced-move
fraction, branching-collapse fraction, opening Anchor legal counts, and all
12 raw trajectories in `artifacts/f86e_anchor_placement_ablation/results.json`.

## Observed comparisons and routing

- `ORTHO4_CURRENT` versus `FULL8_CURRENT`: both have zero decisive games and
  zero stalemates, but ORTHO4 has 3/4 ongoing-at-32 versus FULL8's 4/4. The
  bounded result routes `FULL8_ESCAPE_CAPACITY_TOO_HIGH`.
- `ORTHO4_HOME` versus `ORTHO4_CURRENT`: HOME changes the distribution from
  one repetition plus three ongoing games to four ongoing games; it does not
  add decisive capacity.
- `FULL8_HOME` versus `FULL8_CURRENT`: both remain four ongoing games, so HOME
  has no observed effect in the FULL8 cell.
- Placement therefore has an Anchor-profile-dependent interaction in this
  probe, routing `ANCHOR_PLACEMENT_INTERACTION_OBSERVED`. No positive
  `PLACEMENT_MATERIALLY_AFFECTS_TERMINATION` result is claimed because no HOME
  cell reduced bad outcomes while increasing decisive games.
- All reversible-Anchor cells remain entirely non-decisive and at least 75%
  stalemate-or-ongoing, routing `MATE_CAPACITY_REMAINS_LIMITING`.

The combined routing is:

```text
FULL8_ESCAPE_CAPACITY_TOO_HIGH
ANCHOR_PLACEMENT_INTERACTION_OBSERVED
MATE_CAPACITY_REMAINS_LIMITING
```

This means full-eight Anchor mobility appears to provide too much escape
capacity relative to ORTHO4 in the bounded sample, while neither reversible
Anchor cell demonstrates decisive mate capacity. It does not authorize a
default-generator change.

## Exact validation

```text
\.venv\Scripts\python.exe -m pytest tests/test_f86a_minimal_game_benchmark.py tests/test_f86b_quality_calibration.py tests/test_f86c_generator_viability.py tests/test_f86d_mobility_ablation.py tests/test_f86e_anchor_placement_ablation.py tests/test_f85_lane_scaling_calibration.py tests/test_f85_c2_train_teacher_acquisition.py tests/test_benchmark.py --tb=no
```

Result: **43/43 PASS**. F86D and F86E artifact contracts both pass. F85
actual compute is 0; no seed was replaced; the default generator remains
unchanged.

## Durable evidence

- `artifacts/f86e_anchor_placement_ablation/static_diagnostics.json`
- `artifacts/f86e_anchor_placement_ablation/counterfactual_rulesets.json`
- `artifacts/f86e_anchor_placement_ablation/results.json`
- `tests/test_f86e_anchor_placement_ablation.py`
