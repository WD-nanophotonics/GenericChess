<!-- Gmail provenance -->
<!-- message_id: 19ffeabe63433873 -->
<!-- thread_id: 19ffeabe63433873 -->
<!-- subject: GenericChess — F16: Native Semantic Position Runtime Stack + Evidence-Gated Lifecycle Foundation -->
<!-- from: W D <icywoods.1@gmail.com> -->
<!-- attachment: GenericChess_F16_Native_Position_Runtime.md -->
<!-- fetched_at: 2026-08-14 Asia/Tokyo -->
<!-- processing_state: complete-authoritative-attachment -->
<!-- end Gmail provenance -->
# GenericChess — F16: Native Semantic Position Runtime Stack + Evidence-Gated Lifecycle Foundation

## 0. AUTHORITATIVE TASK

This is the authoritative F16 task for `WD-nanophotonics/GenericChess`.

F15 concluded:

```text
F15_RESULT = AUDIT_ONLY_PASS
H15B_RETAINED = false
SELECTED_NEXT_BOUNDARY = NATIVE_POSITION_RUNTIME
```

F15 proved that a Python-authoritative immutable-child Native mirror is semantically correct, but its lifecycle cost is too high:

```text
Profile A mirror overhead = 9.28%
Profile B mirror overhead = 6.25%

Projected Native attack/check routing headroom:
Profile A = 6.85%   FAIL
Profile B = 14.13%  PASS
```

F16 implements exactly the selected boundary:

> Create and certify a C-owned mutable Native semantic position runtime stack that keeps one current Native position and uses in-place push/unmake semantics, eliminating per-node child-capsule allocation and Python parent-capsule stacking.

F16 remains a **foundation phase**.

Python `SearchPathRuntime` remains the production authority.

F16 MUST NOT route production attack/check, legal generation, terminal, evaluator, or search policy to Native.

Valid successful outcomes:

```text
F16_RESULT = POSITION_RUNTIME_PASS
```

or:

```text
F16_RESULT = AUDIT_ONLY_PASS
```

Do not force a retained runtime if the measured lifecycle economics remain insufficient.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before work:

1. locate this task by GenericChess/Gmail fuzzy subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. only then begin implementation/audit.

Do not execute from the email subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
1182d98f3c4efe1de1b4049049f73ba6c47e0199

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three.

If `origin/sandbox` moved:

```text
BASELINE_MOVED
STOP
```

Do not reset, rewrite, force-push, or overwrite another task.

Work only on `sandbox`.

`master` and `chat` remain read-only.

---

# 3. F15 / F14 FROZEN AUTHORITY

Treat all decisions through F15 as closed.

## F14

Certified:

```text
PUBLIC_NATIVE_SEMANTIC_ATTACK = PASS
PUBLIC_NATIVE_SEMANTIC_IN_CHECK = PASS

packed Native attack speedup = 9.19x
packed Native check speedup = 8.47x

per-query Python -> Native pack = REJECT
```

Do not alter the F14 attack/check truth or API.

## F15

Certified:

```text
Core Native imports = 0
lossless semantic action packing = PASS
root/history transport = PASS
push/pop/exception/sibling sync = PASS
O(depth) capsule lifetime = PASS
AlphaBeta shadow logical parity = PASS
```

Rejected:

```text
immutable child-capsule mirror lifecycle
```

Do not revive `generic_chess/native/mirror.py` as a retained immutable-child design.

If useful, H15B commit `4dba42f` may be inspected as historical/audit reference only.

---

# 4. CURRENT NATIVE IN-PLACE PRIMITIVE — VERIFY FIRST

Current source contains:

```c
typedef struct {
    GCSemanticPosition saved;
} GCSemanticUndo;

int gc_semantic_runtime_make_trusted(
    GCSemanticPosition *position,
    const GCSemanticRules *rules,
    uint64_t action,
    GCSemanticUndo *undo
);

void gc_semantic_runtime_unmake(
    GCSemanticPosition *position,
    const GCSemanticUndo *undo
);
```

Current implementation is effectively:

```text
checked make into local child
save full parent position into undo
assign child to current position
```

and unmake restores the saved position.

This is semantically promising because:

```text
no child PyCapsule is required
no Python parent-capsule stack is required
```

but it may still copy a large `GCSemanticPosition`.

