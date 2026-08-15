<!-- Gmail provenance
message_id: 1a003e9312f9da08
thread_id: 1a003e9312f9da08
subject: GenericChess — F21: Production Native Legal-Action Routing + Fail-Safe Search Integration
from: W D <icywoods.1@gmail.com>
to: icywoods.1@gmail.com
received: 2026-08-15T05:33:28+00:00
attachment: GenericChess_F21_Production_Native_Legal_Action_Routing.md
attachment_id: ANGjdJ_m1-pdp0xaQCHleGz9RGO_lcYRUeeRtNG0vLZtQp8ISfPi1KbIjD06RaU5zcgeZELB21TeVUtC4HW-_axgE3jmTServhFKoajnXRL5qvRQvv0UmztFznce8BUtMPhpLx1cctaoFOEzNxAzOvX-cO4hRbYTQFfh1PLV69NEybxrVDU80as9CBOGjojdyBgMukmQR-TVv_gugmom5K_JG60S41hDQBTNOkPARvmTSoMwCbqNfJ9AGq_cx2u0QTuqGoilHBWEOIUcyjhPQP5V016m_3X3_W4RVZUmzRxesxhCe3kBaS8wvgNldQcmpOovGiU7QgcdyxQXKJmsIEv9kxceNvSmTt-akqMw78sZVMVy-sdnmVu36wipNEowi3kzVmfr6Wu8XMd2CIGZ
attachment_bytes: 26542
fetched_at: 2026-08-15 Asia/Tokyo
processing_state: complete-authoritative-attachment
-->
# Gmail record — GenericChess F21

## Gmail body (complete)

# GenericChess — F21: Production Native Legal-Action Routing + Fail-Safe Search Integration

## 0. AUTHORITATIVE TASK — EXECUTE NOW

This is the authoritative F21 task for `WD-nanophotonics/GenericChess`.

F20 closed as:

```text
F20_RESULT = LEGALITY_KERNEL_PASS
H20B_RETAINED = true
TRANSIENT_NATIVE_LEGALITY_KERNEL = PASS
STANDARD_SHOGI_ORDERED_LEGALITY = PASS
GENERIC_ORDERED_LEGALITY = PASS
BINDING_BRIDGE = PASS
PYTHON_CHILD_TRANSITION_BRIDGE = PASS
ONE_SHOT_ROUTING_GATE = PASS
SEARCH_SHADOW_PARITY = PASS
Profile A end-to-end gain = 33.50%
Profile B end-to-end gain = 32.31%
SELECTED_NEXT_BOUNDARY = NATIVE_LEGAL_ACTION_ROUTING_DIRECT
PRODUCTION_SEARCH_ROUTING_CHANGED = false
```

F21 implements exactly that selected boundary.

Goal:

> Route production AlphaBeta semantic legal-action generation through the certified F20 Native transient legality kernel when the Native semantic ruleset is executable, while preserving Python `SearchPathRuntime` as the authority for position transition, history, terminal, repetition, TT identity, evaluator, search policy, and all non-semantic/unsupported fallbacks.

Successful result:

```text
F21_RESULT = PRODUCTION_ROUTING_PASS
```

If correctness or fallback safety fails: `F21_RESULT = BLOCKED`.
If correctness passes but final performance no longer supports default-on routing: `F21_RESULT = ROUTING_REVERTED`.

Do not begin F22.

---

## 1. GMAIL / INBOX PROTOCOL

Follow the repository-local GenericChess Gmail/inbox workflow.

Before implementation:

1. locate this F21 task using fuzzy GenericChess/F21 subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task under top-level `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. execute immediately.

Do not execute from subject/snippet alone.

---

## 2. BASELINE HARD LOCK

Required refs:

```text
origin/sandbox =
3b2f253d7bbb7ed16ff705206644a1d76ece6977

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three.

If sandbox moved:

```text
BASELINE_MOVED
STOP
```

No reset, rebase, force-push, or master/chat modification.

---

## 3. F20 FROZEN AUTHORITY

Treat F20 as certified and closed.

Retained API:

```python
generic_chess.native.semantic.transient_legal_actions(
    native_rules,
    packed_position,
) -> tuple[int, ...]
```

It returns exact canonical ordered S0–S4 actions and performs zero candidate-child canonical-key/history work.

F20 realistic route included:

```text
Python state payload build
Native position pack
one Native S0–S4 call
packed-action decode
public action projection
exact binding reconstruction
```

Measured:

```text
median one-shot speedup = 4.7933x
median saving = 4127.98 us
40/40 Standard Shogi positions faster
max Native legality latency = 584.04 us
Profile A gain = 33.50%
Profile B gain = 32.31%
search logical parity = PASS
```

Do not reopen the F20 kernel architecture.

---

## 4. CURRENT PRODUCTION SEARCH CONTRACT — FREEZE

Current semantic search contract:

```text
SearchPathRuntime.legal_actions()
    -> SemanticEngine.iter_legal_action_bindings()
    -> cache:
       _legal_cache
       _bindings[public] = (semantic_action, binding)

SearchPathRuntime.push(action)
    -> membership in legal_actions()
    -> semantic_action, binding = _bindings[action]
    -> Python SemanticEngine._transition(...)
    -> Python runtime history/hash/terminal/TT authority
```

F21 must preserve this push contract.

Native must not become child-transition authority.

---

## 5. HARD ARCHITECTURE RULE — CORE REMAINS NATIVE-UNAWARE

No file under:

```text
generic_chess/core/
```

may import `generic_chess.native`.

No Native capsule/rules object may be stored directly in Core state.

A Core change is allowed only if it introduces a generic Native-neutral provider/callback boundary.

Preferred concept:

```python
legal_binding_provider(position, ply_count, checkpoint)
    -> iterable[(public_action, opaque_binding_payload)]
```

Core must not know the provider implementation.

If correct production routing requires Core Native awareness:

```text
CORE_NATIVE_BOUNDARY_VIOLATION
STOP
```

---

## 6. REQUIRED INTEGRATION ARCHITECTURE

Preferred architecture:

```text
AlphaBetaPlayer
    |
    | once per player/ruleset
    v
NativeSemanticLegalityProvider.try_create(compiled)
    |
    +-- Native unavailable / unsupported -> None
    |
    +-- executable semantic rules
            -> compile Native semantic rules once
            -> precompute ID maps once

run_root_search(...)
    -> SearchPathRuntime.from_state(
           ...,
           legal_binding_provider=provider_or_none,
       )

SearchPathRuntime.legal_actions()
    +-- cached -> cached
    +-- semantic + provider -> provider result -> _legal_cache/_bindings
    +-- otherwise -> existing Python SemanticEngine path
```

Exact names may differ.

---

