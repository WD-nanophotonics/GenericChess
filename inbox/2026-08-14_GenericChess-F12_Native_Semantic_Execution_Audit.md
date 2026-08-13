# Gmail provenance

- Subject: GenericChess — F12: Native Semantic Execution Capability Audit + Migration Boundary Decision
- Message ID: 19ffcb0f6cccd6e5
- Thread ID: 19ffcb0f6cccd6e5
- From: W D <icywoods.1@gmail.com>
- To: icywoods.1@gmail.com
- Date: Thu, 13 Aug 2026 15:54:43 -0400
- Attachment: GenericChess_F12_Native_Semantic_Execution_Audit.md
- Retrieved: 2026-08-14
- Processing state: authoritative attachment persisted before execution

# Complete authoritative attachment
# GenericChess — F12: Native Semantic Execution Capability Audit + Migration Boundary Decision

## 0. AUTHORITATIVE TASK

This is the authoritative F12 task for `WD-nanophotonics/GenericChess`.

F11 established:

```text
F11_RESULT = AUDIT_ONLY_PASS
PYTHON_LOCAL_RUNTIME_HEADROOM = LIMITED
recommended_next_boundary = NATIVE_SEMANTIC_EXECUTION_AUDIT
```

F12 executes exactly that boundary.

F12 is primarily an **architecture/capability/performance audit**, not a production migration phase.

Its purpose is to answer:

> What semantic execution already exists in Native, what exact Semantic Standard Shogi functionality is or is not executable there today, what the actual Python↔Native boundary costs are, and what is the smallest safe next implementation boundary capable of producing material end-to-end speedup?

F12 MUST NOT directly switch production AlphaBeta/SearchPathRuntime to Native semantic execution.

F12 MUST NOT redesign game semantics.

F12 MUST end by selecting exactly one future implementation boundary.

The normal successful result is:

```text
F12_RESULT = AUDIT_PASS
```

A blocked result is allowed only for a genuine reproducibility/build/correctness failure.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before work:

1. locate this task using GenericChess/Gmail fuzzy subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. then begin audit/execution.

Do not execute from the email subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
26f697aec3b990e60b60a225236037adcff2c570

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three before changes.

If `origin/sandbox` moved:

```text
BASELINE_MOVED
STOP
```

Do not reset, rewrite, force-push, or overwrite another task.

Work only on `sandbox`.

`master` and `chat` remain read-only.

---

# 3. F4–F11 FROZEN RESULTS

Treat all earlier decisions as closed.

## Accepted Python-local runtime work

- F4 checkpoint fixed-node fast path.
- F5 semantic `(owner, current_type_id)` source dispatch.
- F10 operation-local semantic source-index reuse.

## Rejected Python-local candidates

- F6 target-directed geometry.
- F7 general exact attack/check memoization.
- F8 `known_checked` push→terminal forwarding.
- F9 terminal legal-probe continuation/eager materialization.

Do not revive any of these.

## F11 current authority

Post-F10 hotspot ranking:

1. semantic attack/check;
2. checkpoint dispatch;
3. runtime push/terminal/hash;
4. geometry enumeration;
5. residual source-index construction;
6. evaluator.

Representative current attack cost from F11:

```text
Profile A is_square_attacked self ≈ 18.1%
Profile B is_square_attacked self ≈ 23.1%
```

F11 concluded:

```text
PYTHON_LOCAL_RUNTIME_HEADROOM = LIMITED
```

Do not reopen Python micro-optimization selection inside F12.

---

# 4. CURRENT NATIVE SURFACE — AUDIT, DO NOT ASSUME

Audit the current repository as source of truth.

Known surfaces that must be inspected include at least:

```text
generic_chess/native/compiler.py
generic_chess/native/semantic.py
generic_chess/native/engine.py
generic_chess/native/search.py
generic_chess/native/adapter.py
generic_chess/native/differential.py
generic_chess/native/search_differential.py

generic_chess/_native/*.c
generic_chess/_native/*.h

scripts/build_native_zig.py
```

Important existing observations that MUST be verified rather than blindly trusted:

- semantic compiler lowers IR v2 to a numeric payload;
- `NativeSemanticCompilationReport.native_executable` exists;
- Python wrapper exposes semantic:
  - pack/snapshot/key;
  - candidate actions;
  - guarded actions;
  - make_checked;
  - terminal;
  - fixed-depth/probe search;
