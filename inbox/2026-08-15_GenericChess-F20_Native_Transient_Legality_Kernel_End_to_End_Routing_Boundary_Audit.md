<!-- Gmail provenance
message_id: 1a0004071392a069
thread_id: 1a0004071392a069
subject: GenericChess — F20: Native Transient Legality Kernel + End-to-End Routing Boundary Audit
from: W D <icywoods.1@gmail.com>
to: icywoods.1@gmail.com
received: 2026-08-14T05:30:18-07:00
attachment: GenericChess_F20_Native_Transient_Legality_Kernel.md
attachment_id: ANGjdJ-TIDXVvVCMacEmQXQ1PdUQpr8vJRwYzWDoCISLZZ6pXyI-lCgPr3Fd9wLS83kx_V0iA3qD7ZotNKL46llWLPQ1mKg7F5AVCFztEKAn_-tsibvz95OO56kbsCgGPzU3dgmzy21gsXEjT_rw26XGv7cc9F3_RNc1u9WZHHFQVcmk-SJadngXa6ql6rz1pNOSSMwzMncUAuuOoQQsF0s7PBwFUc_iJk9B8zwkUKWBCtjr4ValUxoOgPkwl6iockNnot9AHq1e10xeebb99AwemRdXG75-V0liSoC0xNAYc1r-a3g298JTJEZaHRavcnMLfnjg55BBizRtQpho-grO3WYOytsUN6jV2voLcFh6ak5G1bINl4u4oOztQcvfumEIAZQ-Kdcx_5sHzHiB
attachment_bytes: 34667
fetched_at: 2026-08-15 Asia/Tokyo
processing_state: complete-authoritative-attachment
-->

# Gmail body

# GenericChess — F20: Native Transient Legality Kernel + End-to-End Routing Boundary Audit

## 0. AUTHORITATIVE TASK — EXECUTE NOW

This is the authoritative F20 task for `WD-nanophotonics/GenericChess`.

F19 closed as:

```text
F19_RESULT = ARCHITECTURE_DECISION_PASS
S0_S4_HISTORY_INDEPENDENT = true
HISTORYLESS_DELTA_GATE = PASS
ARCHITECTURE_SEPARATION_BENEFIT = PASS
SELECTED_NEXT_BOUNDARY = NATIVE_LEGALITY_KERNEL
PRODUCTION_RUNTIME_CHANGED = false
```

F19 proved:

```text
exact-history delta push+pop median = 36.38 us
TRANSIENT_NONE delta push+pop median = 14.29 us
exact/transient = 2.55x
absolute saving = 22.08 us

nested S3 reply transient canonical child-key computations = 0
state / legality / attack-check differential = 0 mismatches
```

But F19 did NOT prove >=10% end-to-end gain in both Profile A and B for fine-grained attack/check routing.

F20 implements and audits the broader boundary selected by F19:

> Execute the complete Native S0–S4 legal-action decision as one coarse-grained transient legality kernel, without child external SHA/history bookkeeping, and determine whether that one-shot boundary is economically strong enough to become the next production search integration.

F20 is NOT a production search-routing phase.

F20 may retain a certified Native legality-kernel API/implementation if its own correctness and performance gates pass.

F20 MUST NOT modify production Python `SearchPathRuntime` legal generation or AlphaBeta routing.

Valid final outcomes:

```text
F20_RESULT = LEGALITY_KERNEL_PASS
```

or:

```text
F20_RESULT = AUDIT_ONLY_PASS
```

A correctness/build stop is:

```text
F20_RESULT = BLOCKED
```

Do not begin F21.

---

# 1. GMAIL / INBOX PROTOCOL

Follow the repository-local GenericChess Gmail/inbox workflow.

Before doing any code work:

1. locate this F20 task by fuzzy GenericChess Gmail subject matching;
2. read the complete body/attachment;
3. persist the complete authoritative attachment/body under top-level `inbox/`;
4. record Gmail message/thread provenance and processing status;
5. execute immediately after persistence.

Do not execute from subject/snippet alone.

Do not wait for another authorization after the authoritative F20 task is persisted.

---

# 2. BASELINE HARD LOCK

Required refs:

```text
origin/sandbox =
f2992ce07272a0b8ccee87ddf7a5595e67e1f8ed

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three before H20A.

If sandbox moved:

```text
BASELINE_MOVED
STOP
```

Do not reset.
Do not overwrite another task.
Do not force-push.
Do not modify master/chat.

Work only on sandbox.

---

# 3. F13–F19 FROZEN AUTHORITY

Treat all previous certified results as closed.

## Standard Shogi fingerprint

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

## F13

```text
STANDARD_SHOGI_NATIVE_EXECUTABLE = true
action_delivers_check = native code 2
S4 forbidden-condition conjunction = PASS
uchifuzume = PASS
```

## F14

```text
PUBLIC_NATIVE_SEMANTIC_ATTACK = PASS
PUBLIC_NATIVE_SEMANTIC_IN_CHECK = PASS

packed attack = 9.19x Python
packed check = 8.47x Python

per-query full pack = REJECT
```

## F15

Immutable child-capsule mirror:

```text
correctness = PASS
Profile A overhead = 9.28%
Profile B overhead = 6.25%
retention = REJECT
```

## F16

Full-position mutable undo:

```text
GCSemanticPosition = 27296 bytes
GCSemanticUndo = 27296 bytes
mutable push+pop = 23.89 us
retention = REJECT
```

## F17

Bounded transactional delta:

```text
GCSemanticDeltaUndo = 656 bytes
board journal capacity = 9
hand journal capacity = 10
aux physical capacity = 24

semantic differential = PASS
delta push+pop with exact history = 31.39 us
retention = REJECT
```

## F18

Exact SHA/history micro-optimization:

```text
196 external key rows = zero mismatch
same-run key speedup = 1.19x
raw history speedup = 1.19x
retention = REJECT
```

## F19

Architecture split:

```text
external canonical SHA remains frozen

S0–S4 = history independent

transient F17 delta state:
state differential = PASS
attack/check differential = PASS
legality differential = PASS

exact-history delta = 36.38 us
historyless transient delta = 14.29 us
2.55x architecture separation

fine-grained attack routing not authorized
selected boundary = NATIVE_LEGALITY_KERNEL
```

Do not reopen any rejected F15/F16/F18 design.

---

# 4. CURRENT PYTHON LEGALITY AUTHORITY — FREEZE

Current semantic search path:

```text
SearchPathRuntime.legal_actions()
    -> SemanticEngine.iter_legal_action_bindings()
        -> S0/S1 candidates
        -> one S3 trial transition
        -> S3 invariants
        -> S4 forbidden-condition conjunction
        -> yield SemanticAction + exact binding
    -> _semantic_public_action()
    -> cache:
       _legal_cache
       _bindings[public] = (semantic_action, binding)
```

Current push:

```text
SearchPathRuntime._push_impl(action)
    -> membership in legal_actions
    -> semantic_action, binding = _bindings[action]
    -> engine._transition(parent, semantic_action, binding)
    -> Python runtime identity/history/terminal/TT authority
```

F20 MUST NOT change this production path.

---

# 5. IMPORTANT BINDING FACT — USE IT, DO NOT RE-RUN LEGALITY

Current `SemanticEngine._make_binding_from_action(...)` is the exact bridge from a known legal semantic action back to the pre-action binding.

It:

```text
uses exact pattern identity
uses exact geometry identity
checks actor type
reconstructs exact path for the declared geometry
does not first-match fallback
does not re-infer an alternative geometry
```

Therefore a future Native legality route can be:

```text
Native returns exact ordered packed semantic actions
        |
        v
decode exact stable identity
        |
        v
SemanticAction
        |
        v
_make_binding_from_action(...)
        |
        v
existing Python authoritative _transition on push
```

F20 realistic routing benchmarks MUST use this bridge.

Do NOT benchmark a fake route that skips binding reconstruction.

Do NOT re-run Python guards/S3/S4 merely to obtain bindings.

---

# 6. NATIVE LEGALITY KERNEL DEFINITION

For F20, "Native legality kernel" means:

> Given one exact current semantic state and compiled Native semantic rules, return the complete canonical ordered S0–S4 legal semantic action set.

The kernel includes:

```text
pattern iteration
source/type dispatch
geometry enumeration
target predicates
promotion choices
path predicates
state guards
slot guards
S3 transition
own_anchor_safe
squares_not_attacked
S4 action_delivers_check
S4 opponent_checked
S4 no_legal_reply
nested S3 reply existence
```

The kernel does NOT need:

```text
child external canonical SHA
child history append
repetition count
terminal
max-ply terminal
Native search
TT
evaluator
```

F19 is the authority for this history independence.

---

# 7. CURRENT NATIVE `guarded_actions` — BASELINE AUDIT

Current public Native API already exposes:

```python
generic_chess.native.semantic.guarded_actions(native_rules, position)
```

Current C path conceptually:

```text
candidate actions
for each candidate:
    gc_semantic_runtime_make_checked(...)
        -> exact child transition
        -> exact canonical key/history bookkeeping
    if success:
        retain action
