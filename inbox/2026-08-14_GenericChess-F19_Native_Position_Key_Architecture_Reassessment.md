<!-- Gmail provenance
message_id: 1a00013d5cd343f7
thread_id: 1a00013d5cd343f7
subject: GenericChess — F19: Native Position-Key Architecture Reassessment + History-Decoupled Runtime Feasibility
from: W D <icywoods.1@gmail.com>
to: icywoods.1@gmail.com
received: 2026-08-14T04:41:34-07:00
attachment: GenericChess_F19_Position_Key_Architecture_Reassessment.md
attachment_bytes: 26312
fetched_at: 2026-08-14 Asia/Tokyo
processing_state: complete-authoritative-attachment
-->

# Gmail body

EXECUTE NOW.

The attached Markdown is the complete authoritative GenericChess F19 task. Follow the repository-local Gmail/inbox protocol, persist the complete attachment and provenance first, then execute immediately on sandbox only.

Do not wait for another authorization message. Do not begin F20. Do not retain any test-only transient/delta probe in production at E19 closure.

# Complete authoritative attachment

# GenericChess — F19: Native Position-Key Architecture Reassessment + History-Decoupled Runtime Feasibility

## 0. AUTHORITATIVE TASK — EXECUTE NOW

This is the authoritative F19 task for `WD-nanophotonics/GenericChess`.

F18 closed as:

```text
F18_RESULT = AUDIT_ONLY_PASS
H18B_CREATED = false
DELTA_RUNTIME_REQUALIFIED = false
SELECTED_NEXT_BOUNDARY = NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT
```

F17/F18 together established:

```text
F17 bounded delta journal:
sizeof(delta undo) = 656 bytes
semantic differential = PASS
delta push+pop median = 31.39 us
required <= 18.0 us
main measured residual = position-key/history append path

F18 exact key candidate:
key parity = PASS
same-run old key = 13.56 us
candidate key = 11.39 us
speedup = 1.19x
required >= 1.67x

raw digest/direct history:
speedup = 1.19x
required >= 1.20x
```

Therefore F19 MUST NOT try another implementation-level SHA-256 micro-optimization.

F19 asks a different architecture question:

> For the specific future goal of Native semantic attack/check routing, does every transient search child actually need an externally canonical SHA-256 history identity, or can Native maintain an exact current semantic state with a deliberately narrower capability that omits child key/history maintenance while Python remains the authoritative repetition/terminal/history engine?

F19 is an **architecture reassessment and audit-only prototype phase**.

No production runtime, attack routing, or search integration may be retained.

Expected successful result:

```text
F19_RESULT = ARCHITECTURE_DECISION_PASS
```

A genuine correctness/build/audit failure is:

```text
F19_RESULT = BLOCKED
```

F19 must end by selecting exactly one next implementation boundary.

Do not begin F20.

---

# 1. GMAIL / INBOX PROTOCOL

Follow the repository-local GenericChess Gmail/inbox workflow.

Before doing any code/audit work:

1. locate this F19 task by GenericChess Gmail fuzzy subject matching;
2. read the complete authoritative attachment/body;
3. persist the complete task to top-level `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. then execute immediately.

Do not wait for another authorization message after the authoritative F19 attachment is persisted.

Do not execute from subject/snippet alone.

---

# 2. BASELINE HARD LOCK

Required refs:

```text
origin/sandbox =
651cff849b597eae6481b42057f7d59880988d91

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three before H19A.

If `origin/sandbox` moved:

```text
BASELINE_MOVED
STOP
```

Do not reset. Do not force-push. Do not overwrite another task. Do not modify master/chat.

Work only on sandbox.

---

# 3. F13–F18 FROZEN AUTHORITY

Treat all previous results as closed.

## F13

```text
Standard Shogi native_executable = true
action_delivers_check Native parity = PASS
S4 conjunction = PASS
uchifuzume = PASS
```

## F14

```text
public Native semantic attack = PASS
public Native semantic in_check = PASS
packed attack speedup = 9.19x
packed in_check speedup = 8.47x
per-query Python -> Native pack = REJECT
```

## F15

Immutable child-capsule mirror:

```text
semantic correctness = PASS
Profile A shadow overhead = 9.28%
Profile B shadow overhead = 6.25%
retention = REJECT
```

## F16

Full-position mutable undo:

```text
sizeof position = 27296 bytes
sizeof full undo = 27296 bytes
estimated push+pop copy = 109184 bytes
temporary mutable push+pop = 23.89 us
retention gate = FAIL
```

