# Reverse-order joint proposal: exact efficiency gate before implementation

Base b34c2885a25b9936e4e8839d0e7576d4912d6142. No failed-corpus retry,
new task/value sample or reference change. Question: can reversing L/N and
Pawn placement preserve the globally dead-free joint law AND improve raw
proposal acceptance? Count first; do not build a sampler if this gate fails.

Original structural proposal has M=57^9 uniform Pawn layouts. On each, the
eight restricted L/N tokens (two per owner/type) have
U63=C(63,2)C(61,2)C(59,2)C(57,2) unrestricted physical placements. Dead L/N
placements are subsequently rejected. The other 14 tokens have constant
completion multiplicity on the remaining 55 cells.

Candidate: uniformly draw a dead-free L/N layout A on the EMPTY 81-cell board.
Let W81 be its exact physical layout count. Let C(A) be the product, over files,
of compatible unpromoted Pawn rank-pair counts after excluding occupied L/N
cells. Accept A with exact probability C(A)/M, then uniformly draw compatible
Pawn pairs and inject the other 14 tokens uniformly. Zero C is rejected, never
parent-fixed redraw. Every compatible physical pair (A,P) has equal unnormalized
probability (1/W81)*(C/M)*(1/C)=1/(W81*M), preserving the global conditioned
law and automatically its W(P)-weighted Pawn marginal. Apply the same subsequent
whole-state quiet/ongoing/capture filters; no omitted state condition is repaired.

The original valid (A,P) pair has unnormalized probability 1/(U63*M).
For ANY identical final acceptance predicate, both success probabilities have
the same numerator. Therefore candidate/original acceptance ratio is exactly
U63/W81. This compares RAW structural attempts, not accepted-output counts or
CPU speed. If the ratio is <=1, reject this candidate as a way to improve raw
acceptance without random trials or corpus regeneration. If >1, it is only a
necessary efficiency premise; implementation/cost still need a separate freeze.

Compute W81 using the existing cell-polynomial coefficient counter, with quotas
(2,2,2,2) and eligible groups read from the compiled Standard Shogi L/N empty
mobility masks. Check those four actual masks and that all remaining ordinary
types/anchors have nonempty empty-board mobility everywhere. Independently
test the counter on a tiny exhaustive assignment space. Record exact integers,
ratio, protocol/program hashes and result. One process, one full-board count,
at most 81 coefficient states/cell, 10 seconds total including compilation.
No Pawn-profile enumeration, unranking, random draw, coefficient or higher-budget
retry. A failure says nothing about the usefulness of the original Q or priors.