```

H20A must verify this source path and instrument:

```text
candidate count
S3 trial count
S4 count
nested reply count
child canonical-key computations
history appends
attack/check calls
```

This is the baseline Native legality implementation.

---

# 8. F20 SINGLE PRODUCTION CANDIDATE FAMILY

Only one implementation family is authorized:

```text
TRANSIENT S0–S4 LEGALITY KERNEL
```

Do not benchmark multiple competing production architectures and select the winner.

The candidate must reuse the F19-proven semantic idea:

```text
S0–S4 transition
+
history policy = TRANSIENT_NONE
```

Internal candidate-child and nested reply probes must:

```text
NOT compute external canonical SHA
NOT append history
NOT claim terminal/repetition authority
```

The kernel returns only legal action identities.

No transient child capsule escapes the kernel.

This is materially safer than exposing an inexact public position.

---

# 9. PREFERRED FUSED ONE-SHOT API

The preferred retained boundary, if authorized, is a fused one-shot call conceptually:

```python
transient_legal_actions(
    native_rules,
    state_payload,
) -> tuple[int, ...]
```

where `state_payload` contains current-state semantic data only:

```text
ruleset fingerprint / matching rule authority
side_to_move
ply
board
hands
aux
```

and deliberately excludes:

```text
history
repetition counts
external child key
```

The exact API name may differ.

### Safety requirement

The one-shot call must:

1. parse current state into a local/internal semantic position;
2. mark/use it only as transient legality state;
3. run complete S0–S4;
4. return packed actions;
5. destroy the local state;
6. expose no transient position capsule.

Therefore terminal/search APIs cannot accidentally consume this state.

### Reuse

Refactor/reuse existing internal position packing helpers if clean.

Do not duplicate the entire semantic position parser merely to create this API.

If a clean fused parser/helper refactor would be too invasive, a packed-capsule transient legality API may be used instead, but H20 must then include the capsule-allocation boundary in all realistic routing measurements.

---

# 10. H20 PHASE STRUCTURE

Use:

```text
E19 baseline
  -> H20A audit / harness / candidate probe
  -> optional H20B retained Native legality kernel
  -> E20 certification / decision closure
```

## H20A

Allowed:

```text
audit scripts
test-only C counters/probes
test-only fused transient kernel
performance harness
exact action bridge harness
```

H20A MUST NOT route production Python search.

Commit and push H20A.

## H20B

Create only if Sections 18–19 authorization gates pass.

H20B may retain:

```text
one Native transient legality-kernel API
its Python native wrapper
internal helper/refactor needed by that API
focused correctness tests
```

H20B MUST NOT change Core or AlphaBeta routing.

Commit and push H20B before final E20 evidence.

If final H20B retention gates fail:

```text
cleanly revert H20B production kernel
retain H20A/E20 diagnostic evidence
F20_RESULT = AUDIT_ONLY_PASS
```

---

# 11. STATE-ONLY PAYLOAD CONTRACT

A one-shot transient legality payload must be constructed from the current Python `Position`.

It must encode exactly:

```text
ruleset fingerprint match
side_to_move
ply if needed by effects/guards
board:
    occupied
    owner
    base type
    current type
    promoted
hands
aux logical/physical state
```

It must NOT require:

```text
GameState.history
repetition_counts
position_identity_key
external SHA
```

For formal timing, record Python-side state-payload construction cost separately.

Do not hide it inside "Native kernel" timing.

---

# 12. NO CHILD EXTERNAL SHA — HARD GATE

Inside the transient legality kernel:

```text
candidate child canonical key computations = 0
candidate child history appends = 0

nested S3 reply canonical key computations = 0
nested S3 reply history appends = 0
```

The current/root input may carry or not carry exact history depending on implementation, but legality must not consult it.

Any child key/history work:

```text
TRANSIENT_LEGALITY_KEY_LEAK
```

and H20B is not authorized.

---

# 13. CANONICAL ACTION ORDER — HARD AUTHORITY

Native legal actions must match Python exactly in:

```text
count
order
kind
pattern identity
geometry identity
actor current type
base type
source
target
promotion target
```

Do not compare as unordered sets only.

Canonical order is part of the search determinism contract.

---

# 14. STANDARD SHOGI DIFFERENTIAL

Hard assert Standard Shogi fingerprint.

Use at minimum:

```text
the four frozen Standard Shogi prefixes
all legal root actions
bounded depth-1 children
bounded deterministic depth-2 states
```

For every state compare:

```text
Python SemanticEngine.iter_legal_action_bindings
vs
Native transient legality kernel
```

Require:

```text
action count mismatch = 0
action order mismatch = 0
identity mismatch = 0
```

Record row-level evidence.

---

# 15. GENERIC SEMANTIC DIFFERENTIAL

Use at minimum the executable Native semantic corpus:

```text
cannon
castling
en_passant
nifu
uchifuzume
weird_0
weird_1
weird_2
weird_3
weird_4
```

Also include focused fixtures for:

```text
own_anchor_safe
squares_not_attacked
path guards
state guards
slot guards
promotion
forced promotion
capture-to-hand
drop
checking drop
action_delivers_check
opponent_checked
no_legal_reply
aux trigger
expire_next_turn
```

Require exact action-order parity.

---

# 16. EXACT PYTHON ACTION / BINDING BRIDGE DIFFERENTIAL

For every Native packed legal action in the Standard Shogi corpus:

1. decode packed bit fields directly;
2. map Native numeric indices through frozen/precomputed:
   ```text
   type_ids
   pattern_ids
   geometry_ids
   ```
3. construct the exact `SemanticAction`;
4. convert to public action using current `_semantic_public_action`;
5. find exact pattern by ID using a precomputed map;
6. call:
   ```text
   engine._make_binding_from_action(position, semantic_action, pattern)
   ```
7. compare that reconstructed binding with the binding yielded by Python authoritative `iter_legal_action_bindings`.

Compare at least:

```text
pattern
geometry_id
actor_owner
actor_type
actor_base
actor_current
source
target
promotion_target_id
path
```

Require zero mismatch.

Then apply:

```text
engine._transition(position, semantic_action, reconstructed_binding)
```

and compare child with the Python authoritative binding child.

Require zero mismatch.

This proves Native legality output can feed the current Python push without re-running S0–S4.

---

# 17. ACTION DECODE PERFORMANCE CONTRACT

Do not perform one C-extension `unpack_action()` call per returned action in the realistic routing benchmark unless the final production design genuinely requires it.

The 64-bit action layout is frozen.

Preferred realistic bridge:

```text
Python integer bit decode
+
precomputed tuple/index maps
```

Measure separately:

```text
packed tuple -> semantic actions
semantic actions -> public actions
binding reconstruction
```

Do not introduce coordinate-only identity.

Do not drop pattern/geometry identity.

---

# 18. H20B CORRECTNESS AUTHORIZATION GATES

All must pass.

## G1 — S0–S4 exact parity

```text
Standard Shogi order/identity mismatches = 0
generic corpus mismatches = 0
```

## G2 — binding bridge

```text
binding mismatches = 0
Python child mismatches = 0
```

## G3 — history independence enforced

```text
candidate child key computations = 0
nested reply child key computations = 0
history appends = 0
```

## G4 — public exact APIs unchanged

Require existing exact:

```text
guarded_actions if left public
make_checked
position_key
terminal
perft
probe search
fixed-depth search
```

to retain current semantics.

If H20B replaces the internal implementation of existing `guarded_actions`, exact output parity must be complete.

## G5 — fail-closed input validation

Reject:

```text
wrong fingerprint
non-native-executable rules
malformed board
invalid owner/type
invalid aux
out-of-range square
invalid payload shape
```

---

# 19. H20B PERFORMANCE AUTHORIZATION GATE

Run on same process/environment.

## 19.1 Packed-state Native legality kernel

Compare:

```text
current exact-history Native guarded_actions
vs
transient Native legality kernel
```

on the same already-packed states.

Require one of:

```text
aggregate speedup >= 1.50x
```

OR:

```text
absolute saving >= 50 us per full legality operation
```

and:

```text
no semantic case stable regression > 5%
```

## 19.2 Python authoritative legality comparison

Compare:

```text
Python SemanticEngine.iter_legal_action_bindings
```

against Native kernel only, excluding payload/decode/binding bridge.

This is diagnostic, not the routing decision.

Record:

```text
Python us/operation
Native kernel us/operation
kernel speedup
```

If G1–G5 pass but the transient kernel is not materially faster than the existing Native path:

```text
H20B_CREATED = false
```

Do not retain speculative API.

---

# 20. REALISTIC ONE-SHOT ROUTING COST

This is the most important F20 integration measurement.

For each Python `Position`, time the complete route:

```text
A. build state-only Native payload
B. enter Native once
C. parse/pack current transient state
D. complete Native S0–S4 legality kernel
E. return ordered packed actions
F. Python direct bit decode
G. stable ID mapping
H. SemanticAction creation
I. public Action creation
J. exact binding reconstruction
```

Result must be equivalent to:

```text
tuple(public legal actions)
+
bindings dict
```

currently produced by `SearchPathRuntime.legal_actions()`.

Do NOT include Python authoritative child transition because current legal generation also does not retain child positions.

Do NOT omit binding reconstruction.

Report:

```text
payload_build_us
native_parse_pack_us if separable
native_kernel_us
return_decode_us
public_action_us
binding_rebuild_us
total_one_shot_us
python_authoritative_us
speedup
```

---

# 21. LEGALITY POSITION CORPUS FOR PERFORMANCE

Use:

1. four frozen Standard Shogi prefixes;
2. deterministic children sampled from those prefixes;
3. positions sampled from actual Profile A/B search traces;
4. control generic semantic fixtures.

Do not measure only initial position.

Record branching factor and candidate/legal counts.

At minimum:

```text
>= 40 distinct Standard Shogi positions
```

unless the bounded search corpus cannot produce that many unique states; if not, record exact reason and use all available deterministic states.

---

# 22. ONE-SHOT DIRECT ROUTING ECONOMIC GATE

To select future direct routing, require aggregate realistic one-shot legality:

```text
speedup >= 1.50x
```

versus Python authoritative legal-action+binding generation,

AND:

```text
median absolute saving >= 100 us per expanded legality operation
```

AND:

```text
at least 80% of measured Standard Shogi positions faster
```

AND:

```text
no important action-count/branching class stable regression > 10%
```

These are routing-decision gates, not H20B kernel-retention gates.

---

# 23. ATOMIC NATIVE CALL LATENCY / INTERRUPTIBILITY

The legality kernel is one synchronous C call.

Record per operation:

```text
median
p90
p99
max
```

Across measured Standard Shogi positions.

For future direct routing require:

```text
max observed <= 10 ms
```

under the frozen corpus.

If any stable >10 ms operation exists:

```text
NATIVE_LEGALITY_INTERRUPTIBILITY_RISK
```

Direct production routing must not be selected.

Do NOT add callback checkpoints into C in F20.

---

# 24. SEARCH-SHADOW ROUTING PROBE — TEST/AUDIT ONLY

If the realistic one-shot gate in Section 22 passes, run a test-only AlphaBeta shadow/alternate legality probe.

Do NOT modify production `SearchPathRuntime`.

Use an audit-only AI/native wrapper, subclass, monkey-patched method, or isolated harness that:

```text
replaces only semantic legal-action generation
with the Native one-shot legality route