## F17

Transactional delta prototype:

```text
delta undo = 656 bytes
board capacity = 9
hand capacity = 10
aux physical capacity = 24
exact mutation/rollback differential = PASS
delta push+pop median = 31.39 us
p90 = 32.09 us
retention gate = FAIL
selected next boundary = NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION
```

## F18

Canonical key/history implementation optimization:

```text
196 key rows = 0 mismatch
canonical-byte parity = PASS
key 13.56 -> 11.39 us
1.19x only
raw-digest history = 1.19x only
candidate rejected
production source restored to F17-closed baseline
selected next boundary = NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT
```

Do not revive rejected F15/F16/F18 production candidates.

---

# 4. CURRENT ARCHITECTURAL FACT — VERIFY FROM SOURCE

F19 must verify and document the current authority split.

Expected current behavior:

## Current semantic state

`GCSemanticPosition` contains:

```text
rules fingerprint
board
hands
side_to_move
ply
aux
history_lo
history_hi
history_digest
history_len
history_exact
```

## Current checked make

`gc_semantic_runtime_make_mode(...)`:

```text
validate action
copy/construct exact child work state
apply expire-next-turn aux resets
apply ordered effects
promotion
S3 invariants
triggers
aux effects
side_to_move flip
ply increment
S4 postconditions
THEN:
compute canonical semantic position SHA-256
append one history entry
increment history_len
```

## Current attack/check

```text
gc_semantic_runtime_is_square_attacked
gc_semantic_runtime_in_check
```

consume current semantic state and do NOT require repetition history.

## Current terminal/search

Public semantic terminal and probe/fixed-depth search require exact history.

`gc_semantic_repetition_count()` consumes exact full history digest.

`gc_semantic_require_exact_history()` is a fail-closed gate.

F19 must prove these facts with file/function evidence.

---

# 5. THE IDENTITY ARCHITECTURE QUESTION

F19 must explicitly separate three concepts.

## A. External canonical position identity

The frozen public identity:

```text
semantic_position_key
= SHA-256(canonical semantic position JSON)
```

This remains authoritative for public/external position identity, serialization compatibility, history records promising exact external identity, and cross-language differential.

F19 MUST NOT change it.

## B. Exact-history terminal/repetition capability

A Native position that may be used as authority for repetition, terminal, semantic perft terminal cutoffs, or Native fixed-depth/probe search must have exact current history.

F19 MUST NOT weaken this.

## C. Transient semantic state capability

Potential narrow capability for:

```text
attack/check query
S0-S4 action transition needed only to keep a shadow current state
future Python-authoritative search attack/check routing
```

This capability may not need:

```text
child canonical SHA
child history append
repetition authority
terminal authority
Native search authority
```

F19's job is to prove whether C is semantically valid and economically useful.

---

# 6. HARD SAFETY PRINCIPLE — DO NOT MAKE AN INEXACT POSITION LOOK EXACT

A transient/history-decoupled state MUST NOT be represented to existing public terminal/search APIs as an ordinary exact-history position.

The preferred future architecture, if justified, is a **distinct runtime capsule/capability type**, conceptually:

```text
GC_SEM_TRANSIENT_RUNTIME_CAPSULE
```

whose public surface may expose only:

```text
push
pop
is_square_attacked
in_check
debug snapshot
depth
```

and MUST NOT be accepted by:

```text
semantic_terminal
semantic_fixed_depth_search
semantic_probe_search
semantic_perft
history_occurrences
exact-history authority APIs
```

F19 does NOT implement this production capsule.

It only audits/prototypes the architecture.

Do not solve safety by merely leaving a stale exact-history bit set.

Do not let stale history silently pass exact-history gates.

---

# 7. PHASE STRUCTURE

Use:

```text
E18 baseline
  -> H19A architecture/capability audit + test-only prototype
  -> E19 architecture decision closure
```

There is NO production H19B.

H19A may add only audit scripts, test-only C probes, test-only Python wrappers, microbenchmarks, differential fixtures, and evidence.

No retained public API.
No production search integration.

Commit and push H19A before final decision evidence.

---

# 8. CAPABILITY-DEPENDENCY MATRIX

Create a machine-readable matrix for at least:

