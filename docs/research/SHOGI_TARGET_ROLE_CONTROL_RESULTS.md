# Actual sparse Shogi custody/target-role controls

2026-10-04. Frozen SHOGI_TARGET_ROLE_CONTROL_PROTOCOL.md executed once.
Raw data/shogi_target_role_controls_20261004.json pins10 inputs and preserves
full initial/final states, complete action counts, physical tag mass and stock
deficits. All20 controls completed:40 public transitions,4060 public/binding
enumerations,0.454 seconds. Every child advanced real history/ply; independent
public capture counts agreed with verified binding rewards. Both owner
directions have identical reported values. No goal label or coefficient batch.

|Declared tag mode|First fixed reward|Next-own choices|Conditional next tag reward|
|---|---:|---:|---:|
|board native P|1|67|0|
|board native L|1|77|0|
|board native N, no first promotion|1|74|0|
|board P-origin TP|1|78|1/78|
|hand P, n=1|0|4|1/4|
|hand P, n=2|0|66|1/132|
|hand L, n=1|0|4|1/4|
|hand L, n=2|0|72|1/144|
|hand N, n=1|0|7|2/7|
|hand N, n=2|0|66|1/66|

These are CONDITIONAL means after the protocol's fixed role-based own action
and quiet King reply, not a population H2 expectation. A sparse board/hand root
is missing35 tokens (34 for n=2). The unchanged resource_ledger correctly
rejects full Shogi inventory claims for every root. Session claims do not
appear; all required parent/successor states are ongoing. The results qualify
this mechanism scope, not natural play, full material pricing or official WDL.

At n=2 a drop puts only1/2 of hidden tag mass on e5 and leaves1/2 in hand.
The remaining untagged/fungible physical token ALSO keeps a whole legal drop
family available next turn. Compared with n=1, the conditional tag reward is
not merely halved: Pawn next choices grow4->66 and Lance4->72. For two initial
same-base held tokens, total next-own tagged expectation summed over both
exchangeable labels is1/66 (P),1/72 (L),1/33 (N), still below respective n=1
means1/4,1/4,2/7. This is actual uniform-policy allocation, not negative intrinsic
resource value. More optional actions can lower an average, although an
optimal controller could ignore them when all original subtrees stay unchanged.

Held N has TWO positive next actions: capture to f7 with or without promotion.
They are distinct real resulting modes, not duplicate physical rewards on one
trajectory. Each actually chosen action removes one victim, so2/7 respects the
unit per-action bound. Never merge these semantic choices or count a selected
capture twice. Board TP can remove the other target after first capture,
where native P/L/N on the fixed path cannot; current-mode/provenance matters.

The changed target roles solve a narrow support defect from the symmetric
Shogi proposal: straight-file native P/L now have actual first reward1. This
does not validate a complete H2 law, give a held premium or rescue failed
inventory transfer. Next address controllable task meaning with a genuinely
different premise, retaining the spent uniform pilot and scope restrictions.
Objective OPEN.