but keeps:
Python SearchPathRuntime
Python push transition
Python terminal
Python repetition/history
Python runtime hash
Python TT
Python evaluator
Python qsearch policy
Python move ordering
```

The bridge must populate equivalent:

```text
_legal_cache
_bindings
```

for the audit runtime.

No Native position persists across nodes in this route.

---

# 25. SEARCH PARITY FOR SHADOW ROUTE

Compare baseline Python search vs test-only Native-legality route.

Require exact:

```text
chosen action
score
PV
nodes
qnodes
completed depth
termination reason
terminal result
legal action order
TT probes
TT hits
TT stores
TT cutoffs
runtime history evidence
TT eligibility
child external key computation counters
```

Only timing/native-legality counters may differ.

Run:

```text
PVS
aspiration
qsearch
root tactical
cancellation
node budget
time budget
exception rollback
```

focused routes.

---

# 26. PROFILE A/B END-TO-END PERFORMANCE

If Section 24 is authorized:

## Profile A

```text
TT on
ordering off
qsearch max depth = 0
root tactical off
max_depth = 2
max_nodes = 512
fresh TT
no wall-clock limit
```

## Profile B

Current production/default tuning:

```text
max_nodes = 256
deterministic node budget
no wall-clock limit
```

For each of four Semantic Shogi cases:

```text
1 warm-up
5 measured runs
```

Compare:

```text
baseline Python legality
test-only Native one-shot legality
```

Formal runs:

```text
no heavy trace
no snapshot differential inside timing
```

Report per case and aggregate.

---

# 27. DIRECT ROUTING SELECTION GATE

Select future:

```text
NATIVE_LEGAL_ACTION_ROUTING_DIRECT
```

only if all are true:

```text
H20 kernel correctness = PASS
realistic one-shot legality gate = PASS
search parity = PASS
interruptibility = PASS

Profile A end-to-end gain >= 8%
Profile B end-to-end gain >= 8%

at least 3/4 semantic cases in each profile gain >= 5%
no semantic case stable regression > 3%
```

F20 does NOT implement the production route.

---

# 28. IF ONE-SHOT PACKING IS THE BOTTLENECK

If:

```text
packed Native legality kernel is strongly faster
but realistic one-shot route fails because state payload/packing dominates
```

then update the economic model using F19 transient runtime:

```text
transient delta lifecycle = 14.29 us
```

Estimate:

```text
persistent transient state
+
Native legality queries
+
Python binding reconstruction
```

against current Python legality.

If conservative projected end-to-end gain is:

```text
>= 10% Profile A
>= 10% Profile B
```

then select:

```text
NATIVE_TRANSIENT_LEGALITY_RUNTIME
```

as the next boundary.

Do NOT implement it in F20.

This future runtime would be a distinct capability type and remain terminal/repetition/search-authority ineligible unless separately expanded.

---

# 29. IF ACTION BRIDGE IS THE BOTTLENECK

If Native kernel and state packing are strong, but:

```text
decode/public action/binding reconstruction
```

consumes most of the advantage, quantify it.

Do NOT weaken semantic action identity.

Do NOT replace binding reconstruction with first-match or coordinate-only matching.

If bridge cost alone prevents material routing benefit, choose:

```text
SEARCH_STRENGTH_EVALUATOR_PHASE
```

unless a clearly bounded future `NATIVE_ACTION_BRIDGE` phase has >=10% modeled end-to-end benefit.

F20's final allowed selection list intentionally does not include open-ended bridge micro-optimization.

---

# 30. FINAL NEXT-BOUNDARY SELECTION

Choose exactly one:

```text
NATIVE_LEGAL_ACTION_ROUTING_DIRECT
NATIVE_TRANSIENT_LEGALITY_RUNTIME
SEARCH_STRENGTH_EVALUATOR_PHASE
```

### Choose `NATIVE_LEGAL_ACTION_ROUTING_DIRECT`

only by Section 27 gate.

### Choose `NATIVE_TRANSIENT_LEGALITY_RUNTIME`

only if:

```text
packed kernel materially strong
one-shot route bottleneck = state packing/capsule boundary
F19 transient runtime model removes that bottleneck
projected >=10% gain in both A/B
```

### Choose `SEARCH_STRENGTH_EVALUATOR_PHASE`

if neither Native legality integration architecture has credible >=10% end-to-end benefit.

Do not choose based on theoretical ceiling alone.

Do not start the selected phase.

---

# 31. H20B RETENTION POLICY

A faster standalone Native legality kernel may be retained even though production Python routing remains deferred, but only if:

```text
all H20B correctness gates pass
H20B performance gate passes
public/fail-closed semantics are clean
no old behavior regresses
```

Reason:

```text
Native guarded/legal action execution is an already-existing certified public Native capability;
replacing unnecessary child SHA/history work inside that capability is independently useful.
```

If those gates fail:

```text
H20B_RETAINED = false
F20_RESULT = AUDIT_ONLY_PASS
```

Do not keep speculative transient APIs.

---

# 32. NO CORE NATIVE DEPENDENCY

Hard invariant:

```text
generic_chess.core.*
```

must remain Native-unaware.

F20 MUST NOT import:

```text
generic_chess.native
```

from Core.

No Native field in:

```text
SearchPathRuntime
_Frame
Position
GameState
```

Any future routing belongs in AI/native integration.

---

# 33. PUBLIC EXACT-HISTORY AUTHORITY FREEZE

Do not change:

```text
semantic_position_key
canonical JSON identity
external SHA-256
exact-history pack semantics
terminal exact-history gate
repetition authority
perft terminal semantics
probe/fixed-depth search exact-history requirements
```

The transient legality kernel is history-independent because it returns actions only.

It must not weaken exact-history APIs.

---

# 34. VERSION / IDENTITY INVARIANTS

Must remain unchanged:

```text
Standard Shogi fingerprint
Semantic IR version = 2
SEMANTIC_PAYLOAD_VERSION = 2
NATIVE_SCHEMA_VERSION = native-0.5.0

