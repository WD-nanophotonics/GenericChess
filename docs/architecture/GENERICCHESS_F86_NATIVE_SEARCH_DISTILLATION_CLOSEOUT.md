# F86 Native Search Distillation Closeout

Date: 2026-09-15

## Scope

F86 changed the learning mechanism from F84/F85 linear TDLeaf updates to a
single parent-anchored compact nonlinear residual fit. The parent remained
`c45623c0b905780ed1fd896a8f9364fd369bed1e641519f45fb40a3faf014d71` under
the canonical standard shogi ruleset. Exactly one deterministic native
self-play trajectory was used (`seed=860401`, 512 nodes/move, depth 12,
epsilon 0, TT 8 MiB, max 64 plies); no TDLeaf update, teacher label, or
second optimizer run was used.

The implementation was published at sandbox commit
`17bb478eb35c3b35a0bfba46d26e2aea3d595fc5` and its tests passed before the
bounded stages.

## Stage A: native-search distillation

The trajectory supplied 64 training roots and 2,964 legal-action rows. Each
root was reconstructed from the actual action prefix; the target was the
native search-selected legal action. The parent-anchored Adam fit used 100
steps, learning rate 0.001, and proximal coefficient 0.001, updating only
hidden weights, hidden bias, and output weights.

The pairwise objective improved from `395.79037498687774` to
`11.727928225365863`. The candidate checkpoint was
`27a5e00c2c91072b59bbadb61415cb055696c582fd5cd88bc75572c590a33028`.
Parent maximum absolute residual was `20484.41703912475`; candidate maximum
was `19907.041904312664`, within the 2x safety cap. All frozen representation
and linear evaluator fields were preserved.

Transient evidence hashes:

- Stage A envelope: `40368c0b793074cfa6a837322908bc12eee5609a8651ba238665d19f7e72d6e2`
- Stage A result: `37d69be3ce4a9ae9e685a0044ed4ab9df132d4829cfc09589b669fd57a802ef7`
- Candidate descriptor: `7d39ecabcf8939f9963b0cc44f227e1d8b4308aef17a507084b32ce3b3b200fd`
- Candidate result: `1592f72dabdd079082940587ae62309a61c1aedcae08c5c9d3dfdb8c297854e6`

## Stage B: minimum strength probe

The requested registered Arena4 opening was corpus
`593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1`,
opening index 2, seed 820401, with symmetric 512-node/depth-12 settings and
role swapping. One game completed (candidate owner 0 lost to the parent at
163 plies), but the second game did not complete before the execution stage
wall boundary. Therefore no complete role-swapped pair score exists.

Stage B status was `INCOMPLETE`, `completed_games=1`, `completed_pairs=0`,
reason `stage_wall_seconds`. This is inconclusive evidence, not a strength
result; the work order forbids rerunning or extending the pair.

Transient evidence hashes:

- Stage B envelope: `0cca46c3de5b720ffc4bbe4171ed3ddeab4901d8f9e259cf034465e9f895335c`
- Stage B result: `3d8eb4effc0ffc8e769208eb6df52e764fc1a9dab238499e32462aaf30931af4`

## Decision

The distillation gate passed, but the prescribed role-swapped Arena4 pair was
incomplete. Stop this candidate as inconclusive: do not run a second pair,
Arena8, confirmation, backtracking, or promotion. A future work order must
choose a distinct intervention or explicitly re-register a bounded probe.
