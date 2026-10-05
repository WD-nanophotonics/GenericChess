# Complete-action inventory dual qualifier

Freeze before a NEW semantic root enumeration. Standard Shogi: own K a1/P a4,
enemy K a9, own hand P1; all remaining ordinary stock is enemy hand:
P16 L4 N4 S4 G4 B2 R2. Global40, both Kings safe. Own side0. Enumerate ALL
legal semantic actions exactly once. Bound128 root actions/5000 total/15sec;
0 materializations, goal probes, history construction or independent labels.

Every root action is either a P drop (hand P-1, board P+1), a quiet native P
move or a King move (ordinary inventory unchanged). Verify compiled action
patterns have exactly drop or move effects, no promotion/removal/aux effects.
Map every full parent action to its exact inventory delta; this is a complete
position-level action-to-feature table, not an observed full-history child table.
No root actions filtered. Native P on file a makes nifu exclude all a-file drops;
therefore no drop checks enemy K a9. Full-stock origin context retained.

For each predeclared duration separately compare independent20-mode boxes with
the normalized same-parent proved constraint board P-hand P >= positive gap.
Use a supplied nonnegative multiplier1 for drop-vs-quiet and0 for equal drops.
Canonical action ordering determines ties. Require same choice for both laws.
No tuned coefficient, midpoint, fit or game usefulness inference. State whether
box-only uncertainty is removed by the exact shared-law certificate.
