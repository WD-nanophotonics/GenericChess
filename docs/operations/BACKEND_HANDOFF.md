# Backend handoff from sandbox

PRIMARY maintains the backend on sandbox. The user maintains UI Test and its
frontend integration on the other computer. DEV_AUX validates in its own
sidemission checkout. Import backend changes from sandbox as needed; no automatic
UI branch merge, replacement or Agent-maintained UI copy is required.

Backend source pinned at 7b988c9f247fd3eb96ca17daedf28e5c4d93b3cd includes the
tested q0 repairs described below. Later commits must be assessed by their
actual tests and supported parameters; newest does not mean every prototype
is enabled or every evaluation configuration is equally strong.

| Public entry | Actual execution and activation | Boundary |
|---|---|---|
| AlphaBetaPlayer.choose_action(session, limits, cancel_token=...) | Complete Core search with existing q4/hard8 defaults, TT, progress and cancellation. Native semantic legality is requested by default where supported. | Native legality acceleration is not a claim the whole search is Native. UI may retain this complete player. |
| Native SemanticSearchEngine.search(session, limits, root_window_pruning=True) | Explicit exact-root finite q0: set quiescence_max_depth=0, quiescence_hard_max_depth=0 and an explicit max_depth. Match a supported semantic compiled ruleset/native rule product and fixed evaluator inputs. | Integer threshold confirmation, exact-root bound handling and full selected canonical reconstruction are enabled only in this mode. Full history/witnesses and evaluator/root-offset/TT context remain required. |
| Existing ordering_checkpoint/min-depth option | Explicit ordering profile and ordering_min_depth=2 were used in the published finite cost controls. | Optional configuration, not a universal optimum or a default/strength guarantee. |
| Core q4 versus Native q0 | Distinct evaluations/horizons; preserve requested parameters and report actual backend. | Native q4 is unsupported; do not quietly run q0 for a q4 request. No claim q0 is stronger than q4. |

Native requires building the current optional extension on the target computer;
do not copy a research binary or venv. The repository's normal package/build
instructions and scripts/build_native_zig.py are the supported source build
routes, with an installed compatible compiler/runtime. Without the extension,
the existing complete Core player remains available. A local compiled test
on the work machine does not prove a different computer has its dependencies.

Native output is SemanticIterativeSearchResult, not an implicit UI
PlayerDecision. A UI integration must handle returned Action, declarations,
termination cause, legal fallback, cancellation and stale-snapshot commit under
its own existing controller contract. The optional q0 repairs do not provide
a new declaration/legacy-generated UI adapter. Standard supported semantic
engine and actual GameSession tests are backend evidence; frontend integration
belongs to the user. Preserve declarations/drop/promotion/aux/history rather
than removing them to admit a backend. Unsupported rule/evaluator combinations
must remain explicit or use an explicitly selected complete Core route.

Validated at the pinned source: 44 focused production regressions after the disabled-cache allocation repair; saved
16000-node case oldD3 versusnewD4/fullPV; finite score/action/PV comparisons;
integer tie/one-point boundary checks; budget abort and same-TT recovery.
Details/immutable inputs: Q0_THRESHOLD_CONFIRMATION.md and its indices.
The controls are finite/exposed, not a full-domain, independent strength or Elo
acceptance certificate.

Explicit ordering_cache_enabled=False now avoids allocating the idle ordering
table (11,108,360 bytes in the measured build). Default True is unchanged.
ordering_cache_allocated_bytes reports table allocation, not RSS or active
capacity; None indicates older kernels or a search that did not start.
Rebinding, clearing TT, cancellation and retry are tested.

Persistent iterative Native search now reports child-identity execution failures
as internal_error and retains the last completed action/score/PV. An error result
is not a claim the requested horizon completed. Actual serializer fault
regressions and full active tests cover the repaired path; standalone Boolean
helpers and arbitrary OOM/corrupt-state handling are not universally certified.
See research/NATIVE_EXECUTION_FAILURES.md and SEARCH_SPEED_EVIDENCE.md for scope.

