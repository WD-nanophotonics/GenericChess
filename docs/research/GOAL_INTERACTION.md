# Conditional goal interaction and allocation

2026-10-08. A constructive rule-goal diagnostic, not a selected material formula.
It distinguishes terminal utility from mobility and retains useful coalition
effects without human prices, fitted weights, position patches or NNUE.

## Why a single-actor goal count is insufficient

2048 predeclared unique K+actor versus K layouts share squares across Q/R/B/N.
Both Kings are safe and no candidate initially checks the enemy King, using an
independent coordinate prefilter before evaluation. Product Western semantic
rules retain supported legality/terminal behavior; all initial castling rights
are explicitly0. These are synthetic starts, not standard-opening reachability
or a claim to implement every FIDE adjudication convention.

Enumerating every legal first action yields mate-in-one root counts Q36/R19/
B0/N0. Q also has142 roots with minimum enemy mobility0 but no winning action:
stalemate focus cannot silently be valued as a win. All147373 transitions have
independent Native/Core full-state and terminal parity. The Q/R ratio is not
a fitted human-price target; B/N0 alone rules out using this count as a complete
material table. It does not show those pieces are useless.

Rule-derived goal/mobility features are plausible construction inputs, but the
literature does not identify this particular population or material utility.
[Clune's primary dissertation summary](https://link.springer.com/article/10.1007/s13218-010-0074-7)
describes stable abstract mobility/payoff/termination features. The
[Walędzik/Mańdziuk author manuscript](https://pages.mini.pw.edu.pl/~mandziukj/dynamic/wp-content/uploads/TCIAIG-2014-1.pdf)
derives features from rules and assesses outcome correlation through simulation;
its learned linear-feature pipeline is not a universal piece-price theorem or
the pipeline implemented here.

## Four matched intervention cells

Keep four occupied squares K+actor+helper versus K. A virtual I has no movement
or attack, retains ownership/occupancy and remains capturable. It is explicitly
outside orthodox reachable inventory. Helper is B or N, retained as separate
fixed strata. Compare AH, IH, AI and II, where m is existence of a legal one-ply
winning action. The paired interaction is

    D = mAH - mIH - mAI + mII.

Actor's gain with a helper alone also includes its independent contribution.
The advisor's four-cell objection was adopted before these measurements; it
does not count as independently executed evidence. Common safety filters apply
to every actor/cell, not separately chosen populations. Compiler setup options
require equal inventory, so B/N strata compile separately. The initial failed
mixed-inventory producer and partial output remain in the archive.

The broad law has512 layouts/helper and one shared all-Q/R/B/N-safe prefilter.
Only Q shows positive D:17 B-helper and13 N-helper roots. Others are0 in this
batch. To check existence separately, a constructed K(g6), B(g5), N(e7) versus
K(h8) permits Bf6 mate. In both actor/helper role assignments its four m values
are1/0/0/0. K covers g7/h7, N covers g8 and B checks h8. This confirms a missed
coalition mechanism, not its prevalence or independent validation of a price.

A changed-premise, predeclared goal-focused law puts the enemy King on an edge
and the own King at Chebyshev distance2; other filters/occupancy/cells stay the
same. Its original1024 layouts are retained. One II layout has no legal initial
King action and is rejected by the compiler. The corrected common geometric
preflight excludes that layout from ALL cells without replacement:511 B-helper
and512 N-helper contexts. The failed batch is preserved; this is a corrected
declared population, not a result-driven resample or restored holdout.

| Helper | Actor | Broad AH/AI wins | Near-anchor AH/AI wins | Near-anchor positive D |
|---|---|---:|---:|---:|
|B|Q|27/10|171/115|56|
|B|R|3/3|78/61|17|
|B|B|0/0|8/0|8|
|B|N|0/0|1/0|1|
|N|Q|16/3|158/129|29|
|N|R|3/3|92/79|13|
|N|B|0/0|2/0|2|
|N|N|0/0|0/0|0|

IH and II have no mate roots in these cohorts; no negative D occurs. This is an
observation, not a general nonnegativity theorem. Sparse zero cells have zero
empirical standard error; their printed degenerate normal intervals do NOT
establish a zero population rate. Changed laws are compared descriptively,
without treating them as one common-population estimator or tuning mixture
weights after outcomes. Both cohorts retain every legal first action and
Native/Core state/terminal checks:187766 and178559 transitions respectively.

## An explicit constructive allocation, with its boundary

Average the actor's marginal contribution when added first and when added
second, with equal order probability:

    phiA = (mAI - mII + mAH - mIH)/2
    phiH = (mIH - mII + mAH - mAI)/2.

Then phiA+phiH=mAH-mII on every context, checked exactly. The B/N witness gives
1/2 each. Broad Q with B helper gives observed mean phiQ=37/1024 and
phiB=17/1024; near-anchor gives143/511 and28/511. The near-anchor B+B pair
gives4/511 to each. These are exact averages of finite observed contexts,
not exact population probabilities, unique rule-implied allocation weights or
universal material coefficients. Equal order weighting is an explicit symmetry
convention. Helper, occupancy law and one-ply task materially affect the vector.

## Cross-game hand-goal intervention

An actual sparse Standard Shogi history captures P/G with N, then makes an
enemy N reply. The same seven-entity starts retain full ordinary Shogi rules;
no hand is injected and no virtual opponent pass occurs. Original P forbids
the mating drop(8,7) and has0 legal winning actions. Removing ONLY the pawn-drop
mate S4 postconditions permits that drop and1 winning action; original G permits
it and has3. Nifu, drop masks, promotion and other semantics remain unchanged.
This tests typed rule-goal effects, not interchangeable Chess/Shogi mate rules.
Every route root and child has full Native/Core legality/state/terminal parity.

A separate exact finite continuation uses uniform legal target drops, then
uniform enemy replies, and records both terminal probabilities and the deployed
actor's endpoints at its next actual turn. Immediate wins have activity0 because
the game ended, but retain positive win probability in the separate component.

| Cell | Legal target drops | Expected endpoints | Terminal win probability |
|---|---:|---:|---:|
|P, original prohibition|66|31/33|0|
|P, only S4 prohibition removed|67|62/67|1/67|
|G, original rules|75|117/25|1/25|

Permitting a winning move LOWERs endpoint-only mean from0.93939 to0.92537:
the extra terminal branch dilutes the uniform-drop average. This is a concrete
utility-bridge failure, not just a small sampling error or horizon mismatch.
For an illustrative blend U+lambda*win, the P rule-change difference is exactly
`(33*lambda-31)/2211`; its sign depends on an unselected utility scale. Keep the
terminal/activity vector rather than silently treat terminal0 activity as
worthlessness or fit lambda against human prices. These exact finite-policy
averages are not full-game WDL probabilities or universal prices.

A constructive rule-only convention can normalize endpoints by81 and give a
terminal win1: E[win]+E[U]/81. It yields31/2673,143/5427 and22/225 in the three
cells. The convention bounds an ongoing actor's endpoint score below a terminal
win at each leaf, without claiming calibrated game utility or selecting it by
human agreement. More generally G exceeds both P cells for EVERY nonnegative
lambda because both coefficients of the paired difference are positive. Ordering
is robust on this cohort, while G/P ratios are not: illustrative lambda0 versus81
moves G/originalP from4.982 to8.431 and G/noS4P from5.057 to3.711. Retain the
conditional ordering and an explicit utility family, not an outcome-chosen ratio.


Per-drop decision checks sharpen the distinction: endpoint-only maximization
has62 nonwinning ties in each P cell and30 nonwinning maxima for G. The
declared terminal-normalized convention instead selects the sole permitted P
win or the three G wins. This is a finite-policy proxy failure, not a diagnosed
player regression. Twelve repeated public depth1 calls on these actual-history
roots (Python and available Native routes, equal512node/5sec ceilings) already
select a known winning action whenever legal; original P has no legal mate.
All calls complete and repeat. No terminal-priority player patch is needed.

The first continuation producer incorrectly identified the tagged G by unique
base type although another friendly G was already present. Its partial P rows
and source remain. The corrected producer identifies the actor at its actual
drop destination; the single enemy reply can capture but cannot move that own
actor. The previous failure is not hidden by a new output name.

Retain conditional goal contributions alongside time-aware service, without
promoting either into default prices. Another unchanged random sweep would not
resolve the utility scale/context bridge. A useful next step is a declared
terminal-aware finite contribution or a longer legal goal window, keeping the
sparse zeros and cross-game legality differences intact. Science remains OPEN.

[Compact results](data/goal_interaction_20261008.json) retain exact fractions,
both cohorts, exclusions and witnesses. [Archive](../archive/goal_interaction_20261008/README.md)
retains executed definitions, producers and failures, separate from temporal and
search evidence. No live product dependency imports this experiment.

## Behavior-law sensitivity

Exact frozen-census reweighting selects uniformly among immediate winning drops
when available. G and P without S4 both saturate at win1/activity0; original P
stays win0/activity31/33. Terminal-normalized values are1,1 and31/2673. Thus
the uniform-law G/P distinction is not an intrinsic material ratio. Selecting
minimum-scalar enemy replies changes none of these three cells: their existing
reply outcomes lack discrimination. No new player patch, sample or fit follows.
[All policy combinations](data/service_context_sensitivity_20261008.json) and
[isolated sources](../archive/service_context_sensitivity_20261008/README.md).
