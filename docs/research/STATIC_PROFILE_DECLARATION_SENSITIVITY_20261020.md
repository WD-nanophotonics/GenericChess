# Static profile sensitivity to an unused duplicate type — 2026-10-20

## Question and decision criterion

Does the per-declared-type median used to normalize rule-only movement prices
change existing values when a ruleset adds an unused piece type with geometry
identical to an existing type? A changed profile would establish representation
sensitivity; only a real same-state search-choice change or downstream consumer
could motivate reconsidering the normalizer. This is a scoped diagnostic, not a
claim that equal movement signatures must have equal value in every rule.

## Fixed profile comparison

The base is canonical Western Chess. The variant appends `N2`, an exact copy of
`N`'s movement atoms and drop mask. No start-position piece, promotion edge or
rule action creates it from the canonical start; externally supplied custom
positions containing `N2` were not tested. The profile is built through the normal
`compile_ruleset_for_execution` and `build_ruleset_profile` path. The duplicate
does not alter any starting legal moves.

The canonical board values `P/N/B/R/Q = 361/775/1000/1462/2439` become
`407/873/1127/1647/2749` (and `N2=873`) after adding that declaration. Hand
values move from `325/698/900/1316/2195` to `366/786/1014/1482/2474`
(`N2=786`). The cross-type ratios remain close after integer rounding, while
the static-material scale rises about 12.7% because the raw median now weights
the duplicated geometry twice. The dynamic evaluator weights do not scale with
that median.

As a diagnostic alternative, take the median over one raw capability per unique
movement signature. It restores the canonical Western values for this exact
duplicate construction. On canonical Shogi, thirteen non-anchor declarations
collapse to nine signatures, but this same calculation leaves its current
integer board values unchanged. Recomputing raw capability values confirms the
Western median is `6.2176222454` in both canonical and unique-signature forms;
the Shogi median is `4.7097917181` in both forms. Shogi's repeated exact
signature group is `G/TP/TL/TN/TS`; all five raw values equal that median, which
explains why deduplication leaves the reference point unchanged there. Neither
observation validates
unique-signature normalization as a global price policy; it would change the
meaning of the scale anchor and could affect other type compositions.
`movement_signature` is
only the analyzer's canonicalized leap/ray atom set; it does not encode
promotion targets, drop eligibility, semantic guards or action frequencies.
Deduplicating that signature would therefore assert that declaration
multiplicity is irrelevant to the reference scale even where declarations
differ in those other rule semantics. This is a candidate invariance choice,
not a consequence of the current geometry-only capability model.

## One existing public search comparison

The canonical starting position has twenty legal actions in both declarations.
With `AlphaBetaPlayer`, TT/order/root tactical scan disabled, q0, and a
4096-node cap, both complete depth three at 2,239 nodes, score 21, and return
the same action and three-ply PV.

The first root from the already-frozen corrected Western profile panel
(`seed301`, the saved deterministic twelve-ply prefix) has no captures or hand
pieces. The two reconstructed complete states and their 34 root actions match.
Under the same cap and switches, both complete depth two and then hit the node
limit at 4,096 nodes. Scores change from 368 to 414, while the selected action
and PV remain equal by actor/from/to/promotion. Compiler geometry IDs differ
between rule fingerprints, so raw dataclass action equality is not a valid
cross-ruleset comparison; the selected move and replayed action agree by
actor/from/to/promotion. This is finite score sensitivity on one even-material
state, not evidence of changed utility or playing strength.

The panel's eight registered twelve-ply roots (seeds 301–308) were reconstructed
in fixed order only to find a suitable existing post-capture state. None had a
captured piece or hand inventory, so the planned post-capture check is
underidentified in this frozen panel. No new root was created or selected.

## Decision

Retain the current per-declared-type normalizer for now. The diagnostic proves a
scale response to a duplicate declaration not reachable from the canonical
start and one score shift, but no action change, utility difference, or
representative post-capture case.
The unique-signature alternative is a falsifiable future candidate if a real
consumer requires equivalence under type aliasing; changing normalization would
also alter fixed dynamic-feature balance. The current movement-capability and
rule-profile cache identities include `evaluator_version`; disk-profile lookup
also checks it, and learned checkpoints record the profile version. Any future
adoption therefore needs a deliberate version/retraining compatibility plan,
not just a formula substitution. No code or default change follows.

Exact compact results and conditions are in
[`data/median_profile_duplicate_type_20261020.json`](data/median_profile_duplicate_type_20261020.json).
