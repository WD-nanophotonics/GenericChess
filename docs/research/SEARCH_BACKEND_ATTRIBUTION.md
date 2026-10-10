# Search backend and algorithm attribution

This development assay implements the search-first direction. Its entry is
`scripts/search_backend_comparison.py`; it does not replace the product player
or propagate research changes into `ui-test`.

## Frozen first comparison

Eight source-declared roots cover Chess middle game, immediate mate, promotion
and en passant; Shogi middle game, a tactical sparse position, promotion and
held-piece drops. Played roots replay their entire declared opening. Sparse
snapshots start a new history explicitly. These are exposed development controls,
not human-labelled holdouts or a representative strength population.

The source fixes arbitrary, distinct integer material controls. They are neither
human-price fits nor proposed universal prices. Both leaf and ordering tables
are explicit. Shogi held pieces use their base-type values, promoted board pieces
their current-type values. King material is zero. Terminal scores have a separate
mate range and distance convention.

One lexical-order negamax alpha-beta drives Core and specialized libraries.
There is no TT, PVS, quiescence, reduction, tactical prescan or hidden heuristic.
Native legality is a third arm using the same Core state/history/algorithm, not
a claim that the entire search runs in native code. The fourth arm uses current
production iterative search with cold TT and ordering, the same material, q0
and tactical root scan off. Its node definition differs from the minimal search.

First declare D2, two order-counterbalanced repeats and a30second safety ceiling.
Then D6, two repeats,45seconds and1000000 recursive-entry ceiling per call.
Four arms x8roots x2repeats x45seconds has a48minute maximum requested search
budget; individual calls are interruptible and below the long-run threshold.
Audit/initialization/save overhead is outside the timed search, counted separately.
Do not extend these frozen calls after adverse completion or utility results.

## Semantic boundaries

Current Western Chess production declares repetition100000 and max-ply1000.
The specialized arm follows that scoped policy: it does not silently enable
FIDE claim,75move or insufficient-material draws. The finite assay cannot reach
100000 repeated occurrences. This is not certification of standard draw rules.

