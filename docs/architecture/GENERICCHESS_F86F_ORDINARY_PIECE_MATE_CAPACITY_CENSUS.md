# GenericChess F86F ordinary-piece mate-capacity census

Status: bounded static census complete. No real games, teacher/search games,
Heavy work, ladder, training, C2, F85 acquisition, admission thresholds, or
default-generator changes were run.

## Frozen scope and reused rulesets

The census uses only the frozen V4-3 and V5-3 serialized rulesets and the two
reversible-Anchor profiles from the accepted artifacts. No ruleset was
regenerated, modified, or replaced:

| sample | ORTHO4_CURRENT | FULL8_CURRENT |
|---|---|---|
| V4-3 | `ea993a6147595b1ce740cc91ad426a96395edcb6de479c95c23ecc88800a0e17` | `7511327e944c195de71de536f818e8a2028136d4b04123937596f4dce46bda62` |
| V5-3 | `1a256a4fcc763cb6f4e5ca1037a77b72885d4e85a4d5e46ccf88c69f552b266d` | `8d77e9671449b2d6952aa7c80c898d7e390eff0fa534ac8be6d55e7f055ec1d8` |

## Census definition

For every possible defending Anchor square, the Anchor zone is that square
plus its legal empty-board mobility targets. The exact ordinary-piece
material multiset for the sample is used. The geometric layer enumerates
ordinary-piece empty-board attack masks only; it intentionally excludes the
attacker Anchor's attack contribution and ignores attacker safety, captures,
blockers, and reachable history. This is an optimistic upper bound, not a
checkmate claim.

The geometric layer records:

- `anchor_square_checkable_fraction`: fraction of defender Anchor squares
  reachable by at least one ordinary empty-board attack mask;
- mean and maximum Anchor-zone coverage fractions using the exact ordinary
  material multiset;
- `geometric_full_net_anchor_fraction`: fraction of Anchor squares for which
  the exact ordinary material can cover the complete Anchor zone;
- minimum ordinary attackers needed by geometric full-net Anchor square.

For every full geometric net, the engine layer enumerates canonical ordinary
placements, then every remaining attacker-Anchor square. It constructs a real
Core `Position` with the defender to move and validates `is_in_check` plus
`has_legal_action`; candidates with the attacker Anchor in check are rejected.
Thus an engine-valid result is a static stripped-defender checkmate under the
real compiled ruleset, not a fabricated mate rule.

The cap is 2,048 candidate positions per cell and 8,192 across all four
cells. The actual census checked 1,593 positions, with no truncation.

## Results

| sample | cell | ordinary multiset | checkable | mean zone | max zone | geometric full net | engine mate | checked positions |
|---|---|---|---:|---:|---:|---:|---|---:|
| V4-3 | ORTHO4_CURRENT | P0,P0,P1 | 15/16 | 0.705208 | 1.0 | 5/16 | yes, 5/16 | 132 |
| V4-3 | FULL8_CURRENT | P0,P0,P1 | 15/16 | 0.574653 | 1.0 | 1/16 | no, 0/16 | 12 |
| V5-3 | ORTHO4_CURRENT | P0,P1,P1 | 20/25 | 0.744667 | 1.0 | 7/25 | yes, 7/25 | 1,407 |
| V5-3 | FULL8_CURRENT | P0,P1,P1 | 20/25 | 0.623333 | 1.0 | 1/25 | yes, 1/25 | 42 |

Minimum geometric attacker distributions are `{3: 5}`, `{3: 1}`, `{3: 7}`,
and `{3: 1}` in the table's row order. The
`full_material_validated_mate_position_count_by_attacker_count` distributions
are respectively `{3: 89}`, empty, `{3: 1262}`, and `{3: 37}`. These counts
use the full three-piece material multiset in each sample; they are not a
minimum-attacker result. The large V5-3 ORTHO4 count is still below its
per-cell cap and is a count of static candidate positions, not played games
or search nodes.

## Canonical validated-mate examples

The full canonical examples are durably stored in
`artifacts/f86f_mate_capacity/examples.json`. The retained examples are:

| sample | cell | defender Anchor | attacker Anchor | ordinary placements |
|---|---|---|---|---|
| V4-3 | ORTHO4_CURRENT | (3,1) | (2,2) | P0@(2,0), P0@(2,1), P1@(1,0) |
| V4-3 | ORTHO4_CURRENT | (3,1) | (3,3) | P0@(2,0), P0@(2,1), P1@(1,0) |
| V4-3 | ORTHO4_CURRENT | (3,2) | (2,3) | P0@(2,1), P0@(2,2), P1@(1,1) |
| V5-3 | ORTHO4_CURRENT | (0,2) | (0,0) | P0@(2,1), P1@(1,0), P1@(1,1) |
| V5-3 | ORTHO4_CURRENT | (0,2) | (2,0) | P0@(2,1), P1@(1,0), P1@(1,1) |
| V5-3 | ORTHO4_CURRENT | (0,2) | (3,0) | P0@(2,1), P1@(1,0), P1@(1,1) |
| V5-3 | FULL8_CURRENT | (0,4) | (0,0) | P0@(2,2), P1@(1,2), P1@(0,3) |
| V5-3 | FULL8_CURRENT | (0,4) | (1,0) | P0@(2,2), P1@(1,2), P1@(0,3) |
| V5-3 | FULL8_CURRENT | (0,4) | (2,0) | P0@(2,2), P1@(1,2), P1@(0,3) |

## Routing

Both profiles have optimistic geometric full nets, and the engine validates
static stripped-Anchor mates in three of four cells. The routing is therefore:

```text
STRIPPED_ANCHOR_MATE_CAPACITY_EXISTS
```

Per-cell routing is retained under `(sample_id, cell)` keys: V4-3/FULL8 is
`GEOMETRIC_NET_EXISTS_BUT_RULE_LEGAL_MATE_ABSENT`; the other three cells are
`STRIPPED_ANCHOR_MATE_CAPACITY_EXISTS`.

This proves that the ordinary material has static mating geometry under a
stripped defender model. It does not prove that normal generated games can
reach those positions. The next question is MATE_REACHABILITY under real
material, captures, safety, and state distribution—not another Anchor or
placement ablation.

## Exact validation and resource accounting

```text
\.venv\Scripts\python.exe -m pytest tests/test_f86a_minimal_game_benchmark.py tests/test_f86b_quality_calibration.py tests/test_f86c_generator_viability.py tests/test_f86d_mobility_ablation.py tests/test_f86e_anchor_placement_ablation.py tests/test_f86e_r1_common_policy_replay.py tests/test_f86f_ordinary_mate_capacity_census.py tests/test_f85_lane_scaling_calibration.py tests/test_f85_c2_train_teacher_acquisition.py tests/test_benchmark.py --tb=no
```

Result: **49/49 PASS**. This includes direct Core revalidation of one V4-3
ORTHO4 and one V5-3 FULL8 canonical example. Real played games: 0.
Teacher/search compute: 0.
Checked candidate positions: 1,593/8,192 maximum; truncation: false. F85
actual compute is 0. The default generator and all frozen rulesets remain
unchanged.

## Durable evidence

- `artifacts/f86f_mate_capacity/census.json`
- `artifacts/f86f_mate_capacity/examples.json`
- `tests/test_f86f_ordinary_mate_capacity_census.py`
