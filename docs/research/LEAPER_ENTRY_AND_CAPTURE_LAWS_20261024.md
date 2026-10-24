# Legal entry, capture remnants and conditional mate laws — 2026-10-24

The structural-first Main produces three distinct coordinates: static mate
capacity, legal entry from an admitted fresh state, and forced outcome with its
actual history/clock. They differ even in four-actor plain-Leaper games. Adding
moves can change an existing action's continuation value while both immediate
children remain ongoing. The public packet retains a failed history prediction,
negative controls and unresolved outcomes instead of converting them to draws.

## Scope, sources and reproducibility

K is the eight-neighbour royal King. Movement masks use Wazir=1, Ferz=2,
Dabbaba=4, Knight=8, Alfil=16, all complete symmetric leap orbits. There is one
White K and A, one Black K and B unless the explicit capture remnant removes B.
Rules remove captures, disable drops/promotion/pass/effects, draw stalemate and
use H6/repetition-limit2 unless H1/H2 is explicitly stated. Both initial Kings
must be safe; complete RuleSets, records, selected initializers, clocks, legal
frontiers and returns are retained. These exclusions define a scoped experiment,
not GenericChess's full generated domain.

This follows [Chat's named continuation/history advice](https://nanomelon.slack.com/archives/C0C6L21UU20/p1792813645559729)
read and privately preserved this patrol, and the preceding
[PRIMARY structural packet](https://github.com/WD-nanophotonics/GenericChess/blob/1e959cefb792f3067fc0b3aab8b402a63a7d9b1f/docs/research/LEAPER_STRUCTURAL_COUNTERFACTUAL_20261024.md).
The earlier AUX WDL labels remain attributed to
[e71968ff](https://github.com/WD-nanophotonics/GenericChess/blob/e71968ff8ec5e3ab57cade9b965e44a23558780a/docs/research/LEAPER_H6_MATCHED_RULE_TRUTH_20261024.md);
no competing whole-game solver, AUX execution, Player, training or default
activation was used here.

[Data and reader guide](data/leaper_delayed_capture_20261024/README.md),
[manifest](data/leaper_delayed_capture_20261024/manifest.json) and
[summary](data/leaper_delayed_capture_20261024/summary.json) provide the fixed
inputs and full evidence. Reproduce semantic qualification with:

```
python -m scripts.verify_leaper_delayed_capture --directory docs/research/data/leaper_delayed_capture_20261024 --output NEW_IGNORED_OUTPUT.json
```

The reader checks complete rule grammar/inventory, fingerprints, actual prefixes,
all retained states/returns/frontiers, exact reuse and independently specified
finite combinatorics. It hashes source capsules as data and never executes them.
It binds 106 delayed-record occurrences/98 unique, 20 history occurrences/18
unique and 4,199 other occurrences/3,920 unique within those reader groups,
plus 492 static frontiers and 160 inverse predecessor positions. This is same-Core
semantic validation, not an independent WDL engine or finite proof of all n.

## Shared ongoing action, then capture-dependent revaluation

Use physical White K a1/A c1, Black K b3/B a3, Black to move, A6 versus A22,
B27. Black-first is represented by global ownership exchange in fresh compiled
rules because Core's initial mover is seat0. This diagnostic is outside the
original 128 White-first distribution.

Shared Black K b3-c2 is legal in both rules. Both children are ongoing, with the
same physical board, roster, White mover and five plies remaining. In A6 White's
only A moves c1-b2/c3 permit the retained Black B mating responses. In A22 White
can instead play c1xa3, removing the only Black attacker. Under these exact
policies a bare Black King cannot mate, and a lone A22 plus its King cannot
mate a bare King: parity leaves two orthogonal escapes which its King cannot
both cover. Other endings draw. Thus the shared action changes White LOSS to
DRAW (Black WIN to DRAW), despite ongoing-to-ongoing immediate status. This is
an all-choice finite certificate plus the scoped remnant argument, not a root
Black WDL claim or a claim based on one principal variation.

For the separate fresh White-to-move K a1/A c1 versus K c2/B a3, H1 makes both
rules DRAW; H2 gives A6 LOSS versus A22 DRAW. Literal legal responses and terminal
precedence are retained. Changing only stalemate draw to loss on the fixed named
path yields 12 compared ongoing nodes and no observed payoff change. Root WDL
under that scoring change remains UNKNOWN; no positive case was hunted after
this negative diagnostic.

## Failed history prediction retained

A complete rule with default A c1 and a named alternate A b2 reaches the same
physical position at ply4 by two legal prefixes. The default prefix returns to
its root for the second occurrence and draws; the alternate prefix remains
ongoing. The prediction that the latter is LOSS was refuted: White A c1-c3 at
ply5 repeats the alternate prefix's real ply1 child and draws before the proposed
mate. Both certified values are DRAW. Different terminal status and legal-history
continuation do not alone establish different WDL. The original failed loss
qualifier remains present, and a regression test requires that claim to fail.

## Conditional static capacity law

For any square n>=3 in this scope, with the previous mover's King safe, a mating
position with A6 or A22 can exist only with the checked King in a corner. A's
attacks preserve checkerboard colour. Each orthogonal neighbour of the checked
King is unattacked by A; the nonadjacent attacking King covers at most one, and
B occupies at most one. An edge or interior target has too many such escapes.

Orient Black K at (0,0), B at (0,1), White K at (2,0) or (2,1). Checking A6 may
stand at (1,1),(2,0),(0,2), excluding the Royal collision: five templates. A22
adds (2,2): seven. The diagonal Royal escape is already covered by White K.
B attacks White K by Knight in the first placement or Dabbaba in the second;
B captures the checker by Wazir at (1,1)/(0,2), or Knight at (2,0)/(2,2).
A noncapturing leap cannot interpose. Classifying those templates gives, for
B's Boolean W,D,N bits:

- C6: at most one of W,D,N is present.
- C22: not N, or neither W nor D.

Ferz/Alfil bits of B are irrelevant to this particular property. Of B masks1..31,
15 permit A6 capacity and 19 permit A22; the added masks are 5,7,21,23. B27
permits neither. All coordinates fit on n>=3 and D4 covers the other corners.
Finite checks comprise the n5 joint-cage census, missing n3/n4 boundary cases,
173 new corner-law static frontiers and seven exact reused B27 frontiers. The
all-n claim rests on the geometric argument, not those checks alone.

The Boolean value functions have third finite differences2 and1, but both are
linearly threshold-classifiable. This is no linear-classifier impossibility,
NNUE/learning requirement or playing-strength gate.

## Static capacity does not imply legal entry

On n3 each added-capacity B5/7/21/23 has eight A22 mating cages under D4.
All 32 cages' possible last White K/A moves were inverted: 416 sources are
outside, 64 occupied and 160 already check the enemy King before White's turn.
No legal predecessor remains. Fresh compilation also rejects attacked initial
Kings. With no drops, promotions, extra actors or recapture-to-hand, no earlier
history can enter a four-actor mating cage through another mechanism. Capturing
B leaves the no-mate single-A remnant. Hence no White mate is reachable from
admitted fresh n3 histories in these A22 rules, despite positive static capacity.
This does not distinguish LOSS from DRAW.

On n4, K c1/A d4 versus K a1/B a2 admits shared A d4-c3 for all four B masks:
A6 remains ongoing, A22 mates. A n5 B5 witness K c1/A e3 versus K a1/B a2,
A e3-c3, gives the same ongoing-to-mate change. The first draft's old-stalemate
prediction was corrected before queries because the surviving B has legal moves;
the original and causal correction remain in the packet.

For A6/A22 with B5, uniform common-safe physical initializers give:

| Board n | Common initializer count | A22 immediate-mate roots | Fraction |
| --- | ---: | ---: | --- |
| 3 | 360 | 0 | 0/360 |
| 4 | 12,500 | 24 | 24/12500 |
| 5 | 130,316 | 64 | 64/130316 |

For ordered nonadjacent Royal squares u,v, let U be the remaining allowed A
squares excluding A22 attacks on v and V the allowed B squares excluding B5
attacks on u. The denominator sums |U||V|-|U intersect V|. Independent permutation
counts agree for n3/n4. Inverse corner entry gives 0/24/64 roots; all 88 positive
full-rule records were replayed. On n4 all 24 mating actions are shared; n5 has
40 shared and 24 new Alfil actions. For n>=5 the finite local templates fit and
the numerator stays64, while mu_n=n^8+O(n^6): immediate incidence is Theta(n^-8).
This is not total WIN rate or overall difficulty. Initially these are a family
of complete rules with varied fresh boards, not one hidden fixed RuleSet.

## Odd movement, explicit fixed rules and a partial strategic region

Adding Wazir to A22 produces A23 and breaks the even-offset corner lemma.
Literal n3 K c2/A c3 versus K a2/B a1, A c3-b2, stays ongoing under A22 and
mates the noncorner a2 King under A23. Removing B changes old A22 to stalemate
DRAW, while A23 still mates. Roster survival changes absorption independently
of the newly admitted movement.

There are 360 old A22/B5 safe fresh placements but only 152 also safe for A23;
208 old-only placements are excluded, never assigned invalid A23 labels.
Across all 152 common roots, A23 has 112 immediate-WIN roots and 40 negatives.
Its 192 mating actions split into 80 shared actions revaluing old terminals
(72 ongoing, eight stalemate), 16 new actions entering an already mating old
static position, and 96 new actions whose old static post is checked but has
legal defenses. An illegal old action receives an old static Position, never
an invented old GameRecord. There are 1,382 new child applications and two exact
retained return reuses.

These physical results were then bound to TWO fixed complete RuleSets using
one default plus 151 distinct named setups, uniformly selected by the explicit
152-key mu. The default is counted once. The first construction failed duplicate
initial-position admission before child queries; the source contract was checked,
all inputs saved before compilation, and the original absolute phase deadline
preserved. Full fixed-rule replay binds 304 root frames, 1,384 oneply children,
and four actual four-ply repetition cycles. Fingerprints and default/named record
schemas differ; no old record is transplanted. This finite correspondence does
not claim Player/TT/evaluator timing equivalence or all-history engine equivalence.

D4 gives 19 orbits, each size8, with 14 immediate-WIN orbits and five negative.
Data-only audits check 2,432 root transforms, 11,072 child transforms and 1,536
mating-action channel transforms. These are deterministic symmetries, not 152 or
19 IID trials; named setup keys and Player behaviour are not assumed equivariant.

The next step was actually begun: for every White choice at each of the 40
negative roots, seek a legal Black capture removing the only White A, or a
nonwinning terminal. 184 strict capture responses close 24 roots (three orbits)
as NOT-WIN. Sixteen roots (two orbits) remain UNKNOWN with 24 unresolved White
actions. Thus the true WIN count is bounded by **112..128 of152**, or
**14/19..16/19**. NOT-WIN is not imputed DRAW. The two actual representative
frontiers and full named records are prepared in next-two-orbits.json.gz.
Two later hand-derived finite strategies were registered but voluntarily closed
unexecuted before their deadline: their predicted extra labels are unverified,
not part of this bound, and this phase must not be silently restarted/refilled.

## Validation, cost, corrections and next choice

Fourteen focused tests guard actual observed defects: duplicate-record cache
prefix skipping, extra live attacking inventory, omitted inverse atoms, omitted
mating actions, illegal-action record substitution, wrong rule effects/defender,
foreign fingerprints/default double weight, transformed terminal corruption,
and missing White choices or mixed capture prefixes. Contract diagnosis fixed
readers/guards; scientific expectations were not changed to fit observed output.

Manifest hashes bind 53 evidence files. Source capsules preserve executed bytes
when captured and are data only. The first delayed producer source was not
captured before its first extension: provenance.json discloses that gap, and
current maintained code is not claimed to be that original executed version.
An old radius producer start field was corrected to the actual registration
start in its publication copy; private original retained. The named qualification
label was corrected from misleading '152 named' to 151 names plus one default;
underlying rule bytes and measurements were unchanged.

Recorded effective research is 4,093.91718 seconds (68.232 minutes), after a
conservative exclusion of mixed transport/administrative windows. Scheduling,
publication, documentation and offline gaps are not credited. Producer seconds
exclude some import/final-serialization overhead; actual end-to-end work includes
engineering and analysis, so no equal-cost or runtime-strength claim follows.
All measurement phases are closed, including failed/unexecuted proposals. Source
capsules are not execution receipts, and tests do not force honest self-reporting.

Next choose a genuinely decision-changing structural question, not a wholegraph
or cost/price panel. Ask Chat to audit the corner/no-entry argument and whether
closing two remaining finite-strategy orbits would improve the interpretation
enough to justify a separately assessed task. Until then, examine common-support
admission before another rule contrast; inverse/learning remains conditional.
