# ADR-092: AlphaSho benchmark protocol certification

## Status

Accepted for F30 R1.

## Decision

The F30 first-pass evidence remains immutable.  R1 binds all fresh evidence to
a SHA-256 manifest frozen before any new external search.  The manifest fixes
the F29 product authority, Standard Shogi fingerprint, F22 descriptors and
reference identities, AlphaSho provenance, exact 0.50/2.00 second controls,
and the paired-game protocol.

Each fresh engine reference has three complete repetitions per position and
time control.  The AlphaSho checkout remains read-only and is invoked with its
FULL heuristic profile.  GenericChess uses evaluator-v1, TT and ordering on,
Native requested, disk cache off, default tuning, qsearch 4/8, and a high
maximum depth.

Each paired game constructs one GenericChess AlphaBetaPlayer and retains its
TT for the complete game.  F29 GameSession is the arbiter; external USI is
translated and checked against product legal actions before submission.
The frozen SFEN ply is preserved.  Missing pre-root history is represented by
the explicit `IMPORTED_HISTORY_PREFIX_UNAVAILABLE` boundary, not invented
moves.  An ongoing game at 256 additional plies is reported separately as
`BENCHMARK_PLY_CAP` and counted as a draw for the clean aggregate.  Complete
per-move transcripts, terminal state, cap state, and transcript hashes are
durable evidence.

No evaluator, search, rule, Native, or production change is permitted from
the observed gap.  The first-pass provisional score is retained separately
from the corrected persistent-TT result.

## R1 result

The pre-run manifest is SHA-256
`3af3ac415bf5fee1f52bae7fe09d6a888db1a90be3d12c10cce1acd477ed2d7e` and is
bound to the R1 fresh and paired fixtures.  At 0.50 seconds AlphaSho matched
the F22 reference 10/10 position modals (9/10 stable); GenericChess matched
2/10 (10/10 stable) and had completed-depth distribution 30 at depth 0.  At
2.00 seconds AlphaSho matched 7/10 (10/10 stable); GenericChess matched 1/10
(10/10 stable) and had completed-depth distribution 30 at depth 1.  Modal
cross-engine agreement was 2/10 and 3/10 respectively.  These are descriptive
results, not tuning targets.

The corrected persistent-TT paired transcript completed 20/20 games with no
technical failures and no cap hits.  The clean aggregate was GenericChess
0W/3D/17L, score 0.075; by GenericChess side, black-side games were 0W/1D/9L
and white-side games were 0W/2D/8L.  The preserved first-pass result remains
0W/2D/18L, score 0.05, and is explicitly provisional.  Full R1 evidence is in
`tests/fixtures/f30r1_fresh_move_reference.json` and
`tests/fixtures/f30r1_paired_match.json`.
