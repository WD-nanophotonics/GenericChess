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
policy and the transient static-ordering view. Larger cache capacity was rejected; normal-output parity of the view does not establish identical digest/allocation failure handling. Small learned evaluators
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