```text
semantic_position_key
semantic_position_snapshot
semantic_candidate_actions
semantic_guarded_actions
semantic_make_checked
semantic_is_square_attacked
semantic_in_check
semantic_terminal
semantic_candidate_perft
semantic_probe_search
semantic_fixed_depth_search
action_delivers_check
S3 own_anchor_safe
S3 squares_not_attacked
S4 action_delivers_check
S4 opponent_checked
S4 no_legal_reply
```

For every operation record whether it needs:

```text
board
hands
side
ply
aux
current exact position key
history contents
history_len
history_exact
repetition count
terminal authority
```

Classify history dependency:

```text
NONE
ROOT_ONLY
CURRENT_KEY_ONLY
FULL_EXACT_HISTORY
```

Do not infer from API naming alone. Trace actual call paths.

---

# 9. S3 / S4 HISTORY-INDEPENDENCE PROOF

This is mandatory.

F19 must prove whether action validation through S4 can execute without repetition/history maintenance.

Audit:

```text
validate_action
path predicates
state guards
slot guards
effects
promotion
invariants_hold
semantic_attacked_by
semantic_action_delivers_check
semantic_has_s3_reply
postconditions_hold
trigger_event_fires
```

For each state whether any logic reads history, repetition count, canonical position key, or terminal status.

Expected hypothesis:

```text
S0-S4 legality is history-independent
```

except that current implementation computes/appends history as post-transition bookkeeping.

If this hypothesis is false:

```text
TRANSIENT_RUNTIME_SEMANTICALLY_INVALID
```

and the architecture must be rejected.

---

# 10. TEST-ONLY HISTORYLESS MAKE MODE

If and only if Section 9 proves history independence, H19A may implement an audit-only make mode conceptually:

```c
gc_semantic_runtime_make_mode_ex(
    ...,
    include_postconditions,
    history_policy
)
```

with:

```text
history_policy = EXACT_APPEND
history_policy = TRANSIENT_NONE
```

This is test-only.

`EXACT_APPEND` must preserve current production behavior byte-for-byte.

`TRANSIENT_NONE` must perform exact S0-S4 transition and update board, hands, side, ply, aux, promotion/effects/triggers/invariants/postconditions, but MUST NOT compute semantic_position_key SHA or append history or claim exact-history authority for the child.

Do not modify production public `make_checked`.
Do not alter the frozen external key.

---

# 11. NESTED S3-REPLY MODE — CRITICAL

Current S4 `no_legal_reply` calls `semantic_has_s3_reply()` which internally tries child transitions.

The test-only transient mode must ensure those nested S3 reply probes also avoid unnecessary key/history work.

Required:

```text
nested reply transition uses transient/no-history bookkeeping
```

because S3 reply existence asks only whether an S0-S3 legal reply exists.

It must NOT evaluate repetition, call terminal, or append exact history merely for the probe.

This must be differentially proven.

---

# 12. REUSE F17 DELTA JOURNAL — AUDIT-ONLY

Use the F17 H17A transactional delta implementation as the exact semantic oracle/reference for the mutation side.

Do NOT invent a second unrelated delta architecture.

The F19 audit-only prototype should combine:

```text
F17 bounded delta journal
+
pre-view semantics
+
TRANSIENT_NONE history policy
```

The purpose is to isolate whether canonical key/history maintenance was truly the blocker.

Required F17 invariants remain:

```text
first-write old-value journaling
pre-state read semantics
ordered effects
promotion
expire-next-turn
triggers
S3/S4
failure atomicity
nested push/pop
sibling isolation
```

Do not retain the delta code in production in F19.

---

# 13. TRANSIENT STATE DIFFERENTIAL

Use the same frozen Standard Shogi and generic semantic corpus.

After every transient action compare against authoritative Python child:

```text
side_to_move
ply
board
base/current/promoted
hands
aux state
```

Do NOT compare child history because transient mode intentionally omits it.

Require:

```text
state mismatches = 0
```

For selected roots/children also compare:

```text
81 squares × 2 owners attack truth
in_check side 0/1
```

Require zero mismatch.

---

# 14. LEGALITY DIFFERENTIAL

For generic S3/S4 fixtures and Standard Shogi cases compare exact accepted/rejected action truth:

```text
Python authoritative legal/guarded result
vs
test-only transient Native S0-S4 result
```

Cover at least:

```text
own_anchor_safe
squares_not_attacked
action_delivers_check
opponent_checked
no_legal_reply
nifu
uchifuzume
promotion
forced promotion
capture
drop
checking drop
discovered check distinction
```

Require zero mismatch.

---

# 15. HISTORY-CAPABILITY FAIL-CLOSED PROOF

