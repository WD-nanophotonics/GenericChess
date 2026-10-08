# Semantic capability input diagnostic

2026-10-08. This is an exposed development check of rule-only valuation inputs,
not a selected price formula or player-strength result.

## Finite generator consistency,2026-10-08

The direction review prioritizes supported semantic equivalence, behavioral
stability and finite-board saturation before more search or dynamic features.
tests/product/test_semantic_ray_equivalence.py checks one5x5 orthogonal-ray
family at L1..5: capped rays versus one exact-distance ray per endpoint, retaining
all intermediate path_clear cells. These are not leaps. Every owner/source
endpoint/path set agrees;1250 actual Core single-blocker positions additionally
match an independent straight-line/first-blocker census for attacks and actions.
Compiled all-false drop masks still emit excluded drop patterns; the result is
explicitly about the supported board projection, not full legal/material value.

At density0/.125/.5/.875/1 with equal weights, raw rises
2.4,3.4875,4.1,4.3756640625,4.3756640625. Same-L encodings agree; quiet/capture
curves never decrease and L4/L5 agree exactly. Predeclared floating tolerance is
1e-12 absolute. Fixed N raw=.72 gives a separate fixed-reference scale; the
production median normalization/rounding is also retained. Unchanged N's
integer value falls as C grows because the median scale changes, not because
N's capability changes. No generator correction was indicated by this family.

For these nested endpoints, extending L leaves old path events unchanged.
An added endpoint contributes P(clear)*(1-d+d/2), between0 and1. Thus raw
increment lies between0 and the mean number of added endpoints under this
unit-sum nonnegative density law. Observed increments1.0875/.6125/.275664/0
respect bounds2.4/1.6/.8/0. This is a scoped proxy stability bound, not universal
material/win-rate monotonicity, actor-splitting conservation or arbitrary-rule
continuity. Passing this family does not start a universal proof campaign.

For the existing cannon/rook mixture under unchanged default density law,
weighted quiet opportunity is identical8.0643227148; capture is0.4377235079
versus0.8555921483. Raw8.5020462227 versus8.9199148631 becomes976 versus1024.
The common quiet baseline dilutes the differing capture mechanism. This
explains weak proxy separation, not material-price validity. For an endpoint
with k intermediate squares, cannon/rook capture-event probability ratio is
k*d/(1-d) for0<d<1; whether the screen mechanism helps depends on context.
Do not select a new density law or weight against human references or exposed
search choices. Next construction needs one explicit decision-changing context
or response assumption, with a counterexample and retained finite scope.

Exact rows and source recovery:
data/semantic_attack_authority_20261008.json;
../archive/semantic_attack_authority_20261008/README.md.

An actual source-capture witness makes the missing context assumption concrete.
Fix actor(0,3), enemy R(3,3), two intervening friendly-screen cells and anchors.
Each screen has marginal occupancy.5 under all three laws. Equal00/11 gives
C/R legal-capture probabilities0/.5; equal01/10 gives1/0; independent four
states gives.5/.25. Eight Core source-specific checks pass; Native full attack
maps separately agree but are not source attribution (screens can attack too).
Next let the opponent make one uniformly sampled legal action within each of
the same eight cells.126 exact reply transitions, tracking the enemy R's actual
new square and retaining captured-source outcomes as zero, give correlated
C/R.03333/.26471 versus anti-correlated.48333/.06458; independent.25833/.16464.
Initial cells retain equal weights despite different legal-action counts.
The reversal survives this declared response, but no context/behavior law is
uniquely implied by rules or selected for deployment. This is a changed-premise
screen mechanism witness, not a material-price or WDL result. The addendum's
five members were extracted/rehashed and two producer pins verified; original
packages/failed records stay unchanged. See the same archive's
screen-context-index.json and compact data screen_context_counterexample.

