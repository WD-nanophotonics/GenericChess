# Complete Shogi current-board interval family

Same uniform511920-world law and two predeclared durations. Exact2 prefixes
come from the frozen shared-geometry report; full support bounds come from
constructive promotion paths and Gold routing. No hand coefficients or new
goal labels. Every current-mode interval is positive; finite tail bounds are
sufficient rather than exact shortest distances. Raw means, no guessed maximum
normalization or midpoint.

|Mode|Half lower|Half upper|Mixture lower|Mixture upper|
|---|---:|---:|---:|---:|
|P|4307162761/357858017280|828011/10920960|199252744/16148996325|2423677/35834400|
|L|410058011/11183063040|89819/682560|421387/14589720|51389/511920|
|N|1374577517/67098378240|55981/511920|916033/53751600|72311/853200|
|S|125402767649/2147148103680|219089/1365120|5919359/141289920|115763/959850|
|G|1981233101/33549189120|665683/4095360|779291/17405280|37523/307152|
|B|791142302131/4294296207360|95197/409536|61894909/499122000|309833/1919700|
|R|941/3160|941/3160|7061/35550|7061/35550|
|TP|1981233101/33549189120|665683/4095360|779291/17405280|37523/307152|
|TL|1981233101/33549189120|665683/4095360|779291/17405280|37523/307152|
|TN|1981233101/33549189120|665683/4095360|779291/17405280|37523/307152|
|TS|1981233101/33549189120|665683/4095360|779291/17405280|37523/307152|
|TB|315184679/1397882880|327/1264|992429/6526980|56599/319950|
|TR|315059/1023840|315059/1023840|393997/1919700|393997/1919700|

R/TR exact3 follows R-ray coverage of every world plus the saved first2
histograms. TR one-step diagonal additions leave residual2772 instead of3024.
TB contains Gold orthogonal routes, so its remaining136104 worlds reach in<=16.
Native L residual461688 minus exact72918 zeros leaves388770 at times3..17.

The same-world simulations TB>=nativeB and TR>=nativeR survive actual quiet
promotion, whereas promoted Gold is not assumed to dominate native S/N/L.
The extra direct worlds give positive gaps at least22752 or20224 times
(m1-m2)/511920. Native L>P and TP>P retain their prior coupled bounds.
Overlapping coordinate boxes do not erase these constraints, but arbitrary
independent box selection can lose them. The current operator supplies sound
bounds, not a complete strategic material prior or deployment benefit.

Four exact-arithmetic controls pass. S/N/B constructive tests cover both owners.
Evidence: SHOGI_NATIVE_PROMOTION_REACHABILITY_RESULTS.md,
SHARED_GEOMETRY_CONTACT_PREFIX_RESULTS.md, SHOGI_PAWN_PROMOTION_SUPPORT_RESULTS.md,
SHOGI_LANCE_SUPPORT_COUPLING.md and scripts/shogi_complete_board_intervals.py.