semantic action bit layout
external semantic position key
history digest format
Python runtime identity/history contract
```

A new function entrypoint does not itself require a schema bump.

If a serialized semantic payload format must change:

```text
VERSION_CONTRACT_BLOCKED
STOP
```

---

# 35. F13/F14/F19 REGRESSION HARD GATE

Re-run at minimum:

```text
F13 action_delivers_check witnesses
S4 truth table
checking/non-checking drop
uchifuzume

F14 648 attack queries
F14 8 in_check queries
curated semantic attack differential

F19 S0-S4 history independence assertions
F19 nested reply zero-key expectation
F19 public exact-position/key regressions
```

All PASS.

---

# 36. F4–F19 EVIDENCE IMMUTABILITY

Preserve byte-identically all previous evidence/artifacts/docs:

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
artifacts/f19_position_key_architecture/**

docs/architecture/F4_EVIDENCE.md
...
docs/architecture/F19_EVIDENCE.md

ADR-022 through ADR-036
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f20_native_legality_kernel/
```

---

# 37. REQUIRED F20 EVIDENCE

At minimum:

```text
artifacts/f20_native_legality_kernel/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    python_legality_authority.json
    native_guarded_baseline.json
    transient_legality_design.json

    state_only_payload_contract.json
    child_key_history_counters.json

    standard_shogi_legality_rows.jsonl
    standard_shogi_legality_summary.json
    generic_legality_differential.json

    binding_bridge_rows.jsonl
    binding_bridge_summary.json
    child_transition_bridge_parity.json

    fail_closed_api.json
    exact_history_regression.json
    f13_f14_f19_regression.json

    packed_native_baseline_microbench.json
    packed_transient_kernel_microbench.json
    python_legality_microbench.json

    payload_build_microbench.json
    action_decode_microbench.json
    binding_rebuild_microbench.json
    one_shot_legality_microbench.json

    atomic_latency.json
    one_shot_routing_gate.json

    search_shadow_parity.json
    profile_a_baseline.jsonl
    profile_a_native_legality.jsonl
    profile_b_baseline.jsonl
    profile_b_native_legality.jsonl
    end_to_end_search_performance.json

    transient_runtime_economic_model.json
    selected_next_boundary.json

    h20b_authorization_gate.json
    h20b_retention_gate.json

    old_evidence_before.sha256
    old_evidence_after.sha256

    focused_tests.txt
    full_pytest.txt
    final_native_build.txt

    final_verdict.json
    manifest.json
```

For files not run because a prior gate failed, write explicit machine-readable:

```text
NOT_RUN_NOT_AUTHORIZED
```

Do not fabricate measurements.

Create:

```text
docs/architecture/F20_EVIDENCE.md
docs/architecture/ADR-037-native-transient-legality-kernel.md
```

ADR-037 must document:

- Python legality/binding authority;
- why S0–S4 does not need child history;
- exact transient legality-kernel boundary;
- canonical action-order contract;
- exact Python binding reconstruction;
- packed-kernel speed;
- one-shot state-pack/decode/binding economics;
- interruptibility;
- retained Native kernel or rejection;
- selected next integration boundary.

---

# 38. TESTS

Focused tests must include:

```text
Native transient legality kernel
state-only payload validation
zero child key/history instrumentation

Standard Shogi ordered legal differential
generic IR-v2 ordered legal differential

exact packed-action decode
stable ID mapping
binding reconstruction
Python child transition using reconstructed binding

S3 own_anchor_safe
squares_not_attacked
S4 action_delivers_check
opponent_checked
no_legal_reply
nested reply
nifu
uchifuzume
promotion
drop
capture
aux trigger/lifetime

wrong fingerprint
malformed payload
invalid action data

existing guarded_actions
make_checked
position_key
terminal
perft
probe/fixed-depth

F13/F14/F19 focused regressions
F3 history/TT regressions
search interruptibility regressions
```

Then full:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then fresh final Native build:

```text
python scripts/build_native_zig.py
```

Require PASS.

No AlphaSho.

No long games.

---

# 39. RUNTIME SAFETY

Hard controller limits:

```text
single focused/differential subprocess <= 60 s
single microbenchmark process <= 120 s
single Profile A/B measured search <= 120 s
```

No multi-hour workload.

On breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve completed evidence.

Do not restart an hours-long runner.

---

# 40. FORBIDDEN SCOPE

F20 must not:

```text
modify production SearchPathRuntime legality
modify production AlphaBeta routing
import Native into Core

retain Native transient position runtime
retain F17 delta runtime stack

route attack/check separately
route terminal to Native
route repetition/history to Native
route evaluator to Native
route search to Native

change TT
change qsearch
change move ordering
change evaluator
change search heuristics

add attack cache
add terminal cache
add bitboards
add incremental attack map

change external SHA
change canonical JSON
change semantic fingerprint
change IR/payload/schema versions
change action layout
```

No F21 work.

---

# 41. GIT / PROVENANCE

Possible retained path:

```text
E19
  -> H20A audit/harness
  -> H20B retained Native transient legality kernel
  -> E20 closure
```

Possible audit-only path:

```text
E19
  -> H20A
  -> E20 audit closure
```

If H20B is created but fails final retention:

```text
revert H20B production kernel cleanly
retain diagnostic evidence
close E20 audit-only
```

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

# 42. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
VERSION_CONTRACT_BLOCKED

TRANSIENT_LEGALITY_KEY_LEAK

STANDARD_SHOGI_LEGALITY_MISMATCH
GENERIC_LEGALITY_MISMATCH
CANONICAL_ACTION_ORDER_MISMATCH

BINDING_BRIDGE_MISMATCH
CHILD_TRANSITION_BRIDGE_MISMATCH

FAIL_CLOSED_API_FAILURE
EXACT_HISTORY_AUTHORITY_REGRESSION

F13_F14_F19_REGRESSION

SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE

OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance failure is not a correctness STOP.

It determines H20B retention and the next boundary.

---

# 43. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. Python legality/binding authority
6. Existing Native guarded-actions baseline
7. Transient legality-kernel design
8. State-only payload contract
9. Child key/history elimination
10. H20A provenance
11. H20B authorization
12. H20B implementation or rejection
13. Standard Shogi ordered legality differential
14. Generic semantic legality differential
15. Packed-action decode / stable-ID bridge
16. Binding reconstruction differential
17. Python child-transition bridge parity
18. Fail-closed API
19. Exact-history/public API regression
20. F13/F14/F19 regression
21. Packed Native kernel benchmark
22. Python legality benchmark
23. State-payload / decode / binding cost
24. Realistic one-shot legality benchmark
25. Atomic latency / interruptibility
26. One-shot routing gate
27. Search-shadow parity
28. Profile A/B end-to-end performance
29. Transient-runtime economic model
30. H20B retention gate
31. Selected next boundary
32. Tests
33. Evidence / manifest
34. Git
35. Deferred
36. Final verdict

Successful retained kernel verdict:

```text
F20_RESULT = LEGALITY_KERNEL_PASS

TRANSIENT_NATIVE_LEGALITY_KERNEL = PASS
CHILD_KEY_HISTORY_ELIMINATED = PASS

STANDARD_SHOGI_ORDERED_LEGALITY = PASS
GENERIC_ORDERED_LEGALITY = PASS

BINDING_BRIDGE = PASS
PYTHON_CHILD_TRANSITION_BRIDGE = PASS

EXACT_HISTORY_AUTHORITY = PASS
FAIL_CLOSED_API = PASS

H20B_RETAINED = true

ONE_SHOT_ROUTING_GATE = <PASS|FAIL|NOT_RUN_NOT_AUTHORIZED>

SELECTED_NEXT_BOUNDARY =
<NATIVE_LEGAL_ACTION_ROUTING_DIRECT |
 NATIVE_TRANSIENT_LEGALITY_RUNTIME |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

PRODUCTION_SEARCH_ROUTING_CHANGED = false

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Audit-only verdict:

```text
F20_RESULT = AUDIT_ONLY_PASS