F16 MUST measure this rather than assume it is cheap.

---

# 5. `GCSemanticPosition` COPY COST — MANDATORY AUDIT

The Native semantic position currently includes at least:

```text
fingerprint
board[GC_MAX_SQUARES]
hand_counts[2][GC_MAX_TYPES]
side_to_move
ply
aux slots
history_lo[GC_MAX_PLY + 1]
history_hi[GC_MAX_PLY + 1]
history_digest[GC_MAX_PLY + 1][4]
history_len
history_exact
```

H16A must record:

```text
sizeof(GCSemanticPosition)
sizeof(GCSemanticUndo)

bytes copied per make_trusted
bytes copied per unmake
estimated bytes copied per push+pop

memory for undo depth:
1
2
4
8
16
32
64
128
512
```

Do not treat O(depth) as automatically acceptable if each frame is excessively large.

---

# 6. ARCHITECTURE INVARIANT — CORE REMAINS NATIVE-UNAWARE

Hard constraint:

F16 MUST NOT add imports from:

```text
generic_chess.native
```

into:

```text
generic_chess.core.*
```

Do not add Native state to:

```text
SearchPathRuntime
SearchPathRuntime._Frame
semantic_executor
terminal
core identity/history
```

The Native position runtime lives below:

```text
generic_chess.native
```

and may be driven by an opt-in AI/native integration layer for certification.

If a correct implementation requires Core to own the Native runtime:

```text
ARCHITECTURE_BOUNDARY_VIOLATION
F16_RESULT = AUDIT_ONLY_PASS
```

---

# 7. OWNERSHIP — FROZEN

For F16:

```text
Python SearchPathRuntime / Position
    = AUTHORITATIVE

NativeSemanticPositionRuntime
    = MUTABLE SHADOW FOUNDATION
```

No production result may depend on Native runtime truth in F16.

The Native runtime may be queried for certification/performance only.

Future F17 may separately authorize routing.

---

# 8. PHASE STRUCTURE

Use three provenance stages.

## H16A — AUDIT / PROBE

Before retained runtime implementation:

1. audit current internal in-place make/unmake;
2. measure its raw C/Python boundary cost;
3. measure full-position-copy cost and memory;
4. re-measure F15 immutable child-capsule lifecycle on the same environment;
5. implement/precompute the exact action-ID maps needed to remove F15's per-push map rebuilding in an audit-only probe;
6. decide whether a C-owned runtime stack using the **existing full-position undo** is economically viable.

H16A MUST NOT retain AlphaBeta integration.

Commit and push H16A.

Record exact SHA.

## H16B — OPTIONAL RETAINED POSITION RUNTIME

H16B may be created only if H16A passes the Section 14 authorization gate.

Implement:

```text
Native semantic mutable position runtime stack
```

using the existing exact checked make/unmake semantics.

Do NOT implement a new delta-undo architecture in F16.

If full-position undo is too costly:

```text
FULL_POSITION_UNDO_NOT_ECONOMIC
F16_RESULT = AUDIT_ONLY_PASS
H16B_CREATED = false
```

Do not broaden scope.

## E16 — CERTIFICATION CLOSURE

Run all correctness, lifecycle, shadow-overhead, regression, tests/builds, evidence/docs.

---

# 9. H16A RAW PRIMITIVE BENCHMARK

Add a test-only/audit-only entrypoint if required to benchmark the existing C primitive without child-capsule allocation.

Measure on an already-packed Standard Shogi Native position:

```text
checked in-place push
unmake
push+pop pair
```

Use deterministic legal packed actions.

At minimum:

```text
warm-up >= 100
measured repetitions >= 5000 where safe
median
p90
p99/max
```

Compare on the same action/corpus against F15-style:

```text
semantic_make_checked -> new child capsule
Python parent capsule stack restore
```

Also compare:

```text
action packing with F15 rebuild-every-call maps
action packing with precomputed maps
```

Do not include snapshot verification in timing.

---

# 10. PRECOMPUTED LOSSLESS ACTION PACKING

F15 proved exact direct action packing, but its historical helper rebuilt:

```text
type_map
pattern_map
geometry_map
```

inside the action-packing path.

F16 must not repeat that cost.

A retained runtime wrapper may precompute once:

```text
type_id -> index
pattern_id -> index
geometry_id -> index
```

