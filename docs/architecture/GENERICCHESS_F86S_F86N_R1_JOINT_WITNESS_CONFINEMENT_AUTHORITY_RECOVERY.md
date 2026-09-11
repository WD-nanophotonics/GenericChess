# GenericChess F86S: F86N-R1 Joint-Witness Confinement Authority Recovery

Status: complete. F86S is a static, authority-bound recovery analysis over the frozen F86N-R1 candidates. It does not generate a new candidate, resample movement, run games, or perform dynamic search.

## Frozen authority

The run is bound to baseline `453dac15fc5b0568d285615c142f572a0dc6a233`, the F86N-R1 PREP blob `adba41fa02a6e44459d3692ba232bf564c4450c7`, the F86N-R1 RESULT blob `d7f7e7648255e009a1544908a75e7d49ee4a8e72`, and the F86R RESULT blob `c0de094522a8660750221d9fa948cfd79a5c00cf`. Candidate fingerprints are frozen as:

| sample | candidate fingerprint | census status |
|---|---|---|
| V4-3 | `856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2` | complete, 1296 checks |
| V5-3 | `e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5` | observed under truncated census, 2048 checks |

The census reproduced the F86N-R1 counts exactly: V4-3 had 1166 validated positions and 108 templates; V5-3 had 1592 validated positions and 90 templates. The total was 3344 checks against the 4096 total cap. No cap was raised.

## Joint witnesses

The durable witness rows are in `artifacts/f86s_f86n_r1_joint_witness_confinement/witnesses.json`. They retain the source template, defender Anchor, admissible/frozen attacker Anchor target, ordinary target types and squares, actual opening-piece-to-target assignments, optimistic path lengths, joint lower bound, candidate fingerprint, and exact confinement profile.

There are exactly 2 complete V4-3 joint witnesses and 21 V5-3 witnesses observed under the truncated census. Every row is an exact checkmate under the F86R checker geometry: defender legal replies, Anchor flight replies, checker-capture replies, and interposition/screen replies are all zero.

## Static versus dynamic confinement

F86R ARM-N is the dynamic control. Its frozen distributions were 1 checker and coverage 2 for V4-3, and 13 single-checker actions with coverage 0 or 1 for V5-3; Anchor flight was the primary breaking-reply mode in both samples.

| sample | static witness coverage | static checker multiplicity | dynamic ARM-N coverage | route |
|---|---:|---:|---:|---|
| V4-3 | 2×1, 3×1 | 1×2 | 2×1 | `STATIC_MATE_CONFINEMENT_DEPENDS_ON_OCCUPANCY_STRUCTURE` |
| V5-3 | 2×13, 3×6, 4×2 | 1×19, 2×2 | 0×8, 1×5 | `STATIC_MATE_WITNESSES_HAVE_STRICTLY_STRONGER_NEIGHBOR_ATTACK_COVERAGE` |

The V4-3 static coverage overlaps the dynamic value, so the distinction is occupancy structure: static witnesses have enemy-occupied Anchor-neighbor squares and no legal flight, while the dynamic control exhibits Anchor-flight breaks. V5-3 has strictly stronger static attacked-neighbor coverage because its minimum is 2 and the dynamic maximum is 1. The overall route is `CONFINEMENT_GAP_IS_SAMPLE_DEPENDENT`.

## Compute boundary

New games, movement candidates, dynamic work beyond F86R, AlphaBeta, BFS, training, teacher search, C2, F85, and Heavy were all zero. The default generator was unchanged.