H20B_CREATED = <true|false>
H20B_RETAINED = false
reason = <exact failed gate>

SELECTED_NEXT_BOUNDARY =
<NATIVE_TRANSIENT_LEGALITY_RUNTIME |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

PRODUCTION_SEARCH_ROUTING_CHANGED = false

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Blocked verdict:

```text
F20_RESULT = BLOCKED
reason = <exact stop condition>

PRODUCTION_SEARCH_ROUTING_CHANGED = false

FULL_PYTEST = <PASS|FAIL>
FINAL_NATIVE_BUILD = <PASS|FAIL>
```

---

# 44. FINAL STOP

F20 ends after E20 closure.

Do not begin F21.

Do not route production Python search to Native.

Do not implement the selected next boundary.

The next phase must be separately audited and authorized.


# Complete authoritative attachment

# GenericChess — F20: Native Transient Legality Kernel + End-to-End Routing Boundary Audit

## 0. AUTHORITATIVE TASK — EXECUTE NOW

This is the authoritative F20 task for `WD-nanophotonics/GenericChess`.

F19 closed as:

```text
F19_RESULT = ARCHITECTURE_DECISION_PASS
S0_S4_HISTORY_INDEPENDENT = true
HISTORYLESS_DELTA_GATE = PASS
ARCHITECTURE_SEPARATION_BENEFIT = PASS
SELECTED_NEXT_BOUNDARY = NATIVE_LEGALITY_KERNEL
PRODUCTION_RUNTIME_CHANGED = false
```

F19 proved:

```text
exact-history delta push+pop median = 36.38 us
TRANSIENT_NONE delta push+pop median = 14.29 us
exact/transient = 2.55x
absolute saving = 22.08 us

nested S3 reply transient canonical child-key computations = 0
state / legality / attack-check differential = 0 mismatches
```

But F19 did NOT prove >=10% end-to-end gain in both Profile A and B for fine-grained attack/check routing.

F20 implements and audits the broader boundary selected by F19:

> Execute the complete Native S0–S4 legal-action decision as one coarse-grained transient legality kernel, without child external SHA/history bookkeeping, and determine whether that one-shot boundary is economically strong enough to become the next production search integration.

F20 is NOT a production search-routing phase.

F20 may retain a certified Native legality-kernel API/implementation if its own correctness and performance gates pass.

F20 MUST NOT modify production Python `SearchPathRuntime` legal generation or AlphaBeta routing.

Valid final outcomes:

```text
F20_RESULT = LEGALITY_KERNEL_PASS
```

or:

```text
F20_RESULT = AUDIT_ONLY_PASS
```

A correctness/build stop is:

```text
F20_RESULT = BLOCKED
```

Do not begin F21.

---

# 1. GMAIL / INBOX PROTOCOL

Follow the repository-local GenericChess Gmail/inbox workflow.

Before doing any code work:

1. locate this F20 task by fuzzy GenericChess Gmail subject matching;
2. read the complete body/attachment;
3. persist the complete authoritative attachment/body under top-level `inbox/`;
4. record Gmail message/thread provenance and processing status;
5. execute immediately after persistence.

Do not execute from subject/snippet alone.

Do not wait for another authorization after the authoritative F20 task is persisted.

---

# 2. BASELINE HARD LOCK

Required refs:

```text
origin/sandbox =
f2992ce07272a0b8ccee87ddf7a5595e67e1f8ed

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three before H20A.

If sandbox moved:

```text
BASELINE_MOVED
STOP
```

Do not reset.
Do not overwrite another task.
Do not force-push.
Do not modify master/chat.

Work only on sandbox.

---

# 3. F13–F19 FROZEN AUTHORITY

Treat all previous certified results as closed.

## Standard Shogi fingerprint

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

## F13

```text
STANDARD_SHOGI_NATIVE_EXECUTABLE = true
action_delivers_check = native code 2
S4 forbidden-condition conjunction = PASS
uchifuzume = PASS
```

## F14

```text
PUBLIC_NATIVE_SEMANTIC_ATTACK = PASS
PUBLIC_NATIVE_SEMANTIC_IN_CHECK = PASS

packed attack = 9.19x Python
packed check = 8.47x Python

per-query full pack = REJECT
```

## F15

Immutable child-capsule mirror:

```text
correctness = PASS
Profile A overhead = 9.28%
Profile B overhead = 6.25%
retention = REJECT
```

## F16

Full-position mutable undo:

```text
GCSemanticPosition = 27296 bytes
GCSemanticUndo = 27296 bytes
mutable push+pop = 23.89 us
retention = REJECT
```

## F17

Bounded transactional delta:

```text
GCSemanticDeltaUndo = 656 bytes
board journal capacity = 9
hand journal capacity = 10
aux physical capacity = 24

semantic differential = PASS
delta push+pop with exact history = 31.39 us
retention = REJECT
```

## F18

Exact SHA/history micro-optimization:

```text
196 external key rows = zero mismatch
same-run key speedup = 1.19x
raw history speedup = 1.19x
retention = REJECT
```

## F19

Architecture split:

```text
external canonical SHA remains frozen

S0–S4 = history independent

transient F17 delta state:
state differential = PASS
attack/check differential = PASS
legality differential = PASS

exact-history delta = 36.38 us
historyless transient delta = 14.29 us
2.55x architecture separation

fine-grained attack routing not authorized
selected boundary = NATIVE_LEGALITY_KERNEL
```

Do not reopen any rejected F15/F16/F18 design.

---

# 4. CURRENT PYTHON LEGALITY AUTHORITY — FREEZE

Current semantic search path:

```text
SearchPathRuntime.legal_actions()
    -> SemanticEngine.iter_legal_action_bindings()
        -> S0/S1 candidates
        -> one S3 trial transition
        -> S3 invariants
        -> S4 forbidden-condition conjunction
        -> yield SemanticAction + exact binding
    -> _semantic_public_action()
    -> cache:
       _legal_cache
       _bindings[public] = (semantic_action, binding)
```

Current push:

```text
SearchPathRuntime._push_impl(action)
    -> membership in legal_actions
    -> semantic_action, binding = _bindings[action]
    -> engine._transition(parent, semantic_action, binding)
    -> Python runtime identity/history/terminal/TT authority
```

F20 MUST NOT change this production path.

---

# 5. IMPORTANT BINDING FACT — USE IT, DO NOT RE-RUN LEGALITY

Current `SemanticEngine._make_binding_from_action(...)` is the exact bridge from a known legal semantic action back to the pre-action binding.

It:

```text
uses exact pattern identity
uses exact geometry identity
checks actor type
reconstructs exact path for the declared geometry
does not first-match fallback
does not re-infer an alternative geometry
```

Therefore a future Native legality route can be:

```text
Native returns exact ordered packed semantic actions
        |
        v
decode exact stable identity
        |
        v
SemanticAction
        |
        v
_make_binding_from_action(...)
        |
        v
existing Python authoritative _transition on push
```

F20 realistic routing benchmarks MUST use this bridge.

Do NOT benchmark a fake route that skips binding reconstruction.

Do NOT re-run Python guards/S3/S4 merely to obtain bindings.

---

# 6. NATIVE LEGALITY KERNEL DEFINITION

For F20, "Native legality kernel" means:

> Given one exact current semantic state and compiled Native semantic rules, return the complete canonical ordered S0–S4 legal semantic action set.

The kernel includes:

```text
pattern iteration
source/type dispatch
geometry enumeration
target predicates
promotion choices
path predicates
state guards
slot guards
S3 transition
own_anchor_safe
squares_not_attacked
S4 action_delivers_check
S4 opponent_checked
S4 no_legal_reply
nested S3 reply existence
```

The kernel does NOT need:

```text
child external canonical SHA
child history append
repetition count
terminal
max-ply terminal
Native search
TT
evaluator
```

F19 is the authority for this history independence.

---

# 7. CURRENT NATIVE `guarded_actions` — BASELINE AUDIT

Current public Native API already exposes:

```python
generic_chess.native.semantic.guarded_actions(native_rules, position)
```

Current C path conceptually:

```text
candidate actions
for each candidate:
    gc_semantic_runtime_make_checked(...)
        -> exact child transition
        -> exact canonical key/history bookkeeping
    if success:
        retain action