## 7. CORE-NEUTRAL PROVIDER CONTRACT

If a provider hook is added to `SearchPathRuntime`, define it exactly.

Preferred private contract:

```python
provider(
    position: Position,
    ply_count: int,
    checkpoint,
) -> tuple[tuple[Action, object], ...]
```

For the Native semantic provider the opaque value is exactly:

```text
(semantic_action, binding)
```

Requirements:

```text
canonical order preserved
no duplicate public actions
binding for every action
no extra binding without action
provider called at most once per uncached runtime position
cache invalidated on push exactly as before
cache restored on pop exactly as before
```

Provider must not mutate runtime position/history.

---

## 8. DO NOT BYPASS `SearchPathRuntime`

Forbidden production shortcuts:

```text
search.py replacing only its local actions list
AI layer mutating runtime._legal_cache/_bindings externally
production monkey-patching/subclass global swapping
Native legality followed by Python runtime.legal_actions anyway
```

F20 audit monkey-patching was test-only.

---

## 9. PRODUCTION NATIVE LEGALITY PROVIDER

Create a narrow module preferably under:

```text
generic_chess/ai/alphabeta/native_legality.py
```

or another AI/native integration location outside Core.

It may import Native and Core semantic/action types.

It owns:

```text
NativeSemanticCompiledRules
precomputed type/pattern/geometry maps
pattern_by_id
state-only payload conversion
packed-action direct decode
public action projection
binding reconstruction
fallback/counters
```

No unbounded global mutable singleton.

---

## 10. COMPILE NATIVE SEMANTIC RULES ONCE

Do not compile Native semantic rules inside `legal_actions()`.

Compile once per `AlphaBetaPlayer` / fixed compiled ruleset.

Creation logic:

```text
native disabled -> provider None
native extension unavailable -> provider None
no SemanticEngine -> provider None
compile unsupported -> provider None
native_executable false -> provider None
otherwise -> provider active
```

Optional Native acceleration must never prevent normal Python search setup.

---

## 11. PRODUCTION ENABLEMENT POLICY

Add an explicit AlphaBetaPlayer option:

```python
use_native_semantic_legality: bool = True
```

or an equivalently explicit backend option.

Required default: `True`.

Behavior:

```text
True + supported Native semantic rules -> Native legality route
True + unavailable/unsupported -> Python fallback
False -> force Python legality route
```

This is an execution backend choice, not a chess heuristic. Prefer not to overload `SearchTuning`.

---

## 12. STATE-ONLY PAYLOAD — PRODUCTION IMPLEMENTATION

Promote/refactor the F20 state-only logic into production-quality code.

For every current Python position include exactly:

```text
side
ply
board:
    base type index
    current type index
    owner
    promoted
hands
aux_state
```

Exclude:

```text
history
repetition
external position SHA
terminal
TT identity
```

Requirements:

```text
precomputed type map
no per-call map rebuild
exact owner/type validation
fingerprint compatibility
no child SHA
```

Do not reuse an exact-history mirror payload if it computes history/SHA.

---

## 13. PACKED ACTION DECODE — NO PER-ACTION FFI

Do not call `semantic.unpack_action()` once per returned action in production.

Use direct Python bit decode of the frozen 64-bit layout, or one bulk decode if a clean bulk API already exists.

Precompute:

```text
type_ids
pattern_ids
geometry_ids
pattern_by_id
```

Then construct exact:

```text
SemanticAction
public SemanticBoardMove / SemanticDropMove
binding via _make_binding_from_action
```

No coordinate-only matching.
No first-match fallback.
No geometry re-inference.

---

## 14. EXACT BINDING RECONSTRUCTION

For every Native legal action:

```text
packed action
 -> exact fields
 -> SemanticAction
 -> exact pattern
 -> engine._make_binding_from_action(position, semantic_action, pattern)
 -> public action
```

Cache:

```python
bindings[public_action] = (semantic_action, binding)
```

Do not rerun Python S0/S1/S3/S4 in production.

---

## 15. PROVIDER FAILURE SAFETY

Separate two failure classes.

### Setup-time unavailability

```text
native extension unavailable
rules not semantic
Native compile unsupported
native_executable false
```

Behavior: normal Python fallback, no product exception.

### Operational failure after provider is active

Examples:

```text
payload pack failure
Native legality raises
invalid packed decode
ID index out of range
binding reconstruction failure
duplicate public action
```

Preferred production behavior:

1. provider has not mutated SearchPathRuntime;
2. discard partial Native result;
3. disable Native legality for the remainder of the current root search;
4. recompute current node with Python authority;
5. continue search;
6. increment fallback/error counters.

Do not mix partial Native and Python action lists.

Strict test mode may raise.

---

## 16. FALLBACK LOGICAL PARITY

Force operational provider failure at:

```text
root
depth-1 node
qsearch node
root tactical path
```

Compare against pure Python:

```text
action
score
PV
nodes
qnodes
depth
termination reason
TT probes/hits/stores/cutoffs
history/TT eligibility
```

Require exact parity.

---

## 17. CHECKPOINT / CANCELLATION CONTRACT

Native transient legality is one atomic call. F20 max was 584.04 us.

Provider must checkpoint at minimum:

```text
before payload/native call
after Native call
during Python decode/binding loop at bounded intervals
before returning
```

Requirements:

```text
pre-call cancellation observed
post-call cancellation observed before search continues
deadline bounded by one Native call + bounded decode chunk
node-only deterministic budget behavior unchanged
```

No C callback checkpoints in F21.

---

## 18. ROOT FIRST-ACTION / ABORT CONTRACT

Preserve:

```text
time_to_first_legal_action
root_first_action
root_scan_used_fallback
historical NO_LEGAL_FALLBACK behavior where applicable
```

Test:

```text
pre-cancelled token
tiny node limit
tiny wall-clock deadline
cancel during legality
provider exception during root legality
```

No empty or illegal fallback.

---

## 19. COMPLETE SEARCH-PATH COVERAGE

The single provider boundary must naturally cover every `SearchPathRuntime.legal_actions()` call:

```text
normal negamax
PVS null-window and re-search
aspiration re-search
in-check qsearch
non-check qsearch action source
root tactical scan
root fallback
```

Do not add ad-hoc Native calls in each search function.

---

## 20. LEGACY / NON-SEMANTIC ZERO-CHANGE

For non-semantic rules:

```text
provider = None
```

Existing legacy move generation remains unchanged.

No semantic Native compile attempt should occur.

Run legacy controls.

---

## 21. UNSUPPORTED SEMANTIC FALLBACK

Use at least one intentionally Native-unsupported semantic ruleset.

With default `use_native_semantic_legality=True`:

```text
AlphaBetaPlayer construction PASS
search PASS
provider inactive
Python legality used
result == forced-Python result
```