Still private, not enabled: root-only canonical ordering (observed depth loss),
immediate-terminal proof stop (different caller goal), altered q4 completion
policy. Larger cache capacity and the no-gain ASCII-run key candidate were rejected. Small learned evaluators
remain separate research; no UI/default training model has been promoted.

LOCAL_UI_SEARCH_TEST.md describes a historical work-machine browser/worker test,
not a portable Git-only delivery or the user's current recommended integration.
Its ignored launcher, dependencies, overlay and binary were not pushed; the
published bridge fragment alone cannot reconstruct that exact local bundle.
The current handoff is these tested backend sources and explicit contracts,
with the user integrating their own UI Test. No original user UI, private saves
or raw Slack/account data is copied into sandbox.

Dot's completed-thread supplements were read and reconciled on2026-10-12.
The compatible backend/UI boundary is adopted; quoted other-chat user context
does not expand branch, publication, master-promotion or machine authority.

Guarded discarded static-material ordering is now enabled only by existing
explicit ordering_cache_enabled=False with no dynamic/spatial/localized/compact
or policy ordering consumer. It retains full parent history/postconditions and
required nested failure propagation; recursive/TT/PV children keep full identity.
Deleting an unused digest removes its failure opportunity deliberately, without
claiming identical OOM trajectories. ordering_material_view_trials exposes actual
attempts (None for older/not-started kernels). Exact decimal key formatting keeps
canonical bytes; no cache/default/evaluation/UI policy changes. See
research/MATERIAL_ORDERING_VIEW.md for actual local costs and resource limits.

Fixed/probe backend correction2026-10-13: normal dict shape is unchanged, but
returned canonical moves now genuinely realize the complete reported value.
Required child identity failures raise RuntimeError rather than returning an
apparently completed empty/material result. Direct full checked children retain
all effects/aux/history/postconditions; no new public trusted API is needed.
The original Shogi fixed/probe policy gate remains explicit. Persistent Native
and Core/UI routes are separate; no frontend branch or default was modified.
Final2280 full regressions and preserved old-fails/new-passes witnesses qualify
this finite repair. See research/PACKED_ORDER_AND_FIXED_SEARCH.md.

## Terminal identity update2026-10-13

Rebuild the optional Native extension with scripts/build_native_zig.py to get
semantic_fixed_depth_terminal_winners. Payload remains4; old kernels without
that capability keep rejecting continuous-check fixed/probe calls. The fixed
reference searches board/drop actions with complete terminal winner/history,
not optional declaration decisions. Persistent search retains declarations.
Its internal nonroot checked-child digest reuse preserves canonical full SHA,
root revalidation, exact history, prices, TT/ordering and required error paths.
There is no public result schema or UI/default policy change.2286 active tests
pass on the final source; current finite resource/cost evidence and limitations:
../research/CURRENT_CALLER_TERMINAL_IDENTITY.md. UI Test remains user-owned;
PRIMARY only publishes backend changes on sandbox, with reviewed later merges.

## Scalar attack execution2026-10-13

Rebuild the optional Native extension from sandbox for source-first scalar
attack traversal. Public payload/version/result/identity and required-error
contracts are unchanged. Capture-eligible pseudo-attacks still include empty
and friendly targets; selected-action check witnesses keep separate predicates.
A duplicate Python typeclass import is removed without cache or class change.
Independent SemanticSearchEngine remains q0; Core AlphaBeta supplies q4 with
Native legality/availability. Do not infer independent Native qsearch support
from provider labels.2,298 final active tests pass without Native skips;
local fixed/resource limits are in ../research/SCALAR_ATTACK_TRAVERSAL.md.
PRIMARY sandbox backend only; UI Test stays user-owned on the other computer.

###2026-10-13 rule lookup delivery

GENERIC_RULE_LOOKUP.md records tested mechanical capture-selector and sorted-source
lookup plus a small Native legality payload encoder change. Numeric payload/v4
and Python entry signatures are unchanged, but C Rules internal layout changes:
rebuild ALL Native sources via scripts/build_native_zig.py and restart the process;
do not mix old capsules/objects with new consumers. Final2,314 installed/source
checks pass. Coreq4 remains supported through Core; independent Native search is
q0. Search/evaluation/ordering/TT/UI policies are unchanged. PRIMARY publishes
sandbox backend only; user-maintained UI Test integration remains separate.