```

H20A must verify this source path and instrument:

```text
candidate count
S3 trial count
S4 count
nested reply count
child canonical-key computations
history appends
attack/check calls
```

This is the baseline Native legality implementation.

---

# 8. F20 SINGLE PRODUCTION CANDIDATE FAMILY

Only one implementation family is authorized:

```text
TRANSIENT S0–S4 LEGALITY KERNEL
```

Do not benchmark multiple competing production architectures and select the winner.

The candidate must reuse the F19-proven semantic idea:

```text
S0–S4 transition
+
history policy = TRANSIENT_NONE
```

Internal candidate-child and nested reply probes must:

```text
NOT compute external canonical SHA
NOT append history
NOT claim terminal/repetition authority
```

The kernel returns only legal action identities.

No transient child capsule escapes the kernel.

This is materially safer than exposing an inexact public position.

---

# 9. PREFERRED FUSED ONE-SHOT API

The preferred retained boundary, if authorized, is a fused one-shot call conceptually:

```python
transient_legal_actions(
    native_rules,
    state_payload,
) -> tuple[int, ...]
```

where `state_payload` contains current-state semantic data only:

```text
ruleset fingerprint / matching rule authority
side_to_move
ply
board
hands
aux
```

and deliberately excludes:

```text
history
repetition counts
external child key
```

The exact API name may differ.

### Safety requirement

The one-shot call must:

1. parse current state into a local/internal semantic position;
2. mark/use it only as transient legality state;
3. run complete S0–S4;
4. return packed actions;
5. destroy the local state;
6. expose no transient position capsule.

Therefore terminal/search APIs cannot accidentally consume this state.

### Reuse

Refactor/reuse existing internal position packing helpers if clean.

Do not duplicate the entire semantic position parser merely to create this API.

If a clean fused parser/helper refactor would be too invasive, a packed-capsule transient legality API may be used instead, but H20 must then include the capsule-allocation boundary in all realistic routing measurements.

---

# 10. H20 PHASE STRUCTURE

Use:

```text
E19 baseline
  -> H20A audit / harness / candidate probe
  -> optional H20B retained Native legality kernel
  -> E20 certification / decision closure
```

## H20A

Allowed:

```text
audit scripts
test-only C counters/probes
test-only fused transient kernel
performance harness
exact action bridge harness
```

H20A MUST NOT route production Python search.

Commit and push H20A.

## H20B

Create only if Sections 18–19 authorization gates pass.

H20B may retain:

```text
one Native transient legality-kernel API
its Python native wrapper
internal helper/refactor needed by that API
focused correctness tests
```

H20B MUST NOT change Core or AlphaBeta routing.

Commit and push H20B before final E20 evidence.

If final H20B retention gates fail:

```text
cleanly revert H20B production kernel
retain H20A/E20 diagnostic evidence
F20_RESULT = AUDIT_ONLY_PASS
```

---

# 11. STATE-ONLY PAYLOAD CONTRACT

A one-shot transient legality payload must be constructed from the current Python `Position`.

It must encode exactly:

```text
ruleset fingerprint match
side_to_move
ply if needed by effects/guards
board:
    occupied
    owner
    base type
    current type
    promoted
hands
aux logical/physical state
```

It must NOT require:

```text
GameState.history
repetition_counts
position_identity_key
external SHA
```

For formal timing, record Python-side state-payload construction cost separately.

Do not hide it inside "Native kernel" timing.

---

# 12. NO CHILD EXTERNAL SHA — HARD GATE

Inside the transient legality kernel:

```text
candidate child canonical key computations = 0
candidate child history appends = 0

nested S3 reply canonical key computations = 0
nested S3 reply history appends = 0
```

The current/root input may carry or not carry exact history depending on implementation, but legality must not consult it.

Any child key/history work:

```text
TRANSIENT_LEGALITY_KEY_LEAK
```

and H20B is not authorized.

---

# 13. CANONICAL ACTION ORDER — HARD AUTHORITY

Native legal actions must match Python exactly in:

```text
count
order
kind
pattern identity
geometry identity
actor current type
base type
source
target
promotion target
```

Do not compare as unordered sets only.

Canonical order is part of the search determinism contract.

---

# 14. STANDARD SHOGI DIFFERENTIAL

Hard assert Standard Shogi fingerprint.

Use at minimum:

```text
the four frozen Standard Shogi prefixes
all legal root actions
bounded depth-1 children
bounded deterministic depth-2 states
```

For every state compare:

```text
Python SemanticEngine.iter_legal_action_bindings
vs
Native transient legality kernel
```

Require:

```text
action count mismatch = 0
action order mismatch = 0
identity mismatch = 0
```

Record row-level evidence.

---

# 15. GENERIC SEMANTIC DIFFERENTIAL

Use at minimum the executable Native semantic corpus:

```text
cannon
castling
en_passant
nifu
uchifuzume
weird_0
weird_1
weird_2
weird_3
weird_4
```

Also include focused fixtures for:

```text
own_anchor_safe
squares_not_attacked
path guards
state guards
slot guards
promotion
forced promotion
capture-to-hand
drop
checking drop
action_delivers_check
opponent_checked
no_legal_reply
aux trigger
expire_next_turn
```

Require exact action-order parity.

---

# 16. EXACT PYTHON ACTION / BINDING BRIDGE DIFFERENTIAL

For every Native packed legal action in the Standard Shogi corpus:

1. decode packed bit fields directly;
2. map Native numeric indices through frozen/precomputed:
   ```text
   type_ids
   pattern_ids
   geometry_ids
   ```
3. construct the exact `SemanticAction`;
4. convert to public action using current `_semantic_public_action`;
5. find exact pattern by ID using a precomputed map;
6. call:
   ```text
   engine._make_binding_from_action(position, semantic_action, pattern)
   ```
7. compare that reconstructed binding with the binding yielded by Python authoritative `iter_legal_action_bindings`.

Compare at least:

```text
pattern
geometry_id
actor_owner
actor_type
actor_base
actor_current
source
target
promotion_target_id
path
```

Require zero mismatch.

Then apply:

```text
engine._transition(position, semantic_action, reconstructed_binding)
```

and compare child with the Python authoritative binding child.

Require zero mismatch.

This proves Native legality output can feed the current Python push without re-running S0–S4.

---

# 17. ACTION DECODE PERFORMANCE CONTRACT

Do not perform one C-extension `unpack_action()` call per returned action in the realistic routing benchmark unless the final production design genuinely requires it.

The 64-bit action layout is frozen.

Preferred realistic bridge:

```text
Python integer bit decode
+
precomputed tuple/index maps
```

Measure separately:

```text
packed tuple -> semantic actions
semantic actions -> public actions
binding reconstruction
```

Do not introduce coordinate-only identity.

Do not drop pattern/geometry identity.

---

# 18. H20B CORRECTNESS AUTHORIZATION GATES

All must pass.

## G1 — S0–S4 exact parity

```text
Standard Shogi order/identity mismatches = 0
generic corpus mismatches = 0
```

## G2 — binding bridge

```text
binding mismatches = 0
Python child mismatches = 0
```

## G3 — history independence enforced

```text
candidate child key computations = 0
nested reply child key computations = 0
history appends = 0
```

## G4 — public exact APIs unchanged

Require existing exact:

```text
guarded_actions if left public
make_checked
position_key
terminal
perft
probe search
fixed-depth search
```

to retain current semantics.

If H20B replaces the internal implementation of existing `guarded_actions`, exact output parity must be complete.

## G5 — fail-closed input validation

Reject:

```text
wrong fingerprint
non-native-executable rules
malformed board
invalid owner/type
invalid aux
out-of-range square
invalid payload shape
```

---

# 19. H20B PERFORMANCE AUTHORIZATION GATE

Run on same process/environment.

## 19.1 Packed-state Native legality kernel

Compare:

```text
current exact-history Native guarded_actions
vs
transient Native legality kernel
```

on the same already-packed states.

Require one of:

```text
aggregate speedup >= 1.50x
```

OR:

```text
absolute saving >= 50 us per full legality operation
```

and:

```text
no semantic case stable regression > 5%
```

## 19.2 Python authoritative legality comparison

Compare:

```text
Python SemanticEngine.iter_legal_action_bindings
```

against Native kernel only, excluding payload/decode/binding bridge.

This is diagnostic, not the routing decision.

Record:

```text
Python us/operation
Native kernel us/operation
kernel speedup
```

If G1–G5 pass but the transient kernel is not materially faster than the existing Native path:

```text
H20B_CREATED = false
```

Do not retain speculative API.

---

# 20. REALISTIC ONE-SHOT ROUTING COST

This is the most important F20 integration measurement.

For each Python `Position`, time the complete route:

```text
A. build state-only Native payload
B. enter Native once
C. parse/pack current transient state
D. complete Native S0–S4 legality kernel
E. return ordered packed actions
F. Python direct bit decode
G. stable ID mapping
H. SemanticAction creation
I. public Action creation
J. exact binding reconstruction
```

Result must be equivalent to:

```text
tuple(public legal actions)
+
bindings dict
```

currently produced by `SearchPathRuntime.legal_actions()`.

Do NOT include Python authoritative child transition because current legal generation also does not retain child positions.

Do NOT omit binding reconstruction.

Report:

```text
payload_build_us
native_parse_pack_us if separable
native_kernel_us
return_decode_us
public_action_us
binding_rebuild_us
total_one_shot_us
python_authoritative_us
speedup
```

---

# 21. LEGALITY POSITION CORPUS FOR PERFORMANCE

Use:

1. four frozen Standard Shogi prefixes;
2. deterministic children sampled from those prefixes;
3. positions sampled from actual Profile A/B search traces;
4. control generic semantic fixtures.

Do not measure only initial position.

Record branching factor and candidate/legal counts.

At minimum:

```text
>= 40 distinct Standard Shogi positions
```

unless the bounded search corpus cannot produce that many unique states; if not, record exact reason and use all available deterministic states.

---

# 22. ONE-SHOT DIRECT ROUTING ECONOMIC GATE

To select future direct routing, require aggregate realistic one-shot legality:

```text
speedup >= 1.50x
```

versus Python authoritative legal-action+binding generation,

AND:

```text
median absolute saving >= 100 us per expanded legality operation
```

AND:

```text
at least 80% of measured Standard Shogi positions faster
```

AND:

```text
no important action-count/branching class stable regression > 10%
```

These are routing-decision gates, not H20B kernel-retention gates.

---

# 23. ATOMIC NATIVE CALL LATENCY / INTERRUPTIBILITY

The legality kernel is one synchronous C call.

Record per operation:

```text
median
p90
p99
max
```

Across measured Standard Shogi positions.

For future direct routing require:

```text
max observed <= 10 ms
```

under the frozen corpus.

If any stable >10 ms operation exists:

```text
NATIVE_LEGALITY_INTERRUPTIBILITY_RISK
```

Direct production routing must not be selected.

Do NOT add callback checkpoints into C in F20.

---

# 24. SEARCH-SHADOW ROUTING PROBE — TEST/AUDIT ONLY

If the realistic one-shot gate in Section 22 passes, run a test-only AlphaBeta shadow/alternate legality probe.

Do NOT modify production `SearchPathRuntime`.

Use an audit-only AI/native wrapper, subclass, monkey-patched method, or isolated harness that:

```text
replaces only semantic legal-action generation
with the Native one-shot legality route

