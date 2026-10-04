# Prospective pilot: positivity without coefficient sampling

2026-10-04. Uses the frozen common eligible support and reported choice maxima
in TWO_VICTIM_PREFLIGHT_RESULTS.md; no root/action/control is rerun.
This is a source-derived lower bound, not an observed coefficient ordering.

Each type has at least one eligible positive first-reward layout in both owner
directions. For the owner-zero version, tracked token is d4:

|Type|Displacement v|One legal ordinary capture|Max choices/root|
|---|---|---|---:|
|P|(1,1)|d4-e5|5|
|N|(1,2)|d4-e6|11|
|B|(1,1)|d4-e5|15|
|R|(1,0)|d4-e4|17|
|Q|(1,0)|d4-e4|29|

Victims are enemy native Pawns. Both initial Pawns are away from attacks on
the own King a1 in these chosen layouts; moving the tag cannot expose a slider
attack because neither enemy ordinary is a slider. Enemy King h7 is remote.
The destinations contain the stated victim, paths for B/R/Q have no intervening
squares, and no promotion condition applies. Western capture patterns therefore
admit these actions and remove exactly one ordinary victim. Rank reflection
with owner swap preserves this argument, including Pawn direction. The full
root preflight independently reports these layouts ongoing across every type.

Let Amax_t be the measured maximum of complete choices for that type. At each
of the two specified roots, uniform complete-action policy gives first reward
at least1/Amax_t. Root mass is1/24; all other first/future rewards are nonnegative.
Thus direct actual H2 value satisfies v_t>=1/(12*Amax_t): P>=1/60,
N>=1/132, B>=1/180, R>=1/204, Q>=1/348. The two-victim bound gives v_t<=2.
These different LOWER bounds are not the ordering of actual coefficients;
none imply P>N or R>B. Do not fit a point vector from bound endpoints.

This removes the provable-all-zero native-board gate for this declared sparse
law without sampling a coefficient batch. It says nothing about required held
support, other base/current origins, cost-efficient refinement or useful choices.
The broad boxes overlap and cannot certify the exposed R>B diagnostic ordering.

Next interval pilot can start with these honest boxes and retain original root
mass. Source-derived positivity allows exploration; it is not approval to skip
the actual numerator/continuation/cost evidence or reserved use protocol.
