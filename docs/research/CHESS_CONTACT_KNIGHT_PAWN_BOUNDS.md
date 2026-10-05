# Missing Chess modes: finite contact bounds and parameter reversals

2026-10-05. New analytical extension of the SAME uniform249984 native-mode
triple population; no coefficient batch, public transition, outcome fitting,
tour search or Xiangqi holdout. Keep virtual stationary target/passive blocker,
clear compiled intrinsic actions, no royal safety/full-history/castling, EP
initially absent. Geometry
is compatible only under these declared source-only assumptions.

## Knight: parity and one-blocker reachability

Eight(1,2)/(2,1) oriented displacements have42 placements each, so336 direct
ordered source/target pairs contribute20832 triples. Of2048 opposite-colour
pairs,1712 are nondirect:106144 triples have odd distance at least3. The1984
same-colour distinct pairs give123008 triples with even distance at least2.
Native N has no promotion, intermediate-square constraint or source/state guard.

[Schwenk's original paper](https://www.math.cmu.edu/~nkomarov/21-110/knighttour.pdf)
(Mathematics Magazine64(5),1991, pp325–332; theorem p326 and8x8 base case p331)
proves a closed Knight tour exists on8x8. A closed tour is a Hamiltonian cycle.
Our consequence: deleting ANY one passive-blocker vertex leaves a spanning path
on63 vertices, connecting every other s/d in at most62 steps. Every edge is a
compatible empty-square Knight move until the final designated capture; stop
on FIRST arrival at d. Source vacates, no other path occupancy changes. Thus
all N worlds are reachable. Opposite-colour paths have odd length<=61, same-
colour paths even length<=62. The paper establishes graph existence; it does
not establish chess strategic values, our world law, or these contact weights.

Therefore

    L_N=(20832*g+106144*g^61+123008*g^62)/249984,
    U_N=(20832*g+123008*g^2+106144*g^3)/249984.

These are bounds, NOT measured/exact N histograms. R-U_N equals
g*(1-g)*(32928+104352*g)/249984>0 throughout0<g<1.
B versus N instead REVERSES: at g1/100, L_B>U_N; at g99/100, L_N>U_B
(approximately0.57638>0.48267). Exact rational checks certify both witnesses.
Since N tends to1 but B has permanent unreachable mass, treating this model
as a discount-free total type ranking is untenable. Neither witness selects g.

## Pawn: forced promotion provides a compatible reachable stratum

Native P direct captures have98 ordered pairs per owner, hence6076 triples.
Exact zero subsets: source on its last rank(31248 triples); OR target forward
on the source's SAME file(13888 triples). They are disjoint. P cannot change
file without absorbing target capture; forward quiet or double moves cannot
jump/capture that on-file enemy. Standing native P on the last rank does not
auto-promote. Initial EP is absent; later token effects cannot escape these
subsets because an EP victim is off the source file, not the same-file target.
This proves at least45136 zero triples. Everything else nondirect retains
upper g^2, so U_P=(6076*g+198772*g^2)/249984.

A separate reachable stratum: source is BELOW its last rank, and BOTH d/b
are on OTHER files. It has56*56*55=172480 triples. Take at most7 single quiet
forward steps, forcing chosen promotion to Q on the last rank, then Q reaches
the stationary target in at most3 compatible actions by the proved Queen/Rook
detour. Cost<=10. Neither d nor b is on the quiet path; old source squares vacate.
This is a full stratum witness, not sampled shortest paths. Direct P overlap
is98*55=5390; remove that overlap exactly once. Consequently

    L_P=(6076*g+167090*g^10)/249984.

Other reachable cases remain unmeasured. The lower does NOT claim all quiet
promotion paths take10 or that all native P worlds reach. Optional initial
double-step is not needed. Forced last-step promotion has Q/R/B/N choices;
using Q preserves native P origin with declared zero-rights/no-history scope.
R-U_P has positive lower margin: g*(47684-4340*g+1792*g^2)/249984>0.
Here B versus P also reverses: L_B>U_P at g1/100; L_P>U_B at g99/100.
Gamma sensitivity is thus a substantive construction assumption, not just
numerical truncation error or a request for a universal WDL calibration.

## Semantic and next-use limits

Compiled N ordinary leap patterns have no path/source/history/promotion forms;
ordinary target removal is remove_from_game. P one-step and diagonal capture
patterns inherit compiled forced last-rank masks; double-step guard applies
only on owner-relative initial rank. EP patterns have explicit slot guards and
are initially unavailable under the declared absent EP state, not assigned zero
without a state premise or claimed permanently unavailable after token changes.
Pawn double-step can set an EP token; the existing board-event composer does
not model that auxiliary effect. Do NOT claim a complete composed P graph or
artificially force future tokens absent. These bounds do not need that shortcut:
the positive witness uses only single quiet steps; the direct class assumes
initially absent EP; same-file forward/last-rank zeros cannot be rescued by EP's
off-file victim geometry. Remaining mass is unresolved regardless of any later
auxiliary shortcut. Dynamic own_anchor_safe and full-history/royal legality stay omitted throughout.
This is source qualification plus mathematical proof, not an actual full public
path audit. Tests check displacement/mass/overlap arithmetic, parity frontiers,
cycle-deletion consequence, compiled contracts and rational sign certificates.

Together Q/R exact and B/N/P censored define a COMPLETE native Chess virtual
interval FAMILY on this law, not a complete generic-game scalar material prior.
Origin/provenance deployment, Shogi remaining modes and independent useful
leaf choices beyond the exposed R/B family remain open. Do not choose g from
conventional prices or the just-observed baseline margin. A separately declared
exogenous task-duration convention is an executable modeling alternative.