but keeps:
Python SearchPathRuntime
Python push transition
Python terminal
Python repetition/history
Python runtime hash
Python TT
Python evaluator
Python qsearch policy
Python move ordering
```

The bridge must populate equivalent:

```text
_legal_cache
_bindings
```

for the audit runtime.

No Native position persists across nodes in this route.

---

# 25. SEARCH PARITY FOR SHADOW ROUTE

Compare baseline Python search vs test-only Native-legality route.

Require exact:

```text
chosen action
score
PV
nodes
qnodes
completed depth
termination reason
terminal result
legal action order
TT probes
TT hits
TT stores
TT cutoffs
runtime history evidence
TT eligibility
child external key computation counters
```

Only timing/native-legality counters may differ.

Run:

```text
PVS
aspiration
qsearch
root tactical
cancellation
node budget
time budget
exception rollback
```

focused routes.

---

# 26. PROFILE A/B END-TO-END PERFORMANCE

If Section 24 is authorized:

## Profile A

```text
TT on
ordering off
qsearch max depth = 0
root tactical off
max_depth = 2
max_nodes = 512
fresh TT
no wall-clock limit
```

## Profile B

Current production/default tuning:

```text
max_nodes = 256
deterministic node budget
no wall-clock limit
```

For each of four Semantic Shogi cases:

```text
1 warm-up
5 measured runs
```

Compare:

```text
baseline Python legality
test-only Native one-shot legality
```

Formal runs:

```text
no heavy trace
no snapshot differential inside timing
```

Report per case and aggregate.

---

# 27. DIRECT ROUTING SELECTION GATE

Select future:

```text
NATIVE_LEGAL_ACTION_ROUTING_DIRECT
```

only if all are true:

```text
H20 kernel correctness = PASS
realistic one-shot legality gate = PASS
search parity = PASS
interruptibility = PASS

Profile A end-to-end gain >= 8%
Profile B end-to-end gain >= 8%

at least 3/4 semantic cases in each profile gain >= 5%
no semantic case stable regression > 3%
```

F20 does NOT implement the production route.

---

# 28. IF ONE-SHOT PACKING IS THE BOTTLENECK

If:

```text
packed Native legality kernel is strongly faster
but realistic one-shot route fails because state payload/packing dominates
```

then update the economic model using F19 transient runtime:

```text
transient delta lifecycle = 14.29 us
```

Estimate:

```text
persistent transient state
+
Native legality queries
+
Python binding reconstruction
```

against current Python legality.

If conservative projected end-to-end gain is:

```text
>= 10% Profile A
>= 10% Profile B
```

then select:

```text
NATIVE_TRANSIENT_LEGALITY_RUNTIME
```

as the next boundary.

Do NOT implement it in F20.

This future runtime would be a distinct capability type and remain terminal/repetition/search-authority ineligible unless separately expanded.

---

# 29. IF ACTION BRIDGE IS THE BOTTLENECK

If Native kernel and state packing are strong, but:

```text
decode/public action/binding reconstruction
```

consumes most of the advantage, quantify it.

Do NOT weaken semantic action identity.

Do NOT replace binding reconstruction with first-match or coordinate-only matching.

If bridge cost alone prevents material routing benefit, choose:

```text
SEARCH_STRENGTH_EVALUATOR_PHASE
```

unless a clearly bounded future `NATIVE_ACTION_BRIDGE` phase has >=10% modeled end-to-end benefit.

F20's final allowed selection list intentionally does not include open-ended bridge micro-optimization.

---

# 30. FINAL NEXT-BOUNDARY SELECTION

Choose exactly one:

```text
NATIVE_LEGAL_ACTION_ROUTING_DIRECT
NATIVE_TRANSIENT_LEGALITY_RUNTIME
SEARCH_STRENGTH_EVALUATOR_PHASE
```

### Choose `NATIVE_LEGAL_ACTION_ROUTING_DIRECT`

only by Section 27 gate.

### Choose `NATIVE_TRANSIENT_LEGALITY_RUNTIME`

only if:

```text
packed kernel materially strong
one-shot route bottleneck = state packing/capsule boundary
F19 transient runtime model removes that bottleneck
projected >=10% gain in both A/B
```

### Choose `SEARCH_STRENGTH_EVALUATOR_PHASE`

if neither Native legality integration architecture has credible >=10% end-to-end benefit.

Do not choose based on theoretical ceiling alone.

Do not start the selected phase.

---

# 31. H20B RETENTION POLICY

A faster standalone Native legality kernel may be retained even though production Python routing remains deferred, but only if:

```text
all H20B correctness gates pass
H20B performance gate passes
public/fail-closed semantics are clean
no old behavior regresses
```

Reason:

```text
Native guarded/legal action execution is an already-existing certified public Native capability;
replacing unnecessary child SHA/history work inside that capability is independently useful.
```

If those gates fail:

```text
H20B_RETAINED = false
F20_RESULT = AUDIT_ONLY_PASS
```

Do not keep speculative transient APIs.

---

# 32. NO CORE NATIVE DEPENDENCY

Hard invariant:

```text
generic_chess.core.*
```

must remain Native-unaware.

F20 MUST NOT import:

```text
generic_chess.native
```

from Core.

No Native field in:

```text
SearchPathRuntime
_Frame
Position
GameState
```

Any future routing belongs in AI/native integration.

---

# 33. PUBLIC EXACT-HISTORY AUTHORITY FREEZE

Do not change:

```text
semantic_position_key
canonical JSON identity
external SHA-256
exact-history pack semantics
terminal exact-history gate
repetition authority
perft terminal semantics
probe/fixed-depth search exact-history requirements
```

The transient legality kernel is history-independent because it returns actions only.

It must not weaken exact-history APIs.

---

# 34. VERSION / IDENTITY INVARIANTS

Must remain unchanged:

```text
Standard Shogi fingerprint
Semantic IR version = 2
SEMANTIC_PAYLOAD_VERSION = 2
NATIVE_SCHEMA_VERSION = native-0.5.0

