# Frozen exact dead-placement conditioning check

The support search rejected 101/128 Shogi proposals first for dead nonfocal
placement, with only five admitted roots. Do not enlarge that search. Before
optimising its proposal mechanism, check whether retaining a uniformly drawn
Pawn frame and merely redrawing other tokens until L/N can move would preserve
the SAME joint conditioned law. This is a measure question, not another score.

Use only the six already recorded Shogi Pawn frames: the original admitted frame
and all five support-search frames. No new random draws, quiet screening, scored
root or type utility. Strip all non-Pawn tokens; retain eighteen occupied Pawn
squares including the fixed focal token. The remaining 63 cells are uniform
physical destinations for 22 labelled ordinary/anchor tokens.

Four restricted groups L0,N0,L1,N1 have two tokens each. Their nondead ranks are
respectively 0..7,0..6,1..8,2..8. Count valid unlabelled placements exactly via
the coefficient of x0^2*x1^2*x2^2*x3^2 in the product, over available cells,
of (1 + sum eligible group variables). All fourteen remaining unrestricted
tokens have a constant number of completions and cancel. The unrestricted
denominator is C(63,2) C(61,2) C(59,2) C(57,2). Label multiplicities cancel.

An independent brute-force miniature oracle must verify the coefficient count.
If counts differ across Pawn frames, global dead-placement conditioning weights
their initially equal probabilities in proportion to these counts. Redrawing
only non-Pawns while keeping the Pawn frame would leave their marginals equal
and therefore bias the intended law. This does not estimate the quiet-screen
acceptance probability; anchors and common-family check remain further filters.

Limit six exact counts, 81 coefficient states per cell, ten seconds with a
15-second external timeout. Report exact fractions, source and input hashes;
no quiet-root search, score tuning, Xiangqi reference or engine change.
