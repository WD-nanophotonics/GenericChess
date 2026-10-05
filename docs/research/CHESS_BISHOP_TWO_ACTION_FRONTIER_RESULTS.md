# Exact Bishop two-action mass and residual uncertainty

2026-10-05. The prospective CHESS_BISHOP_TWO_ACTION_FRONTIER_DESIGN.md
was written before these counts. Native Chess, the same249984 ordered distinct
source/target/blocker worlds; virtual compatible contact, not official play.
No engine graph, coefficient batch, goal/source queries or human holdout.

## Count and proof

The225 displacement cells give1424 same-colour nonaligned ordered pairs:
640 have one valid diagonal elbow,784 have two, none have zero. For one elbow,
the union of its two ray legs has max(|dx|,|dy|)-1 eligible blocking squares.
For two elbows the two routes intersect only at source and target, so a single
blocker cannot eliminate both. Applying the design's rectangle multiplicities
and all62 blocker placements yields exactly85824 distance2 worlds.

The full partition is33936 exact distance1,85824 exact distance2, at least
127216 permanent zero, and3008 remaining worlds at distance>=3 or unreachable.
The permanent-zero classes are opposite colour and the disjoint source/target
corner traps. No unknown mass is discarded or normalized. Blocked aligned
contact cannot evade its blocker in two diagonal actions; any successful
two-action route between aligned endpoints stays on the original diagonal.

Therefore L_B=(33936*g+85824*g^2)/249984 and
U_B=L_B+3008*g^3/249984. The previous upper bound exceeds this one by
3008*g^2*(1-g)/249984, strictly positive for0<g<1. This also improves the lower
bound by the exact positive two-action mass. It does not claim all3008 take3.

## Duration implications

At g=1/2 the interval is approximately[.1537058372,.1552099334]. For the
independently declared density2(1-g) duration hypothesis, shared moment
m_t=2/((t+1)(t+2)) gives[.1024705581,.1036738351]. The Knight interval remains
approximately[.0282392676,.1522486772] and Pawn[.0182291667,.140625], both
overlapping the refined Bishop interval. These are illustrations of declared
hypotheses, not parameter selection or fitted intrinsic material prices.

The tightened frontier makes B substantially better determined cheaply, but
does not resolve B/N/P ordering under that mixture. Keep Q>R>B/N/P and the
reported fixed-g sign reversals; a generic scalar prior is still unadmitted.
Next useful effort is tightening N/P or independent duration/use motivation,
not another Bishop pair witness or adjusting gamma to an exposed outcome.

## Verification and cost scope

Three tests independently check rectangle counts against coordinate-pair
intersections on3/4/5/6/8 boards, exact two-ray existence over every triple
on3/4/5 boards, and trap exclusion/full mass/discount and mixture bounds.
These are geometry proof controls, not native engine candidate observations.
The construction uses225 displacement cells and constant-size formulas;
the verification enumerations are not proposed deployment preprocessing.
Frozen common-law and scoped-use producer inputs remain untouched.
