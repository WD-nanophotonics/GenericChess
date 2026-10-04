# Why merely varying native target types does not fix held Pawn

2026-10-04. New source-only design check; no simulated batch, labels or budget
increase. Consider the proposed wider sparse control family: own King a1,
enemy King i8, two enemy ordinary native pieces on distinct squares inside
c3..g7, own held native Pawn(s), no other own board pieces, fresh history.
Require physically legal native modes, and the same two-own-turn designated
target/custody task. Targets may be any of P,L,N,S,G,B,R, not just Pawns.
This is a hypothetical family, not an admitted context law or tested sample.

Any first own King move leaves the source held, so its final drop cannot
capture. For a first source Pawn drop which does NOT immediately attack the
designated target, enemy can move King i8-i9, leaving the target fixed. This
King destination is safe from the distant own King and the dropped Pawn:
a Pawn attacking i9 would have had to drop onto occupied i8. Any check from
a Pawn dropped i7 is thereby evaded. The source's final native Pawn geometry
cannot remove the unchanged target; promotion afterward cannot repair it.

If the dropped Pawn immediately attacks the ordinary target, it stands one
rank below that target. Enemy has the following legal counterstrategy:

- Target P,L,R,G,S captures the dropped Pawn on that same file in one native
  forward step/ray. Capture promotion choices do not affect source removal.
- Target B moves one square diagonally off the source file. All four adjacent
  diagonal destinations are inside the board for central target squares;
  neither King occupies them, and only one other enemy piece can obstruct
  one. At least one legal escape exists.
- Target N jumps two ranks toward enemy forward and one file sideways.
  Both destinations are on-board for c3..g7; neither King occupies them, and
  the other enemy piece can block at most one. Any required promotion occurs
  after the jump and leaves the target off the source file.

Enemy King safety cannot veto these replies: own board attacks consist only
of the far-away King and the Pawn's single forward square, occupied by the
ordinary target, not King i8. Moving that target cannot uncover a Pawn ray.
Own Pawn thereafter has at most one native forward action, so cannot capture
the escaped physical target. Additional source identities remaining held
cannot drop AND capture in the single own action left.

Thus held-P task value stays0 for n=1 or2 throughout this proposed central
native-target family. Merely replacing Pawn-only target types with a uniform
native-type ensemble is not a useful next batch for repairing this task's
held-P support. This narrows a concrete proposed alternative before spending
transitions; it does not forbid board modes, interacting background resources,
longer independently motivated tasks, nonadversarial approximations or other
constructors. Changing those premises must be declared, not tuned to labels.
No full Shogi position distribution or material price follows from this bound.
