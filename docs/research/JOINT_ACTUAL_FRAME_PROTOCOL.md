# Full Shogi actual-inventory joint sampler integration gate

Base 69f8954e1ede99eaff432d0d0c3e079c4be07aa2. Use proven file-joint integer
unranking unchanged, followed by uniform injection of the remaining actual
initial B/G/K/R/S tokens into the 55 free squares. Each physical configuration
has the same labelled-token multiplicity. Verify compiled initial inventory is
unpromoted, exactly nine Pawns and two L/N per owner; all remaining types must
have nonempty empty-board mobility everywhere. Fail closed on scope drift.

Construct the existing synthetic initial-inventory position (owner zero, empty
hands, reset history). Apply unchanged rejection_reason whole-board anchor
checks and terminal-root test. The proposal is uniform on the old structural
law conditioned on non-dead L/N; therefore identical subsequent rejection
produces the same accepted Q. No dead non-Pawn rejection may occur: treat it as
an implementation error, not an ordinary retry. Never retain a Pawn background.

One process, seed 202610040402, at most 128 joint proposals to ONE quiet ongoing
root, 10 seconds total including compilation and single reused preprocessing.
No capture stratum, corpus, task labels, coefficients or Xiangqi/human values.
Record protocol/program hashes, proposals/reasons, full state evidence and time.
Proposal exhaustion preserves incomplete counters; cost abort cannot qualify.

Tests must compare full board inventory to compiled initial state, public
structural validation, empty hands, side, no dead placements, deterministic
draws, retained quiet/terminal filtering and fail-closed inventory/mobility
drift. Existing exhaustive tiny unranking test remains the uniformity oracle.
Passing this gate permits a separately frozen NEW corpus-generation protocol;
it does not repair or extend the earlier incomplete corpus or establish values.