- old `native_attack.c` operates on legacy movement atoms / `GCRules` and is NOT automatically equivalent to `SemanticEngine.is_square_attacked`;
- Python SemanticEngine pseudo-attack includes:
  - only `target_enemy` patterns;
  - type/geometry compatibility;
  - path predicates;
  - state guards;
  - slot guards;
  - attacker-relative owner semantics;
  - S4-bearing patterns contribute their S0/S1 projection;
  - S3 and S4 are not recursively evaluated for pseudo-attack.

Audit actual code and tests before making any compatibility statement.

---

# 5. F12 PHASE STRUCTURE

F12 has one audit harness phase and one evidence closure.

Expected:

```text
E11 baseline
  -> H12A native semantic capability/benchmark harness
  -> E12 evidence/docs closure
```

There is NO production H12B.

H12A may add:

- audit scripts;
- test-only adapters;
- isolated native probe wrappers;
- capability diagnostics;
- microbenchmarks;
- differential harnesses;
- documentation;
- evidence artifacts.

H12A MUST NOT:

- route production AlphaBeta through Native;
- modify SearchPathRuntime behavior;
- change production semantic truth;
- add production caching;
- change evaluator/search policy.

If a tiny test-only C/Python probe is required to measure an otherwise-unobservable Native primitive, it must remain explicitly audit-only and must not be wired into production APIs.

---

# 6. FRESH BUILD / ENVIRONMENT BASELINE

Use the repository `.venv`.

Record:

```text
Python version
platform
compiler / Zig version
native schema version
semantic payload version
Semantic IR version
extension output path
extension size
```

Run a fresh supported build:

```text
python scripts/build_native_zig.py
```

Require PASS before Native conclusions.

Record build command and output.

If build fails:

```text
NATIVE_BUILD_BLOCKED
STOP
```

Do not substitute an old binary.

---

# 7. STANDARD SHOGI NATIVE COMPILATION AUDIT

Use the certified Semantic Standard Shogi builder/corpus used in F4–F11.

Hard assert fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

Run:

```text
build_semantic_compile_payload(...)
compile_native_semantic_rules(...)
```

Record separately:

```text
payload_build = PASS/FAIL
native capsule compile = PASS/FAIL
report.native_executable = true/false
```

If any stage fails, capture the exact:

```text
exception type
stable reason
primitive / enum / stratum
pattern_id if identifiable
semantic feature
```

Do NOT patch the compiler merely to make Standard Shogi compile.

The audit must distinguish:

```text
LOWERING_UNSUPPORTED
STRUCTURAL_GATE_FAIL
C_KERNEL_EXECUTION_UNSUPPORTED
HISTORY_POLICY_UNSUPPORTED
SEARCH_WRAPPER_LIMITATION
```

---

# 8. SEMANTIC CAPABILITY MATRIX

Produce an explicit current capability matrix.

At minimum cover:

## Geometry

```text
leap
ray
drop
min_steps
owner-relative geometry
precompiled paths
```

## Targets / paths

```text
target_empty
target_enemy
target_friendly
target_any

path_clear
path_count_eq
path_count_range
path_first_blocker_owner
path_last_blocker_owner
```

## State guards

```text
owner self/opponent/any
action_base
action_current
explicit type
promoted selector
same_file
same_rank
exact
adjacent
path_between
zone
board location
hand location
```

## Aux / triggers

```text
global/per_owner
bool
square_or_none
persistent
expire_next_turn
piece_leaves_square
piece_removed_from_square
slot guards
```

## Effects

Audit every current IR-v2 effect.

## Promotion / drop

```text
none
inherit_compiled_masks
explicit
forced promotion
drop masks
capture-to-hand
```

## S3 invariants

```text
own_anchor_safe
squares_not_attacked
```

## S4

At minimum inspect actual support for:

```text
action_delivers_check
opponent_checked
no_legal_reply
max_stratum <= S3
```

Do not infer support from Python enum names alone.

## S5 / terminal

```text
checkmate
stalemate
ordinary repetition
continuous_check_loss
max_ply
history evidence
exact repetition identity
```

## Search

```text
guarded action generation
make/unmake
terminal
fixed-depth search
material evaluation
TT if any
interruptibility if any
```

For each feature classify:

```text
SUPPORTED_AND_DIFFERENTIAL_TESTED
IMPLEMENTED_BUT_NOT_CERTIFIED
LOWERED_BUT_NOT_EXECUTED
FAIL_CLOSED_UNSUPPORTED
NOT_APPLICABLE
```

