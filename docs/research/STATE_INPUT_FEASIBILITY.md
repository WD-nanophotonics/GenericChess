# State inputs: semantics, finite-search signal and caller cost

2026-10-09. This is an offline feasibility study, not training, a learned
evaluation deployment, an Elo result or a replacement for rule-derived prices.
The decision is to retain a small sparse Position candidate for the next signal
study, with material and coarse occupancy controls. Do not put freshly computed
semantic attack relations at every leaf merely because their vector is small.
No product evaluator, compact model schema, search default or resource setting
changed. Full generated-rule transfer remains an open target.

## What state must the input distinguish?

The old `semantic_state_features` encodes current board identity, base hand
counts, side, three supplied dynamic values and auxiliary slots. On an existing
mixed-custody rule, swapping the base identities P/Q of two promoted R actors
leaves its 525-dimensional vector identical when the dynamic inputs are fixed
to zero. The same actual capture and legal reply yield P versus Q in hand;
only Q can then drop at b2. This is an input collision with a consequential legal
continuation, not proof that the full dynamic evaluator returns equal values.
The swapped root is a declared counterfactual, not a proven reachable opening.
An inert off-board semantic augmentation selects the proper semantic compiler
without changing the twelve root legal actions. The earlier five-dimensional
legacy-compiler result was input misuse and is retained separately.

`scripts/position_features.py` supplies a separate offline layout. It keeps
current/base board types, promoted flags, base hand counts, side and compiled
auxiliary values; rectangle coordinates use width and height separately.
Fingerprint and ordered type metadata bind the layout to one compiled RuleSet.
Absent auxiliary storage uses the declared logical initial value; an explicit
cleared square remains distinct. Unknown identities are not silently discarded.
Nine tests compare actual semantic transitions against an independent dense
oracle, preserve the old square prefix and exercise base, promotion, rectangle,
logical-default and contract boundaries. Existing live model dimensions remain
unchanged; equal dimension does not authorize cross-rule weight sharing.

This still encodes Position, not full GameState. A legal knight-cycle control
with an explicitly changed repetition limit of four has identical Positions
at plies4/8/12 but current repetition counts2/3/4. The first two are ongoing;
the last is drawn. The same four-move continuation from the first two has
different adjudication. Both old and new Position vectors alias these states;
the actual search history keys distinguish them. Correct search history does
not make a history-blind finite leaf predictor complete. No opaque hash feature
or weakened provenance guard is introduced.

All68states and64actions of the four frozen generated8 temporal routes were
also replayed. Sixteen active-right counterfactuals change the existing aux
feature but no immediate legal action, since eligible P hand stock is absent.
No selected action changes auxiliary state while conserving material inventory.
This cohort supplies no consequential aux-only q omission. It neither warrants
all-quiet expansion nor proves temporal rights generally irrelevant.

## Sparse recomputation is feasible, not automatically faster

A fixed width16 random network was evaluated and discarded; every search still
returned the same unit-material score. On78actual mixed-custody leaves, sparse
reconstruction matches the1165-dimensional dense input exactly; standardized
dense and sparse forwards differ by at most2.50e-16. Folding mean/scale into
weights/bias is explicit. Ten to thirteen active features use160–208first-layer
multiply terms versus18640dense terms. These are full recomputations, not
incremental accumulator updates, learned scores or quantized NNUE.

Forty-eight D2q0 calls span four existing generated8 frontiers, two rectangular
cannon roots and two mixed roots, with two order-balanced repetitions and
baseline/dense/sparse methods. All complete with identical choices, scores and
main nodes. Generated vectors have1682dimensions and44–65active terms. Across
the eight roots, median wall ratios relative to baseline are1.147dense and
1.014sparse. The q2/hard8 repeat completes30/48calls; three generated frontiers
hit the5second checkpoint in every method and returnD1. Completed-root ratios
are1.228dense and1.016sparse. Capped calls have different explored work and must
not be described as exact-cost parity or a speed gain.