A cheap next approximation has a concrete declared law. Before compile-safety
acceptance, the existing six-piece inner6x6 placement procedure
(immediate wins are labeled and retained, not filtered in this cohort),
conditioned on two distinct actor/target locations, leaves four occupants among
34 cells. For two distinct inner screen cells, p=2/17 and P(both)=2/187.
Hypergeometric P(clear)=145/187 and P(exactly one)=40/187, versus independent
225/289 and60/289. These follow directly from30*29/(34*33) and
2*4*30/(34*33), without enumerating all46376 placements or fitting prices.
They describe the pre-acceptance context law, not the accepted cohort's distribution
or a response law. A check after filtering/actual replies can decide whether
this low-cost joint correction earns its cost. For the earlier fixed-marginal
.5 witness, writing P(11)=P(00)=t gives fixed-target C-R=1-3t; after the declared
uniform reply C-R=67/160-(5305/4080)t, crossing at3417/10610 rather than1/3.
The response law therefore matters even when one joint scalar suffices for
this finite family. No deployment context parameter is selected by this algebra.

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

## Capture reset and hand-use boundary

The decomposition `V_i=A_i-beta*A_base(i)`, `H_base=beta*A_base` makes
`V_i+H_base=A_i`. It erases base identity from a local capture coefficient
when current geometry agrees. Beta is a free assumption, not identified by
rules. A real four-entity Shogi conditional continuation exposes the omission:
own K(7,6), enemy K(8,8), own N(3,2), enemy G or baseP/currentTP(4,4).
After unpromoted N capture, the enemy has one legal reply K(7,8). Captured G
permits one winning gold drop; reset P has no same-horizon win. Complete
terminal-only Core2ply differs mate versus0;0 is finite no-mate, not game draw.
Replacing N with R(4,1) is a negative control: both have rook mates. Native
verifies362 frontier transitions;24 cold public calls repeat. Static profile
comparisons vary scoring and ordering together and do not establish prices.

A position-only census retains full Shogi legality, opposite-corner kings,
rank1 fillers and one/two hand pieces. All160 owner/filler/type/count cells
agree with Native. Nine files filled with own unpromoted P give hand P zero
drops; TP fillers instead give62. Hand G has70 in both. Multiplicity1/2 gives
the same immediate action set, not equal stock utility. An actual four-ply
capture/reply/mandatory-promotion/reply line opens a captured P from zero to
seven drops: conditional delay, not standard-opening reachability, minimum
release time or an optimal policy.

Let each file in this declared rank1 context have own current P probability
`a`, own TP probability `b`, otherwise empty. Then
`E[L_P]=71*(1-a)-9*b`, `E[L_G]=79-9*(a+b)`.
Linearity needs those marginals, not independent files. An exhaustive512-mask
Core/Native census at fixed nine-file occupancy checks the P/TP composition
formula. Equal P marginals1/2 give mean31 drops under three different laws:

| Explicit context law | Probability P is immediately usable | Mean drops when usable |
|---|---:|---:|
| Independent file types |511/512|15872/511|
| All files share one type |1/2|62|
| Uniform four/five P files |1|31|

Mean opportunity, release probability and conditional opportunity are separate
inputs. Sampling only usable hands hides blocked contexts; equal density/type
marginals do not identify immediate release probability. A possible development
proxy, not a selected material formula, is
`H_b(C)=E_C[discount^T * 1(T<=h) * U_b(drop_context)]`, with declared
context/behavior law, first available own-turn T, horizon h and deployment
potential U. Blocked observations remain in the expectation. Availability does
not specify U, enemy responses, later recapture or shared deployment tempo.
The observed line supplies one conditional T, not a population model. Next
work should test one assumption against an independent deployment observation
rather than fit human prices or normalize old signed tag rewards.

That proxy has a small executable diagnostic: uniform legal drop followed by
uniform **real** enemy reply, then distinct legal target endpoints of the deployed
piece on its next actual turn. Four actual-history roots and344 Core/Native
reply frontiers complete. Conditional mean endpoints are G763/156, resetP34/35,
blockedP0 and releasedP5/7. The initial action-count version gave P6/5 and1
because it counted promotion alternatives separately; both versions remain.
The winning G drop has no later endpoints, so activity alone cannot replace
terminal utility. This does **not** reject an approximate static table used with
normal terminal-aware search. Nor are these few conditional averages a chosen
population law or deployable hand-price estimate.