Do not weaken Native compile gates.

---

## 22. PROVIDER OBSERVABILITY

Add internal search statistics, without unnecessary public API expansion.

At minimum:

```text
native_legality_enabled
native_legality_calls
native_legality_actions
native_legality_seconds
native_legality_payload_seconds
native_legality_decode_binding_seconds
native_legality_fallbacks
native_legality_operational_failures
```

Use `SearchStatistics` if appropriate.

Do not expand `PlayerDecision` unless clearly required by existing reporting conventions.

---

## 23. NO EXTERNAL SHA / HISTORY WORK

For Native legality provider calls require:

```text
Native candidate child key computations = 0
Native history appends = 0
Python child external SHA computations unchanged from F20/F3
```

Do not call `position_identity_key()` in the provider.
Do not inspect public history to build the state-only payload.

---

## 24. BINARY-SIZE PROVENANCE AUDIT

F20 final Native build recorded:

```text
3,384,432 bytes
```

Earlier phases frequently recorded about:

```text
335,360 bytes
```

F21 must explain this discrepancy.

Record:

```text
current baseline build size
-O2 / --debug state
compiled source file list
debug/symbol section explanation if applicable
whether audit-only F20 code is linked
whether H20B duplicates major semantic code
```

This is not automatically a correctness blocker.

If large audit-only instrumentation or duplicate implementation is accidentally retained in the production extension and can be removed without altering certified behavior, clean it before final closure.

Do not trade correctness/performance for arbitrary size reduction.

---

## 25. H21 PHASE STRUCTURE

Use:

```text
E20 baseline
  -> H21A provider boundary + fallback integration
  -> H21B default-on production routing
  -> E21 closure
```

### H21A

May implement:

```text
Core-neutral provider hook
AI/native provider module
stats
fallback machinery
strict test mode
integration tests
```

Keep production default routing disabled until H21A gates pass.

Commit and push H21A.

### H21B

After authorization, enable default-on Native legality for eligible `AlphaBetaPlayer` search.

Commit and push H21B.

---

## 26. H21B AUTHORIZATION GATES

All must pass.

### G1 Core boundary

```text
Core Native imports = 0
Core Native objects = 0
provider contract Native-neutral = PASS
```

### G2 Standard Shogi parity

Use at least F20's 84-state corpus.

Require zero:

```text
count mismatch
order mismatch
action identity mismatch
binding mismatch
Python transition mismatch
```

### G3 Generic semantic parity

F20 10/10 corpus + focused S3/S4 fixtures PASS.

### G4 Fallback

Setup fallback and injected operational fallback PASS.

### G5 Search parity

F20 shadow routes PASS through the real provider architecture.

### G6 cancellation / interruptibility

PASS.

Any failure:

```text
H21B_NOT_AUTHORIZED
```

Do not enable production default.

---

## 27. PRODUCTION SEARCH PARITY

Compare:

```python
AlphaBetaPlayer(use_native_semantic_legality=False)
```

vs:

```python
AlphaBetaPlayer(use_native_semantic_legality=True)
```

Require exact:

```text
action
score
PV
completed depth
selective depth
nodes
qnodes
termination reason
TT probes/hits/cutoffs/stores where exposed
beta cutoffs
PVS stats
aspiration stats
qsearch stats
root tactical stats
legal action order
runtime history/repetition behavior
TT eligibility
child external key computation behavior
```

Ignore only elapsed time and Native provider timing/counters.

---

## 28. TWO-CONSECUTIVE-SEARCH TT REGRESSION

Because `AlphaBetaPlayer` retains TT across searches, explicitly test two consecutive controlled `choose_action()` calls.

Native legality routing must not change:

```text
TT generation
persistent hits
history-aware eligibility
collision guards
```

Re-run F3 TT/history-specific tests.

---

## 29. STANDARD SHOGI PRODUCTION PROVIDER DIFFERENTIAL

Use four frozen prefixes and deterministic sampled children.

At least the 84 F20 states.

For every state compare production provider output against Python authority:

```text
public action count/order
semantic identity
binding
Python child transition
```

Zero mismatch.

---

## 30. GENERIC IR-v2 PRODUCTION PATH

Run:

```text
cannon
castling
en_passant
nifu
uchifuzume
weird_0..4
```

through the production provider implementation.

Require provider activation when executable and exact legal/binding/child parity.

---

## 31. FINAL PERFORMANCE PROFILES

Re-run F20 Profile A/B under actual production integration.

### Profile A

```text
TT on
ordering off
qsearch max depth = 0
root tactical off
max_depth = 2
max_nodes = 512
fresh TT per measured run
no wall-clock limit
```

### Profile B

Current production/default tuning:

```text
max_nodes = 256
deterministic node budget
no wall-clock limit
```

For each four frozen semantic cases:

```text
1 warm-up
5 measured runs
```

Compare forced-Python legality vs default production Native legality.

No heavy trace in timing.

---

## 32. FINAL PERFORMANCE RETENTION GATE

For default-on production retention require:

```text
Profile A aggregate gain >= 20%
Profile B aggregate gain >= 20%
```

AND:

```text
at least 3/4 cases in each profile gain >= 10%
no semantic case stable regression > 3%
```

F20 measured 33.50% / 32.31%; F21 may pay some integration overhead but must remain materially strong.

If correctness passes but this gate fails:

1. revert default-on routing;
2. an opt-in route may remain only if both profiles still gain >=8% and no case regresses >3%;
3. final result is:

```text
F21_RESULT = ROUTING_REVERTED
```

Do not claim production routing pass.

---

## 33. PLAYER INITIALIZATION COST

Measure once-per-player provider compile/create latency.

Do not mix it into search-node elapsed time unless historically included.

If >1 s, document and consider only a bounded fingerprint-scoped cache in AI/native layer.

No unbounded global cache.

---

## 34. THREAD / REENTRANCY SAFETY

Audit sequential reuse and separate player instances.

Require:

```text
no mutable per-call action buffer stored globally
no cross-search provider contamination
no shared partial result
```

Production route must use non-audit `transient_legal_actions`, not audit entrypoints.

Do not claim unsupported multithreaded search guarantees.

---

## 35. F13/F14/F19/F20 REGRESSION

Re-run at minimum:

```text
F13 action_delivers_check
S4 truth table
checking/non-checking drop
uchifuzume

F14 648 attack differential
F14 8 in_check
curated attack corpus

F19 history-independence and exact external-key regression

F20 ordered legality
binding bridge
child transition bridge
zero child key/history
exact-history Native API regression
```

All PASS.

---

## 36. F3–F11 SEARCH REGRESSION

Re-run focused tests for:

