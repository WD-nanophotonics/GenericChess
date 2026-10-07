# Joint service and replacement contribution

This is exposed, rule-only development with an explicitly virtual context law.
It separates task utility, matched replacement contribution and compensating
inventory prices. None of these results selects a new default material table.

## Active opponent, same ordinary targets

One Q/R/B/N actor, one active Q/R/B/N opponent and one stationary enemy ordinary
token occupy distinct squares. Each side acts once. Captures gain one unit;
losing the actor costs one. Rays stop at occupied squares, captured entities
are removed, loss is absorbing. There are no anchors, promotions, hands or
reachable-game distribution. Both actor-first max/min and opponent-first min/max
are solved; equal opponent modes and equal action orders are descriptive mixtures.

| Actor |4x4 actor-first |4x4 opponent-first |4x4 equal orders |8x8 equal orders |
|---|---:|---:|---:|---:|
| Q |649/840 |197/1680 |299/672 |11629/35712 |
| R |39/70 |-101/1680 |167/672 |6277/35712 |
| B |529/1680 |-31/168 |73/1120 |69/896 |
| N |89/420 |-181/840 |-1/560 |209/124992 |

The4x4 census has53760 mode/context roots and a separate independent full-board
oracle checks every root. The8x8 census has3999744 roots,110.345 observed seconds,
and4096 prespecified independent oracle cases. Both have zero checked mismatches.
N changes sign with board size; the negative4x4 result is not a general claim
about N. Signed utility, even when positive on8x8, is not a compensation price.
The first producer's tie selection did not match the declared smallest-square
rule. Its exact source/output survive separately; correction leaves all net
means unchanged and qualifies gross/loss tie statistics.

## Matched replacement, not deletion or normalization

Following the advisor's useful distinction, hold source, opponent, stationary
target, action order, reward and horizon fixed and compare V(c,p)-V(c,b).
Policies reoptimize within that same task. Deleting an entity would also change
blocking and exposure, so it answers a different question. Dividing these
differences by a pawn reward would not establish how multiple pawns compensate
one queen: their placements and interactions would need a separate construction.

The4x4 paired projection preserves per-opponent/order signed histograms and
witnesses. Q-R has no negative roots; mean differences span1/5..101/420
actor-first and2/21..53/210 opponent-first. Q contains R's actions and the
one-action unit reward depends on destination/capture rather than actor name.
Consequently this dominance is an action-set consistency check, not independent
evidence for a queen/rook material ratio. B-N is not nested and has positive,
zero and negative root differences despite positive aggregate means in each
opponent/order stratum. Its average is not a pointwise ranking.

The conceptual distinction does not require a complete WDL model before useful
approximation. It does require naming the payoff and context law. Shapley's
stochastic-game construction specifies payments, transition probabilities and
starting state before solving its value; that theorem does not select our
reward or sampling law. See the [original paper](https://cs.siu.edu/~hexmoor/classes/CS539-F10/Shapley.pdf).
The advisor's bibliographic reference to [A Value for N-Person Games](https://www.rand.org/pubs/papers/P295.html)
concerns coalition allocation; our paired replacement is not asserted to be a
Shapley value. Only its bibliography, not its scanned full argument, is used here.

## Current mode and custody continuation

Two40-entity counterfactual9x9 roots use actual Standard Shogi semantic effects.
The target is current G or base P/current TP on the same square. Other geometry
is identical; replacement changes the base inventory and its promoted provenance.
These are not asserted historically reachable Standard Shogi positions. An
initial duplicate-current-pawn construction is retained as unqualified; the
corrected shared context uses a promoted black pawn and checks every current
pawn file count. State acceptance alone is not a reachability certificate.

Both target modes have the same five initial legal destinations. A fixed legal
capture, reply and common-square drop transfers G to enemy G, but TP to enemy P.
After a further fixed reply, the G token has five legal actions including the
preselected ordinary capture; P has one and cannot make that capture. All12
full-history native/Core legal sets agree. This is one mechanism witness, not
a numeric price or optimal-strategy result.

A subsequent matched-placement check enumerates all common legal drop squares
in that same captured context: G has42 legal drops, P6, and all6common squares
allow the identical predeclared White reply. Three yield a positive G-minus-P
next-capture opportunity count; three yield zero. All24 full-history native/Core
legal-set checks agree. The original chosen square is a conditional witness,
not an all-placement effect. Capture-to-base identity changes both the legal
drop population and later service; averaging only the common squares would
omit G's other36 placements. No population/phase weights are chosen from these
results to obtain desired material values. The follow-up is indexed separately
in the same archive, preserving the initial trace and all failed versions.

An own-tag estimator that becomes absorbing on enemy capture omits this later
opponent service. A signed custody model can retain it. Under the deliberately
restricted approximation of equal pre-capture Gold service A and common
discounted transfer factor b, V_G=A-b V_G and V_TP=A-b V_P, hence
V_TP-V_G=b(V_G-V_P). This explains a possible base-dependent contrast when the
enemy's base G service exceeds base P service. No b or V_P is fitted or admitted
as a common hand price. Actual drop constraints, actions and context determine
those continuation terms; the observed trace verifies only one such distinction.

The explicit finite continuation now replaces speculation about a common b:
all48 drops have zero forced immediate service, and12 common-drop two-tag-turn
cells remain zero. A uniform legal-action custody law retains return/redrop and
exchangeable hand provenance, but yields context-dependent signed task rewards.
It does not establish positive inventory prices. CUSTODY_CONTINUATION.md owns
this next stage and its distinct conditions; the earlier mechanic witnesses
and scalar restricted approximation remain qualified historical evidence.

Evidence/source hashes, full histograms, failed versions and actual semantic
traces are retained in data/joint_service_20261008.json and its indexed archive.