Construct a test-only transient state/capability representation that cannot be accidentally consumed by exact-history APIs.

At minimum prove attempted use is rejected for:

```text
terminal
repetition/history occurrence authority
probe search
fixed-depth semantic search
semantic perft if it uses terminal/repetition authority
```

Attack/check must remain allowed in the conceptual capability model.

If a separate test-only capsule is too invasive, a test-only opaque wrapper plus direct C calls may be used for the prototype, but the architecture decision must still specify a future distinct capsule/type.

Do NOT weaken `gc_semantic_require_exact_history()`.

---

# 16. PUBLIC EXACT POSITION REGRESSION

Current exact public behavior must remain unchanged during the H19A probe.

Require exact parity for:

```text
pack_position
snapshot
position_key
make_checked
candidate_actions
guarded_actions
terminal
probe/fixed-depth search
```

on existing certified cases.

F18's 196 external-key rows must remain:

```text
0 mismatch
```

No public exact-history behavior may change.

---

# 17. PERFORMANCE PROTOCOL — PRIMARY TEST

The central question is:

> What is the lifecycle cost of F17 delta mutation when exact child SHA/history bookkeeping is removed?

Benchmark on frozen Standard Shogi corpus.

Compare same-run:

```text
A. F17-equivalent delta + exact key/history
B. F17 delta + TRANSIENT_NONE
C. current production make_checked reference
```

Use:

```text
warm-up >= 100
measured repetitions >= 5000 where safe
same packed action
same root
same process
```

Report median, p90, p99/max.

For B include delta journal mutation, S3/S4, push, and pop.

No snapshot verification inside timing.

---

# 18. F19 PERFORMANCE DECISION GATES

These are architecture-decision gates, not production-retention gates.

## G1 — HISTORYLESS DELTA LIFECYCLE

Require:

```text
TRANSIENT_NONE delta push+pop median <= 18.0 us
```

AND:

```text
<= 0.60 × F17 31.39 us
```

AND:

```text
p90 <= 22.0 us
```

## G2 — MATERIAL KEY/HISTORY REMOVAL

Require same-run:

```text
exact-history delta / transient delta >= 1.50x
```

or:

```text
absolute saving >= 10 us/push+pop
```

This proves architecture separation, not another tiny optimization, is material.

## G3 — S3/S4 NO-HISTORY BENEFIT

Measure a representative `no_legal_reply` / uchifuzume path.

Require transient nested-reply mode to avoid child key/history calls and show:

```text
canonical child-key computations in nested S3 reply = 0
```

while exact legality parity remains zero mismatch.

No hard speed threshold beyond measurable positive benefit is required here.

## G4 — CAPABILITY SAFETY

All exact-history authority misuse tests must fail closed.

---

# 19. ATTACK/CHECK ROUTING ECONOMIC MODEL

If G1–G4 pass, update the F14–F17 model.

Use:

```text
F14 packed attack speedup = 9.19x
F14 packed check speedup = 8.47x
F11/F15 measured attack/check share
F19 transient push/pop cost
F17/F16/F15 lifecycle references
```

Estimate conservative end-to-end routing headroom for Profile A and Profile B.

Do not fabricate unavailable precision.

Require for selecting transient runtime implementation next:

```text
projected net gain >= 10% Profile A
projected net gain >= 10% Profile B
```

If only one profile clears this, do not force attack routing.

---

# 20. ARCHITECTURE OPTIONS TO COMPARE

F19 must compare at least:

## Option A — Exact external SHA/history on every Native child

Current architecture.

Expected status:

```text
correct but too expensive for fine-grained attack/check shadow
```

## Option B — Capability-separated transient runtime

```text
exact S0-S4 state
no child external SHA/history
separate runtime capsule/type
attack/check capable
terminal/repetition/search ineligible
Python history authority
```

## Option C — Native internal runtime identity

A future internal non-external identity system analogous in purpose to Python F2/F3:

```text
fast runtime hash
exact collision guard
history context
external SHA deferred/on-demand
```

Relevant for a future Native-authoritative terminal/search backend.

F19 must NOT implement it.

## Option D — Native legality kernel without persistent runtime

Broader Native call boundary that may amortize transition cost.

Do not implement.

## Option E — Stop runtime migration and return to strength/evaluator

Valid if economics no longer justify Native integration.

---

# 21. EXTERNAL SHA CONTRACT — HARD FREEZE

F19 MUST NOT:

