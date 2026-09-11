# GenericChess F86A minimal game benchmark admission foundation

Status: implemented as a cheap, deterministic foundation. No Heavy job, F85
teacher acquisition, large scan, or 20-game benchmark was run.

## Scope

F86A adds an independent native random-ruleset entry point for board sizes 4,
5, and 6. Each generated position has exactly one Anchor per side and 2--5
ordinary pieces per side, with owner-0 material mirrored to owner 1 by a
180-degree board rotation. Movement uses only the existing LEAP and RAY atoms.
Drops, hands, promotion, castling, en passant, declarations, and
rule-specific special actions are disabled. Repetition draw and optional
stalemate draw use the existing generic session rules.

The entry point is `generic_chess.benchmark.minimal_generator`; the existing
`generic_chess.generation` API is unchanged. Generation uses a local seeded
RNG and bounded retries for invalid initial checks or no-legal-move positions.

## Quality profile

`generic_chess.benchmark.game_quality.measure_game_quality` produces a raw,
JSON-serializable `GameQualityProfile` from fixed-seed, bounded random legal
trajectories. It records:

- structural counts, type counts, opening legal actions, and opening mobility;
- branching samples, median/p10/p90 summaries, forced/low-branch fractions,
  and mid/end collapse;
- trajectory lengths, terminal distribution, repetition draws, and very-short
  terminal fraction;
- optional fields reserved for paired side-bias, shallow tactical probes,
  solved fractions, unique-best fractions, and future skill discrimination.

Classification is diagnostic rather than an admission claim. It reports
obvious pathology reason codes (for example `SIDE_BIASED`, `FORCED_LINE`,
`SEARCH_EXPLOSIVE`, or `DRAW_DOMINATED`) and otherwise remains
`UNRESOLVED`; F86A does not declare a random ruleset generally qualified.
Synthetic pathology controls are tested without changing benchmark behavior.

## Agent ladder contract

`generic_chess.benchmark.agent_ladder` registers the future comparison names
`random_legal`, `very_shallow`, `low_node`, and `medium_node`. It validates the
ladder and can report a score span when all entries are supplied, but it does
not assign node budgets or run real games. Calibration is deferred to F86B.

## Evidence and next direction

Focused tests cover deterministic generation, board-size/material contracts,
disabled features, serializable raw metrics, synthetic pathology diagnostics,
and the ladder interface. The next bounded step is F86B: a few fixed-seed
random 4--4 and 5--5 games to calibrate the profile and agent ladder. F85
Standard Shogi 36-root teacher acquisition remains HOLD pending the separate
Chat authority reconciliation.
