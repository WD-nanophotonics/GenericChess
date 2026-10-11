# Runtime typed auxiliary identity and whole-board projection

Science remains OPEN. This follows the private hash pilot in
COMPLETION_POLICY_ATTRIBUTION.md, using sandbox base
8c3da7b0db64f061371513e7131b1a8f22a63af1. UI99c97 remains frozen.
The existing eight Chess/Shogi roots and recombined fixture are exposed
development controls, not independent playing-strength validation.
Exact source/output hashes and failures are indexed in
[runtime_aux_identity_20261011.json](data/runtime_aux_identity_20261011.json).

## Selected identity repair

The public JSON/direct RuleSet compiler rejects boolean operands for declared
integer-valued set_bool effects with FIELD_NOT_INT. Four declared integer0/1
writes agree with the full hash. This does not establish a generated-rule bug.
However, immutable imported Positions accept boolean auxiliary values. Four
actual legal declared writes from those roots replace bool with int while the
old delta hash stays unchanged; the independent full hash changes.

A separate forced-hash17 control compares nondefault int1 and boolTrue roots.
Their public SHA identities differ, but the old exact runtime position guard,
TT key and occurrence counter conflate them. This is a collision-guard contract
defect, not an observed natural128bit collision or demonstrated playing loss.
Nested tuple scalar types and unknown None component insertion/removal have
the same Python-equality/presence pitfall.

The selected repair preserves auxiliary scalar types in logical-default
normalization, exact runtime identity and imported history witness reuse.
Delta hashing distinguishes missing components from explicit None and bool
from int, including nested square tuples. Public SHA bytes, generated values,
rules, evaluation and search policy are unchanged. Thirteen new regression
cases pass the repair and all13fail the isolated old Git source.
This is an auxiliary-state repair, not validation or canonicalization of every
arbitrary malformed imported board/hand/type representation.

## Selected mechanical projection

Semantic hash updates scan every board cell, skip identical immutable piece
objects, and materialize tokens only for changed cell values. Full hands and
logical auxiliary state, including unknown entries, remain represented.
Source/target squares are never treated as a complete action footprint:
compound actions and transition triggers can change remote cells.

The18-root depth3 traversal retains its2000successful-push cap per root and
a single300second whole-batch fuse. Both the private candidate and installed
source agree on15122actual public transitions, terminal states and undo.
Installed hashes also match the independently pinned old full-map oracle.
Several named weird-rule initial positions only exercise kings; their names
do not establish mechanism coverage. The raw promoted_changes counter counts
same-cell current-type replacement, including captures, not true promotions.
An additional existing eight-ply capture/promotion/right-expiry/capacity/drop
route checks all275legal children of nine actual parents. It observes58drops
after expiry, actual R-to-TP promotion, and guards suppressing drops at2/4/8.

Ninety-six lexical minimal-AB fixed controls and24trace controls retain moves,
scores and work across the eight roots. Typed repair alone adds roughly
0.9–5.7percent mean cost versus the old module. Private projection removes
6.8–13.2percent versus repair on seven roots; the Shogi-drop mean is0.26percent
adverse. Short timings are jitter-sensitive and are not universal speed claims.

Actual public weighted2/5/3 q4 calls retain16fixed-node pairs and32one-second
controls. Fixed-node means generally save3–6percent; an immediate-mate control
is adverse and too short for a useful speed conclusion. The supported hybrid
Native-legality/Core assay adds16fixed-node pairs and64one/four-second calls.
Actual provider calls and fallback counts are recorded. Fixed-node means save
about3–11percent on substantive roots. The budget controls return the same
completed depths/actions/scores; extra work has not demonstrated better choices.
Shogi-promotion finishes depth4 early. Other time-limited roots commonly retain
depth1; four seconds adds depth2 in EP/Shogi-middle and depth3 in Chess-promotion.
These observations do not justify changing q policy, default evaluator or UI.

## Checkpoint exception-origin repair

All733production SearchAborted injections restore the tested roots/history/hash.
During a separate RuntimeError callback control,42throws are swallowed by the
existing S3 trial's broad RuntimeError-to-illegal-candidate conversion. Recorded
callback counts exceed the throw indices: the initial cache-warming explanation
was wrong and is explicitly corrected. Production SearchAborted does not inherit
RuntimeError; no production cancellation failure is inferred from this control.

The narrow repair records whether the supplied checkpoint raised during the
trial transition. Such exceptions propagate with their original object; actual
transition RuntimeError still rejects an unexecutable candidate. Only supplied
checkpoints allocate a wrapper. Two new Chess/Shogi regressions fail the isolated
old source; the real-transition rejection control remains valid. All733tested
RuntimeError injections now propagate and restore the root. No instant or hard
deadline promise follows; synchronous native operations remain cooperative.
The128matched fixed-work callback controls preserve decisions/work. Mean
cooperative cost ranges from2.6percent lower to3.8percent higher; no-checkpoint
calls allocate no wrapper. The hybrid projection assay was loaded before this
separate callback repair, so its timings are not final combined-source timings.

## Failure and evidence limits

Initial scalar probes selected a lowered legacy king action, not the declared
write; corrected sem_ selection is explicit and the failed probes remain.
A tuple forced-hash argument was unsupported and corrected to the existing
integer override. An initial delta patch landed in the legacy branch and was
corrected by diff review before regression. Baseline export first used tar as
zip; the retry used explicit --format=zip. A module alias lacked its relative
import package before any timing; its failed source remains.

Automatic review rejected the original traversal's cumulative per-root limits
because its worst case could exceed one hour without Dot necessity assessment.
The approved alternative has one five-minute whole-batch fuse; no rejected job
ran and no review bypass occurred. Actual traversal duration is recorded.

