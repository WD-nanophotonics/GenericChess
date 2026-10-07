# Semantic capability input diagnostic

2026-10-08. This is an exposed development check of rule-only valuation inputs,
not a selected price formula or player-strength result.

## Observed interface gap

`build_ruleset_profile` derives generic-v1 static capability from movement atoms.
The execution adapter exposes retained legacy metadata; it does not reconstruct
semantic movement. Canonical Western P has no atoms, raw capability0 and the
clamped board value1. Its executable quiet/capture rules do exist. A longer
semantic capture and a capture-only variant retain exactly those old values.
Nonempty atoms can also differ from replaced/augmented semantic movement.
Correct legality therefore does not establish correct capability inputs.

This concerns the static component, not the whole default evaluator score.
Its promotion-zone construction also reads legacy empty-forward metadata:
canonical semantic P currently gets all64 squares classified as its zone.
The isolated input witness below zeros dynamic terms; it does not validate or
repair that separate dynamic approximation. Input-source repair should precede
piece-specific positional patches.

The existing unfamiliar-search report now states this input scope and lists
semantic moving types without atoms. That list detects a concrete omission;
an empty list does not certify complete semantic valuation. Frozen outputs,
evaluator defaults and earlier comparisons retain their original status.

## A bounded approximation that can see the change

The pilot projects simple actor moves, target removal and optional clear paths
from compiled IR, separating empty and enemy targets. Guards, auxiliary effects,
compound movement, drops, zones and postconditions are explicitly excluded;
own-anchor safety and future promotion/custody are ignored. Under the declared
independent occupancy law, empty probability is1-d and each ownership probability
is d/2. Path-clear unions are computed without double counting endpoints.
Promotion alternatives to the same endpoint are not extra current mobility.

| Predeclared variant | Quiet endpoints | Capture endpoints | Weighted projected mobility |
|---|---:|---:|---:|
| Canonical P |56|98|0.8501171875|
| Longer semantic capture |56|84|0.825234375|
| Capture-only |0|98|0.1741796875|
| Type-ID rename |56|98|0.8501171875|

Weights/densities are the existing generic-v1 configuration, retained as an
explicit development law, not asserted to be uniquely implied by the rules.
Capture-only mobility is zero at density0 and positive when enemies can occur.
Treating the union capture graph as empty-board quiet movement would fail this
basic distinction. Longer range need not increase this context-average measure:
finite-board boundaries reduce the number of its valid endpoints.

Independent Core checks cover both owner orientations,512 quiet contexts and
32256 single-enemy contexts. Another10240 fixed occupancy samples inspect the
density law and rename invariance. These synthetic pseudo contexts have no
anchors; they do not validate full-game legal mobility or material prices.
Reuse of the same samples exposes the omitted double-step, exclusively on rank1:
paired missing means are0.123046875 at density0 and0.03125 at0.5. Guards are thus
a measurable approximation issue, not a reason to keep semantic movement absent.

In these particular all-N-background contexts, the omitted double-step mean is
analytically (1-d)^2/8: one eligible source rank and two empty squares. This
explains the paired sample effect without a new sweep or a universal guard law.
The simple weighted proxy's pawn-normalized ratios are N5.473, B7.146, R10.493,
Q17.638, with Q/R1.681. These are opportunity ratios under this law, not selected
material coefficients. Seeing previously omitted movement is necessary input
repair; it does not establish that this mobility normalization is useful prices.

## Decision

Prioritize a scoped semantic capability input for a rule-only candidate, retaining
empty/enemy availability and explicit unsupported mechanics. Do not silently
replace generic-v1, normalize signed service into positive prices, or select
parameters for human-reference agreement. One next implementation check should
use the existing comparison entry with a semantic-only unfamiliar movement;
its purpose is sensitivity and cost, not universal optimality or Elo.