semantic action bit layout
external semantic position key
history digest format
Python runtime identity/history contract
```

A new function entrypoint does not itself require a schema bump.

If a serialized semantic payload format must change:

```text
VERSION_CONTRACT_BLOCKED
STOP
```

---

# 35. F13/F14/F19 REGRESSION HARD GATE

Re-run at minimum:

```text
F13 action_delivers_check witnesses
S4 truth table
checking/non-checking drop
uchifuzume

F14 648 attack queries
F14 8 in_check queries
curated semantic attack differential

F19 S0-S4 history independence assertions
F19 nested reply zero-key expectation
F19 public exact-position/key regressions
```

All PASS.

---

# 36. F4–F19 EVIDENCE IMMUTABILITY

Preserve byte-identically all previous evidence/artifacts/docs:

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
artifacts/f19_position_key_architecture/**

docs/architecture/F4_EVIDENCE.md
...
docs/architecture/F19_EVIDENCE.md

ADR-022 through ADR-036
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f20_native_legality_kernel/
```

---

# 37. REQUIRED F20 EVIDENCE

At minimum:

```text
artifacts/f20_native_legality_kernel/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    python_legality_authority.json
    native_guarded_baseline.json
    transient_legality_design.json

    state_only_payload_contract.json
    child_key_history_counters.json

    standard_shogi_legality_rows.jsonl
    standard_shogi_legality_summary.json
    generic_legality_differential.json

    binding_bridge_rows.jsonl
    binding_bridge_summary.json
    child_transition_bridge_parity.json

    fail_closed_api.json
    exact_history_regression.json
    f13_f14_f19_regression.json

    packed_native_baseline_microbench.json
    packed_transient_kernel_microbench.json
    python_legality_microbench.json

    payload_build_microbench.json
    action_decode_microbench.json
    binding_rebuild_microbench.json
    one_shot_legality_microbench.json

    atomic_latency.json
    one_shot_routing_gate.json

    search_shadow_parity.json
    profile_a_baseline.jsonl
    profile_a_native_legality.jsonl
    profile_b_baseline.jsonl
    profile_b_native_legality.jsonl
    end_to_end_search_performance.json

    transient_runtime_economic_model.json
    selected_next_boundary.json

    h20b_authorization_gate.json
    h20b_retention_gate.json

    old_evidence_before.sha256
    old_evidence_after.sha256

    focused_tests.txt
    full_pytest.txt
    final_native_build.txt

    final_verdict.json
    manifest.json
```

For files not run because a prior gate failed, write explicit machine-readable:

```text
NOT_RUN_NOT_AUTHORIZED
```

Do not fabricate measurements.

Create:

```text
docs/architecture/F20_EVIDENCE.md
docs/architecture/ADR-037-native-transient-legality-kernel.md
```

ADR-037 must document:

- Python legality/binding authority;
- why S0–S4 does not need child history;
- exact transient legality-kernel boundary;
- canonical action-order contract;
- exact Python binding reconstruction;
- packed-kernel speed;
- one-shot state-pack/decode/binding economics;
- interruptibility;
- retained Native kernel or rejection;
- selected next integration boundary.

---

# 38. TESTS

Focused tests must include:

```text
Native transient legality kernel
state-only payload validation
zero child key/history instrumentation

Standard Shogi ordered legal differential
generic IR-v2 ordered legal differential

exact packed-action decode
stable ID mapping
binding reconstruction
Python child transition using reconstructed binding

S3 own_anchor_safe
squares_not_attacked
S4 action_delivers_check
opponent_checked
no_legal_reply
nested reply
nifu
uchifuzume
promotion
drop
capture
aux trigger/lifetime

wrong fingerprint
malformed payload
invalid action data

existing guarded_actions
make_checked
position_key
terminal
perft
probe/fixed-depth

F13/F14/F19 focused regressions
F3 history/TT regressions
search interruptibility regressions
```

Then full:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then fresh final Native build:

```text
python scripts/build_native_zig.py
```

Require PASS.

No AlphaSho.

No long games.

---

# 39. RUNTIME SAFETY

Hard controller limits:

```text
single focused/differential subprocess <= 60 s
single microbenchmark process <= 120 s
single Profile A/B measured search <= 120 s
```

No multi-hour workload.

On breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve completed evidence.

Do not restart an hours-long runner.

---

# 40. FORBIDDEN SCOPE

F20 must not:

```text
modify production SearchPathRuntime legality
modify production AlphaBeta routing
import Native into Core

retain Native transient position runtime
retain F17 delta runtime stack

route attack/check separately
route terminal to Native
route repetition/history to Native
route evaluator to Native
route search to Native

change TT
change qsearch
change move ordering
change evaluator
change search heuristics

add attack cache
add terminal cache
add bitboards
add incremental attack map

change external SHA
change canonical JSON
change semantic fingerprint
change IR/payload/schema versions
change action layout
```

No F21 work.

---

# 41. GIT / PROVENANCE

Possible retained path:

```text
E19
  -> H20A audit/harness
  -> H20B retained Native transient legality kernel
  -> E20 closure
```

Possible audit-only path:

```text
E19
  -> H20A
  -> E20 audit closure
```

If H20B is created but fails final retention:

```text
revert H20B production kernel cleanly
retain diagnostic evidence
close E20 audit-only
```

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

# 42. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
VERSION_CONTRACT_BLOCKED

TRANSIENT_LEGALITY_KEY_LEAK

STANDARD_SHOGI_LEGALITY_MISMATCH
GENERIC_LEGALITY_MISMATCH
CANONICAL_ACTION_ORDER_MISMATCH

BINDING_BRIDGE_MISMATCH
CHILD_TRANSITION_BRIDGE_MISMATCH

FAIL_CLOSED_API_FAILURE
EXACT_HISTORY_AUTHORITY_REGRESSION

F13_F14_F19_REGRESSION

SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE

OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance failure is not a correctness STOP.

It determines H20B retention and the next boundary.

---

# 43. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. Python legality/binding authority
6. Existing Native guarded-actions baseline
7. Transient legality-kernel design
8. State-only payload contract
9. Child key/history elimination
10. H20A provenance
11. H20B authorization
12. H20B implementation or rejection
13. Standard Shogi ordered legality differential
14. Generic semantic legality differential
15. Packed-action decode / stable-ID bridge
16. Binding reconstruction differential
17. Python child-transition bridge parity
18. Fail-closed API
19. Exact-history/public API regression
20. F13/F14/F19 regression
21. Packed Native kernel benchmark
22. Python legality benchmark
23. State-payload / decode / binding cost
24. Realistic one-shot legality benchmark
25. Atomic latency / interruptibility
26. One-shot routing gate
27. Search-shadow parity
28. Profile A/B end-to-end performance
29. Transient-runtime economic model
30. H20B retention gate
31. Selected next boundary
32. Tests
33. Evidence / manifest
34. Git
35. Deferred
36. Final verdict

Successful retained kernel verdict:

```text
F20_RESULT = LEGALITY_KERNEL_PASS

TRANSIENT_NATIVE_LEGALITY_KERNEL = PASS
CHILD_KEY_HISTORY_ELIMINATED = PASS

STANDARD_SHOGI_ORDERED_LEGALITY = PASS
GENERIC_ORDERED_LEGALITY = PASS

BINDING_BRIDGE = PASS
PYTHON_CHILD_TRANSITION_BRIDGE = PASS

EXACT_HISTORY_AUTHORITY = PASS
FAIL_CLOSED_API = PASS

H20B_RETAINED = true

ONE_SHOT_ROUTING_GATE = <PASS|FAIL|NOT_RUN_NOT_AUTHORIZED>

SELECTED_NEXT_BOUNDARY =
<NATIVE_LEGAL_ACTION_ROUTING_DIRECT |
 NATIVE_TRANSIENT_LEGALITY_RUNTIME |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

PRODUCTION_SEARCH_ROUTING_CHANGED = false

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Audit-only verdict:

```text
F20_RESULT = AUDIT_ONLY_PASS

H20B_CREATED = <true|false>
H20B_RETAINED = false
reason = <exact failed gate>

SELECTED_NEXT_BOUNDARY =
<NATIVE_TRANSIENT_LEGALITY_RUNTIME |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

PRODUCTION_SEARCH_ROUTING_CHANGED = false

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Blocked verdict:

```text
F20_RESULT = BLOCKED
reason = <exact stop condition>

PRODUCTION_SEARCH_ROUTING_CHANGED = false

FULL_PYTEST = <PASS|FAIL>
FINAL_NATIVE_BUILD = <PASS|FAIL>
```

---

# 44. FINAL STOP

F20 ends after E20 closure.

Do not begin F21.

Do not route production Python search to Native.

Do not implement the selected next boundary.

The next phase must be separately audited and authorized.


