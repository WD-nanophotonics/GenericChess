# Exact joint count and uniform restricted-placement draw

Frozen count and draw protocols: `FILE_JOINT_COUNT_PROTOCOL.md` and
`FILE_JOINT_UNRANK_PROTOCOL.md`. Certificates preserve hashes and the actual
26-token draw in `data/file_joint_count_20261004.json` and
`data/file_joint_unrank_20261004.json`.

The nine-file coefficient is
Z=12,666,047,573,426,791,865,632,639,560 distinct physical Pawn/L/N layouts.
The original structural denominator is
61,988,329,179,514,495,683,187,237,080. Intrinsic acceptance is exactly
68583753375713622837517/335652637965748839523431, approximately 20.43%.
This describes dead-placement filtering alone, before anchor checks or captures.
The coefficient tables never exceed 81 states; counting with compilation took
0.156 s. It counts all Pawn backgrounds with their valid L/N multiplicity,
without enumeration of 57^9 backgrounds or fixed-background bias.

Integer unranking gives a bijection: a file occupancy block has size
F[g] times its remaining-files coefficient; quotient/remainder separate the
local rank and suffix rank. Pawn-pair blocks have sizes given by the pair's
coefficient, and cell choices use suffix completion counts. Every physical
layout has exactly one rank. Uniform `randrange(Z)` therefore induces the
globally dead-free conditional law; no floating probabilities or rejection
inside this layer. A tiny two-file/four-rank independent physical oracle checks
EVERY rank for complete coverage and absence of duplicate output. It also
confirms unequal Pawn-frame completion weights. Boundary/abort tests pass.

One full 9x9 draw at seed 202610040401 completed in 0.156 s including compilation,
preprocessing and unranking. All 18 Pawns satisfy owner/file and dead-rank rules;
all eight L/N tokens have correct inventory and compiled non-dead mobility;
26 occupied cells are distinct. This verifies restricted-placement construction,
not a quiet full GameState, corpus coverage, task labels or predictive validity.
The unranking routine is research code; no production evaluator was modified.

Next place the remaining 14 actual initial tokens uniformly on the 55 free
cells (constant completion multiplicity), assemble full state and retain the
existing whole-state quiet/ongoing filters. Validate inventory and state scope,
include all preprocessing in the cost gate, then freeze a NEW corpus protocol
before any new draw batch or labels. Keep the old incomplete corpus unchanged;
this new algorithm addresses its independently observed intrinsic-rejection
problem, and does not justify raising the old budget or dropping a stratum.