```text
change semantic_position_key
change canonical JSON
change SHA-256 algorithm
change public history record external identity
change Python Position identity
change ruleset fingerprint
```

Do not propose replacing external SHA with Zobrist.

Any future internal runtime hash must be explicitly non-authoritative and separate.

---

# 22. NO RETAINED PRODUCTION CODE

At E19 closure:

- remove all test-only C transient/delta probe entrypoints from production extension sources;
- remove temporary Python probe wrappers;
- retain only normal audit harnesses, evidence, docs/ADR.

Production semantic runtime behavior at E19 must remain the E18/F17-closed baseline.

If cleanup fails:

```text
PROBE_CLEANUP_FAILURE
STOP
```

---

# 23. SELECT EXACTLY ONE NEXT BOUNDARY

F19 must choose exactly one:

```text
NATIVE_TRANSIENT_DELTA_RUNTIME
NATIVE_INTERNAL_RUNTIME_IDENTITY
NATIVE_LEGALITY_KERNEL
SEARCH_STRENGTH_EVALUATOR_PHASE
```

## Select `NATIVE_TRANSIENT_DELTA_RUNTIME` only if

```text
S0-S4 history independence = PROVEN
G1 = PASS
G2 = PASS
G3 = PASS
G4 = PASS
projected net gain >= 10% A
projected net gain >= 10% B
```

This would authorize F20 to implement a distinct transient runtime capsule.

## Select `NATIVE_INTERNAL_RUNTIME_IDENTITY` only if

historyless transient state is semantically valid but future required capability clearly includes repetition/terminal/search and exact history remains the blocker.

Do not choose it merely because it is theoretically elegant.

## Select `NATIVE_LEGALITY_KERNEL` if

fine-grained runtime attack/check routing is still economically weak, but a broader S0-S4 Native call boundary has a stronger amortization argument.

## Select `SEARCH_STRENGTH_EVALUATOR_PHASE` if

no Native runtime architecture now has credible material end-to-end benefit.

Do not implement the selected boundary.

---

# 24. F4–F18 EVIDENCE IMMUTABILITY

Preserve byte-identically all prior evidence:

```text
artifacts/f4_runtime_cost/**
artifacts/f5_semantic_attack_s3/**
artifacts/f6_target_directed_semantic/**
artifacts/f7_semantic_attack_query_reuse/**
artifacts/f8_push_terminal_check_dedup/**
artifacts/f9_terminal_legal_probe_reuse/**
artifacts/f10_source_index_lifetime/**
artifacts/f11_post_f10_rebaseline/**
artifacts/f12_native_semantic_audit/**
artifacts/f13_native_action_delivers_check/**
artifacts/f14_native_semantic_attack_api/**
artifacts/f15_native_mirrored_position/**
artifacts/f16_native_position_runtime/**
artifacts/f17_native_delta_position_runtime/**
artifacts/f18_native_position_key_history/**

docs/architecture/F4_EVIDENCE.md
...
docs/architecture/F18_EVIDENCE.md

ADR-022 through ADR-035
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f19_position_key_architecture/
```

---

# 25. REQUIRED F19 EVIDENCE

At minimum:

```text
artifacts/f19_position_key_architecture/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    current_identity_architecture.json
    capability_dependency_matrix.json
    s3_s4_history_dependency.json
    exact_history_authority_map.json

    transient_design.json
    transient_fail_closed_model.json

    f17_delta_reference.json
    transient_state_differential.json
    transient_attack_check_differential.json
    transient_legality_differential.json
    nested_s3_reply_differential.json

    public_exact_regression.json
    external_key_196_regression.json

    delta_exact_history_microbench.json
    delta_transient_microbench.json
    current_make_reference_microbench.json
    nested_reply_microbench.json

    performance_gate.json
    attack_routing_economic_model.json

    architecture_options.json
    selected_next_boundary.json

    probe_cleanup.json

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
docs/architecture/F19_EVIDENCE.md
docs/architecture/ADR-036-native-position-identity-capability-split.md
```

ADR-036 must state:

- external canonical SHA remains frozen;
- which operations actually require full exact history;
- whether S0-S4 is history-independent;
- transient runtime capability model;
- why transient runtime must use a distinct capsule/type;
- F17 delta + no-history measured lifecycle;
- projected attack/check integration economics;
- selected next boundary.

---

# 26. TESTS

Focused tests must include:

