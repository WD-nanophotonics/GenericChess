# Frozen physical-placement conditioning and sampling check

Predeclared 2026-10-03 before sampler execution. This concerns the next actual
obstacle: a shared, explicit physical-state law, not motif-weight tuning.

## Population and modelling assumptions

For each game, fix owner 0 to move and a focal token at (3,3), replacing one
owner-0 Pawn from the declared initial inventory. Keep all other initial tokens,
empty hands, no historical entitlements (Chess castling/en passant off), and
reset synthetic history. Other tokens have uniformly labelled injective physical
placements. Equal-type label permutations have constant multiplicity and hence
induce uniform physical placements after quotienting them.

Condition on a common, explicitly chosen structural domain. Chess remaining
Pawns occupy ranks 1..6. Shogi remaining owner-0 Pawns occupy ranks 0..7 and
owner-1 Pawns ranks 1..8; both owners' unpromoted Pawns have distinct files. The
focal file is reserved as if the focal type were Pawn, for every query type.
This conservative shadow-Pawn condition keeps a single denominator for all
types. It is an assumption, not a universal validity test or occupancy-only
consequence. Nifu is preserved by the local initial Pawn structure and legal
Pawn movement/drop rules, but Core need not reject every synthetic board with
duplicate-file Pawns; do not falsely claim this screen is its root validator.

Shogi nonfocal Lance/Knight dead placements are rejected using their declared
empty-board mobility. After the Pawn-conditioned direct proposal, reject an
entire physical frame if ANY queried type gives either king in check or a
terminal root. This selects a common quiet support, deliberately omitting legal
checked roots. No per-type deletion or renormalization is allowed. It is not
uniform reachable play or the unique distribution implied by rules.

Common screening family: all five Chess ordinary types and all thirteen Shogi
ordinary current types. Only the five Chess and seven unpromoted Shogi base
types are scored in this cost/coverage pilot: 12 roots, one common frame per game.
Promoted screening is not promoted scoring; held mode remains absent.

## Exact support counts before sampling

With fixed focal square, Chess has 63 other cells, 7 own and 8 opposing Pawns.
The Pawn-mask acceptance mass is
`C(47,7) C(40,8) / [C(63,7) C(56,8)]`.

For Shogi there are 80 other cells, 8 own and 9 opposing Pawns. In each of
the eight nonfocal files there are 8x8 minus 7 = 57 distinct allowed owner-row
pairs. The focal file has 7 allowed opposing rows. The common Pawn-structure
mass is `7*57^8 / [C(80,8) C(72,9)]`. Remaining token completions have constant
multiplicity in either count. These are structural proposal masses, not full
legality probabilities or material values. Additional rejection can only reduce
the acceptance of a naive uniform-placement proposal.

Direct conditioned proposals: Chess samples the 15 remaining Pawn squares
without replacement from the 47 admissible cells, split 7/8 by owner. Shogi
uniformly samples one of the 57 owner-row pairs independently in each nonfocal
file and one of the 7 opposing rows in the focal file. Then assign remaining
labelled non-Pawn tokens uniformly without replacement to remaining cells.
These operations sample exactly the stated Pawn-conditioned base law. Rejecting
whole frames conditions it further without changing to type-specific measures.
Do not repair blocked proposals greedily or choose a seed for favourable scores.

## Frozen execution and gates

Seed 20261003, deterministic stable initial-token ordering, at most 128 direct
proposals per game, 12 scored roots, 20,000 materialized transitions, 30 seconds
total and a 35-second external timeout. First common admitted frame only; do
not select for captures/scores. Enumerate all focal actions and opponent replies
with the already frozen secured-exchange task (win=1, draw/loss=0, ongoing
positive custody=1; no-contest unsupported). Any cutoff/unsupported event leaves
an incomplete experiment, never a zero coefficient. No budget increase if this
pilot fails; first identify the specific cost/support cause.

Before interpreting sampling output, verify exact small-board enumerations:
the per-file paired sampler's images are uniform over all valid Pawn pairs;
uniform row-by-row repair is not assumed equivalent. Test token inventories,
no overlaps, common-family safety, budget abort and deterministic reproduction.
Store physical boards, common-screen rejection reasons and all action evidence.
One admitted frame cannot establish a population mean, reference agreement or
a nonzero prior. It tests feasible unbiased proposals and first full-inventory
cost/coverage only. No Xiangqi material reference, coefficient fitting, broader
worker, parallel job or workflow changes are part of this experiment.
