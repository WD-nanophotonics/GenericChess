# ADR-121: Static semantic material prior V2

- Status: candidate definition frozen before V2 human-agreement calculations
- Scope: isolated zero-game Western Chess development and Standard Shogi retention audit
- Production evaluator: unchanged

## Question and observation

The single question is whether one label-invariant rule-derived material prior
can recover the frozen Western Chess material ratios while retaining the
frozen Standard Shogi ordering. The smallest direct observation is a static
calculation on those two compiled RuleSets. Search, games, Arena, Heavy,
self-play, mutation, and additional games are unnecessary for this question.

## Frozen candidate hypothesis: local executable-option measure

This is a falsifiable rule-affordance proxy, not an expectation over legal
whole-game positions and not a claim that one move option has proven
game-theoretic utility. For a piece type `t`, the intrinsic board score is

`B(t) = (1 / (2*|S|)) * sum(owner in {0,1}, source in S, a in U(t,owner,source)) Pr(a executable)`

where `S` is the set of board squares and `U` is the set of distinct semantic
successor action/effect outcomes. A distinct outcome contributes one unit.
This unit choice is the hypothesis that, absent positional or human priors,
each additional executable choice contributes equal first-order option
capacity. The benchmark can falsify its relevance by disagreement with frozen
human values; it is not an established law of chess.

For the local occupancy calculation, every non-source square has one of three
labels `{empty, own piece, opposing piece}`, independently and uniformly.
The three-state uniform measure is maximum entropy over those *local labels
only*. It can generate globally illegal or unreachable boards; therefore
`B(t)` is called a local semantic option measure, never a legal-position
expectation. Both owners and every geometric source square are weighted
equally. A source square forbidden by an executable source restriction
contributes no action; the uniform source measure is a deliberate structural
average, not a claim about how often a piece occupies that square in play.

For each distinct semantic outcome, its contribution is the exact probability
of its occupancy predicates under this finite local measure. Path and screen
constraints are evaluated jointly over the involved square labels, so
overlapping predicates are not treated as independent events. Empty and
opposing endpoints are mutually exclusive states; when both are legal, their
probabilities are summed for the corresponding successor outcomes rather than
counting the same action description twice. Board boundaries, directional
asymmetry, restricted destinations, and occupancy-based blockers/screens
come from executable geometry and predicates. Reachability and coverage are
reported diagnostically but are not added again because they describe the
same option set. No density grid, fitted weight, median, or human-value
normalization enters `B(t)`.

Quiet and capture outcomes are ledgered separately and contribute to `B(t)`
only when their executable effect yields a distinct successor. Duplicate
semantic descriptions of the same outcome are counted once. If any movement,
occupancy predicate, or effect used by either benchmark ruleset cannot be
represented and evaluated exactly by the candidate, it is listed as
unsupported; it is never silently assigned zero. Any such relevant omission
makes the benchmark `INCONCLUSIVE`.

## Conditional rules and options

Rules guarded by board occupancy are evaluated under the same square-state
prior when their predicates are exactly representable. Rules requiring
history or auxiliary state (including en-passant-like one-ply rights) are
retained in the ledger with their guards, effects, and state dependencies.
They are separated into two ledger classes. A history/auxiliary-state
conditional action is explicitly outside this *state-free intrinsic* measure
when the rules provide no stationary distribution over that state; the ledger
records its guard, effect, source type, and why no state-free probability is
assigned. Such an action is not silently treated as zero, and this principled
boundary alone does not force `INCONCLUSIVE`. By contrast, an action whose
geometry or occupancy/transition semantics are claimed to be part of the
state-free measure but cannot be parsed or evaluated exactly is unsupported;
any such omission makes the benchmark `INCONCLUSIVE`. No low-frequency
judgment or game-/piece-specific exception is permitted.

Global legality invariants such as own-anchor safety are recorded separately
as state-dependent semantics. They depend on the joint board, attacker
identities, and anchor state, none of which is specified by the local
three-label measure. Their geometric movement rows may appear as explicitly
partial diagnostics, but any unmodeled invariant keeps the whole benchmark
`INCONCLUSIVE`; it cannot be reclassified as irrelevant to claim complete
coverage. Simple source-location guards exactly resolvable from owner/source
and an executable fixed zone (such as a start-rank move) are evaluated
exactly. Associated history-token effects are separately ledgered and do not
create an extra material option. A board-state guard requiring type-specific
inventory or an unmodeled global postcondition is unsupported and likewise
keeps the benchmark `INCONCLUSIVE`.

Promotion and other explicit type transitions are separated into immediate
action options and future capability. Each legal optional promotion branch
that produces a distinct immediate action/effect outcome is counted in `U`
and therefore in `B(t)`; a forced replacement is one outcome, not an
additional choice. The ledger separately records each reachable
source-to-destination type transition, its exact immediate executability
probability when representable, whether it is optional or forced, and
`B(destination)-B(source)`. That future-state delta is diagnostic only, not an
additive term in the frozen single-piece score: the rules alone do not
establish a universal time horizon or discount making future capability
commensurate with current options. A forced transition's signed delta is
retained and never clipped to a positive bonus.

Drop/re-entry is a separate held-token state, not a game-specific bonus to a
board piece's score. Its raw hand measure `H(t)` is the expected number of
distinct legal drop successor outcomes for one held token under the same
local occupancy measure, including executable drop restrictions. Board
scores are `B(t)`; hand scores are `H(t)` where hand references exist. They
are not added together. Capture dispositions and the base type to which a
captured/promoted piece returns are recorded as transition semantics, but
do not alter `B(t)` or `H(t)` absent a distribution over inventory states.
Types without an executable drop path have hand component explicitly zero.

The only additive coefficient inside either raw quantity is one per distinct
option, as part of the equal-first-order-option hypothesis. No coefficient
combines board, promotion, and hand states. The candidate's raw values remain
unscaled until the single global validation scale is computed solely for
comparison. Anchor handling is a benchmark convention only and does not
change the candidate formula for ordinary piece types.

## Validation boundary

Only after this definition is frozen may the audit read the frozen Western
bands/conventional vector and Standard Shogi reference. Human values are
validation targets only. Report per-component ledger rows, raw values,
single-global-scale correlations/order metrics, Western pawn-normalized
ratios, and Shogi piece-level normalized residuals. A failed gate is reported
as a scientific failure; no coefficients or per-piece values may be changed
in response to the observed target metrics.
