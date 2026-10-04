# R/B/N origin boundary: prospective controls

Frozen before new observations, 2026-10-04. No Queen rerun or price estimation.
Changed question: which other same-current Chess origins can share a semantic
representative, and does a rook's native-base castling guard defeat generalization?

Use the production Western RuleSet. For each owner, compare native currentB/N
against Pawn-origin promotedB/N on identical current boards, empty hands,
matching aux/ply and single-root synthetic history. B fixture owner0:
`7k/6r1/8/8/3B4/8/8/K7 w - - 0 1`, capture d4-g7.
N fixture: `7k/8/8/5r2/3N4/8/8/K7 w - - 0 1`, capture d4-f5.
Owner1 reflects ranks and swaps owners; rights are absent. Require complete
canonical public/binding action sets equal across origins and materialize ONLY
the declared capture. Compare current board/hands/aux/side/terminal and history
actor/action/check signature/count shape; do not require raw provenance keys equal.

R fixture owner0: `k7/8/8/8/8/8/8/4K2R w K - 0 1`.
NativeR at h1 versus P-originR, same imported rights. Require the sole action-set
difference to be native kingside castling; execute that native castle once and
check king g1/rook f1 and cleared own rights. This promoted-rights state is an
IMPORTED synthetic guard counterexample, not claimed historically reachable.
Owner1 reflects ranks/swaps owners and uses black kingside rights explicitly.
Then remove all own castling rights in both variants, require complete action
sets equal, execute h1-h2 (h8-h7 owner1), and compare current/history projections.
Native/promoted inventory must separately pass the resource ledger, including
graveyard deficits; synthetic history is not historical reachability.

Total: exactly14 public transitions (8 B/N captures,2 native castles,4 no-rights
rook moves), <=5,000 enumerated public+binding choices,<=128 choices/state,
<=10 seconds including compile/control work. No deeper search or random samples.
Failure/incomplete output preserves spent evidence; no automatic unchanged rerun.
Pin protocol, script, production Western rules, executor, trace/state helpers.
Report source-proof scope separately from these finite controls. No Core policy,
keys, rules, candidate coefficients or deployment labels are changed.