Include file/function evidence.

---

# 9. CERTIFIED CORPUS

Reuse the frozen corpus:

- 4 reachable Semantic Standard Shogi prefixes;
- legacy draw control;
- continuous-check control.

Also retain curated witnesses for:

```text
capture
drop
promotion
forced promotion
own_anchor_safe
squares_not_attacked
nifu
uchifuzume
S4 no_legal_reply
checkmate
stalemate
ordinary repetition
continuous_check_loss
max_ply
```

Do not modify rules to make Native look better.

Unsupported cases must remain unsupported evidence.

---

# 10. EXISTING NATIVE DIFFERENTIAL AUDIT

Run all currently applicable native semantic differential/readiness tests.

At minimum test, when supported:

```text
position pack -> snapshot
position key
action pack/unpack
candidate action order
guarded action order
make_checked child
make/unmake roundtrip
terminal
fixed-depth search
PV legality
node/result determinism
```

Compare against authoritative Python semantic/Core behavior.

For unsupported Standard Shogi paths:

```text
NOT_RUN_UNSUPPORTED
```

is correct.

Never fabricate parity by dropping unsupported rules.

---

# 11. ATTACK/CHECK MIGRATION FEASIBILITY AUDIT

Because F11 identifies semantic attack/check as the dominant Python-local cost, F12 must audit this slice specifically.

## 11.1 Python semantic truth contract

Freeze the exact current contract of:

```text
SemanticEngine.is_square_attacked
SemanticEngine.in_check
```

Document all data they observe.

## 11.2 Existing Native attack code

Audit whether any existing Native code is exactly reusable.

Specifically distinguish:

```text
legacy movement-atom attack
vs
semantic IR pseudo-attack
```

If they differ, produce concrete counterexample fixture(s).

## 11.3 Required Native semantic attack slice

Without implementing production routing, specify the minimal native inputs needed for exact semantic pseudo-attack:

```text
position state
piece base/current/promoted
owner
aux state
semantic patterns
geometry
path predicates
guards
slot guards
zones
type mapping
```

Clarify what is NOT needed:

```text
S3 own-anchor safety
S4 postconditions
history
repetition
TT
evaluation
```

unless current code proves otherwise.

## 11.4 Capability independence

Determine whether an exact attack/check kernel can be:

```text
ATTACK_CAPABLE = true
```

even when full:

```text
NATIVE_SEMANTIC_EXECUTABLE = false
```

for the same ruleset.

This is an architecture question only.

Do NOT weaken `native_executable`.

If partial capability is recommended, it must use a separate explicit fail-closed capability contract, not overload the meaning of `native_executable`.

---

# 12. BOUNDARY-COST BENCHMARKS

F12 must measure actual Python↔Native costs before recommending a migration slice.

Use process-isolated microbenchmarks.

At minimum measure:

```text
Python Position -> Native semantic position pack
Native snapshot -> Python materialization
Python action -> packed action
packed action -> Python action
one no-op/cheap Native call boundary
candidate_actions call
guarded_actions call, on supported semantic fixtures
make_checked call
terminal call
fixed-depth semantic search call, where supported
```

For each:

```text
warm-up
>= 100 repetitions for cheap calls
median
p90
min/max
```

Use enough repetitions for stable microsecond/millisecond values.

Do not benchmark unsupported Standard Shogi operations by silently using a different ruleset without labeling it.

---

# 13. POSITION OWNERSHIP / LIFETIME AUDIT

This is mandatory.

A Native acceleration that repacks the entire Python Position for every attack query may erase the kernel gain.

Audit current ownership:

```text
Python SearchPathRuntime owns Position
Native semantic position capsule lifecycle
make_checked ownership
make/unmake availability
history storage
aux state
hash/key state
```

Evaluate these architecture options:

```text
A. Python-authoritative position + per-call Native pack
B. Python-authoritative position + mirrored Native frame
C. Native-authoritative search path + Python debug/differential shadow
D. full Native semantic search backend
```

For each record:

```text
boundary crossings per node
pack/copy cost
rollback complexity
history/repetition complexity
interruptibility complexity
semantic divergence risk
expected speedup ceiling
```

Do not implement any option in F12.

---

# 14. NATIVE SEARCH READINESS AUDIT

The repository already exposes semantic fixed-depth/probe search APIs.

Determine exactly what they are today:

```text
production-ready
experimental
debug-only
partially semantic
fully semantic for supported rulesets
```