and reuse them for the entire runtime lifetime.

Exact public semantic action identity remains:

### Semantic board

```text
pattern_id
geometry_id
actor_type_id
from_square
to_square
promotion_target_id
parent piece base_type_id
```

### Semantic drop

```text
pattern_id
geometry_id
base_type_id
to_square
```

No coordinate-only fallback.
No guarded-action enumeration.
No first-match lookup.

Require the F15 all-actions packing differential again.

---

# 11. TARGET C RUNTIME STACK

Preferred conceptual C-owned structure:

```c
typedef struct {
    GCSemanticPosition current;
    GCSemanticUndo *undos;
    uint16_t depth;
    uint16_t capacity;
} GCSemanticRuntimeStack;
```

Exact naming may differ.

Requirements:

```text
one current position
undo storage grows with actual search depth
no child GCSemanticPosition PyCapsule per push
no Python parent-capsule list
no node-count-proportional retention
```

Do NOT allocate the full `GC_MAX_PLY` undo array eagerly unless H16A memory evidence explicitly justifies it.

Prefer bounded dynamic capacity growth.

Capacity growth is allowed only occasionally and must fail cleanly.

---

# 12. PUBLIC/PRIVATE PYTHON RUNTIME SURFACE

Preferred Python wrapper:

```python
class NativeSemanticPositionRuntime:
    @classmethod
    def from_position(native_rules, position_capsule):
        ...

    @property
    def depth(self) -> int:
        ...

    def push_packed(self, packed_action: int) -> None:
        ...

    def pop(self) -> None:
        ...

    def is_square_attacked(self, square: int, by_owner: int) -> bool:
        ...

    def in_check(self, side: int) -> bool:
        ...

    def snapshot(self) -> dict:
        ...

    def position_key(self) -> str:
        ...
```

The exact API may be functions over a runtime capsule rather than a class.

Important:

```text
attack/check query current mutable runtime state
```

without producing a position capsule.

This is required for future zero-repack routing.

Do not add:
- legal-generation authority;
- terminal authority;
- evaluator;
- search backend.

---

# 13. PUSH / POP FAILURE CONTRACT

Native runtime must be internally exception-safe.

## Push success

After:

```text
runtime.push_packed(action)
```

require:

```text
depth += 1
current == exact checked child
```

## Push invalid action / Native checked-make failure

Require:

```text
depth unchanged
current unchanged
undo stack unchanged
```

## Pop success

Require:

```text
depth -= 1
exact parent restored
```

## Pop underflow

Fail closed.

## Allocation/capacity-growth failure

Require:

```text
current unchanged
depth unchanged
```

No half-written undo frame.

---

# 14. H16B AUTHORIZATION GATE

All gates must pass before creating retained H16B.

## G1 — IN-PLACE LIFECYCLE ADVANTAGE

Require raw already-packed:

```text
in-place native push+pop median
<= 0.50 ×
F15 immutable child-capsule mirror lifecycle median
```

on Standard Shogi aggregate.

OR:

```text
absolute in-place push+pop median <= 20 us
```

with stable p90.

## G2 — ACTION PACK IMPROVEMENT

Precomputed-map semantic action packing must achieve at least:

```text
2.0x
```

speedup over F15 rebuild-per-call action packing.

If the historical F15 implementation cannot be reproduced exactly, use the committed H15B helper as the oracle and record methodology.

## G3 — MEMORY

At expected search depths:

```text
depth 16
depth 32
depth 64
```

undo memory must be bounded and acceptable.

Hard reject if the proposed runtime requires:

```text
node-count-proportional memory
```

or an obviously excessive eager 512-frame allocation without measured justification.

## G4 — EXACT SEMANTICS

Raw in-place push/pop differential must show zero mismatch on certified corpora.

If any gate fails:

```text
F16_RESULT = AUDIT_ONLY_PASS
H16B_CREATED = false
```

Do not implement delta undo as an emergency fallback.

---

# 15. ROOT CREATION / HISTORY

Reuse F15 exact semantic root transport.

Requirements:

```text
full SHA-256 history
board
hands
side
ply
aux
fingerprint
```

Opaque/incomplete history:

```text
Native runtime unavailable
Python-only fallback
```

Do not weaken history exactness.

Do not fabricate missing history.

Do not change F3 TT eligibility.

---

# 16. NO CHILD PYTHON SHA-256