```text
RuntimeSearchKey
RuntimeHistoryContext
continuous-check TT eligibility
opaque history bridge
forced collision
push/pop exception rollback
checkpoint
lazy/eager
qsearch
PVS
aspiration
root fallback
ordering
TT generation
```

No F3 contract may regress.

---

## 37. OLD EVIDENCE IMMUTABILITY

Preserve byte-identically all F4–F20 evidence/artifacts/docs and ADR-022 through ADR-037.

Create normalized-content before/after SHA-256 manifests.

Any old evidence mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f21_native_legality_routing/
```

---

## 38. REQUIRED F21 EVIDENCE

At minimum:

```text
artifacts/f21_native_legality_routing/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    architecture_boundary.json
    provider_contract.json
    provider_activation.json
    native_compile_once.json

    standard_shogi_provider_rows.jsonl
    standard_shogi_provider_summary.json
    generic_provider_differential.json
    binding_child_parity.json

    setup_fallback.json
    operational_fallback.json
    cancellation_deadline.json
    root_fallback.json

    search_parity.json
    repeated_search_tt_parity.json

    native_legality_stats.json
    child_key_history_regression.json

    binary_size_provenance.json

    profile_a_python.jsonl
    profile_a_native.jsonl
    profile_b_python.jsonl
    profile_b_native.jsonl
    production_performance.json

    initialization_cost.json
    threading_reentrancy.json

    h21a_gate.json
    h21b_gate.json
    retention_gate.json

    old_evidence_before.sha256
    old_evidence_after.sha256

    focused_tests.txt
    full_pytest.txt
    final_native_build.txt

    final_verdict.json
    manifest.json
```

Create:

```text
docs/architecture/F21_EVIDENCE.md
docs/architecture/ADR-038-production-native-legality-routing.md
```

ADR-038 must document:

- Core-neutral provider architecture;
- compile-once provider lifecycle;
- state-only payload;
- direct packed-action decode;
- exact binding reconstruction;
- setup/operational fallback;
- default-on production policy;
- cancellation semantics;
- measured production speedup;
- binary-size provenance;
- remaining Python authorities.

---

## 39. TESTS

Focused tests must include:

```text
provider create supported
provider unavailable fallback
provider unsupported-rules fallback
provider operational failure fallback

Core provider cache
Core provider push/pop cache restoration
duplicate provider action rejection
binding completeness

Standard Shogi 84-state production provider parity
generic semantic provider parity

AlphaBeta native-on/native-off parity
two consecutive searches
PVS
aspiration
qsearch
root tactical
pre-cancel
mid-search cancel
tiny time budget
tiny node budget
exception rollback

F13/F14/F19/F20
F3 history/TT
legacy non-semantic controls
```

Then:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then:

```text
python scripts/build_native_zig.py
```

Require final Native build PASS.

No AlphaSho.
No long games.

---

## 40. RUNTIME SAFETY

Hard limits:

```text
single focused/differential subprocess <= 60 s
single Profile A/B measured run <= 120 s
single microbenchmark <= 120 s
```

No multi-hour workloads.

On breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve completed evidence.

---

## 41. FORBIDDEN SCOPE

F21 must not:

```text
route Python push transition to Native
route terminal to Native
route repetition/history to Native
route TT identity to Native
route evaluator to Native
route full search to Native

route attack/check separately outside legality
add persistent Native position runtime
retain/revive F17 delta runtime

change move ordering
change evaluator
change qsearch policy
change search heuristics
change TT replacement/bounds/generation

import Native from Core
store Native capsule in SearchPathRuntime

change external position SHA
change canonical JSON
change fingerprint
change IR version
change semantic payload version
change Native schema version
change action bit layout
```

No F22 work.

---

## 42. GIT / PROVENANCE

Expected:

```text
E20 baseline
  -> H21A provider/fallback integration
  -> H21B default-on production routing
  -> E21 closure
```

If H21B fails final retention, revert default-on routing and close per Section 32.

Final:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

If push is blocked solely because the required F21 inbox contains the authoritative Gmail task:

```text
STOP before push
report exact local commits
request explicit authorization for that specific F21 inbox record
do not start F22
```

Do not silently omit required inbox provenance.

---

## 43. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
CORE_NATIVE_BOUNDARY_VIOLATION
STANDARD_SHOGI_PROVIDER_MISMATCH
GENERIC_PROVIDER_MISMATCH
BINDING_CHILD_MISMATCH
FALLBACK_PARITY_FAILURE
SEARCH_PARITY_FAILURE
TT_HISTORY_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
ROOT_FALLBACK_FAILURE
CHILD_EXTERNAL_KEY_REGRESSION
EXACT_HISTORY_AUTHORITY_REGRESSION
F13_F14_F19_F20_REGRESSION
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance failure is handled by Section 32 rather than as an immediate correctness stop.

---

## 44. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. F20 retained kernel confirmation
6. Core-neutral provider architecture
7. Provider compile-once lifecycle
8. Production enablement policy
9. State-only payload implementation
10. Packed-action decode implementation
11. Binding reconstruction integration
12. H21A provenance
13. H21A authorization gates
14. H21B production enablement
15. Setup fallback
16. Operational failure fallback
17. Standard Shogi provider differential
18. Generic semantic provider differential
19. Binding / child-transition parity
20. Search parity
21. Repeated-search TT/history parity
22. Root fallback / cancellation
23. qsearch / PVS / aspiration / root tactical
24. Native legality observability
25. Child key/history regression
26. Binary-size provenance
27. Player initialization cost
28. Profile A performance
29. Profile B performance
30. Final retention gate
31. Legacy / unsupported fallback
32. Tests
33. Evidence / manifest
34. Git / push status
35. Deferred
36. Final verdict

Successful verdict:

```text
F21_RESULT = PRODUCTION_ROUTING_PASS

CORE_NATIVE_UNAWARE = PASS

NATIVE_LEGALITY_PROVIDER = PASS
NATIVE_LEGALITY_DEFAULT_ON = true
PYTHON_FALLBACK = PASS
OPERATIONAL_FALLBACK = PASS

STANDARD_SHOGI_PROVIDER_PARITY = PASS
GENERIC_PROVIDER_PARITY = PASS
BINDING_CHILD_PARITY = PASS

SEARCH_PARITY = PASS
TT_HISTORY_PARITY = PASS
INTERRUPTIBILITY = PASS

CHILD_KEY_HISTORY_ELIMINATED = PASS
EXACT_HISTORY_AUTHORITY = PASS

PROFILE_A_GAIN = <percent>
PROFILE_B_GAIN = <percent>
PERFORMANCE_RETENTION_GATE = PASS

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS

F22_STARTED = false
```

Correctness-pass but default routing reverted:

```text
F21_RESULT = ROUTING_REVERTED