```text
F19 capability audit
F17 delta differential oracle
test-only transient make
nested S3 reply
S4 no_legal_reply
uchifuzume
action_delivers_check
attack/check
promotion/drop/capture
aux triggers/lifetimes
invalid-action rollback
nested push/pop
sibling isolation

public position_key regression
public make_checked regression
public terminal exact-history regression
probe/fixed-depth exact-history regression

F13/F14/F15/F16/F17/F18 focused regressions
```

Then:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then fresh final build:

```text
python scripts/build_native_zig.py
```

Require PASS.

Do not use AlphaSho. Do not run long games.

---

# 27. RUNTIME SAFETY

Hard limits:

```text
single focused/differential subprocess <= 60 s
single microbenchmark process <= 120 s
```

No multi-hour workload.

On breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve evidence and continue only if the architecture decision remains sound.

---

# 28. FORBIDDEN SCOPE

F19 must not:

```text
retain a transient runtime implementation
retain F17 delta runtime
retain F18 key candidate

change external semantic position key
change canonical JSON
change SHA-256 authority
change public history semantics

route attack/check to Native production
route legality to Native production
route terminal to Native production
route evaluator to Native
route AlphaBeta to Native

change SearchPathRuntime
import Native from Core

implement Native internal runtime hash
implement Native TT/history redesign
implement full Native search

change IR version
change semantic payload version
change native schema version
change fingerprint
change action layout
```

No F20 work.

---

# 29. GIT / PROVENANCE

Expected:

```text
E18 baseline
  -> H19A architecture audit + test-only prototype
  -> E19 audit/evidence closure
```

No retained production semantic/runtime change.

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

# 30. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
S0_S4_HISTORY_DEPENDENCY_FOUND
TRANSIENT_RUNTIME_SEMANTICALLY_INVALID
TRANSIENT_STATE_MISMATCH
TRANSIENT_ATTACK_CHECK_MISMATCH
TRANSIENT_LEGALITY_MISMATCH
NESTED_REPLY_MISMATCH
FAIL_CLOSED_CAPABILITY_FAILURE
PUBLIC_EXACT_POSITION_REGRESSION
EXTERNAL_KEY_REGRESSION
PROBE_CLEANUP_FAILURE
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance gate failure is not a correctness STOP.

It changes the selected next boundary.

---

# 31. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. Current position-identity architecture
6. Capability dependency matrix
7. Exact-history authority map
8. S3/S4 history-independence audit
9. Transient runtime capability design
10. Fail-closed capability model
11. H19A provenance
12. F17 delta reference
13. Transient state differential
14. Transient attack/check differential
15. Transient legality differential
16. Nested S3-reply differential
17. Public exact-position regression
18. External key regression
19. Exact-history delta benchmark
20. Historyless transient delta benchmark
21. Nested-reply benchmark
22. Performance gates
23. Attack/check routing economic model
24. Architecture options
25. Selected next boundary
26. Probe cleanup
27. Tests
28. Evidence / manifest
29. Git
30. Deferred
31. Final verdict

Successful architecture decision:

```text
F19_RESULT = ARCHITECTURE_DECISION_PASS

EXTERNAL_CANONICAL_SHA_FROZEN = PASS
EXACT_HISTORY_AUTHORITY = PASS

S0_S4_HISTORY_INDEPENDENT = <true|false>
TRANSIENT_CAPABILITY_FAIL_CLOSED = PASS

TRANSIENT_STATE_DIFFERENTIAL = PASS
TRANSIENT_ATTACK_CHECK_DIFFERENTIAL = PASS
TRANSIENT_LEGALITY_DIFFERENTIAL = PASS

HISTORYLESS_DELTA_GATE = <PASS|FAIL>
ARCHITECTURE_SEPARATION_BENEFIT = <PASS|FAIL>

SELECTED_NEXT_BOUNDARY =
<NATIVE_TRANSIENT_DELTA_RUNTIME |
 NATIVE_INTERNAL_RUNTIME_IDENTITY |
 NATIVE_LEGALITY_KERNEL |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

PRODUCTION_RUNTIME_CHANGED = false

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Blocked result:

```text
F19_RESULT = BLOCKED
reason = <exact stop condition>
PRODUCTION_RUNTIME_CHANGED = false
FULL_PYTEST = <PASS|FAIL>
FINAL_NATIVE_BUILD = <PASS|FAIL>
```

---

# 32. FINAL STOP

F19 ends after E19 closure.

Do not begin F20.

Do not implement the selected next boundary.

Do not retain test-only transient/delta production hooks.

The next phase must be separately reviewed and authorized.