Rerunning the callback script accidentally overwrote its pre-fix JSON. The42
old observations are recovered from complete recorded tool stdout and labelled
as recovered values, not original file bytes. Original failed source and failure
notes remain. Do not claim byte-complete recovery of that overwritten report.
Earlier full-suite evidence predates final normalization/projection/callback
changes; final-source validation is recorded separately. Slack raw reads and
account records remain ignored and excluded from the public archive.

## Terminal availability boundary and next choice

Sixteen additional equal-time calls at8/16seconds on Chess-middle and Shogi-drop
retain the same completed depths, scores and actions under final callback code.
Chess-middle retains depth2 and Shogi-drop depth1. These development curves
do not extend old frozen validation or establish a playing gain.

On118actual root/first16lexical-child states,3776serial queries agree in
availability. Native full-frontier boolean proxies are about2-29times slower
on ongoing-root means, with quiet mate/stalemate exceptions near0.36times.
This rejects blanket replacement; it says nothing quantitative about an
unimplemented Native early-exit predicate.

A private checked-child frontier-reuse proposal passes15122old capped tree
transitions but fails a new max_ply1 checking move: Core/public returns MAX_PLY
draw while the proposal returns CHECKMATE. Native transition explicitly rejects
parent.ply>=max_ply. Its empty frontier is not pure pre-adjudication availability.
The current product keeps Core terminal authority; checked/quiet controls pass.
A five-move declared rook cycle supplies a second failure: the private proposal
gets REPETITION right but leaks two eagerly cached actions; current product
returns none. All three boundary regressions pass. The private proposal is
rejected without integration; its prepared cost/frontier-audit scripts were
not executed. Initial modified-builtin helper rejection is retained too.

Dot's complete reply was read, payload-verified and evaluated locally. Adopt
stage/cost attribution before more cache proposals. Dot reviewed the supplied
report, not unpublished code or independent executions; no policy changed.
Eight actual paired hybrid512node callers retain moves/scores and produce
9431availability calls,11510S3candidate trials, all before adjudication, with
zero repeated unchanged frames. The first ID-only counter falsely counted
recycled Python object IDs; retaining identities fixes it, with old output kept.
Instrumented timings include annotation overhead and are not speed evidence.

Thirty-two opposite-order fixed-work calls separately replay prerecorded exact
availability answers. Every input position sequence and decision matches the
recording. Substantive controls show optimistic cost ratios about0.66-0.77;
Shogi-drop is1.01, neutral/adverse. Recording/list overhead, checkpoint behavior
and memory differ. This is a cost-opportunity diagnostic, not a deployable cache,
formal speed bound, hypothetical-kernel prediction or equal-time gain.
The next choice is a scoped pure-availability interface feasibility question;
unchanged-frame cache reuse lacks an observed opportunity in these callers.
Do not infer all generated-rule coverage or rebuild the blocked DLL from this.

## Selected ongoing-continuation support repair

The provider-stage audit found a current product exception to the apparent
ongoing/below-max equivalence. An actual declared automatic threshold at ply1
continues after Qa2-a8 gives check, masking max_ply1. Core/session remains
ONGOING with h8-g7 and h8-h7, but current Native-backed runtime returns no actions.
This is distinct from the rejected private proposals and affects an existing
supported generated-rule interface, not an observed UI user game.

The Native provider now declares per-position support only below its max_ply.
Core's opaque-provider adapter honors an optional supports_position callable:
a false result selects Core for this state, records a normal fallback, leaves
operational-failure count unchanged and retains provider eligibility elsewhere.
Providers without the optional capability retain their existing contract.
No rule/ply/history is rewritten, no native binary rebuilt, and strict mode
also performs this declared capability fallback. Two actual continuation
regressions verify the two legal replies, another child, terminal authority,
push/pop restoration and provider support after returning below the boundary.
That distinct nested S3/S4 question was then executed. An Agent-constructed
imported two-king Shogi position with a pawn in hand has76Core actions at both
max_ply1/2; at1Native returns75, dropping the legal checking pawn move, whereas
at2it returns all76. The S4 no-reply test's child is filtered at max_ply, so a
legal drop is mistaken for forbidden pawn-drop mate. This is not a played
history claim. The first probe mistakenly supplied a nonexistent initial_hands
field, then selected legacy DropMove instead of the actual semantic drop;
both setup/selection failures are retained.

Provider capability therefore also excludes the last pre-limit ply when any
compiled pattern has a no_legal_reply postcondition. It conservatively uses
Core for that boundary rather than changing terminal rules, native ply values
or the DLL. Two adjacent-limit full-action-set/child/undo tests pass. This is
mechanical semantic capability detection, not a manually named Shogi patch.

Earlier algorithms passed2042active tests before provider doc/three boundary
regressions; the19new repair/boundary tests then passed together. The subsequent
continuation repair has54focused runtime/boundary tests and2047full active tests.
The later S4 repair has13focused boundary/provider tests and a separately saved
final whole-suite run:2049tests, zero failures/errors/skips in194.83seconds.
Archive source and output hashes preserve these different
validation stages. Engineering,
failed attempts, instrumentation, test time and archive bytes are real costs;
no universal cutoff or numeric information-per-token claim is imposed.

The next prepared existing-API alternative was executed after the suite:
944opposite-order queries on the same118states compare Core lazy availability
with Native S0 candidates plus individual checked-make early exit. All answers
agree inside its explicitly bounded support. Aggregate ongoing root/child
cost ratios are1.03-2.15Native/Core; quiet mate/stalemate are about0.39.
Checked make still allocates a child and hashes/appends history; this is not
a transient early-exit kernel. Reject deploying this wrapper, keeping the
quiet exceptions and short-timing limits. Next attribute Core first-action
trial/guard/attack/allocation cost without changing semantics or rebuilding DLL.