NATIVE_LEGALITY_DEFAULT_ON = false
OPT_IN_NATIVE_ROUTE = <retained|removed>
reason = <exact performance retention failure>

SEARCH_PARITY = PASS
FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS

F22_STARTED = false
```

Blocked verdict:

```text
F21_RESULT = BLOCKED
reason = <exact stop condition>
FULL_PYTEST = <PASS|FAIL>
FINAL_NATIVE_BUILD = <PASS|FAIL>
F22_STARTED = false
```

---

## 45. FINAL STOP

F21 ends after E21 closure and permitted sandbox push state.

Do not begin F22.
Do not expand Native authority beyond legal-action generation.
The next phase must be separately reviewed and authorized.

## Complete authoritative attachment

# GenericChess — F21: Production Native Legal-Action Routing + Fail-Safe Search Integration

## 0. AUTHORITATIVE TASK — EXECUTE NOW

This is the authoritative F21 task for `WD-nanophotonics/GenericChess`.

F20 closed as:

```text
F20_RESULT = LEGALITY_KERNEL_PASS
H20B_RETAINED = true
TRANSIENT_NATIVE_LEGALITY_KERNEL = PASS
STANDARD_SHOGI_ORDERED_LEGALITY = PASS
GENERIC_ORDERED_LEGALITY = PASS
BINDING_BRIDGE = PASS
PYTHON_CHILD_TRANSITION_BRIDGE = PASS
ONE_SHOT_ROUTING_GATE = PASS
SEARCH_SHADOW_PARITY = PASS
Profile A end-to-end gain = 33.50%
Profile B end-to-end gain = 32.31%
SELECTED_NEXT_BOUNDARY = NATIVE_LEGAL_ACTION_ROUTING_DIRECT
PRODUCTION_SEARCH_ROUTING_CHANGED = false
```

F21 implements exactly that selected boundary.

Goal:

> Route production AlphaBeta semantic legal-action generation through the certified F20 Native transient legality kernel when the Native semantic ruleset is executable, while preserving Python `SearchPathRuntime` as the authority for position transition, history, terminal, repetition, TT identity, evaluator, search policy, and all non-semantic/unsupported fallbacks.

Successful result:

```text
F21_RESULT = PRODUCTION_ROUTING_PASS
```

If correctness or fallback safety fails: `F21_RESULT = BLOCKED`.
If correctness passes but final performance no longer supports default-on routing: `F21_RESULT = ROUTING_REVERTED`.

Do not begin F22.

---

## 1. GMAIL / INBOX PROTOCOL

Follow the repository-local GenericChess Gmail/inbox workflow.

Before implementation:

1. locate this F21 task using fuzzy GenericChess/F21 subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task under top-level `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. execute immediately.

Do not execute from subject/snippet alone.

---

## 2. BASELINE HARD LOCK

Required refs:

```text
origin/sandbox =
3b2f253d7bbb7ed16ff705206644a1d76ece6977

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three.

If sandbox moved:

```text
BASELINE_MOVED
STOP
```

No reset, rebase, force-push, or master/chat modification.

---

## 3. F20 FROZEN AUTHORITY

Treat F20 as certified and closed.

Retained API:

```python
generic_chess.native.semantic.transient_legal_actions(
    native_rules,
    packed_position,
) -> tuple[int, ...]
```

It returns exact canonical ordered S0–S4 actions and performs zero candidate-child canonical-key/history work.

F20 realistic route included:

```text
Python state payload build
Native position pack
one Native S0–S4 call
packed-action decode
public action projection
exact binding reconstruction
```

Measured:

```text
median one-shot speedup = 4.7933x
median saving = 4127.98 us
40/40 Standard Shogi positions faster
max Native legality latency = 584.04 us
Profile A gain = 33.50%
Profile B gain = 32.31%
search logical parity = PASS
```

Do not reopen the F20 kernel architecture.

---

## 4. CURRENT PRODUCTION SEARCH CONTRACT — FREEZE

Current semantic search contract:

```text
SearchPathRuntime.legal_actions()
    -> SemanticEngine.iter_legal_action_bindings()
    -> cache:
       _legal_cache
       _bindings[public] = (semantic_action, binding)

SearchPathRuntime.push(action)
    -> membership in legal_actions()
    -> semantic_action, binding = _bindings[action]
    -> Python SemanticEngine._transition(...)
    -> Python runtime history/hash/terminal/TT authority
```

F21 must preserve this push contract.

Native must not become child-transition authority.

---

## 5. HARD ARCHITECTURE RULE — CORE REMAINS NATIVE-UNAWARE

No file under:

```text
generic_chess/core/
```

may import `generic_chess.native`.

No Native capsule/rules object may be stored directly in Core state.

A Core change is allowed only if it introduces a generic Native-neutral provider/callback boundary.

Preferred concept:

```python
legal_binding_provider(position, ply_count, checkpoint)
    -> iterable[(public_action, opaque_binding_payload)]
```

Core must not know the provider implementation.

If correct production routing requires Core Native awareness:

```text
CORE_NATIVE_BOUNDARY_VIOLATION
STOP
```

---

## 6. REQUIRED INTEGRATION ARCHITECTURE

Preferred architecture:

```text
AlphaBetaPlayer
    |
    | once per player/ruleset
    v
NativeSemanticLegalityProvider.try_create(compiled)
    |
    +-- Native unavailable / unsupported -> None
    |
    +-- executable semantic rules
            -> compile Native semantic rules once
            -> precompute ID maps once

run_root_search(...)
    -> SearchPathRuntime.from_state(
           ...,
           legal_binding_provider=provider_or_none,
       )

SearchPathRuntime.legal_actions()
    +-- cached -> cached
    +-- semantic + provider -> provider result -> _legal_cache/_bindings
    +-- otherwise -> existing Python SemanticEngine path