Audit:

```text
legal action authority
terminal authority
history/repetition
continuous_check_loss
evaluation parity
PV legality
node accounting
TT
qsearch
ordering
PVS
aspiration
node/time/cancel budgets
interruptibility
```

Do not confuse:

```text
fixed-depth correctness probe
```

with:

```text
drop-in production AlphaBeta backend
```

State the gap explicitly.

---

# 15. PERFORMANCE CEILING MODEL

Build a simple evidence-based speedup model.

Use F11 cost shares plus F12 Native boundary measurements.

At minimum estimate for each candidate future boundary:

```text
NATIVE_ATTACK_CHECK_SLICE
NATIVE_LEGALITY_KERNEL
NATIVE_POSITION_RUNTIME
FULL_NATIVE_SEMANTIC_SEARCH
```

Estimate:

```text
fraction of current wall time addressed
Python↔C overhead
expected achievable speedup range
implementation complexity
semantic risk
```

Use Amdahl-style reasoning.

Do not claim precise speedups unsupported by measurement.

Use ranges and assumptions.

---

# 16. FUTURE BOUNDARY DECISION — EXACTLY ONE

F12 must choose exactly one recommended next implementation boundary:

```text
NATIVE_ATTACK_CHECK_SLICE
NATIVE_LEGALITY_KERNEL
NATIVE_POSITION_RUNTIME
FULL_NATIVE_SEMANTIC_SEARCH
NATIVE_CAPABILITY_GAP_CLOSURE
SEARCH_STRENGTH_EVALUATOR_PHASE
```

Selection criteria:

1. must address material current cost;
2. must have a clear exact semantic oracle;
3. must avoid unnecessary broad rewrite;
4. boundary overhead must not obviously erase expected gain;
5. must have a credible differential strategy;
6. must preserve fail-closed behavior.

If Standard Shogi cannot even lower enough semantic IR to support the chosen slice, prefer:

```text
NATIVE_CAPABILITY_GAP_CLOSURE
```

Do NOT recommend `FULL_NATIVE_SEMANTIC_SEARCH` merely because C is faster.

---

# 17. OPTIONAL AUDIT-ONLY PROTOTYPE

An audit-only prototype is permitted only when necessary to resolve the future boundary decision.

Allowed examples:

```text
test-only semantic attack/check C probe
test-only pack/unpack timing hook
test-only native capability introspection
```

Requirements:

- not imported by production packages;
- not used by production search;
- clearly marked audit-only;
- full existing suite remains green;
- removable without changing product behavior.

If no prototype is necessary, do not create one.

---

# 18. NO PRODUCTION MIGRATION

Hard prohibition for F12:

Do NOT:

```text
route AlphaBetaPlayer to Native semantic search
replace SearchPathRuntime with Native
call Native attack/check from SemanticEngine production path
add Native fallback inside semantic_executor.py
add cross-position caches
change ruleset fingerprint
change IR version
change semantic meaning
change evaluator weights/features
change search heuristics
```

F12 is an audit and migration-boundary decision.

---

# 19. INTERRUPTIBILITY / FAILURE MODEL

For each recommended future boundary, explicitly analyze:

```text
node budget
time budget
cancel token
cooperative checkpoints
Python callback overhead
GIL behavior
native polling frequency
exception propagation
rollback after abort
```

The next phase must not sacrifice current bounded interruption guarantees just to gain speed.

F12 itself must preserve current behavior.

---

# 20. F4–F11 EVIDENCE IMMUTABILITY

Preserve byte-identically:

```text
artifacts/f4_runtime_cost/**
artifacts/f5_semantic_attack_s3/**
artifacts/f6_target_directed_semantic/**
artifacts/f7_semantic_attack_query_reuse/**
artifacts/f8_push_terminal_check_dedup/**
artifacts/f9_terminal_legal_probe_reuse/**
artifacts/f10_source_index_lifetime/**
artifacts/f11_post_f10_rebaseline/**

docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
docs/architecture/F7_EVIDENCE.md
docs/architecture/F8_EVIDENCE.md
docs/architecture/F9_EVIDENCE.md
docs/architecture/F10_EVIDENCE.md
docs/architecture/F11_EVIDENCE.md

ADR-022
ADR-023
ADR-024
ADR-025
ADR-026
ADR-027
ADR-028
```