Shogi now declares no-legal-move loss, fourfold repetition/continuous-check
loss and the existing500ply no-contest extension. The first pilot exposed
non-check no-move draws in the previous product. The frozen D6 cohort retained
that previous rule fingerprint ac987c3f and its explicit draw adapter; after
completion, the product changed to ba3518b9. Historical fixtures are not rewritten.
The new rule follows the no-legal-move loss condition in
[CSA competition rules, Article27](https://www.computer-shogi.org/wcsc36/rule.pdf).
This does not adopt the competition's other adjudication or time policies.

A second discrepancy appeared only deeper: on the promotion root, old Core
visited850 recursive entries while the specialist visited795. cshogi's
[Position::isDraw source](https://github.com/TadaoYamaoka/cshogi/blob/master/src/position.cpp)
checks an earlier matching position without requiring four occurrences. It is
a search repetition detector, not a strict fourfold adjudication oracle.
The repaired specialist adapter owns exact SFEN piece/hand/turn identities plus
actor/check history, requires four occurrences and applies continuous-check loss.
Tests cover second-occurrence nontermination, fourfold draw, checker loss and
complete D6 trace/work alignment. Identity construction overhead remains in
specialist timing; it is not hidden behind a claim of native-only execution.

Entering-king declarations and the500ply extension boundary are outside this
board-action assay. Crossing500 raises unsupported rather than silently drawing.
Promotion, drops, base/current identity, auxiliary state and replayed history
remain. These scoped controls do not replace the complete generated-rule target.

Audits compare full represented board/base/promotion/hand/side/auxiliary/ply
states, legal sets, material and terminal values at each visited position.
Search tests compare complete D2 path hashes, work, scores and choices across
the minimal adapters. Abort tests require actual push/pop and history restoration.
This establishes the tested scope, not arbitrary rule equivalence.

## Interpretation

Keep three questions separate: cost of identical primitive work; actual work,
coverage and completion of a defined search; usefulness at the same time budget.
Minimal recursive nodes include root and terminal/static leaves; push counts
are child transitions. Production main+q counts span iterative depths. Neither
node total may be converted into playing strength or equated across algorithms.
Same score with another tied move is not a gain. A capped result is not a
completed D6 reference. Separate initialization, warmed execution, diagnostic
instrumentation and operational timing. Record actual Native calls/fallbacks,
not merely the requested switch or import availability.

Mature engines are overall references unless their complete evaluation and
terminal/search conditions are aligned. A material-leaf override alone still
leaves mature SEE, pruning and capture-order constants coupled to other prices.
No mature node count is equivalent to a Python recursive entry.

Primary adapter documentation: [python-chess core](https://python-chess.readthedocs.io/en/latest/core.html)
and [cshogi](https://github.com/TadaoYamaoka/cshogi). Exact results/source pins and
failures are added below after the frozen run, rather than inferred from these APIs.

## Observed frozen D6 controls (old rule/adapter version)

All64 original calls are retained, including caps and one Native Chess-middle
row contaminated by a concurrent2.44second pytest run. Do not infer clean timing
ratios from that row. Only the two completed Chess roots below have equal
minimal recursive-entry totals across all three backends in this old cohort:

|Root|Entries|Core seconds|Specialized seconds|Native legality seconds|Production seconds / entries|
|---|---:|---:|---:|---:|---:|
|Chess immediate mate|46059|11.77–12.04|0.65–0.66|8.11–8.27|22.79–22.86 /63368|
|Chess promotion|12055|2.66–2.69|0.15–0.16|1.91–2.00|1.57–1.61 /4112|

Production ordering/TT therefore does not uniformly beat bare lexical AB on
these roots: more scheduled work hurts the mate control, fewer entries help
promotion. This is a scoped algorithm/work effect, not evidence to disable
ordering generally. Most other Core calls hit45seconds; several specialized
calls hit the separate1000000entry cap. Neither is a completed D6 comparison.
The old Shogi promotion850/795 discrepancy invalidates its identical-work timing
interpretation. New strict-history controls supersede it without altering it.

## Native provider accounting repair

The common-time pilot's production Native counters reported calls but zero
payload/decode time. Inspection showed SearchPathRuntime read metadata only
from callable.__self__; NativeSemanticLegalityProvider is a callable object.
The same issue ignored its strict flag on operational failure. Resolve the
owner as bound-method owner or the callable object itself. Dedicated tests
cover both forms, strict propagation, explicitly non-strict fallback and metric
aggregation. Old timing/results remain old-source records; subsequent profiles
use the repaired accounting. This repairs observability/declared failure behavior,
not search evaluation or legal action definitions.

## Common-time useful-decision diagnostic (repaired rules)

Frozen budgets0.25/1/4seconds, two reversed-order repeats, eight roots and five
arms produced240 legal choices. Both full-root D4 and selected-child D3 references
completed for every row. Regret uses the same arbitrary material table and mate
distance, not game outcome, independent generalization or strength. These are
exposed controls and repeated correlated roots, not240 independent samples.

|Arm|Positive D4 regret /48 choices|
|---|---:|
|Bare AB/Core|14|
|Bare AB/specialized|2|
|Bare AB/Native legality|12|
|Supported search/Core|18|
|Supported search/Native legality|16|

At1second, the ep control gives100 material regret for completedD3 versus0
for specializedD4; Shogi middle gives200 for Core/native/production choices
versus0 for specializedD4; held-piece drop gives400 for shallow Core/production
versus0 for specializedD4. In four other controls all arms have0 regret and
alternative promotion/terminal choices are ties. A deeper search can also choose
a move worse under this finite D4 teacher; two specialized positives are retained.
These outcomes justify investigating backend execution cost, not adopting a
specialist-only player or claiming a general chess-strength gain.

The first utility attempt failed because a child search compared restoration
against the parent's stored root. It was repaired by constructing a child case
with the entire replayed prefix, leaving the parent untouched. No failed result
was promoted into the completed cohort. The final cohort retains the original
(runtime-accounting pre-fix) source and declares its missing minimal-iterative
provider counters; following profiles measure actual provider counters.

## Fixed primitive question and cost boundary

After whole-search profiling, isolate the same eight roots with20 cold-front
queries,100 cached-parent push/pop pairs and5000 static evaluations per backend.
Core cache clearing is explicit assay instrumentation; initialization is separate.
Specialist libraries retain their own internal representation/caches. All fronts
must stay identical within each row, roots must restore and repeated scores agree.
This is a new component-attribution question, not another price/strength test.
If generation/transition dominate rather than evaluation, the next investment
is an evidenced generator/reuse or bridge bottleneck; otherwise leaf-cost work
must be reconsidered. Estimated incremental local run is under two minutes;
no sample growth or larger training follows. Count actual times and source pins.

## Fixed-work and primitive results; next choice

All four clean25000-entry arms have identical complete work counters on each
profiled root. Chess middle costs9.79sec Core,13.08 with inner cooperative
checks,0.62 specialized and6.19 Native legality. Shogi drop costs34.48/51.43/
0.225/9.99 respectively. cProfile inflates times; cooperative drop reaches its
120second fuse at20708 entries, so that instrumented row is not an equal-work
speed comparison. All16 rows remain, including the fuse.

Core's Python trial transitions are153760/889594 in the two instrumented roots;
Native reduces them to50332/51883, with zero observed fallback and nonzero
payload/decode accounting. Native still uses Python transition/check/history.
The Shogi Native path also decodes763665 legal actions for25000 recursive
entries: binding/public-action conversion is material at high branch counts.
Packing alone is a smaller cost; do not prioritize it merely because it is an
obvious interface boundary. Profile cumulative times overlap; never add them
as independent costs.

Primitive cold fronts on Chess middle average1.691ms Core,0.050ms specialized,
0.630ms Native. Shogi drop averages3.478/0.030/1.384ms. Core static evaluation
averages2.535us on Chess middle and1.114us on the drop root; it is cheaper here
than specialist Python-adapter scoring. Parent-cache push/pop and these two
fixed root snapshots are not averages over search trajectories. These small
primitive measurements support the generator/conversion diagnosis but do not
supply universal performance ratios.

Next isolate high-branch conversion versus residual Core trial/check work,
using the same ordering/material/cancellation and full-state trace witnesses.
A lazy binding or existing successor-reuse candidate must retain legal-front
validation, failure semantics and exact history; it needs a bounded finite-work
and common-time comparison plus unfamiliar generated-rule transfer before a
product change. No default algorithm or evaluation change is adopted here.

Existing mature references are presently unavailable: Stockfish launch returns
App Control4551; the Fairy-original USI handshake lacks a full9x9shogi variant.
Hashes/options/protocol/failures are retained. No security workaround, binary
substitution, claimed mature comparison or heavy new build follows.

Validation:85 affected bridge/runtime/terminal/native/Chess-perft/Shogi tests
pass; frozen old-rule eight-frontier recovery passes, all archive hashes and
source/rule version boundaries are checked. Evidence:
[data index](data/search_attribution_20261010.json) and its purpose archive.

## New binding-path premise (predeclared isolated ablation)

Inspection of `_make_binding_from_action` shows that naive lazy binding would
also delay geometry/type/source/path validation. Do not adopt that shortcut.
A smaller existing-equivalence candidate is `_path_for_geometry`: it still
allocates all geometry endpoints through `geometry_candidates` before finding
one target. Reuse `geometry_paths_to` and its first matching prefix instead.
All prior checks and exact geometry identity remain, with no new cache/API.

Before seeing results, freeze strict Native minimalAB on Chess-middle/Shogi-drop,
25000entries,D8,30second fuse,two reversed-order repeats, with every finite
owner/source/target geometry query compared first. This new premise concerns
binding reconstruction, not the earlier attacked-square iterator experiment.
Possible outcomes determine whether to retain this small cleanup or defer it;
no larger budget, evaluator change or omitted validation follows.

Result:1310162finite geometry queries agree and eight25000-entry calls retain
all work counters. Relative target-directed wall changes are+1.669/-3.631% on
Chess middle and+0.436/-1.183% on Shogi drop. The direction is unstable at this
scale. Preserve the candidate as an isolated diagnostic; no production path
change or larger repeat budget is justified by this result.

## Conversion attribution and bounded public syntax reuse

A new4096-entry decomposition keeps cProfile instrumentation separate from
clean timings. A sixteen-call stage assay then compares4096 with25000 entries
on the same middle/drop roots. Its nonoverlapping provider intervals distinguish
payload, Native legality/return, decode, binding and public projection. On the
drop root provider share rises from about33% to61% as the search prefix grows;
public projection alone reaches about9% of total instrumented wall. Shallow
frontier measurements therefore understate this conversion cost. Additional
instrumentation raises large-drop wall by about3–4%; profile cumulative times
still overlap and are not additive causal shares.

The installed change retains one dictionary of at most2048 packed-action keys
per existing provider thread. Each hit only reuses a frozen public semantic
action. Complete decoding, source/base/current-type validation, pattern lookup
and position-dependent binding reconstruction still run on every action. The
key includes kind, source/target, promotion, base/actor type and exact pattern/
geometry indices within one compiled provider. Public projection depends only
on these fields and that provider's fixed shape/mappings. Aux/history and current
binding are never cached as legality facts. Existing callback scheduling and
strict failure semantics remain, including warm hits and cache eviction.

Sixteen actual-product calls against the frozen uncached method have identical
fixed-work traces. Reversed local wall reductions are2.56/3.07% on Chess middle,
8.38/7.95% on Shogi drop,4.01/6.06% and4.27/2.59% on two generated full-history
roots. Retained shallow object estimates are96–363kB on those controls, including
dictionary/keys/public actions/squares; shared strings, allocator and transient
memory are outside that estimate. The dictionary is bounded, but wider-rule
churn and a total process-memory bound are not established by these timings.

Same-time0.25/1/4second diagnostics retain all192 legal choices at eight roots,
two reversed repeats and minimal/supported algorithms. All96 old/new pairs keep
the same action and finite-D4 regret. Positive regret is12/48 in each minimal
arm and16/48 in each supported arm. Completed depth increases in4/48 minimal
pairs and2/48 supported pairs, never decreases here, but this does not change a
choice or establish better playing strength. Preserve that absence of decision
gain alongside the finite-work throughput improvement.

Transfer audits compare all803 public children at22 existing6x6 event roots:
full position, terminal, runtime hash oracle and history/search keys agree with
Core and the old provider. A separate176-call q0/q2 caller check completes D2
throughout and keeps every action/score/PV, with balanced restoration and zero
Native fallback. Among44 reversed pairs per q setting, faster rows are33(q0)
and29(q2); median reductions are2.01% and1.11%, with regressions as large as
15.96% on tiny q0 calls and5.48% on q2. These exposed repeated roots test scoped
semantic transfer, not the entire generated domain or independent generalization.

Two alternatives remain deferred. Full-cell sparse identity differencing,
first using metadata carriers and then a direct ancillary map, has mixed small
effects across familiar/generated/Core/Native controls. Its512 compound identity
and12 auxiliary/resize oracle cases concern synthetic carriers, not observed
legal production defects. Live hashing is unchanged. Existing semantic-engine
construction is about2% of Native instrumented cost, which does not justify a
global engine cache. Repacking every child for the already installed Native
anchor-check export regresses all eight reversed4096-entry pairs by2.67–11.26%.
Its callback granularity also differs. Retain Python check/history authority;
neither faster primitives alone nor reuse rhetoric warrants a new route.

Exact outputs, original projection method, product source and negative prototype
limits are routed by [the conversion index](data/native_conversion_20261010.json)
to a purpose archive. The first sparse pilot and unpinned intermediate-source
limitation remain explicit. No default algorithm, evaluator, rule definition,
training, game population or frozen `ui-test` revision changes in this step.

## Full Native search has a separate terminal-policy gap

Full C search is distinct from Native legality with Core search. A twenty-call
support pilot uses eight familiar and two generated full-history roots, D2,
one second,100000 entries, explicit material, zero dynamic terms and TT0.
Full Native iterates D1+D2 and orders packed actions; bare Core uses lexical
order without iteration. Their work counts are not aligned. Three Native calls
stop at D1 while Core completes D2. Legal choices/PVs and restored roots alone
certify neither identical semantics nor faster complete search.

On Shogi's tactical root, Native reports1400 versus Core's one-step win.
Two children,3c2c+ and3c3b+, have zero legal moves without check. Current Core
awards the opponent the win; installed raw C reports stalemate without a winner.
Its semantic payload omits `stalemate_result`. Native's10^8 and Core's10^9 mate
scales explain two other differences, but cannot explain this adjudication error.
Old results and installed binary hash stay archived; affected roots cannot
establish correct Native search cost.

Public Native terminal, fixed/probe, iterative, persistent and experimental
parallel search now reject the unsupported loss policy explicitly. Native legal
actions remain usable with Core terminal/history authority. This is a capability
boundary, not a C repair or full-support claim. Existing Native execution tests
use explicit legacy draw-policy variants for their unrelated capabilities;
historical hash fixtures keep that policy and old hashes. Current Standard Shogi
fingerprint checks use its corrected loss definition. Historical numerical
evidence and the frozen UI remain unchanged.

Advisor review supports retaining this boundary and prioritizing a separately
versioned kernel repair before affected full-Native cost attribution. It reviewed
supplied evidence, not an independent rerun. Source inspection finds another
required change: fixed/probe search scores checkmate as loss and other terminals
as zero, ignoring winner; iterative/persistent already score terminal winners.
A payload-only patch is insufficient. Existing Zig builder/compiler are present;
new build execution permission is not established. No rebuild or App Control
change was attempted in this segment.

A typed board-token memo prototype retains all32 fixed-work traces with96–98%
hits. Most gains are0.4–2.6%, with one reversed Chess/Native pair regressing1.58%.
Defer this extra live cache. The first broad regression exposed inaccessible
system temp paths and obsolete Shogi fixtures; retain that failure and validate
the corrections with a project-local temporary directory.

## Post-publication zero-feature scheduling control

The terminal scan generates candidates before probing availability; a nonleaf
then generates them again. Before redesigning this,1800 warmed primitive calls
on three supported Chess roots show that evaluation with explicit zero dynamics
costs more than terminal queries. Source inspection explains why: any supplied
dynamic tuple sets `dynamic_supplied`, so even `(0,0,0)` computes unused features.
An absent profile disables them. Existing product defaults already use absence.

A separate2400-call primitive control preserves scalar material and root state.
Twelve full-Native searches, D8 with512nodes and a two-second fuse, compare zero
versus absent dynamics in reversed order. All six pairs preserve actual action,
decision line, score, PV, completed depth, nodes and termination reason; absent
features take about6–18times less wall on these three roots. This is a bounded
scheduling diagnostic, not a universal speed factor or stronger-player result.
Dynamic feature telemetry/config identity can differ and is not declared equal.
No production default or C binary changes.

The earlier full-Native pilot remains the explicit-zero scheduling version.
Its caps cannot establish inherent Native slowness; its Shogi no-move defect
remains a separate correctness failure. Future material-only comparisons should
omit unused feature profiles and record that version boundary. On affected loss
rules, kernel semantic repair still comes before correct-search cost attribution.

## Supported full-state Native attribution — 2026-10-10

The next segment built an unchanged isolated v4 control and imported it in a
fresh process. A versioned v5 candidate then built successfully, but its fresh
import failed with Windows Application Control. Code Integrity events3033/3077
identify signing/code-integrity enforcement; the policy's owner/name was not
established. No candidate test executed, no replacement was installed and no
system policy changed. Exact candidate sources, tests, build outcome and binary
hashes are retained separately from active code. This supersedes the previous
segment's unestablished-build status, not its historical measurements.

An independent installed-v4 defect is now demonstrated on two fully legal,
owner-reversed12-ply continuous-check cycles, each with13 position witnesses.
Raw terminal reason/winner agrees with Core, but raw fixed/probe returns zero;
iterative returns the correct winner sign. These controls use an explicit legacy
draw-stalemate Shogi variant to isolate repetition scoring. Public fixed/probe
now rejects v4 continuous-check-loss rules before execution; iterative and
Native legality with Core remain available in their existing scope. The v5
candidate would address both no-move policy and winner consumption, but remains
unexecuted. Guarding an unsupported entry is not repairing its C implementation.

`scripts/native_backend_bridge.py` is a diagnostic adapter over immutable C
positions, exact history/events, guarded actions and checked transitions. The
same existing Python lexical alpha-beta drives it and Core. Terminal reason and
winner are consumed by the common Python mate-score contract; the bridge never
calls faulty fixed/probe search. C's10^8 and Python's10^9 mate conventions are
kept separate in algorithm comparisons. Loss-stalemate policies remain rejected,
and declaration actions are outside this adapter's search scope. This is a thin
attribution bridge, not a complete-domain player or a replacement algorithm.

Four existing Chess roots and two existing generated6x6 roots at ply3 yield44
fixedD8/4096-entry calls with two reversed passes, using Core, Native legality
with Core state, full Native state, and specialized Chess where applicable.
Every call reaches the same node cutoff before its30-second safety fuse; return
trace, work counters, action and score match.187 D1 states are checked separately.
Six deeper paired audits compare all24576 visited states and24576 parent
restorations through relativeD8: board/base/current/owner identity, hands, side,
auxiliary fields, exact history/check events, terminal reason/winner, leaf value
and ordered frontier all agree. Instrumentation timing is excluded; its600-second
audit fuse leaves the original4096-entry scientific cutoff unchanged.

The ratio is **Core warm wall / Native-state warm wall =3.37–4.43** on these
reversed calls, so Native state is faster. An earlier ambiguous Slack phrase
caused the opposite interpretation; the numeric evidence and denominator govern.
Specialized Chess remains faster on its four roots.44 separate one-second bare
iterative controls retain incomplete-depth/fallback semantics and legal choices;
completion gains occur on promotion/generated2000, without a strength inference.

Two-root4096-entry profiler controls preserve signatures but add44–62% wall.
Guarded frontier execution has the largest C self-time; terminal scanning and
public-action/label conversion also matter. C's position and undo objects are
53920bytes each. Copy cost is a hypothesis, not a measured dominant component;
inclusive profiler intervals must not be added or read as uninstrumented shares.
The generated zero/absent-feature transfer independently keeps all eight512-node
action/score/PV/work/root signatures, with locally11/14times lower wall for
absent profiles. Product defaults already omit them; no new default follows.

### Syntax reuse and configuration are different causes

A separate per-call2048-entry immutable action/label cache prototype retains
live C guarded frontier and transition checks.24 fixed4096-entry calls preserve
all signatures; repeated-pair mean wall reductions are12.8–32.5%. Six further
paired audits retain another24576 full-state visits and parent restorations,
not independent new samples. Retained shallow cache estimates are64–141kB on
these fixed controls; shared referents, allocator overhead and total process
memory are excluded. No fixed-work control reaches eviction here. The first
prototype incorrectly treated packed integer actions as tuples; that failed
source/output is retained alongside the corrected integer-key version.

Twenty-four one-second calls gain one completed depth on tactic, EP and
generated2001 in both reversed pairs. Only EP changes its action: b1c3 to c2c3.
Reusing the already exposed finiteD4 material reference gives regret100 versus0
on EP; the other three Chess choices remain at0. This is finite-reference utility,
not true game value or playing strength. Generated choices remain unchanged and
have no new utility oracle. The cache stays an archived diagnostic prototype;
the active bridge retains its uncached baseline for attribution.

Fifty-four0.25/1/2-second three-root algorithm controls deliberately disable C
root pruning and TT. Their greater C node throughput does not establish better
completion or decision quality: node definitions, packed versus lexical order,
full-PV replay and partial-root handling differ. Crucially, product
`SemanticSearchEngine` already defaults to root-window pruningON. An OFF control
must not be described as product-default performance or as a missing optimization.
Source inspection finds full windows for every root child when OFF, narrower
subsequent children when ON, and canonical PV re-search cost when ON.

A clean supported ON/OFF ablation has12 completedD2 calls with equal scores,
but node counts845→166(EP),1214→225(generated2000),2028→189(generated2001).
Thirty-six separate common-time calls show completion improvements. The first
attempt overlapped pytest accidentally; its timing is explicitly invalid and
preserved, and the clean repeat starts after pytest exits. Cold64MiB TT is also
an existing product default and receives a separate matched-window control.
Neither attribution control changes the installed default or restores old
unexposed validation status.

Advisor review was read completely and its deeper-contract/score-consumption
objection adopted; it did not independently rerun the evidence. No workflow or
research-direction policy changes follow. Full active regression and focused
preterminal winner-propagation tests pass; exact counts, sources, failures and
completed controls are routed by
[the terminal/bridge index](data/native_terminal_20261010.json). The frozen UI
branch and old conversion archive are untouched.

### Completed score is insufficient: exact selected-child counterexample

The ON/OFF controls above describe the pre-guard implementation, not the final
safe product default. On the existing Chess EP history e2e4 a7a6 e4e5 d7d5,
material K0/P100/N200/B300/R400/Q500, q0, completeD3, TT0 or cold64MiB:

|Root windows|Selected action|Reported root score|Independent complete childD2 root value|
|---|---|---|---|
|Full/OFF|f1d3|100|100|
|Narrowed/ON|f1e2|100|0|

Core and raw installed-Native full-window child searches independently agree.
All calls complete and retain legal PVs/restored roots. This is a selected-value
correctness defect, not merely a different optimal tie. TT0 reproduces it, so
shared TT contamination is not required. Generated2000's apparent discrepancy
normalizes after converting Python10^9/Native10^8 mate scores and child-relative
mate distance; it is explicitly not counted as a defect. The first child audit
used parent-root restoration on a child-root view and failed; that source is
retained separately from the corrected child-root contract.

Source inspection suggests later narrowed children return a root-perspective
UPPER bound equal to the incumbent. Canonical packed-action comparison treats
that as an exact tie; selected-PV full re-search then discards its returned value.
This is a causal hypothesis consistent with the counterexample, not proof that
all defects have this cause or that the installed binary matches these sources.
The source-derived completed-call difference nodes-transitions-iterations counts
replay entry events only: EP/generated2000 TT0/OFF0, ON6; TT64/OFF93/117, ON6.
It does not measure all replay subtree work or time. Training trace computes
extra dynamic features and deduplicates without complete history, so it is not
an inexpensive authoritative state-trace substitute.

The Python product protection rejects explicit ON before C in both low-level
and persistent iterative entries; persistent default changes to full-rootOFF.
Existing persistent instances also use this per-call guard. The parallel wrapper
has no ON option and delegates to the guarded low-level default; no parallel job
was launched. Cold and reused persistent TT0/64 on EP both select a child with
exact root value100. Raw C remains a diagnostic boundary, not public safe ON.
Other supported Native features remain available. Full-root cost increases
relative to the unsafe optimization; the previous work/completion gains cannot
justify accepting incorrect selected moves. This finite regression does not
prove full-root correctness on every rule, extension or evaluator.

Dot's complete reply supports protection and exact candidate verification. Adopt
its single next contract: only EXACT-valued ties can replace an exact incumbent;
verify in the same depth/history/evaluator/q/mate convention, preserve TT bound
semantics, and never install an unverified replacement after a budget interrupt.
Score/action/PV must be committed consistently. The proposed contract is archived,
not an implemented C repair. Terminal-v5 only repairs terminal policy/winner
consumption and does not fix this new root-window defect. Dot reviewed supplied
reports, not an independent implementation or benchmark execution.

Final active suite:1842passing items, exit0; subsequent22focused tests include
cold/reused persistent-TT selected-child checks and both-owner terminal propagation.
Pre-guard wrappers/C sources accompany exact ON experiment outputs; they are
historical reproduction inputs, not production instructions. The current guard,
terminal-v5 unexecuted sources, syntax prototype, failed tuple/child audits and
invalid concurrent timing remain distinguishable in the terminal/bridge index.
Next implementation investment is exact bound/tie handling, followed by matched
supported completion/decision controls, with no automatic kernel installation,
training, UI propagation or policy change.

A final24-call control uses the current protected product default (full-root,
cold64MiB TT, absent features, q0), versus bare lexical AB over the same Native
state, on six existing roots at one second with two reversed pairs. Product
completesD2 middle/D4 tactic/D5 promotion/D3 EP/D2 both generated; bare completes
D3/D4-5/D6/D3/D4/D3. All choices/PVs are legal and roots/history restored. Three
roots change moves (middle, EP, generated2000); depth or changed choices alone
are not utility. Reaggregation uses existing exposed finiteD4 rows only: tactic
and promotion remain regret0, bare EP100; product middle/EP and generated choices
lack matching labels and remain UNKNOWN. No new teacher call fills that gap.
This establishes a remaining supported scheduling/algorithm completion question,
not a reason to restore unsafe ON, replace the default algorithm or claim strength.


## Exact contender verification and finite-horizon cache contract —2026-10-10

The scoped `scripts/root_bound_diagnostic.py` is a Python root-selection
algorithm over complete state adapters, not a complete generic player. It tags
fail-soft child estimates relative to their input window. A narrowed contender
can replace the incumbent only after full-window exact verification in the
original shared time/node budget; interrupted verification leaves the incumbent
unchanged and the root iteration incomplete. Root canonical order is independent
of traversal. There is no TT, qsearch, reduction or new evaluator in this diagnostic.

Thirty-six completeD3 feasibility calls initially found no unsafe difference under
lexical interiors. The changed premise is reverse interior traversal:12 EP
root/interior-order cells then reproduce unsafe f1e2/report100/independent child0;
full and verified choose f1d3/100 throughout. Every PV is legal and parent restored.
The unchanged first result is retained, not reported as another defect. Toy true
and inferior ties, shared-cap interrupts and actual Native EP controls have17 tests.

### Executed C candidates versus blocked final product

These are distinct source/binary identities in the new purpose archive. First
candidate verifies every potential root replacement, skips TT probes in that
rescan, and refuses a root score contradicted by full PV replay. Its actual72
predeclaredD3 cells include5 warm64 internal errors; cold/TT0 controls agree.
The first fail-fast6 rows remain separately preserved; continuation completes the
original cells rather than extending a frozen comparison to obtain success.
Second candidate changes only score/bound cutoff eligibility from deeper-or-equal
to equal remaining depth, retaining different-depth move ordering: all72 cells
agree in complete root value and canonical action. A third metrics-only variant
adds actual contender work counters. Shared-cap interrupts inside EP/generated
rescans at2961/1550 nodes retain the previous completeD2 score/action/PV, with
true-tie and pre-cancel recovery controls (6 rows). Build and fresh imports succeed
for those three candidates; collection times are not matched-work speed ratios.

The final capability-tagged integration is a different build. Windows Application
Control blocks its fresh import. Its source/wrappers and failed deployment boundary
are archived; active C/Python product files and installedv4 were restored to the
reviewed base. Public root-windowON remains rejected and defaultOFF. No policy edit,
retrying alternate blocked binary, security bypass or final-build test claim.
The terminal-v5 candidate is separately unexecuted and not repaired by this work.
Archive build hashes identify actual observations; they do not attest that the
previously installed binary was compiled from a particular tracked source.

### Uniform finite depth is a control, not a universal engine requirement

Installed full-rootOFF warm-TT sequences D3,D1,D2,D3,D3,D1,D2,D3 on middle/EP/
generated2000 produce48 calls. TT0 matches finite references; warm64 has6 D2
mismatches. Middle finite V1=200,V2=-100,V3=100 demonstrates no monotone depth bound.
A deeper ordinary heuristic EXACT entry therefore is not automatically an exact
value or bound for the shallower horizon. Equal remaining depth is an isolated
control, not a sufficient all-rule proof: history, evaluation, q/extensions,
mate-distance and completed-bound semantics also matter. Dot's complete reply
adopts that distinction; detailed new TT-cutoff instrumentation remains deferred
at the final-build deployment boundary, rather than becoming a research blockade.

Pinned [Stockfish17.1 primary source](https://raw.githubusercontent.com/official-stockfish/Stockfish/sf_17.1/src/search.cpp)
uses non-PV depth/bound-based TT cutoffs alongside extensions/reductions. Inference:
its selective reported depth and our uniform noTT/q0 control have different
contracts. This is not a claim that deeper cache reuse is illegitimate or useless
in playing engines. Current warm64 results must be labelled cache/path dependent,
not uniform VD; relabelling alone does not fix a score/action inconsistency.

Replaying all48 saved warm-depth PVs, without a new search, also finds6 literal
leaf/report mismatches on the same warmD2 cells. Returned legal PVs have exactly
2 moves: middle report0/leaf-100, EP100/0, generated2000 mate-in3/nonterminal-200.
All42 remaining rows match. This is an observable distinction between a cached
estimate and its truncated illustrative line, not a proof that the selected
move is strategically bad. A warm report/PV must not be called a finite-horizon
or mate witness; cached selective semantics require a separate stated contract.
The first replay mistook public dataclass records for packed integers and failed
before output; source/failure retained, corrected matching uses the actual legal
public Action records. No oracle expansion or product TT prohibition follows.

A12-cell installedOFF PV-leaf replay check matches the reported selected-line
values on TT0/cold64. Four difficult roots cap atD3 despite requestedD4; tactic/
promotion completeD4. Legal selected-line agreement is neither all-defense
exactness nor broader candidate correctness.

### Completion, conversion and frontier costs

Forty-eight Python full/verified calls use the same4096 recursive-entry cap or
1second with100000-entry/D12 fuse, two reversed orders and unchanged material.
Fixed4096 verified is deeper on tactic,EP and both generated roots; EP changes
f1e2 to f1d3 and generated2000 changes nonmate to mate at that finite horizon.
Timed promotion/generated2000 are consistently deeper; tactic/middle vary across
repeats. Depth and changed choices are not strength. Reusing existing finiteD4
labels only yields16 matched choices (tactic/promotion); all32 unmatched choices
remain UNKNOWN. No teacher, holdout or reference budget is expanded.

A48-cell2x2 on EP/two generated roots crosses full/verified with bare/2048-entry
immutable syntax reuse. Within each algorithm all fixed signatures, candidate
records, work and PVs agree. Mean fixed wall reductions are10.7–34.4%; none of24
timed cells adds completion within its paired algorithm. Four fixed4096 profiles
show direct C terminal, guarded frontier and checked transitions dominate once
conversion disappears. Inclusive profile times are not added; instrumented time
is not production throughput.

The existing transient-frontier API changes only unused trial child-key/history
construction. Real `make_checked` pushes and exact full-history terminal queries
remain. Three every-childD2 audits check813/1173/1988 complete states, with
parent restoration and matching authority/frontiers/material. Twenty-four fixed/
timed cells preserve every fixed signature; fixed wall drops28.5–42.0% relative
to cached guarded frontiers. Generated2001 completesD4 instead ofD3 in both1second
pairs; EP/generated2000 are unchanged. Choices remain unchanged and generated
utility remains UNKNOWN. This supports a scoped execution improvement, not a
full-domain product adoption. No merged terminal/frontier API exists: replacing
terminal authority with legal availability would omit history/adjudication rules.

A further128-entry successor cache retains exact parent capsule/action keys and
complete children, preserving the same3974 audited states and fixed signatures.
It saves only27/50/95 actual checked pushes out of4093 and worsens wall on all
three roots. Both timed pairs retain completed depth. Reject that capacity for
this use; no outcome-driven larger-cache tuning. Native position53920-byte size,
retained capsule count and Python shallow bytes are recorded; memory/resource
tradeoff is explicit rather than called an equal-memory improvement.

All exact sources, original failures, outputs, compatibility notes and validation
are routed by [the root-bound index](data/root_bound_20261010.json). It excludes
binaries and raw Slack/account/user-private records. Active safe product and
frozen UI branch are separate from these isolated prototypes.


### Corrected identical scheduling still separates backend costs

Fifty-two controls cross the same verified root algorithm, lexical interior and
lexical canonical root labels with existing Chess middle/promotion/EP and Shogi
tactic/drop. Core and specialized libraries receive identical material/terminal
scope; Chess also receives Native transient+immutable syntax. Native Shogi
no-move-loss remains unsupported, so no altered rule is substituted to obtain a
Native timing.26 fixed4096 calls have identical per-case selected action/value,
PV labels, work and contender records. Mean Chess Core/Native wall ratios are
about5.57–5.95; Native/specialized about2.34–2.41. Shogi Core/specialized is about
27.4 on tactic and59.3 on drop. These are scoped backend comparisons with an
identical algorithm, not universal speed factors or mature-engine strength.

|Case|Core completed depths|Native transient completed depths|Specialized completed depths|
|---|---|---|---|
|Chess middle|2,3|3,3|4,4|
|Chess promotion|5,5|6,6|7,7|
|Chess EP|3,3|4,4|4,4|
|Shogi tactic|2,2|unsupported|4,4|
|Shogi drop|2,2|unsupported|4,4|

These26 resource-capped calls use1second AND100000 entries/D12, not pure equal-time
runs: specialized Shogi hits the100000-entry cap at roughly0.51/0.80seconds.
Reported wall includes legal PV replay outside the search cap, recorded separately
by the runner's scope; small Core deadline overshoots remain visible. EP changes
b1c3 to c2c3 atD4 on Native/specialized; other moves/depths are not automatically
useful decisions. All52 choices match existing finiteD4 labels: timed EP regret100
for Core
versus0 for Native/specialized, and Shogi drop400 versus0. These finite-reference
differences do not establish game value or strength; no references are enlarged.
The initial runner used the unsupported catalog
name `shogi` after36 completed Chess rows; source/failure/output are preserved.
Continuation fixes only the builtin name and runs the original16 Shogi cells,
retaining all36 previous rows. It is not a rerun or added sample cohort.

Decision: corrected scheduling and tested cheaper Native frontiers reduce part
of the supported gap, while specialized rule execution remains independently
material. Next isolate the remaining terminal/state cost or verify deployment on
an approved runtime; do not substitute another chess-specific solution for the
generated-rule target or restart price/learning work merely at this milestone.

## Terminal/frontier, dispatch and scheduling — 2026-10-10

Evidence: `data/terminal_frontier_20261010.json` indexes the source-pinned purpose
archive. Scoped exposed development, same installed v4 binary; final C candidate
remains blocked/restored. No teacher extension, UI change or strength claim.
Initial algorithm/factor timers accidentally overlapped: entire first sets stay
archived/ineligible;120 formal algorithm cells and24 factor calls/12 profiles
were rerun serially with the same declared caps/orders. Negative prototypes and
earlier packed-action/source-prefix failures remain, rather than favorable subsets.

Native terminal C calls account for38–43% of three instrumented4096-entry totals,
while only331–413 nodes request full frontiers. Availability is insufficient to
reconstruct history/repetition/perpetual/automatic/max-ply adjudication. Core
terminal-prefix reuse preserves3974 full states and24 decisions but slows fixed
calls5–11%; reject. Six coldD3 Native caller profiles show tiny returned feature
cost; replay/packing matter relatively on the very short promotion root. Clarify
kernel versus caller time and estimated score/PV contract, without an unused API.

The simplest inline Core budget dispatch removes a second function call while
retaining every semantic poll, current node cap/live deadline/cancellation and
abort precedence.40 installed q2 fixed1024 controls cover8Chess/Shogi and2generated
roots: exact action/score/PV/non-time statistics agree; mean local reductions
4.49–12.60%.18 interactive variants/9 actual count-triggered cancellations and
24 externally requested timed cancellations retain restoration. Post-repair
maximum observed request-to-return1.108ms; instrumentation/timer scheduling and
small cohort preclude an SLA.101 focused regressions pass.96 common-time calls
(48 matched pairs,1/4sec,q0/q2,1million fuse) mainly retain decisions/completion;
EPq0 at4sec reachesD4/c2c3 versusD3/b1c3 in both reversed pairs. This is scoped
completion evidence; do not interpret depth or changed choices as playing gain.

Compiled-lifetime compatibility atlas is a changed premise from earlier rejected
per-constructor filtering.3974 full-state audits/9928 all-square pseudoattack
queries agree;36 calls preserve fixed signatures. Only1.27–1.97% fixed savings
and no timed completion gain: defer integration. Post-repair two disjoint profiles
put geometry query bodies at6.375%/2.213% of instrumented total, giving only
1.068x/1.023x perfect-removal ceilings for those bodies. Not all attack cost,
not deployment throughput, no inclusive-span summation or cache expansion.

Thirty-two Shogi paired resource cells expose100k premature stop;500k consumes
the1second but leavesD4/choice unchanged on tactic/drop. Original52 cells stay.
The120 crossed algorithm curves distinguish minimal Core/Native/specialized,
product Core/Native legality and full Native. Initialization, caller/kernel and
external PV validation remain separate; numeric node units differ. Thin AB polls
at visits, product inside semantic units. TT/order factors retain finiteD3 scores
but ordering and cancellation differ; no single isolated algorithm-speed claim.

Existing Native trace is unsuitable for cheap PV phase attribution:8 coldD3
OFF/ON calls keep outputs/work but trace costs3.29–4.09x caller time, retaining
4096 rows versus25824/41620 raw events.188719802bytes of JSON are preserved in
the compressed archive; feature materialization/recording cost is reported, not
free instrumentation. No phase/re-search tag or unique-state guarantee. Keep OFF.
Twelve fixedD3 full/minimal calls and six cumulative minimalD1–D3 calls motivate
further scheduling diagnosis: cumulative minimal1944/2027/2112 entries versus
full25824/41620/68505, caller about0.14/0.12/0.18 versus0.90/1.03/1.50sec.
Counts, tie/order and PV contracts differ. The single-depth runner also uses a
different canonical key; it does not isolate iteration overhead. Native mate
scale1e8 versus diagnostic1e9 requires distance-aware interpretation. These are
same-backend scoped scheduling observations, not proof that PV replay alone
explains the gap. Source-only full-window explanation stays a hypothesis.

Dot's complete fresh request reply was read/reconciled: adopt removable-cost,
disjoint-time and cancellation-latency limits; no independent rerun or operating
policy change. Next align cooperative budgeting in the diagnostic or measure one
bounded attack-dispatch mechanism. Phase-specific C counters require supported
execution first; no retry of the blocked binary or security workaround.


## Cooperative budgets and phase attribution, 2026-10-10

72 serial controls show that adding genuine internal semantic node/cancel/time
checks removes some thin-caller completion advantages. Current Native optional
generation/ordinary-transition counters are now available at the high-level
result; missing fields are None. Their definitions exclude caller validation and
nested terminal probes. They do not equal unique positions or another engine's
node unit. Completed q0 entry accounting distinguishes selected-PV replay from
full-window dispatch, and actual interrupted negative residuals forbid applying
the simple residual formula to cancellations. Cold64 exact models put replay
subtree shares at about1-7%; TT0/rootOFF never enters that replay branch.

Matched Core window controls retain fixed-work savings, but no1/4second depth
gain. Product TT/order-off D3 still costs about0.9-1.0sec on the two generated
roots. A shared-root verified-contender bridge with live semantic budgets and
caller replay takes0.94-0.97/1.16-1.17sec, retaining scores, versus6-7sec for the
all-root-full-window model. Retain product; node reductions alone do not justify
replacement. Synthetic equal-bound ties demonstrate that root/leaf agreement
does not certify optimal PV responses. Scoped strict-tie and selected-response
checks are retained without a blanket TT/interruption guarantee.

Captured legal-frontier labels are an explicit diagnostic alternative to replay;
default replay and product validation stay. Owner-only source indexing and Core
Runtime caller validation are deferred after modest scoped measurements. No UI,
C build or workflow change. The complete detailed report, failed harnesses,
source pins, adverse/capped cells and measured cancellation tails are in
data/cooperative_budget_20261010.json -> its evidence.zip/report.md and
phase_contract.md. Dot's complete fresh-root review was assessed and applied;
no independent advisor execution is claimed.