A next approximation family should distinguish hand use from capture hazard:
given an explicitly modeled H, write `V_i=A_i-p_i*H_base(i)`. Its local capture
coefficient is `A_i+(1-p_i)*H_base(i)`, rather than cancellation forced by p=1.
Capture probability/hazard p, deployment scale/discount and context law are
different assumptions. Neither p nor H is identified by this algebra; positivity
must be checked under the same units/context, not repaired by fitting or silent
clamping. This remains a falsifiable development direction, not installed code.

At the same captured-hand blocked root, all109 real enemy-reply frontiers also
expose behavior dependence. Uniform own actions give next-turn release1/14;
uniform promotion-if-available actions give1/3 because two Knight promotions
do not open the Pawn file. The selected Pawn promotion does open it. After
two declared non-release continuations (King move or Knight promotion, each
with a canonical enemy reply),90 further Core/Native frontiers give1/15 under
the next uniform cycle. A stationary geometric waiting law is therefore an
extra approximation, not inferred from that initial1/14. These are conditional
one-cycle results, not the full two-cycle population or eventual release time.

A separate predeclared30sec/20000-frontier Core batch then completes7864
second-cycle frontiers and all probability mass. Under uniform actual policies,
first availability within two cycles is exactly27/196, coinciding with
`1-(13/14)^2`. Thus conditional nonstationarity alone is no reason to reject
this approximation at a measured horizon. This expanded population has Core
full histories, not a claim of complete independent Native replay. Another
actual route takes N(4,4)->N(3,6)->TN(4,8), blocking P(4,7)'s promotion target.
All55 Core/Native enemy-reply frontiers show no release in its next cycle.
That conditional obstruction limits extrapolation; it does not estimate the
whole third-cycle population or invalidate the two-cycle coincidence.

Four frozen generated-rule roots were selected by legal capture structure before
scoring. Fixed baseline ordering, hand0 and equal search conditions yield32
complete repeatable depth2/3 calls,14/16 complete Core references; two6x6seed7
depth3 references stay unknown. All eight paired chosen actions agree. Complete
action spectra on the two4x4 roots also preserve optimum sets: four ties with
next gaps488/500, and one optimum with gaps781/813. This is negative ranking
discrimination evidence, not improved strength or universal interchangeability.

Exact declarations, failed API calls/predictions and corrected sources:
data/lifecycle_20261008.json and ../archive/lifecycle_20261008/.

## Paired capture risk and actual hand use

One explicit five-entity Shogi pressure context replaces the earlier chosen
reply/renewal assumption with actual N capture, all21 enemy replies, all legal
recipient drops and all later enemy replies. Both resetG and resetP populations
complete:42 first replies and56148 later reply frontiers, with independent
Core/Native full-history transition, terminal and action-set checks. Uniform
conditional action policies give H_G4.11206035 and H_P0.82011255 distinct deployed
endpoints at its next actual turn. No-drop/terminal branches contribute activity0;
terminal outcomes remain separate. Completion took75.853sec including repeated
serialization of the growing record, an engineering cost to avoid next time.

Current G/TP endpoint activity A=6 uses an explicit position-only own-turn probe,
while actual initial-opponent uniform actions give capture probability p=1/5.
The illustrative family V_i=A_i-p*delta*H_base(i) is positive for the declared
delta1/2,3/4,1. At3/4, V_G5.38319<V_TP5.87698, whereas transfer coefficients
V_i+delta*H_base(i) give8.46724>6.49207. Shared endpoint units do not remove
different contexts/timing or identify utility/discount. This qualifies a
conditional approximation, not a selected generic table or a new default.

The same complete census changes under policy: maximizing recipient endpoints
with uniform enemies gives G5.13346/P0.89251. Allowing worst first/last enemy
responses reduces both finite activity values to0, also with terminal-first
lexicographic comparison. That is not material worthlessness: an independently
replayed seven-root actual history leaves a deployed Gold alive but unable to
move while its King is checked; after an actual evasion/enemy reply it again
has five legal endpoints. Endpoint activity omits defensive and delayed service.

The earlier66-source renewal check also finds E[pH] unequal to E[p]E[H]
(Gold0.053394 versus0.061958). It is not the complete pre-capture joint process.
In the single initial context of the actual census, p times the conditional
postcapture mean is simply a conditional-expectation identity; it does not test
factorization across contexts or capture times. The next useful construction
check is a predeclared multi-context, fixed-policy/fixed-total-horizon joint
measurement including noncapture zero paths, rather than another horizon proof
or choosing parameters by human agreement.