```

Exact names may differ.

---

## 7. CORE-NEUTRAL PROVIDER CONTRACT

If a provider hook is added to `SearchPathRuntime`, define it exactly.

Preferred private contract:

```python
provider(
    position: Position,
    ply_count: int,
    checkpoint,
) -> tuple[tuple[Action, object], ...]
```

For the Native semantic provider the opaque value is exactly:

```text
(semantic_action, binding)
```

Requirements:

```text
canonical order preserved
no duplicate public actions
binding for every action
no extra binding without action
provider called at most once per uncached runtime position
cache invalidated on push exactly as before
cache restored on pop exactly as before
```

Provider must not mutate runtime position/history.

---

## 8. DO NOT BYPASS `SearchPathRuntime`

Forbidden production shortcuts:

```text
search.py replacing only its local actions list
AI layer mutating runtime._legal_cache/_bindings externally
production monkey-patching/subclass global swapping
Native legality followed by Python runtime.legal_actions anyway
```

F20 audit monkey-patching was test-only.

---

## 9. PRODUCTION NATIVE LEGALITY PROVIDER

Create a narrow module preferably under:

```text
generic_chess/ai/alphabeta/native_legality.py
```

or another AI/native integration location outside Core.

It may import Native and Core semantic/action types.

It owns:

```text
NativeSemanticCompiledRules
precomputed type/pattern/geometry maps
pattern_by_id
state-only payload conversion
packed-action direct decode
public action projection
binding reconstruction
fallback/counters
```

No unbounded global mutable singleton.

---

## 10. COMPILE NATIVE SEMANTIC RULES ONCE

Do not compile Native semantic rules inside `legal_actions()`.

Compile once per `AlphaBetaPlayer` / fixed compiled ruleset.

Creation logic:

```text
native disabled -> provider None
native extension unavailable -> provider None
no SemanticEngine -> provider None
compile unsupported -> provider None
native_executable false -> provider None
otherwise -> provider active
```

Optional Native acceleration must never prevent normal Python search setup.

---

## 11. PRODUCTION ENABLEMENT POLICY

Add an explicit AlphaBetaPlayer option:

```python
use_native_semantic_legality: bool = True
```

or an equivalently explicit backend option.

Required default: `True`.

Behavior:

```text
True + supported Native semantic rules -> Native legality route
True + unavailable/unsupported -> Python fallback
False -> force Python legality route
```

This is an execution backend choice, not a chess heuristic. Prefer not to overload `SearchTuning`.

---

## 12. STATE-ONLY PAYLOAD — PRODUCTION IMPLEMENTATION

Promote/refactor the F20 state-only logic into production-quality code.

For every current Python position include exactly:

```text
side
ply
board:
    base type index
    current type index
    owner
    promoted
hands
aux_state
```

Exclude:

```text
history
repetition
external position SHA
terminal
TT identity
```

Requirements:

```text
precomputed type map
no per-call map rebuild
exact owner/type validation
fingerprint compatibility
no child SHA
```

Do not reuse an exact-history mirror payload if it computes history/SHA.

---

## 13. PACKED ACTION DECODE — NO PER-ACTION FFI

Do not call `semantic.unpack_action()` once per returned action in production.

Use direct Python bit decode of the frozen 64-bit layout, or one bulk decode if a clean bulk API already exists.

Precompute:

```text
type_ids
pattern_ids
geometry_ids
pattern_by_id
```

Then construct exact:

```text
SemanticAction
public SemanticBoardMove / SemanticDropMove
binding via _make_binding_from_action
```

No coordinate-only matching.
No first-match fallback.
No geometry re-inference.

---

## 14. EXACT BINDING RECONSTRUCTION

For every Native legal action:

```text
packed action
 -> exact fields
 -> SemanticAction
 -> exact pattern
 -> engine._make_binding_from_action(position, semantic_action, pattern)
 -> public action
```

Cache:

```python
bindings[public_action] = (semantic_action, binding)
```

Do not rerun Python S0/S1/S3/S4 in production.

---

## 15. PROVIDER FAILURE SAFETY

Separate two failure classes.

### Setup-time unavailability

```text
native extension unavailable
rules not semantic
Native compile unsupported
native_executable false
```

Behavior: normal Python fallback, no product exception.

### Operational failure after provider is active

Examples:

```text
payload pack failure
Native legality raises
invalid packed decode
ID index out of range
binding reconstruction failure
duplicate public action
```

Preferred production behavior:

1. provider has not mutated SearchPathRuntime;
2. discard partial Native result;
3. disable Native legality for the remainder of the current root search;
4. recompute current node with Python authority;
5. continue search;
6. increment fallback/error counters.

Do not mix partial Native and Python action lists.

Strict test mode may raise.

---

## 16. FALLBACK LOGICAL PARITY

Force operational provider failure at:

```text
root
depth-1 node
qsearch node
root tactical path
```

Compare against pure Python:

```text
action
score
PV
nodes
qnodes
depth
termination reason
TT probes/hits/stores/cutoffs
history/TT eligibility
```

Require exact parity.

---

## 17. CHECKPOINT / CANCELLATION CONTRACT

Native transient legality is one atomic call. F20 max was 584.04 us.

Provider must checkpoint at minimum:

```text
before payload/native call
after Native call
during Python decode/binding loop at bounded intervals
before returning
```

Requirements:

```text
pre-call cancellation observed
post-call cancellation observed before search continues
deadline bounded by one Native call + bounded decode chunk
node-only deterministic budget behavior unchanged
```

No C callback checkpoints in F21.

---

## 18. ROOT FIRST-ACTION / ABORT CONTRACT

Preserve:

```text
time_to_first_legal_action
root_first_action
root_scan_used_fallback
historical NO_LEGAL_FALLBACK behavior where applicable
```

Test:

```text
pre-cancelled token
tiny node limit
tiny wall-clock deadline
cancel during legality
provider exception during root legality
```

No empty or illegal fallback.

---

## 19. COMPLETE SEARCH-PATH COVERAGE

The single provider boundary must naturally cover every `SearchPathRuntime.legal_actions()` call:

```text
normal negamax
PVS null-window and re-search
aspiration re-search
in-check qsearch
non-check qsearch action source
root tactical scan
root fallback
```

Do not add ad-hoc Native calls in each search function.

---

## 20. LEGACY / NON-SEMANTIC ZERO-CHANGE

For non-semantic rules:

```text
provider = None
```

Existing legacy move generation remains unchanged.

No semantic Native compile attempt should occur.

Run legacy controls.

---

## 21. UNSUPPORTED SEMANTIC FALLBACK

Use at least one intentionally Native-unsupported semantic ruleset.

With default `use_native_semantic_legality=True`:

```text
AlphaBetaPlayer construction PASS
search PASS
provider inactive
Python legality used
result == forced-Python result
```

Do not weaken Native compile gates.

---

## 22. PROVIDER OBSERVABILITY

Add internal search statistics, without unnecessary public API expansion.

At minimum:

```text
native_legality_enabled
native_legality_calls
native_legality_actions
native_legality_seconds
native_legality_payload_seconds
native_legality_decode_binding_seconds
native_legality_fallbacks
native_legality_operational_failures
```

Use `SearchStatistics` if appropriate.

Do not expand `PlayerDecision` unless clearly required by existing reporting conventions.

---

## 23. NO EXTERNAL SHA / HISTORY WORK

For Native legality provider calls require:

```text
Native candidate child key computations = 0
Native history appends = 0
Python child external SHA computations unchanged from F20/F3
```

Do not call `position_identity_key()` in the provider.
Do not inspect public history to build the state-only payload.

---

## 24. BINARY-SIZE PROVENANCE AUDIT

F20 final Native build recorded:

```text
3,384,432 bytes
```

Earlier phases frequently recorded about:

```text
335,360 bytes
```

F21 must explain this discrepancy.

Record:

```text
current baseline build size
-O2 / --debug state
compiled source file list
debug/symbol section explanation if applicable
whether audit-only F20 code is linked
whether H20B duplicates major semantic code
```

This is not automatically a correctness blocker.

If large audit-only instrumentation or duplicate implementation is accidentally retained in the production extension and can be removed without altering certified behavior, clean it before final closure.

Do not trade correctness/performance for arbitrary size reduction.

---

## 25. H21 PHASE STRUCTURE

Use:

```text
E20 baseline
  -> H21A provider boundary + fallback integration
  -> H21B default-on production routing
  -> E21 closure
