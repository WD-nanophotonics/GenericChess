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