That first interface witness now runs on a predeclared six-piece recombination:
the otherwise atomless type has semantic rook movement. Its complete compiled
quiet/capture/path geometry matches the canonical rook in both orientations.
Only this type's board lookup is changed from1 to1435, using the projected
opportunity and unchanged legacy median scale; all other table entries, search
and dynamic-term switches stay fixed. This is a scoped input intervention,
not a new selected pricing formula. Both owners use the same corrected lookup.

Eight cold public calls atdepth1/2 agree with independent plain Core material
minimax and repeat exactly. Atdepth1 both controls choose the same capture.
Atdepth2 the baseline retains that zero-valued capture, whereas the input
candidate avoids it: the capture's own Core two-ply value changes from0 to-660.
The opponent can also capture a different knight, so the baseline observation
is a tie, not a certified strategic blunder. Both chosen root values remain0.
This demonstrates input sensitivity only, not improved playing strength, an
independent material reference or permission to adopt the candidate by outcome.

[Pell's original Metagamer paper](https://cdn.aaai.org/AAAI/1994/AAAI94-212.pdf)
constructs game-specific evaluation from rules and static analyses, separating
material mobility/reachability features from dynamic advisors. Its reported
static promotion advisor was not implemented. This is precedent for an explicit
approximation, not evidence for our formula or modern playing strength.
[Clune's general-game heuristic paper](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf)
uses payoff, control, termination and feature stability; its sampling assumptions
do not identify universal material prices. Our projected density law is a local
construction, not a result of either paper.

Compact observations: data/semantic_capability_20261008.json. Exact producers,
failed initial rename comparison and complete records:
../archive/semantic_geometry_probe_20261008/. Archived code is on-demand evidence.

## Optional executable candidate and observed costs

`generic_chess.ai.evaluation.semantic.build_semantic_opportunity_profile`
now returns an explicit candidate profile and its scope report. It reads both
owner geometries, conditions empty/enemy targets separately and deduplicates
endpoints/promotion alternatives. Clear and exact occupied-count paths with
`owner_filter=any` are supported; joint overlapping-path events use their
shared cells, not independent-path multiplication. Foreign legacy atom bindings
are ignored just as Core does. Guards, zones, auxiliary/compound effects,
postconditions and other path predicates remain explicitly excluded. Anchor
safety and future promotion/custody utility are outside this static projection.
The callable profile currently requires square-board legacy evaluation metadata;
that restriction is not a statement about rectangular rule legality.

The candidate normalizes projected opportunity by the non-anchor median.
Its hand scaling, promotion-value differences and drop diagnostics reuse legacy
conventions, not validated transfer utility. It does not enter the default cache
or replace generic-v1. Use it explicitly with the existing `Evaluator` and
`AlphaBetaPlayer(evaluator_override=...)`. The existing `run_rule` comparison
callable accepts `semantic_candidate=True` and an explicit `evaluation_config`;
no new CLI or workflow interface is required. Dynamic terms remain separate
legacy approximations; all controlled candidate experiments here set them to0.

Generated legacy rules use the existing `compile_semantic_ir` analysis lowering;
their product executor remains `CompiledRuleSet`. Empty semantic DSL still fails
its original validation. No fake action, new adapter or executor switch is needed.
Four predeclared board4/6, seed7/21 generated rules complete32 cold depth2 calls
with repeat/Core parity. Nonoverlapping mobility curves match independent
analytic formulas; separate legacy Core occupancy samples test hybrid unions.
The generator's current filters ensure structural mobility/safe anchors/opening
moves, not useful price discrimination: board4 seed7 admits an immediate mate.
That root remains in the results as a tactical control, never silently replaced.

Forty real lexical-history roots give120 complete fresh/reused/repeated calls
with Core scores equal. Those routes contain no hands or promoted entities.
Separate declared promotion and C-drop-enabled fixtures cover12 roots/36 complete
public calls, actual promotion, captured base types and two drops. Eleven Core
references complete; one remains unknown, including a separate10-second/8192-leaf
development follow-up. Fresh/reused agreement does not certify that unknown cell.
The original cannon mixture forbids drops; preliminary short routes and a
premature checkpoint claim are retained with corrections, not counted as drops.

Two real Shogi capture transitions expose a useful distinction: G and promotedP
have equal current opportunity/board value1000, but captured hands reset to
G900 versus P156. Existing static lookup already sees gains1900 versus1156
under hand_weight0.9. This verifies execution/accounting, not those hand prices
or a theoretically justified capture-reset liability in the board table.

The initial v0 omitted cannon screens. V1 supports exact occupied-count paths:
independent Core one/two-screen checks and10240 density samples agree with the
projected action set in the declared cannon contexts. Exhaustive small overlapping
path tests independently check the probability calculation. This is current
pseudo-opportunity scope, not full-game legality or material-value validation.

Four initial rules produced32 complete depth2 calls with repeat/Core parity.
Their zero-valued starting roots mostly establish integration, not discrimination.
The original record incorrectly said ordering stayed legacy: public ordering
actually calls the active evaluator's capture/type values. Raw records are
retained with a correction. A crossed scoring/ordering32-call control isolates
that distinction; neither the fixed promotion root nor capped recombination
establishes a universal candidate speed gain.

A new cannon/rook mixture has identical legacy rays but different executable
capture conditions. The old table gives both1000; v1 gives C976/R1024. Two
predeclared capture/recapture continuations have Core static values0/0 before,
and+48/-48 afterward. Eight cold comparisons match Core; aliasing the cannon
type preserves numerical results. Hand weight0 isolates board-table effects,
without altering actual capture/drop rules. These are table-induced decisions,
not an independent true-value oracle, winning proof or player improvement.

An observed engineering cost was removed: `Evaluator` now skips dynamic feature
calculations whose weight is0. On264 deterministic history states, old/new scores
match under two profiles and default/static configurations;158400 paired leaf
evaluations were timed. Static-only leaves became much cheaper, while default
timings remain comparable. Thirty-two matched end-to-end calls show about15–35%
median time reduction on equal-node non-time-capped pairs in these two fixtures.
One before-control hits the time fuse while its after-control reaches the node
ceiling at the same completed depth; that pair is a resource/result observation,
not an equal-work speed certificate. This does not change weights, defaults,
search algorithms or scores and is not a universal acceleration claim.

## Remaining approximation boundary

The observed double-step source guard admits eight sources per owner;64 blocker
checks and16 actual auxiliary-token transitions agree with Core. Under this
particular independent occupancy law, its omitted opportunity is `(1-d)^2/8`,
weighted0.0785546875. Adding that term would move the N/P opportunity ratio from
5.473 to5.010; it is not a selected correction or a full guard implementation.

A separate finite single-actor task checks why future promotion cannot be
identified by current mobility alone. It retains actual supported movement and
all promotion choices but removes castling/double-step/en-passant. There are no
anchors/opponent/capture rewards or game adjudication. An explicit virtual
opponent pass returns the actor's turn; that pass is not claimed legal in Chess.
Uniform target choice then uniform promotion choice is a declared behavior law.
The reward is quiet endpoints, not WDL or material utility. Both Core and Native
verify all20 type/population/mode rows and every declared horizon1/4/8/16.

For uniform all-source P, mean opportunity per turn atH1/4/8/16 is
0.875/2.963/5.934/8.655 with promotion, versus0.875/0.688/0.438/0.219 without.
At owner-relative rank1 the promotion sequence is1/1/3.788/8.391 instead.
The no-promotion values also match a direct remaining-distance sum. This exposes
phase and duration dependence; it does not justify choosing a horizon to fit
human prices, assigning virtual-pass utility to real play or a universal point
vector. The scientific price question remains OPEN.

Current compact evidence: data/semantic_candidate_20261008.json. Exact sources,
version snapshots, immutable raw records and corrections are isolated in
../archive/semantic_candidate_20261008/. They are evidence, not active imports.
