# Exact file-local joint count before drawing states

Base b34c2885a25b9936e4e8839d0e7576d4912d6142. The reverse-order acceptance
certificate rejected that proposal. This experiment counts a new joint
representation; no RNG, corpus, labels, coefficients or Xiangqi access.

For one Shogi file, enumerate its 57 ordered own/enemy Pawn rank pairs:
own rank 0..7, enemy rank 1..8, unequal. For each pair, multiply the remaining
seven physical cells' polynomials (1 + sum eligible L/N group variables).
Groups are own L/N, enemy L/N; truncate each exponent at two. Eligibility must
match actual compiled empty-board mobility. Sum these 57 polynomials to F.
Each physical Pawn/L/N file configuration appears exactly once. Combining nine
files gives Z=[x0^2 x1^2 x2^2 x3^2] F^9. This equals sum_P W(P), implicitly
weighting Pawn frames correctly; unrestricted remaining 14-token completions
have the same constant multiplicity on each remaining 55-cell set.

Use integer arithmetic, at most 81 monomials per table. Build the 57 file terms
with seven cell updates each, then nine truncated polynomial convolutions
(at most 81^2 candidate pairs/convolution). Include compilation and counting
in a 10-second single-process gate; abort yields no complete certificate.
Record hashes, exact Z, intrinsic acceptance Z/(57^9 U63), table size, elapsed
time. Check Z positive and <=57^9 U63, F's constant coefficient exactly 57.

Before using this representation for sampling, independently exhaust a tiny
two-file/four-rank physical space with one Pawn per owner/file and one L per
owner globally. Compare joint count to polynomial composition and explicitly
sum per-Pawn-frame valid L placements. No full-board exhaustive enumeration.
Future uniform sampling needs backward coefficient-weighted file selection,
then weighted Pawn-pair selection and cell completion. Counting alone is not
uniform-draw or cost acceptance for that future sampler. Whole-state quiet,
ongoing and deployment capture filters still apply and are not removed.