F2/F3 frozen contract remains.

Native runtime push MUST NOT require Python to compute:

```text
position_identity_key(child)
```

or any external child SHA.

Production/shadow stats require:

```text
runtime_child_external_key_computations unchanged
```

Audit-only sync verification may compute exact Python keys outside formal performance runs.

---

# 17. STANDARD SHOGI RUNTIME DIFFERENTIAL

Hard assert fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

Use four frozen prefixes.

For every root:

1. create exact Native runtime;
2. compare root snapshot;
3. push every legal depth-1 action individually;
4. compare exact Native current state vs Python child;
5. pop;
6. compare exact root restoration.

Then run bounded deterministic depth-2 DFS subsets.

Cover:

```text
normal board move
capture
promotion
drop
checking move
non-checking move
```

Require:

```text
push mismatches = 0
pop mismatches = 0
depth mismatches = 0
```

---

# 18. GENERIC SEMANTIC RUNTIME CORPUS

Re-run representative executable semantic cases:

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

Cover:

```text
aux state mutation
expire-next-turn
trigger mutation
capture-to-hand
drop
promotion
shift
multiple effects
S3 invariant
S4 postcondition
```

For representative legal actions:

```text
Python child == Native runtime current
pop == exact parent
```

---

# 19. RUNTIME ATTACK/CHECK DIFFERENTIAL

Using the **current mutable runtime state**, not a repacked capsule:

For every Standard Shogi certification root and selected child:

```text
81 squares × 2 owners
in_check side 0/1
```

Compare:

```text
Python SemanticEngine
vs
Native runtime attack/check
```

Require zero mismatch.

This certifies future F17 zero-repack query semantics.

F16 still MUST NOT route production Python calls to Native.

---

# 20. F13/F14/F15 REGRESSION

Re-run at minimum:

```text
F13 action_delivers_check witnesses
checking/non-checking drop
uchifuzume
S4 truth table

F14 648 root attack differential
F14 8 in_check differential
curated generic attack corpus

F15 exact action packing oracle
F15 root/history fallback tests
```

Existing Native semantic paths must not regress.

---

# 21. AI-LAYER SHADOW DRIVER

If H16B is authorized, add the smallest opt-in AI/native shadow integration needed to exercise the actual AlphaBeta DFS lifecycle.

It must live outside Core.

Conceptually:

```text
Python SearchPathRuntime.push(action)
Native runtime.push_packed(exact action)
...
Native runtime.pop()
Python SearchPathRuntime.pop()
```

Use an exception-safe combined context at the AI/native layer.

Python remains authority.

Default product search must not construct the Native runtime.

---

# 22. COMBINED EXCEPTION SAFETY

Test all:

## Python push fails

```text
Native runtime unchanged
```

## Python push succeeds, Native push fails

Rollback Python to parent before propagating.

## Body/search raises

Both return to exact parent.

## Native pop fails

Treat as fatal shadow/runtime consistency error in mandatory test mode.

Never continue with a stale Native runtime.

## Normal exit

Both pop exactly once.

Require after successful combined push:

```text
native_runtime.depth == python_runtime.depth
```

---

# 23. CAPSULE / MEMORY LIFETIME

A retained Native runtime uses:

```text
1 runtime capsule
+
O(depth) undo storage
```

It must NOT create a PyCapsule per child push.

Instrument:

```text
runtime_capsules_created
undo_capacity
peak_depth
peak_undo_frames
capacity_grows
```

After search/exception:

```text
native depth = 0
Python depth = 0
```

No sibling/node leakage.

---

# 24. SHADOW SEARCH PARITY

Use Profiles A/B and four frozen Standard Shogi semantic cases.

Compare:

```text
baseline Python search
vs
Python search + Native mutable-runtime shadow
```

Require exact:

```text
action
score
PV
nodes
qnodes
completed depth
termination reason
terminal result
legal action order
TT probes/hits/stores/cutoffs where deterministic
runtime history
runtime TT eligibility
child external key computations
```

Timing-only/native-runtime counters may differ.

---

# 25. INTERRUPTIBILITY

Preserve:

```text
node budget
time budget
cancel token
checkpoint behavior
root fallback
exception rollback
```

Native runtime push/pop are atomic synchronous calls.

Measure:

