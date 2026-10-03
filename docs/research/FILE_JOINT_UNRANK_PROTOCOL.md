# Exact joint unranking implementation gate

Follow `FILE_JOINT_COUNT_PROTOCOL.md` and its exact count certificate; keep that
protocol unchanged. Test a direct draw, not a retry of the incomplete corpus.
No task labels, coefficients, human values or Xiangqi access. No production
prior changes. One process, 10 seconds including compilation/preprocessing and
one full-board draw, seed 202610040401. Do not require a quiet state or retry.

Draw one integer uniformly in [0,Z). Decompose it across nine files by integer
blocks F[g] * suffix[remaining-g], for file occupancy vector g. Inside that
block use quotient/remainder to select the file configuration and the remaining
files. Select its Pawn pair using the individual file-term coefficient at g;
then unrank the seven free physical cells using exact suffix coefficients,
with choices empty or one eligible L/N group. Thus each physical joint layout
has exactly one integer rank. No floating-point probabilities or fixed-Pawn
redraw. Unsupported/zero-count blocks cannot be selected.

Independent test: enumerate ALL integer ranks for the frozen tiny two-file,
four-rank, one-L-per-owner model from the count test. Compare the resulting
configurations as a set against directly enumerated physical assignments;
require no duplicates and exact size. Test first/last and out-of-range ranks.
Full-board draw must have one unpromoted Pawn per owner/file, 18 distinct Pawn
cells, exactly two tokens per L/N owner/type, 26 distinct occupied cells, and
every restricted token in the compiled non-dead mask. Record all physical
placements, integer rank, exact Z, seed, program/protocol/count-program hashes
and elapsed time. There are still 14 unrestricted initial tokens to place;
full GameState assembly, quiet filtering and corpus cost contract are next work.
