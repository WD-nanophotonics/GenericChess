# Direct physical proposals: exact conditioning and initial cost evidence

The frozen protocol PHYSICAL_PLACEMENT_SAMPLING_PROTOCOL.md has SHA256
`706468d36bcee07e9c32b5d5d0834664e9beb9dc3eb23615d17686f712f8bf7d`.
Run base: sandbox `49debd0ad10200c09e08e4b1897b658c5ae8110e` plus the hashed
new scripts. This is a finite cost/support pilot, not a material coefficient.

## Exact proposal cost and uniformity

Under uniformly labelled injective placement with focal token fixed at (3,3),
the declared common Pawn structural mass is Chess
`775661821/126038941455` (0.00615414), Shogi
`41052847357053/129853494624428432000` (0.000000316147).
Thus naive rejection would take about 162 and 3,163,081 draws respectively
just for these structural conditions. King safety and other constraints are
additional rejection. These are exact model counts, not official legality rates.
Shogi shadow-Pawn file reservation is explicitly imposed on all focal types.

Direct conditional sampling avoids that rejection cost. On a separately brute-
enumerated 3x3 Pawn population, the paired-row construction produces all nine
valid physical placements exactly once. Uniform greedy choice of the own Pawn
row followed by uniform allowed opposing row is biased: its local pair weights
are 1/4,1/4,1/2 instead of 1/3 each. In the production nine-row factor there
are 57 equally weighted row pairs, with own-row marginal 8/57 for row 0 and
7/57 for each other allowed row. This is why whole joint pairs are sampled.

Other equal-type labels have constant permutation multiplicity; remaining tokens
are assigned by uniform sampling without replacement. Whole-frame rejection
then imposes common quiet support across every queried current type; it does
not create separate type-specific denominators. The law remains a declared
synthetic approximation, not reachable strategic visitation.

## Frozen full-inventory pilot

Seed 20261003; first admitted frame per game; no seed/score selection or further
sampling within this pilot after seeing zeros. Chess admitted proposal 2 after one own-anchor-check
rejection. Shogi admitted proposal 7 after six dead-placement rejections.
Rejection reasons are the first failed screen, not an exhaustive cause analysis.
All five Chess and all thirteen Shogi current types passed the common screen.
Five Chess and seven Shogi unpromoted focal roots were scored. Total cost:
1,642 materialized transitions in 0.656 s, within the frozen 30-second/20k cap.

All twelve observed net-custody task scores were zero. This supplies no usable
vector in those two sampled environments, but one frame per game does not
establish a population mean or prove the whole model always zero. No max-gauge
division, engine coefficient, reference comparison or sample increase followed.
Raw boards/actions/replies and hashes are in
data/physical_placement_sampling_20261003.json. Budget/proposal exhaustion is
incomplete evidence, never a zero coefficient.

## First zero diagnosis and its correction

The 46 focal actions include 30 with no immediate token gain and 16 captures
with immediate gains. Replaying only their first recorded refutations took 62
transitions and found 13 other-token countercaptures and three focal recaptures.
This does NOT say only three captures can be recaptured: first-refutation order
is not an exhaustive causal classification. Full replies were subsequently
examined in EXCHANGE_TASK_BACKGROUND_DIAGNOSIS.md; all sixteen capture actions
also permit a focal-loss reply. Keep that correction with the first diagnosis.

Retain the exact direct sampler and common-support account as method evidence.
Do not tune density, source, inventory or task for nicer piece ratios. Promoted
scoring, hands, histories and strategic population validity remain open.
The separately frozen existence question and exact conditioning follow-up are
reported in PHYSICAL_EXCHANGE_SUPPORT_RESULTS.md; they are not a mean estimate
or an enlarged version of this type-vector pilot.