A changed-premise fresh-process check on the completing seed2102 requests one
BLAS thread versus the default environment. The dense/sparse timings overlap
under the one-thread request. Actual worker thread count was not measured.
This rejects a uniform sparse-faster claim; do not change global thread settings
or optimize this kernel further without a concrete decision benefit.

[Stockfish's primary NNUE account](https://github.com/official-stockfish/nnue-pytorch/blob/master/docs/nnue.md)
explains selecting active columns and optionally updating accumulators from
changed inputs. Its chess-specific feature layout and refresh rules do not
establish a generic-rule update scheme. This pilot tests only sparse full
recomputation; generic event invalidation and incremental correctness are open.

## Does anything beyond material carry a signal?

Dot correctly objected that an input distinction or a varying teacher score
alone need not contain a useful residual beyond existing material features.
Adopted one next check: freeze an evaluation-independent route and all child
actions, then compare teacher scores within identical full material vectors.
Dot reviewed published documents and our report, not the local execution.

One already exposed complete generated8 RuleSet, seed202610082102, is fixed.
A lexical-action seeded random route2026100901 selects roots at plies0/4/8/12.
All legal children, material groups and new input hashes are declared before
teacher calls. All135children complete the same remainingD2 q0 unit-material
Core search, no TT/order/native/disk/root tactical shortcut;2048nodes and one
second per child. Full actual history is carried. Total teacher time is28.47s.
No missing labels, resampling, result-driven extension or training occurred.

|Root ply|All children|Same-material pairs|Different finite teacher scores|Ties|
|---|---:|---:|---:|---:|
|0|26|237|104|133|
|4|33|409|2|407|
|8|36|499|0|499|
|12|40|565|123|442|
|Total|135|1710|229|1481|

These sibling pairs are dependent, not229independent examples. All differences
are finite material-search targets, not terminal-derived wins. Old current
Position, new base-aware Position, semantic relations and coarse-plus-relations
have zero input collisions among the229different pairs. Coarse3x3 occupancy
has four. Zero collisions demonstrate neither linear representability nor
learnability, generalization, necessity of nonlinear models or value accuracy.
The base-aware repair addresses the separate custody witness; this cohort does
not show it improving predictive performance over the old full Position input.

The first differing pair in each informative root and every coarse collision
member are retained with actual legal PV replay. Six selected independent
full-width minimax D2 references all complete and match the teacher. They check
the finite-search calculation, not an independent valuation or true WDL.

A post-label, no-fit additive-capacity check uses the same135children. Across
9180unordered input pairs including repeated indices, the old/new full Position
inputs have122revisits with equal input sums but unequal target sums. These are
dependent constraint witnesses, not122independent errors. Four independently
recomputed full-widthD2 values confirm the first witness: input sums are exactly
equal while target sums differ by2000. Any single affine scorer on those raw
inputs must therefore make at least500maximum absolute error on these four
states. Coarse occupancy and semantic relations also have contradictions.
This concerns exact finite-target representation, not ranking failure or useful
approximation. It does not require a neural network: a linear model on suitable
nonlinear interaction features is a different family. Do not make exact fit
a development gate.

## Low dimension can be expensive

Eighty matched calls reuse those four roots: D2/2048nodes/3s, q0 or q2/hard8,
two order-balanced repetitions, five input methods. Fixed sparse-width16 or
linear feature outputs are discarded; all methods return identical unit material.
Ratios below use only complete calls with identical action/score/main/q work.

|Added input work|q0 complete/8; median wall ratio|q2 complete/8; ratio on matched complete calls|q2 depth losses versus baseline|
|---|---|---|---:|
|Sparse Position width16|8;1.021|5;1.036(n=5)|1|
|Coarse3x3 linear|8;1.017|6;1.027(n=6)|0|
|Semantic relations linear|8;2.903|4;1.626(n=4)|2|
|Coarse plus relations linear|8;2.974|4;1.664(n=4)|2|

Baseline q2 completes6/8. The sparse loss is one near3second boundary; report it
rather than dismissing it as noise. Capped methods explore different work.
All completed pairs have identical signatures; no useful learned evaluation was
used. The36-dimensional relation vector makes repeated semantic attack queries;
its small width conceals feature-construction cost. This supports deferring
per-leaf relation extraction, not rejecting every interaction model or rule.

A separate mechanical comparator counts ordered owner/current-type actor pairs
by full signed relative displacement, with no game-specific coefficient table.
Its four-state histogram oracle matches;24channels break the additive witness
sum equality. This is a feature-family distinction, not a fitted prediction.
It omits base/promotion, hand, aux, history and rule descriptors, so it can only
augment a scoped complete input or serve as a limited control. Its32400possible
channels have730–950active terms in measured calls. Forty-eight fresh matched
unit-score calls record42D2completions and6caps. Median matched wall ratios for
pair input are1.113(q0,n=8) and1.037(q2,n=6), versus contemporaneous sparse
width16ratios1.056/1.017. Neither loses completed depth against its baseline in
this repeat. Prior sparse boundary loss stays recorded; this does not erase it.
The pair comparator is worth retaining as a cheap interaction alternative to
semantic attack extraction, not as a new default or a demonstrated useful score.

## Next decision and evidence

One further common-board intervention separates input coverage from transfer:
copy seed2102's initial board into each of the four existing complete generated8
RuleSets, compile each correctly and freeze all roots before searching. Their
1682-dimensional Position vectors are identical but legal root sets differ
(62/48/26/24actions). All fourD2q0 unit controls complete. Two replay-verified
PVs are mate in one, while the other two return zero. These terminal-derived
differences are separate from the229nonterminal same-material differences;
the transplanted boards are not playable-rule validation. A fingerprint guard
is not a numeric rule descriptor. However, semantic search/terminal bypass
already observes rules: this does not prove every cheap leaf model must encode
every mechanism. Per-rule compiled/fitted coefficients and a shared rule-
conditioned predictor are different experiments, neither established here.

This distinction also appears in mature generic-game work. The
[Ludii–Polygames interface paper, section4](https://arxiv.org/html/2101.09562)
constructs state/action tensors mechanically from the game system, including
piece, player, auxiliary and hand/container information. It explicitly notes
state coverage limitations. This supports compiling a shared interface rather
than hand-writing a solution per game; automatic tensor construction alone is
not a claim of one universally trained model.

The [transfer study, sections3–4](https://arxiv.org/pdf/2102.12375) maps channels
using encoded-data semantics, explicitly excluding differences in game rules
from that equivalence test. It reports both successful and negative transfer.
The [official Polygames implementation](https://github.com/facebookarchive/Polygames#examples-for-converting-models)
also distinguishes a game's saved checkpoint from a converted model. Our
inference is that schema portability, per-rule training and zero-shot transfer
need separate measurements. The paper's training costs are not a lower bound
or a budget proposal for this project; no framework is installed here.

Prefer the scoped sparse Position input and retain material/coarse controls,
with relative-pair histograms as an optional low-cost interaction comparator.
Before any fitting experiment, specify what decision a compact predictor would
change, its teacher/return target and an evaluation-independent split. This
study cannot decide sample efficiency, search benefit or unfamiliar-rule transfer.
Relevant history remains an explicit approximation boundary; do not silently
shrink the full target to Position-only games. No automatic training follows.

Raw sources, complete/capped results, declarations, partials and corrected
failures are isolated in `../archive/state_inputs_20261009/`. The public data
index is `data/state_inputs_20261009.json`. The recovery package includes exact
Agent-generated input records and source snapshots, not Slack/account logs or
machine configuration. Earlier stale-history/setter/legacy/PV-adapter failures
remain visible; fixing their experiment setup did not weaken product checks.