Opaque renaming of all14 supported Shogi type/base/current/guard/drop/promotion
references preserves the full candidate profiles. Eight preselected deployment
cells and178 actual reply frontiers also preserve continuation outcomes. Compiler
numeric IDs change under lexical ordering; structural pattern/geometry mapping,
including removed legacy references, matches156 patterns per case. This corrects
an earlier local checkpoint's155 count. It is observed semantic invariance, not
a universal naming theorem or complete alias replay of the56148-frontier census.

Compact exact fractions, assumptions, policy comparisons and corrections:
data/paired_context_20261008.json. Exact producers, failures and recovery inputs:
../archive/paired_context_20261008/. Scientific price construction remains OPEN.

A changed-context control now fixes an equal mixture of ownKing(0,0) and(0,1),
all other entities/rules unchanged, before computing values. Uniform initial
actions make first-ply transfer probability1/5 versus1/7. After that event the
same uniform enemy/drop/enemy policy measures service through ply4; other initial
actions contribute0 to this **first-ply-transfer** observable, even if they might
capture later. The new context completes55944 further actual reply frontiers;
Core/Native also independently agree on its seven initial actions and capture.

Here joint E[p_c H_c] is G0.7052376242/P0.1397518415; separately averaged factors
give G0.7053002229/P0.1395840651. Relative prediction errors are +0.008876% and
-0.120053%. Their exact difference is the two-context covariance
`(p_a-p_b)*(H_a-H_b)/4`. Thus independence is not exact, but this deliberately
small context change gives a close approximation and preserves G/P ordering;
it is not evidence to discard the cheap model. Completion took75.440sec, with
no fitted parameters or added framework. This fixes transfer time, not the
joint distribution of all possible first-transfer times; that remains a useful
next discrimination test. Exact raw supplement: joint-context-index.json in
the same archive, whose original package bytes were kept unchanged.

A Core-only structural preflight confirms that fixing first transfer at ply1
omits real support: after noncapture first moves, exhaustive enemy replies and
3836 third-ply actions contain54 late-capture paths per target in the original
context and90 per target in the changed context. This0.923sec enumeration is not
a probability or service measurement and has no independent Native claim.
It supplies concrete support/cost for the next fixed-total-horizon experiment;
exact source and a witness per cell are in late-transfer-index.json.

## Current temporal and goal construction

The fixed-total-horizon joint check is now complete. Independent six-step paths
retain a cheap qualified H3 approximation; ten-step P paths expose underestimation.
An independently sampled remaining-time kernel substantially reduces that bias,
while G changes are mixed. No coefficient/default is fitted. Exact scope,
conditional-context assumptions and uncertainty: [temporal service](TEMPORAL_HAND_SERVICE.md).

One-ply terminal-goal tests separate checkmate from stalemate focus. Matched
actor/helper/immobile four-cell controls expose conditional interaction; a
constructed B/N mate and a predeclared near-anchor law explain why broad sparse
zeros cannot establish absence. Equal-order marginal allocation constructs
finite goal contributions but depends on the declared context/goal law. It is
not a selected universal material table. See [goal interaction](GOAL_INTERACTION.md).
These current constructions supersede the earlier suggested next experiments,
without altering their frozen records or turning every old limitation into a task.

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


## Fixed-count response check and representation scope

A predeclared96-seed/192 paired-root batch fixes source25/target28, four other
identity slots uniformly among34 inner cells, and the same corner anchors.
All roots pass compile safety; this is not a reachable-position/playability
population. Uniform legal **bindings** within each root produce8102 replies.
Source losses remain zero, the target identity follows its actual move, and
initial roots retain equal weight. C/R mean legal capture is0.166388/0.623076,
compared with initial0.239583/0.75. The geometry/survival-conditioned fixed-count
versus IID pseudo-MSE differences are +0.00000699/+0.00003844, below across-root
SE0.000408/0.000217. Those predictors already use actual response geometry:
there is no demonstrated correction gain or cheap-forward deployment claim.
All127 pseudo-eligible but illegal captures have exact pre-S3 candidates whose
trial leaves the own anchor checked; all were already checked before capture.

