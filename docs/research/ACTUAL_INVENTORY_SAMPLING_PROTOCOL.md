# Actual-inventory joint reference: freeze before proposal observations

Base: 16617e6cb7997cc4631edd6eace0f6d8d2c714f3. This checks an independently
declared synthetic uncertainty baseline, not strategic visitation or material
coefficients. No task score, numerical value or human reference is requested.

Reference Q: uniform distinct physical placements of actual compiled initial
owner/current/base inventory, unpromoted board tokens and empty hands, with
owner 0 to move and synthetic reset history/auxiliary state. Condition on the
listed intrinsic structural constraints and quiet ongoing actual roots. Every
actual actor is part of one board; there is no focal type or fixed source and
no requirement that hypothetical replacements of every type be quiet.

Chess structural proposal: place eight owner-0 Pawns uniformly on eight of the
48 nonterminal-rank squares, then eight owner-1 Pawns uniformly on eight of the
remaining 40. There are C(48,8)*C(40,8) distinct Pawn layouts. Place all other
actual tokens uniformly without replacement on the remaining 48 squares.

Standard Shogi structural proposal: independently choose one of 57 rank pairs
per file. Own Pawn rank is 0..7, enemy Pawn rank 1..8 and their ranks differ.
With nine Pawns per owner and nifu, every file must contain one of each, giving
57^9 distinct Pawn layouts. Place all other actual tokens uniformly without
replacement on the remaining 63 squares. Reject dead non-Pawn placements.
This scope assumes current unpromoted initial inventory, not promoted/hand play.

In both games, reject if either actual anchor is checked or the actual reset
root is terminal. Retain all rejections and proposal accounting. Do not redraw
only selected tokens on a retained background, condition separately by type,
renormalize source support or select successful exchange positions. Permuting
labels of identical tokens has a constant multiplicity, so sequential uniform
placement induces a uniform physical proposal. Whole-board rejection preserves
the proposal law conditioned on the common acceptance predicate.

The independently motivated choice is exchangeable physical uncertainty within
those constraints. It may be strategically unrepresentative; it becomes useful
only through separately frozen validation. Stating this law is not validation.

Feasibility observation: seed 20261004, exactly one admitted root per game,
at most 128 proposals per game, 10 seconds total including compilation. One
process; no task transitions, score estimates, retries with larger budgets or
resampling a game after failure. If no root is admitted in the bounded proposals,
report incomplete, not empty population or a zero value. When admitted, record
the exact board, proposals, rejection reasons, inventory checks, seed and hashes.
This first-admission count is not a reliable acceptance-rate estimate.

Before use, prove uniformity combinatorially, test the pair-factor support
exhaustively, reconstruct initial inventory for proposals, and reject inventory
substitution or missing Pawn-file/forbidden-rank constraints. A passing local
check licenses only the specified proposal/reference construction and observed
feasibility, not a full population mean, inventory transfer or prior validity.