## Consecutive-action history cache repair —2026-10-13

Backend commit f88c0930eed09f55e12d2f909704d868a0b665d8 fixes wrong TT reuse
between complete legal histories with identical boards but different future
consecutive-action adjudication. Only those policies add exact action signatures;
plain-rule cache reuse and public position/repetition SHA stay.2,319 active tests
and89 publisher checks pass. This is Python-source only; restart the downstream
Python engine process after taking this backend commit. It adds no new Native ABI
rebuild requirement; earlier Native-layout commits still require their documented
complete C rebuild. UI Test remains user-maintained, with no automatic integration.
Private shared-check transport and public PVS/q-ordering experiments do not change
engine defaults. Scope, negative completion results and restored temporary-test
validation: ../research/CORE_CHECK_TRANSPORT.md; correctness witness/tests:
../research/HISTORY_ACTION_CACHE.md.

## Mixed q ordering opt-in —2026-10-13

`SearchTuning(use_ordered_qsearch=True, use_ordered_qsearch_in_check=False)`
orders ordinary q nodes with the existing orderer and keeps checked evasions
lexical. The appended field preserves old positional fields; old all-q flags and
default lexical behavior remain. This Python-only change needs consumer process
restart, not a new Native rebuild beyond earlier documented layout changes.

For the measured optional Native terminal route, use the already supported
`AlphaBetaPlayer(..., use_native_semantic_availability=True, tuning=tuning)`;
no scripts helper or private function replacement is required. Core still owns
complete history/adjudication, and unsupported providers retain Core fallback.
The flag is default-off and custom availability callbacks take precedence.
These measurements use the Native semantic evaluator and fixed rule-derived
weights; a different evaluator is a different condition.

Four real public-flag calls reproduce helper full choices/tree work, with
actual Native availability counters. Without the optional callback, the measured
1455 mixed16s horizon gain disappears. The new four-root PVS/mixed plane adds no
retained-depth/action gain; every negative/unavailable result is retained.
Final2,328 active checks pass, including cancellation, implicit type effects,
quiet checking drops and the hard checked boundary. No UI Test/default/PVS
policy change or independent Native q4 capability follows. Complete activation,
finite limits, actual before-source parity and archived evidence:
../research/MIXED_Q_PUBLIC_API.md.

## Explicit child-check input option2026-10-13

AlphaBetaPlayer now supports use_native_semantic_check=False (default) and
generic readonly check_provider(position, side, checkpoint=...) -> bool | None.
To use the measured one-use state import, explicitly request both
use_native_semantic_check=True and use_native_semantic_availability=True.
Both use existing Native functions; no new Native ABI/build feature is required.
Unsupported providers retain Core; required errors propagate. Core still owns
complete actual history, terminal precedence, declarations and checked commits.
Do not expose this implementation option as a new UI task or silently enable it.
Check-alone transport lost cost; combined actual consumers saved locally1.5–5.1%,
while fresh fixed costs were mixed and equal-time completed horizons unchanged.
Default/UI/PVS/price policy stays.2,341 active checks/45 focused pass, candidate
entry-cancel failure and same-object retry fixed before publication. See
research/CHECK_INPUT_HANDOFF.md and data/check_input_handoff_20261013.json.


2026-10-13: Core push membership reuses its already complete validated semantic
binding map, with original tuple handling for pass/legacy/unhashable inputs.
No consumer activation, new option, Native rebuild or UI integration is required.
Current full2349 and focused154 qualification includes value-equal reconstructed
EP/promotion/drop actions and full history/cache restoration. Local fixed-work
savings1.90–5.10percent are conditional; resource curves show no deeper retained
decision. Evidence: research/CORE_BINDING_MEMBERSHIP.md.

2026-10-13: square_to_index avoids temporary BoardShape only for exact positive builtin int. All other extent/error behavior stays;2356 tests pass. No option/Native rebuild/UI work required; consumer process restart loads the Python change. Private prefix-free incoming schedule is research evidence only, unavailable as a product flag. Native20-board remainsunsupported, complete Core fallback retained. See research/COLD_RULE_COORDINATE.md and PREFIX_FREE_INCOMING.md.