Uniform legal actor then its moves gives0.169613/0.628157 without new transitions.
The eight-screen witness still reverses C/R ordering under either declared law;
anti-correlated C changes0.483333 to0.679487 and correlated R0.264706 to0.357143.
Rules alone do not select either law. These old binding-law records stay intact.

A forward one-step construction enumerates S0/S1 replies and their compiled
trial effects, then checks this fixture's source-specific count/clear geometry.
Actual reply outcomes are not predictor inputs. The192-root construction takes
2.502sec including compilation, with8288 explicit candidate transitions. Under
the original binding law, root-mean prediction MSE C/R0.000449/0.001228 is below
the no-response control0.039899/0.050200. It omits S3 reply/capture safety and is
neither exact WDL nor a material table. Timings of its separately measured
prediction/reference blocks are descriptive, not a controlled end-to-end speedup.

The original fixture has equivalent quiet bindings because cannon_quiet augments
legacy quiet movement. On24 fixed exposed roots, copying that action with a fresh
name preserves every physical successor and its capture legality, plus static
raw/profile results. Yet binding-uniform C/R means change0.135178/0.665449 to
0.148224/0.687545. Uniform distinct physical successors stays0.113012/0.631913.
Thus a response law must declare its sampling unit. The demonstrated quotient
includes board/hands/side/aux/shape and applies only to this fixture; source/target
alone does not identify general effects, and Position alone need not cover
history-dependent adjudication. No Core identity/default or generic quotient
framework was changed. A matched physical-law reanalysis gives C/R forward MSE0.000700/0.002033
versus no-response0.042276/0.065332. No root worsens on this exposed sample.
A predeclared32-new-seed/64-root extension randomizes source and target too:
forward MSE0.000000752/0.000994 versus0.000293/0.023976, again no worsened root.
Only7/32 C roots have a positive reference, so rare cannon cases remain a limit.
The extension uses5284 explicit candidate/reference transitions in3.683sec;
compiler/internal legality trials are additional and not included in that count.
This supports a finite positive response approximation, not generic deployment
or scalar material utility. A second predeclared16-seed/48-root batch adds an eight-offset L-leap N and
replaces the hand-written geometry with the generic source-specific S0/S1
candidate iterator. Matched-law C/R/N MSE is0.000320/0.000749/0.000727 versus
no-response0.004290/0.019451/0.021234; no root worsens. It takes3.094sec and4249
explicit frontier transitions; positive-reference roots are8/15/10 out of16.
These observations transfer the approximation interface to one extra mechanic.
All targets are still R, so the opportunity vector is target-specific, not a
universal price ratio. Next separate target-type/context bias before scalar use.

The first kernel failed on an unjustified unique-coordinate assertion and stays
complete=false. V2 incorrectly called legal anchor movement away from its corner
anchor loss; V3 scans owner/type anywhere and finds zero losses. Exact originals,
correction index and16 verified producer pins are retained in
../archive/joint_context_search_20261008/; compact results:
data/joint_context_search_20261008.json. No exposed-validation status is restored.

Advisor-motivated duplicate-predictor control uses the same24 exposed roots,
independently constructs S0/S1 physical-successor predictions before legal
reference enumeration, and copies quiet actions normally. Predictor successor
sets/values and legal reference sets/values are exactly invariant. Matched-law
C/R prediction MSE is0.000073646/0.002820093 versus initial-capture baseline
0.034260856/0.072878763.4364 explicit frontier transitions take7.285seconds.
No new population, fitted weight or universal history quotient is claimed.
This closes the predictor-side duplication check; all targets remain R.


## Target roles, capture legality and a standalone response score (2026-10-08)

The fixed physical-response law now varies source and target C/R/N:72 declared
roots,69 accepted,3 attacked-anchor rejections retained. Seven common layouts
separate source comparison from unequal acceptance. Target mechanics change the
capture probabilities; an equal average over target IDs is therefore a chosen
measure, not an encoding-invariant natural distribution. Splitting the C role's
one-third mass between C/C-prime leaves scores unchanged; assigning four IDs
one-quarter each changes them. The alias check is algebraic, not an extra actor
or a general behavioral-equivalence algorithm.

