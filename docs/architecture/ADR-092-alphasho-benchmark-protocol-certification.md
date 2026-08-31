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