2026-10-13 backend addition: the compile-owned endpoint fallback automatically
accelerates Core scalar attacks only when the original incoming metadata is absent.
Its262144-row bound declines to the complete old executor; no public searchflag
or frontend change.2398 active checks and48fixed publicCore/Native q0/q4 parity
qualify this path. Nativeboard<=16 remains; q4 hardcheck limits and existing
defaults remain. ReservedID generation repair affects boards>=23; original<=22
seed namespaces unchanged.24Core twoD0/node256 choices actually submit, not a
strength/completeNative claim. See research/COMPILED_ENDPOINT_FALLBACK.md.


2026-10-14: complete Core SearchPathRuntime binding materialization uses an
internal full-frontier intent with transaction-local S3 observations.
Other invariants/S4/history/errors/stops and all unsupported guard/source routes
remain complete; existence/provider/cache paths stay. A guarded unused legacy
attack source-coordinate allocation is removed without score/weight changes.
Take the complete backend commit and restart Python; no new Native ABI/build
feature, public UI flag or frontend work is required. UI Test remains user-owned.
Final2,429active tests and200actual calls qualify the finite measured scope;
fixed-cost improvement is not retained-depth/strength improvement. See
research/S3_FULL_FRONTIER_INTENT.md and its explicit scientific archive.

## 2026-10-14 Core work diagnostics

PlayerDecision appends optional nullable runtime_pushes, runtime_pops and
runtime_depth_balanced. AlphaBeta reports already recorded successful Core
runtime operations after unwind, including q classification/root probes.
They exclude failed pushes and S3 trials; nodes/qnodes and budgets keep their
existing meaning. None means not reported, including other player backends.
Existing positional constructors keep their order. Consumers may ignore or
show these diagnostics; no UI/Native/default policy change is required.

## Generic root terminal wins —2026-10-14

AlphaBeta root scans now recognize any Core-authoritative terminal whose winner
is the root side, including stalemate-loss and history-dependent continuous-check
loss of the opponent. A previously discovered win could return score0/emptyPV
as root_scan_fallback when the next scan hit its budget. It now retains the
winning score/one-actionPV/root_immediate_win, as checkmate already did.
Draw terminals, root declaration precedence, legal fallback and cancellation
keep their existing contracts. Six actual draw/loss/history regressions plus
Core/actual Native-query controls cover this correction. This is Python source;
restart a consumer to load it. No new Native ABI, private C reader deployment,
q-policy default or UI maintenance is included. Scope/results:
../research/Q12_COMPLETION_AND_WORK.md.


## 2026-10-14 utility totals and completed root wins

Python search/reference caps only total static utility at existing10M; raw
evaluator/profile values remain available. Core terminal/declaration priority
stays. completed_root_win can retain a completed positive root child after a
later abort. termination_reason remains real node/time/cancel; completed_depth
remains last complete uniform iteration, not the interrupted depth. Its q policy
belongs to that retained proof; PV can omit q continuation. No default q4/hard8/
MDP/Native/Core/UI changes. Integrate tested sandbox backend through the existing
user-maintained UI lane; no UI copy is published. See GEOMETRY_PREFIX_AND_DROP_GOAL.


## 2026-10-14 neutral declaration correctness and optional inputs

Python AlphaBetaPlayer now includes qualified NO_CONTEST as a zero-value
defensive declaration in main/q/reference search; the actual declaration
identity survives warm TT. Callers continue to use choice_kind/declaration
and GameSession.declare, including action=None. WIN priority, RESTART preference,
action ties, stops and existing result_source/depth/q metadata remain.
Code fix932f03b268c2eecd4e3347219ded566d89e8872a passes2502 active tests.
No Native ABI, default flag or UI change accompanies this fix.

The existing explicit use_native_semantic_availability/check options have
finite full-state transfer and1sH3 evidence in
../research/ROOT_WIN_DECLARATIONS_AND_NATIVE_INPUTS.md. A requested backend is
not actual execution: unsupported EP roots retain Core fallback. Private C
payload prototypes are not installed or a consumer requirement. UI Test remains
user-owned; this is backend delivery only.