Exact signed error separates reply-support conditioning from post-reply capture
legality. In69 roots the R post-reply safety gap averages.01761; C/N gaps are0.
The rotated2x2 query experiment separates legality from indexing: full/source-
indexed scans give identical values; adding capture S3 reduces overall MSE from
.00041237 to.00002930. Prediction-stage time is about.52/.18 seconds for full/
indexed queries; this is not an end-to-end search or price-generation speedup.
The public iter_legal_action_bindings(source=...,target=...) retains S0-S4,
lossless bindings/order and cancellation. Source selects a board actor; target
alone also permits drops. It narrows candidates, never substitutes for safety
or postconditions. Product regressions include an actual S3-valid pawn drop
rejected by S4. No default price/search configuration changes.

A separate432-root horizontal0/1/2-screen family gives C opportunity about
.012/.55/.27 and R about.72/.12/.004. N is always0 in that geometry: it is a
C/R mechanism diagnostic, not a general population or evidence of low N value.
The subsequent32-layout frozen role law samples general displacements and keeps
zero captures. It conditions on27 common-accepted layouts and fixed C/R/N target
mass, giving raw forecast .05468/.23428/.13520 versus independent legal reference
.05382/.23264/.13666. This is a standalone response-opportunity candidate, not a
material table; do not mix quiet weights or fit against human references.

Chess/Shogi transfer now uses initial-inventory target/background probability
mass and weighted displacement strata; details and bias remain in
CROSS_GAME_PRICE_DIAGNOSTIC.md. Initial-position validation is distinct from
turn legality; checked-turn support is a separate declared comparison, not a
retroactive replacement of the frozen initial-safe population. Exact producers,
errors and recovery: data/target_context_20261008.json and
../archive/target_context_20261008/index.json. Advisor's fixed-role-mass objection
was adopted; no new universal-equivalence/WDL prerequisite was added.

## A separate preparation task, not a material blend (2026-10-08)

Advisor's utility objection is adopted as one finite next action. Q=R+B under
an additive endpoint count is a geometric identity, not intrinsically a defect.
Changing a metric merely to force a preferred Q ratio would be fitting. Instead
declare a different task before outcomes: one actual legal quiet, nontransforming
source preparation, one uniform distinct physical legal opponent successor,
then a legal capture of the tracked original target. Maximize over preparations.
This conditional task probability is separate from direct capture opportunity;
no quiet weight, material table, default or search change follows.

The first two initial-safe common Chess displacement seeds in ascending order,
202610092008/202610092009, use all P/N/B/R/Q sources, owner0 only (10 exposed
roots). Full Core histories and terminal status survive every transition.
Original target movement/promotion is tracked; duplicate physical replies must
have identical task/terminal/source-survival observables before quotienting.
Preparations preserve source identity and all other board actors. Standard
Chess scope excludes auxiliary target relocation; unsupported cases assert.

Preparation probabilities P/N/B/R/Q are .05/.2/.3/.2/(2/3) on the first layout,
and 0/0/(1/11)/(10/11)/.9 on the second. Original opponent-first direct values
are 0/0/.2/.05/.25 and all0, independently reproduced with complete Core state.
Both Q roots have replayed orthogonal-preparation/diagonal-capture paths with
history lengths1/2/3/4; these example paths need not be maximizers. First-root
Q exceeds R+B; second-root Q does not. Neither universal superadditivity nor
material improvement is established. No early terminal branches occurred;
zero roots and actual terminal checks are retained, not silently discarded.

The pilot used1369 full Core successor transitions in.618seconds. Independent
replay verifies10 retained paths (including two mixed Q paths), all10 direct
baselines and unchanged target ownership until capture. Two layouts/one owner
and the explicit uniform response policy limit deployment claims. Next change
one meaningful task/population premise, not sweep horizons to chase a ratio.
Opponent reply counts depend on the preparation and source type. Maximizing
these conditional probabilities is the declared task, not a same-support causal
effect or an adversarial guarantee. The retained rows include source loss and
zero-valued preparations; a maximum alone must not hide those failure branches.
Data: data/preparation_task_20261008.json; exact declaration/inputs/producers and
full outputs: ../archive/preparation_task_20261008/index.json (7 rehashed members).
