# Rank-stratified Pawn bounds complete the two declared native Chess orders

2026-10-05. CHESS_PAWN_FRONTIER_DESIGN.md preceded all new counts. Same
249984 native Chess worlds; both owners by rank reflection. No game goal,
coefficient fitting, human holdout or new native engine observation budget.

## Better positive support, full target mass

For each k=1..7 remaining quiet actions, there are24640 worlds with source
below last rank and both blocker/target on other files. Direct overlap is770
per rank, leaving23870 nondirect worlds with a single-quiet-to-Q route<=k+3.
Use L_P=(6076*g+23870*sum_(k=1..7)g^(k+3))/249984. All direct worlds remain
once, including their1379 outside that stratum. No favorable normalization.
This improves the old cost10 lower without a double-step or auxiliary shortcut.

## Additional permanent zero

An own blocker ahead on the source file prevents every promotion route.
Only an adjacent-file target at offset1..j, where j is blocker distance, can
be captured before the blocker. Single quiet steps supply that capture route;
an initial double cannot jump the blocker. Exclude old forward-same-file target
zeros, then sum additional zeros:

    sum_(k=1..7) [8*k*(63-k)-14*k*(k+1)/2] =11816.

The14 is summed adjacent-file degree across the eight source files. Source-last
31248 and forward-same-file13888 remain disjoint old zeros. Total zero56952.
No EP victim can arise off-file: the sole enemy target is stationary and never
moved two steps; own double tokens do not create an enemy-victim capture.
This is a physical reachability argument, not deleting a token effect.

## Exact two-action mass

Distance2 splits by first action/source rank:

| Class | Count | Physical qualification |
| --- | --- | --- |
| single quiet then native diagonal capture, source ranks0..5 | 5124 | 84 pairs, one forbidden blocker square |
| initial double then native diagonal capture | 840 | 14 pairs, both path/destination clear |
| quiet promotion then Q backward vertical capture | 2808 | old source vacates; eight files, lengths2..7 |
| quiet promotion then Q horizontal capture | 2450 | exclude direct P targets at length1 |
| quiet promotion then Q diagonal capture | 3304 | exact ray blockers |
| quiet promotion then N capture | 1586 | 26 jump targets, disjoint from Q rays |

Total exact P2=16112. Q includes R/B capture geometry but NOT N jumps; omitting
the last row would make the upper invalid. All promotion-Q/R/B/N choices are
therefore covered for this two-action question. Unknown mass170844 remains>=3,
not unreachable. Upper U_P=(6076*g+16112*g^2+170844*g^3)/249984.

## Declared duration implications and independent verification

Under the previously declared density2(1-g), P lies in[35/1152,5273/60480],
approximately[.0303819444,.0871858466]. Refined B lower exceeds P upper by
28657/1874880, approximately.0152847116. For previously declared fixed g1/2,
B lower-P upper=20005/499968, approximately.0400125608.

Combined with exact Q/R and the new N3 certificate, BOTH predeclared hypotheses
now certify Q>R>N>B>P in this native virtual task. No parameter was selected
from this order, human prices or outcomes. Arbitrary-g reversals remain; this
is not a discount-free intrinsic order or independent useful-search validation.

Three tests independently enumerate direct/first-two-action blocker worlds
over the entire8x8 population, check blocked double, vacated source and Knight
promotion controls, and verify rank-overlap/mass/rational margins. Enumeration
is proof verification, not proposed preprocessing or compiled-rule candidate
observations. Full history, royal legality and generic promoted/held origins
remain outside this virtual scope; source qualification is still required.