```text
push median/p90/p99/max
pop median/p90/p99/max
attack/check median/p90/max on runtime
```

If any individual runtime call shows stable:

```text
> 10 ms
```

record:

```text
NATIVE_POSITION_RUNTIME_INTERRUPTIBILITY_RISK
```

and do not retain unless safely mitigated within scope.

No Native callbacks/checkpoints in F16.

---

# 26. FORMAL PERFORMANCE — MUTABLE RUNTIME SHADOW

Use frozen profiles.

## Profile A

```text
TT = on
ordering = off
quiescence_max_depth = 0
root tactical scan = off
max_depth = 2
max_nodes = 512
fresh TT per measured run
no wall-clock limit
```

## Profile B

Current production/default tuning:

```text
max_nodes = 256
deterministic node budget
no wall-clock limit
```

Per case/profile:

```text
1 warm-up
5 measured repetitions
```

Compare:

```text
baseline Python
mutable Native runtime shadow
```

Snapshot verification OFF during formal timing.

Record:

```text
wall
root runtime creation
action-pack time
native runtime push time
native runtime pop time
push count
pop count
capacity grows
peak depth
```

---

# 27. H16B RETENTION GATE

For:

```text
F16_RESULT = POSITION_RUNTIME_PASS
```

require all correctness gates plus:

## R1 — Core boundary

```text
Core Native imports = 0
Core Native state = 0
```

## R2 — Exact runtime sync

```text
root mismatch = 0
push mismatch = 0
pop mismatch = 0
attack/check mismatch = 0
```

## R3 — Search parity

Exact logical parity.

## R4 — Memory/lifetime

```text
one runtime capsule
O(depth) undo
no per-node retained capsules
```

## R5 — Lifecycle improvement vs F15

Formal aggregate shadow overhead must improve materially over F15:

```text
Profile A overhead <= 5%
Profile B overhead <= 5%
```

AND:

```text
no semantic case stable overhead > 8%
```

Also report direct comparison against F15:

```text
F15 A = 9.28%
F15 B = 6.25%
```

## R6 — Projected F17 net headroom

Using:

```text
F11/F15 attack-check share
F14 9.19x / 8.47x packed speedup
F16 measured mutable-runtime overhead
```

compute a conservative end-to-end projection.

Require:

```text
Profile A projected net gain >= 10%
Profile B projected net gain >= 10%
```

If R5 or R6 fails:

1. do not retain AI shadow integration;
2. if the standalone Native runtime API is independently useful/correct but not economically sufficient for the selected goal, do NOT retain it merely as speculative infrastructure unless this task's measured evidence shows another concrete immediate use;
3. prefer clean audit-only closure.

Final:

```text
F16_RESULT = AUDIT_ONLY_PASS
H16B_RETAINED = false
```

---

# 28. NO DELTA-UNDO EXPANSION

Important scope control:

If full-position `GCSemanticUndo` copying is the dominant remaining cost and causes F16 gates to fail:

```text
FULL_POSITION_UNDO_NOT_ECONOMIC
```

Document:

```text
bytes copied
time share
measured ceiling
```

Do NOT implement:

```text
delta board undo
delta hand undo
delta aux undo
incremental history undo redesign
copy-on-write semantic position
```

inside F16.

That would be a separately-authorized architecture phase.

---

# 29. SELECT EXACTLY ONE NEXT BOUNDARY

F16 must choose exactly one future boundary:

```text
NATIVE_ATTACK_CHECK_ROUTING
NATIVE_LEGALITY_KERNEL
NATIVE_DELTA_POSITION_RUNTIME
SEARCH_STRENGTH_EVALUATOR_PHASE
```

## Select `NATIVE_ATTACK_CHECK_ROUTING` only if

```text
F16_RESULT = POSITION_RUNTIME_PASS
R5 = PASS
R6 = PASS
```

## Select `NATIVE_DELTA_POSITION_RUNTIME` only if

all semantics are correct but measured full-position undo copying is specifically the dominant blocker and a delta runtime is justified by evidence.

Do not implement it in F16.

## Select `NATIVE_LEGALITY_KERNEL` if

mutable runtime lifecycle is correct but attack-only routing still cannot amortize Python+Native duplicate transitions, while broader Native legality has a credible measured boundary advantage.

## Select `SEARCH_STRENGTH_EVALUATOR_PHASE` if