```

### H21A

May implement:

```text
Core-neutral provider hook
AI/native provider module
stats
fallback machinery
strict test mode
integration tests
```

Keep production default routing disabled until H21A gates pass.

Commit and push H21A.

### H21B

After authorization, enable default-on Native legality for eligible `AlphaBetaPlayer` search.

Commit and push H21B.

---

## 26. H21B AUTHORIZATION GATES

All must pass.

### G1 Core boundary

```text
Core Native imports = 0
Core Native objects = 0
provider contract Native-neutral = PASS
```

### G2 Standard Shogi parity

Use at least F20's 84-state corpus.

Require zero:

```text
count mismatch
order mismatch
action identity mismatch
binding mismatch
Python transition mismatch
```

### G3 Generic semantic parity

F20 10/10 corpus + focused S3/S4 fixtures PASS.

### G4 Fallback

Setup fallback and injected operational fallback PASS.

### G5 Search parity

F20 shadow routes PASS through the real provider architecture.

### G6 cancellation / interruptibility

PASS.

Any failure:

```text
H21B_NOT_AUTHORIZED
```

Do not enable production default.

---

## 27. PRODUCTION SEARCH PARITY

Compare:

```python
AlphaBetaPlayer(use_native_semantic_legality=False)
```

vs:

```python
AlphaBetaPlayer(use_native_semantic_legality=True)
```

Require exact:

```text
action
score
PV
completed depth
selective depth
nodes
qnodes
termination reason
TT probes/hits/cutoffs/stores where exposed
beta cutoffs
PVS stats
aspiration stats
qsearch stats
root tactical stats
legal action order
runtime history/repetition behavior
TT eligibility
child external key computation behavior
```

Ignore only elapsed time and Native provider timing/counters.

---

## 28. TWO-CONSECUTIVE-SEARCH TT REGRESSION

Because `AlphaBetaPlayer` retains TT across searches, explicitly test two consecutive controlled `choose_action()` calls.

Native legality routing must not change:

```text
TT generation
persistent hits
history-aware eligibility
collision guards
```

Re-run F3 TT/history-specific tests.

---

## 29. STANDARD SHOGI PRODUCTION PROVIDER DIFFERENTIAL

Use four frozen prefixes and deterministic sampled children.

At least the 84 F20 states.

For every state compare production provider output against Python authority:

```text
public action count/order
semantic identity
binding
Python child transition
```

Zero mismatch.

---

## 30. GENERIC IR-v2 PRODUCTION PATH

Run:

```text
cannon
castling
en_passant
nifu
uchifuzume
weird_0..4
```

through the production provider implementation.

Require provider activation when executable and exact legal/binding/child parity.

---

## 31. FINAL PERFORMANCE PROFILES

Re-run F20 Profile A/B under actual production integration.

### Profile A

```text
TT on
ordering off
qsearch max depth = 0
root tactical off
max_depth = 2
max_nodes = 512
fresh TT per measured run
no wall-clock limit
```

### Profile B

Current production/default tuning:

```text
max_nodes = 256
deterministic node budget
no wall-clock limit
```

For each four frozen semantic cases:

```text
1 warm-up
5 measured runs
```

Compare forced-Python legality vs default production Native legality.

No heavy trace in timing.

---

## 32. FINAL PERFORMANCE RETENTION GATE

For default-on production retention require:

```text
Profile A aggregate gain >= 20%
Profile B aggregate gain >= 20%
```

AND:

```text
at least 3/4 cases in each profile gain >= 10%
no semantic case stable regression > 3%
```

F20 measured 33.50% / 32.31%; F21 may pay some integration overhead but must remain materially strong.

If correctness passes but this gate fails:

1. revert default-on routing;
2. an opt-in route may remain only if both profiles still gain >=8% and no case regresses >3%;
3. final result is:

```text
F21_RESULT = ROUTING_REVERTED
```

Do not claim production routing pass.

---

## 33. PLAYER INITIALIZATION COST

Measure once-per-player provider compile/create latency.

Do not mix it into search-node elapsed time unless historically included.

If >1 s, document and consider only a bounded fingerprint-scoped cache in AI/native layer.

No unbounded global cache.

---

## 34. THREAD / REENTRANCY SAFETY

Audit sequential reuse and separate player instances.

Require:

```text
no mutable per-call action buffer stored globally
no cross-search provider contamination
no shared partial result
```

Production route must use non-audit `transient_legal_actions`, not audit entrypoints.

Do not claim unsupported multithreaded search guarantees.

---

## 35. F13/F14/F19/F20 REGRESSION

Re-run at minimum:

```text
F13 action_delivers_check
S4 truth table
checking/non-checking drop
uchifuzume

F14 648 attack differential
F14 8 in_check
curated attack corpus

F19 history-independence and exact external-key regression

F20 ordered legality
binding bridge
child transition bridge
zero child key/history
exact-history Native API regression
```

All PASS.

---

## 36. F3–F11 SEARCH REGRESSION

Re-run focused tests for:

```text
RuntimeSearchKey
RuntimeHistoryContext
continuous-check TT eligibility
opaque history bridge
forced collision
push/pop exception rollback
checkpoint
lazy/eager
qsearch
PVS
aspiration
root fallback
ordering
TT generation
```

No F3 contract may regress.

---

## 37. OLD EVIDENCE IMMUTABILITY

Preserve byte-identically all F4–F20 evidence/artifacts/docs and ADR-022 through ADR-037.

Create normalized-content before/after SHA-256 manifests.

Any old evidence mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f21_native_legality_routing/
```

---

## 38. REQUIRED F21 EVIDENCE

At minimum:

