# Targeted Pawn guard correction, frozen before replay

2026-10-04. Original protocol90894e85... and raw resource_mode_feasibility_20261004.json
remain immutable. Observed Chess128/128 proposals rejected as dead_board_mode;
Shogi3 roots admitted with51/54/54 choices,159 total,0transitions,0.157seconds.
This is not evidence that the Chess context law is empty or infeasible.

Source diagnosis: western_chess._western_types defines Pawn movement_atoms=(),
while pawn_one_step/double_step/capture semantics specify its actual geometry.
The compiled atom-derived empty_mobility for Pawn is therefore empty at every
square, even on the legal initial board. Other Western types DO have atoms;
the defect is specifically using this table as a Chess Pawn structural guard.

Correct ONLY Chess Pawn handling: reject ranks0/7 explicitly, then exclude that
type from the atom-table dead-mode test. All other guards unchanged, including
whole resources, both anchor checks, fresh ongoing terminal and full choices.
This is a source-qualified implementation repair, not a favourable-law change.
Control first: initial Chess is wrongly rejected by old guard but admitted by
corrected guard; forbidden Pawn terminal ranks remain rejected. Shogi table
handling is unchanged. No goal labels or coefficient observations are involved.

Replay the SAME three Chess PRNG streams, marks/proposals and42/42/44 allocations.
No new seeds or extra unique proposals; stop at corrected first admission.
Reuse the immutable original Shogi rows rather than replaying successful modes.
At most128 distinct Chess proposals remain;0transitions;5000 total visited
choices minus original159;15seconds minus original recorded elapsed time remain
for corrected replay/compilation. No extension of the root128-choice cap.
An admitted capped root stays admitted/incomplete, never resampled.

Save a separate corrected report with original raw file hash, original input
hash ledger, correction source hashes and original Shogi rows. Original128
invalid guard examinations must remain visible, distinct from corrected unique
proposal admission counts; do not sum them as256 independent sampled contexts.
A passing correction qualifies root feasibility only, not a complete mode
vector, positive reward, closure, historical reachability or deployment.