Native runtime integration no longer has credible material end-to-end runtime benefit.

Do not begin the selected phase.

---

# 30. VERSION / SEMANTIC INVARIANTS

Must remain unchanged:

```text
Standard Shogi fingerprint
Semantic IR version = 2
SEMANTIC_PAYLOAD_VERSION = 2
NATIVE_SCHEMA_VERSION = native-0.5.0

semantic action bit layout
semantic position-key format
history digest representation

S3
S4
nifu
uchifuzume
promotion/drop
repetition
continuous_check_loss

F3 history-aware TT identity
TT bounds/generation/replacement
qsearch policy
evaluator
move ordering
search heuristics
```

A new internal runtime capsule name does NOT require a schema-version bump.

If changing frozen serialized payload/state shape becomes necessary:

```text
VERSION_CONTRACT_BLOCKED
STOP
```

---

# 31. F4–F15 EVIDENCE IMMUTABILITY

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
artifacts/f12_native_semantic_audit/**
artifacts/f13_native_action_delivers_check/**
artifacts/f14_native_semantic_attack_api/**
artifacts/f15_native_mirrored_position/**

docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
docs/architecture/F7_EVIDENCE.md
docs/architecture/F8_EVIDENCE.md
docs/architecture/F9_EVIDENCE.md
docs/architecture/F10_EVIDENCE.md
docs/architecture/F11_EVIDENCE.md
docs/architecture/F12_EVIDENCE.md
docs/architecture/F13_EVIDENCE.md
docs/architecture/F14_EVIDENCE.md
docs/architecture/F15_EVIDENCE.md

ADR-022 through ADR-032
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f16_native_position_runtime/
```

---

# 32. REQUIRED F16 EVIDENCE

At minimum:

```text
artifacts/f16_native_position_runtime/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    native_position_size.json
    current_inplace_primitive_audit.json
    f15_lifecycle_reference.json

    inplace_microbench.json
    immutable_capsule_microbench.json
    action_pack_precompute_microbench.json
    h16b_authorization_gate.json

    runtime_api_contract.json
    runtime_failure_contract.json
    runtime_memory_model.json

    standard_shogi_runtime_sync.jsonl
    standard_shogi_runtime_summary.json
    generic_semantic_runtime_sync.json
    runtime_attack_check_differential.json

    f13_f14_f15_regression.json

    push_pop_exception_matrix.json
    opaque_history_fallback.json
    capsule_lifetime.json
    interruptibility.json

    profile_a_baseline.jsonl
    profile_a_runtime_shadow.jsonl
    profile_b_baseline.jsonl
    profile_b_runtime_shadow.jsonl

    shadow_overhead.json
    f15_vs_f16_lifecycle.json
    projected_net_headroom.json

    retention_gate.json
    selected_next_boundary.json

    old_evidence_before.sha256
    old_evidence_after.sha256

    focused_tests.txt
    full_pytest.txt
    final_native_build.txt

    final_verdict.json
    manifest.json
```

If H16B is not authorized, candidate/runtime-shadow files may contain explicit:

```text
NOT_RUN_NOT_AUTHORIZED
```

rather than fabricated data.

Create:

```text
docs/architecture/F16_EVIDENCE.md
docs/architecture/ADR-033-native-semantic-position-runtime.md
```

ADR-033 must document:

- why immutable child capsules failed F15;
- current `GCSemanticPosition` and undo size;
- current in-place make/unmake semantics;
- retained runtime capsule design or rejection;
- precomputed exact action packing;
- memory/depth model;
- shadow overhead;
- projected attack/check routing headroom;
- selected next boundary.

---

# 33. TESTS

Focused tests must include:

```text
raw Native in-place make/unmake
runtime capsule construction
runtime push/pop
invalid push no mutation
pop underflow
capacity growth
allocation-failure path where testable
exact action packing
root/history transport
opaque history fallback

Standard Shogi all depth-1 runtime sync
bounded depth-2 sync
generic 10-case runtime sync
runtime attack/check differential

actual AlphaBeta mutable-runtime shadow
PVS
aspiration
qsearch
root tactical where applicable
node budget
time budget
cancel
exception rollback

F14 648 attack regression
F13 action_delivers_check/uchifuzume
F3 history/TT
F4-F15 regressions
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

Require fresh final Native build PASS.

No AlphaSho.

No long games.

---

# 34. RUNTIME SAFETY

Hard limits:

```text
single focused/differential subprocess <= 60 s
single Profile A/B run <= 120 s
single microbenchmark subprocess <= 120 s
```

No multi-hour workload.

On breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve evidence.

---

# 35. FORBIDDEN SCOPE

F16 must not:

```text
import Native from Core
put Native runtime/capsule in SearchPathRuntime

route Python attack/check truth to Native
route legal generation to Native
route terminal truth to Native
route evaluator to Native
route AlphaBeta itself to Native

implement delta undo
implement copy-on-write Native state
redesign Native history identity

add Native TT/qsearch/search budgets
change search heuristics
change evaluator features/weights

add attack cache
add terminal cache
add bitboards
add incremental attack map

change IR/payload/schema versions
change fingerprint
change action layout
```

No F17 work.

---

# 36. GIT / PROVENANCE

Successful retained path:

```text
E15 baseline
  -> H16A audit/probe
  -> H16B mutable Native semantic position runtime
  -> E16 certification closure
```

Audit-only:

```text
E15 baseline
  -> H16A audit/probe
  -> E16 audit closure
```

If H16B was trialed but fails final retention:

```text
cleanly revert non-qualifying production runtime integration
retain diagnostic evidence
close E16 audit-only
```

Record exact SHAs.

Final:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

---

# 37. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
ARCHITECTURE_BOUNDARY_VIOLATION
VERSION_CONTRACT_BLOCKED

RUNTIME_ROOT_MISMATCH
RUNTIME_PUSH_MISMATCH
RUNTIME_POP_MISMATCH
RUNTIME_ATTACK_CHECK_MISMATCH
RUNTIME_FAILURE_ATOMICITY_FAILURE
RUNTIME_MEMORY_LIFETIME_FAILURE

SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE

F13_F14_F15_REGRESSION
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance gate failure is not a correctness STOP.

Close audit-only.

---

# 38. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. Current in-place Native primitive audit
6. Native position / undo size and memory model
7. F15 immutable lifecycle reference
8. In-place lifecycle microbenchmark
9. Precomputed action-pack benchmark
10. H16A provenance
11. H16B authorization gate
12. Mutable runtime design or rejection
13. Runtime failure/atomicity contract
14. Standard Shogi runtime sync
15. Generic semantic runtime sync
16. Runtime attack/check differential
17. F13/F14/F15 regression
18. Push/pop/exception/sibling isolation
19. Runtime memory/capsule lifetime
20. AlphaBeta shadow search parity
21. Interruptibility
22. Shadow-mode overhead
23. F15 vs F16 lifecycle comparison
24. Projected Native routing headroom
25. Retention gate
26. Selected next boundary
27. Tests
28. Evidence / manifest
29. Git
30. Deferred
31. Final verdict

Successful retained verdict:

```text
F16_RESULT = POSITION_RUNTIME_PASS

CORE_NATIVE_UNAWARE = PASS
MUTABLE_NATIVE_POSITION_RUNTIME = PASS
LOSSLESS_PRECOMPUTED_ACTION_PACK = PASS

RUNTIME_PUSH_POP_SYNC = PASS
RUNTIME_FAILURE_ATOMICITY = PASS
RUNTIME_MEMORY_LIFETIME = PASS

RUNTIME_ATTACK_CHECK_DIFFERENTIAL = PASS
SEARCH_SHADOW_PARITY = PASS
INTERRUPTIBILITY = PASS

SHADOW_OVERHEAD_GATE = PASS
PROJECTED_NET_HEADROOM = PASS

SELECTED_NEXT_BOUNDARY =
<NATIVE_ATTACK_CHECK_ROUTING |
 NATIVE_LEGALITY_KERNEL |
 NATIVE_DELTA_POSITION_RUNTIME |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Audit-only verdict:

```text
F16_RESULT = AUDIT_ONLY_PASS
H16B_RETAINED = false
reason = <exact failed gate>

SELECTED_NEXT_BOUNDARY =
<NATIVE_LEGALITY_KERNEL |
 NATIVE_DELTA_POSITION_RUNTIME |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

---

# 39. FINAL STOP

F16 ends after E16 closure.

Do not begin F17.

Do not route attack/check to Native.

The selected next boundary must be separately reviewed and separately authorized.