```text
artifacts/f21_native_legality_routing/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    architecture_boundary.json
    provider_contract.json
    provider_activation.json
    native_compile_once.json

    standard_shogi_provider_rows.jsonl
    standard_shogi_provider_summary.json
    generic_provider_differential.json
    binding_child_parity.json

    setup_fallback.json
    operational_fallback.json
    cancellation_deadline.json
    root_fallback.json

    search_parity.json
    repeated_search_tt_parity.json

    native_legality_stats.json
    child_key_history_regression.json

    binary_size_provenance.json

    profile_a_python.jsonl
    profile_a_native.jsonl
    profile_b_python.jsonl
    profile_b_native.jsonl
    production_performance.json

    initialization_cost.json
    threading_reentrancy.json

    h21a_gate.json
    h21b_gate.json
    retention_gate.json

    old_evidence_before.sha256
    old_evidence_after.sha256

    focused_tests.txt
    full_pytest.txt
    final_native_build.txt

    final_verdict.json
    manifest.json
```

Create:

```text
docs/architecture/F21_EVIDENCE.md
docs/architecture/ADR-038-production-native-legality-routing.md
```

ADR-038 must document:

- Core-neutral provider architecture;
- compile-once provider lifecycle;
- state-only payload;
- direct packed-action decode;
- exact binding reconstruction;
- setup/operational fallback;
- default-on production policy;
- cancellation semantics;
- measured production speedup;
- binary-size provenance;
- remaining Python authorities.

---

## 39. TESTS

Focused tests must include:

```text
provider create supported
provider unavailable fallback
provider unsupported-rules fallback
provider operational failure fallback

Core provider cache
Core provider push/pop cache restoration
duplicate provider action rejection
binding completeness

Standard Shogi 84-state production provider parity
generic semantic provider parity

AlphaBeta native-on/native-off parity
two consecutive searches
PVS
aspiration
qsearch
root tactical
pre-cancel
mid-search cancel
tiny time budget
tiny node budget
exception rollback

F13/F14/F19/F20
F3 history/TT
legacy non-semantic controls
```

Then:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then:

```text
python scripts/build_native_zig.py
```

Require final Native build PASS.

No AlphaSho.
No long games.

---

## 40. RUNTIME SAFETY

Hard limits:

```text
single focused/differential subprocess <= 60 s
single Profile A/B measured run <= 120 s
single microbenchmark <= 120 s
```

No multi-hour workloads.

On breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve completed evidence.

---

## 41. FORBIDDEN SCOPE

F21 must not:

```text
route Python push transition to Native
route terminal to Native
route repetition/history to Native
route TT identity to Native
route evaluator to Native
route full search to Native

route attack/check separately outside legality
add persistent Native position runtime
retain/revive F17 delta runtime

change move ordering
change evaluator
change qsearch policy
change search heuristics
change TT replacement/bounds/generation

import Native from Core
store Native capsule in SearchPathRuntime

change external position SHA
change canonical JSON
change fingerprint
change IR version
change semantic payload version
change Native schema version
change action bit layout
```

No F22 work.

---

## 42. GIT / PROVENANCE

Expected:

```text
E20 baseline
  -> H21A provider/fallback integration
  -> H21B default-on production routing
  -> E21 closure
```

If H21B fails final retention, revert default-on routing and close per Section 32.

Final:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

If push is blocked solely because the required F21 inbox contains the authoritative Gmail task:

```text
STOP before push
report exact local commits
request explicit authorization for that specific F21 inbox record
do not start F22
```

Do not silently omit required inbox provenance.

---

## 43. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
CORE_NATIVE_BOUNDARY_VIOLATION
STANDARD_SHOGI_PROVIDER_MISMATCH
GENERIC_PROVIDER_MISMATCH
BINDING_CHILD_MISMATCH
FALLBACK_PARITY_FAILURE
SEARCH_PARITY_FAILURE
TT_HISTORY_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
ROOT_FALLBACK_FAILURE
CHILD_EXTERNAL_KEY_REGRESSION
EXACT_HISTORY_AUTHORITY_REGRESSION
F13_F14_F19_F20_REGRESSION
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance failure is handled by Section 32 rather than as an immediate correctness stop.

---

## 44. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. F20 retained kernel confirmation
6. Core-neutral provider architecture
7. Provider compile-once lifecycle
8. Production enablement policy
9. State-only payload implementation
10. Packed-action decode implementation
11. Binding reconstruction integration
12. H21A provenance
13. H21A authorization gates
14. H21B production enablement
15. Setup fallback
16. Operational failure fallback
17. Standard Shogi provider differential
18. Generic semantic provider differential
19. Binding / child-transition parity
20. Search parity
21. Repeated-search TT/history parity
22. Root fallback / cancellation
23. qsearch / PVS / aspiration / root tactical
24. Native legality observability
25. Child key/history regression
26. Binary-size provenance
27. Player initialization cost
28. Profile A performance
29. Profile B performance
30. Final retention gate
31. Legacy / unsupported fallback
32. Tests
33. Evidence / manifest
34. Git / push status
35. Deferred
36. Final verdict

Successful verdict:

```text
F21_RESULT = PRODUCTION_ROUTING_PASS

CORE_NATIVE_UNAWARE = PASS

NATIVE_LEGALITY_PROVIDER = PASS
NATIVE_LEGALITY_DEFAULT_ON = true
PYTHON_FALLBACK = PASS
OPERATIONAL_FALLBACK = PASS

STANDARD_SHOGI_PROVIDER_PARITY = PASS
GENERIC_PROVIDER_PARITY = PASS
BINDING_CHILD_PARITY = PASS

SEARCH_PARITY = PASS
TT_HISTORY_PARITY = PASS
INTERRUPTIBILITY = PASS

CHILD_KEY_HISTORY_ELIMINATED = PASS
EXACT_HISTORY_AUTHORITY = PASS

PROFILE_A_GAIN = <percent>
PROFILE_B_GAIN = <percent>
PERFORMANCE_RETENTION_GATE = PASS

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS

F22_STARTED = false
```

Correctness-pass but default routing reverted:

```text
F21_RESULT = ROUTING_REVERTED

NATIVE_LEGALITY_DEFAULT_ON = false
OPT_IN_NATIVE_ROUTE = <retained|removed>
reason = <exact performance retention failure>

SEARCH_PARITY = PASS
FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS

F22_STARTED = false
```

Blocked verdict:

```text
F21_RESULT = BLOCKED
reason = <exact stop condition>
FULL_PYTEST = <PASS|FAIL>
FINAL_NATIVE_BUILD = <PASS|FAIL>
F22_STARTED = false
```

---

## 45. FINAL STOP

F21 ends after E21 closure and permitted sandbox push state.

Do not begin F22.
Do not expand Native authority beyond legal-action generation.
The next phase must be separately reviewed and authorized.

## Integrity

- Body characters: 26522
- Attachment characters: 26522
- Body/attachment exact match: yes

