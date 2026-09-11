# GenericChess F86A-R1 automated game-quality measurement closure

Status: implemented as a cheap, bounded measurement foundation. No F85
Standard Shogi acquisition, C2 fitting, Heavy job, large ruleset scan, or
20-game benchmark was run.

Baseline: `36d7840362e45fe9dee159c86ebba57c1cb34f8e`.

## Measured contracts

The existing minimal generator is retained unchanged in its F86A contract:
board sizes 4/5/6, one Anchor per side, 2--5 mirrored ordinary pieces,
LEAP/RAY-only movement, no drops or promotions, deterministic seeded retries.

`measure_game_quality` now measures paired random/legal trajectories. It runs
the original opening and a strict 180-degree owner/color-swapped opening when
the transformed ruleset compiles, and reports machine-readable
`first_player_score`, `second_player_score`, `side_bias_magnitude`,
`paired_game_count`, and `swapped_opening_consistent`. The score convention is
win=1, draw=0.5, loss=0. Comparisons are only treated as paired when both
sides' scores are present; no unpaired win-rate claim is made.

The measurement path also runs one bounded terminal-only tactical probe on a
real generated opening. The solver is capped at depth 4 and 256 nodes and
returns unresolved on cutoffs rather than treating them as draws. Its output
includes shallow forced-win rate, solved fraction, unique-best fraction,
probe-position count, and total probe nodes.

`QualityObservation` and `profile_from_observations` provide the shared metric
aggregation path for real observations and deterministic synthetic controls.
The tests exercise five behavior-shaped controls: side bias, forced corridor,
branching explosion, shallow forced win, and repetition-heavy draws. They do
not replace measured fields on a profile.

The Agent Ladder now evaluates adjacent advantages in configured strength
order and reports `adjacent_advantages`, minimum/mean adjacent advantage,
monotonicity, and order-aware `skill_discrimination`. Reversed order returns
zero discrimination; incomplete paired results return `None`.

## Fail-closed admission authority

Classification defaults to `UNRESOLVED` because F86A has no population-
calibrated admission thresholds. Diagnostic reason flags remain visible, and
optional explicit thresholds are required before a diagnostic reason becomes
the returned classification. `QUALIFIED_GENERAL` is not produced by this
foundation.

## Bounded evidence

The focused test set covers F86A/R1 and retained F85 contract tests. The
measurement path uses a small deterministic trajectory count and one solver
position per profile; the solver is hard-capped at 256 nodes. F86B may use a
few fixed-seed 4--4 and 5--5 games to calibrate distributions and ladder
ordering. F85 remains `HOLD` and no authority files were changed.