Create before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f12_native_semantic_audit/
```

---

# 21. REQUIRED EVIDENCE

At minimum:

```text
artifacts/f12_native_semantic_audit/
    baseline.json
    environment.json
    fresh_native_build.txt

    native_surface_inventory.json
    standard_shogi_compile.json
    native_capability_matrix.json
    semantic_gap_matrix.json

    existing_native_differential.json
    standard_shogi_native_differential.json

    python_attack_contract.json
    legacy_vs_semantic_attack.json
    attack_slice_requirements.json

    boundary_microbench.json
    position_ownership_matrix.json
    search_readiness_matrix.json

    speedup_ceiling.json
    future_boundary_candidates.json
    selected_future_boundary.json

    interruptibility_analysis.json
    failure_model.json

    old_evidence_before.sha256
    old_evidence_after.sha256

    focused_tests.txt
    full_pytest.txt
    final_native_build.txt

    final_verdict.json
    manifest.json
```

If a Standard Shogi Native operation is unsupported, explicitly record:

```text
NOT_RUN_UNSUPPORTED
```

with the exact blocking capability.

Create:

```text
docs/architecture/F12_EVIDENCE.md
docs/architecture/ADR-029-native-semantic-execution-boundary.md
```

ADR-029 must document:

- current Native semantic authority;
- exact Standard Shogi coverage/gaps;
- why legacy native attack is or is not reusable;
- position ownership decision analysis;
- Python↔Native boundary cost;
- selected next implementation boundary;
- why alternatives were deferred.

---

# 22. TESTS

Run all relevant existing Native and semantic suites.

At minimum include:

```text
native compile tests
native semantic payload tests
semantic position pack/snapshot/key
native semantic candidate/guarded action tests
make/unmake
terminal
native search differential/readiness
F11/F10 regressions
Standard Shogi semantic certification
S3/S4
repetition / continuous-check
F3 history/TT
interruptibility / native stress
```

Then:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then perform a second fresh supported native build:

```text
python scripts/build_native_zig.py
```

Require PASS.

No AlphaSho benchmark.

No long games.

---

# 23. RUNTIME SAFETY

No unbounded benchmark.

Hard controller limits:

```text
single capability/differential subprocess <= 60 s
single fixed-depth/native benchmark <= 120 s
```

If exceeded:

```text
RUNTIME_SAFETY_ABORT
```

Save evidence and continue only if required conclusions remain valid.

Do not run multi-hour workloads.

---

# 24. GIT / PROVENANCE

Expected:

```text
E11 baseline
  -> H12A audit harness / optional audit-only probe
  -> E12 evidence/docs closure
```

No production migration commit.

Final:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

Record exact SHAs.

---

# 25. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
FRESH_NATIVE_BUILD_FAILURE
NATIVE_DIFFERENTIAL_CORRECTNESS_FAILURE in an already-certified supported path
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Unsupported Standard Shogi Native capability is NOT itself a failure.

It is a valid audit result.

Do not repair broad Native semantics inside F12.

---

# 26. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / native build
5. Native surface inventory
6. Standard Shogi native compile status
7. Semantic capability matrix
8. Standard Shogi gap matrix
9. Existing native differential status
10. Python semantic attack/check contract
11. Legacy native attack comparison
12. Native attack/check slice feasibility
13. Python↔Native boundary microbench
14. Position ownership / lifetime analysis
15. Native search readiness
16. Performance ceiling model
17. Future boundary candidates
18. Selected next boundary
19. Interruptibility / failure model
20. Tests
21. Evidence / manifest
22. Git
23. Deferred
24. Final verdict

Final verdict format:

```text
F12_RESULT = AUDIT_PASS

FRESH_NATIVE_BUILD = PASS
EXISTING_NATIVE_CERTIFIED_PATHS = <PASS|PARTIAL>
STANDARD_SHOGI_NATIVE_EXECUTABLE = <true|false>

SEMANTIC_ATTACK_NATIVE_READY = <true|false|partial>
FULL_NATIVE_SEARCH_READY = <true|false>

SELECTED_NEXT_BOUNDARY =
<NATIVE_ATTACK_CHECK_SLICE |
 NATIVE_LEGALITY_KERNEL |
 NATIVE_POSITION_RUNTIME |
 FULL_NATIVE_SEMANTIC_SEARCH |
 NATIVE_CAPABILITY_GAP_CLOSURE |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

---

# 27. FINAL STOP

F12 ends after E12 closure.

Do not begin F13.

Do not implement the selected migration boundary.

The next phase will be separately authorized after this audit is reviewed.
