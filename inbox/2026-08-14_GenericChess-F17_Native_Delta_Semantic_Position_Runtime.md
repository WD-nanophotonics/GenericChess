<!-- Gmail provenance -->
<!-- message_id: 19fff11f21ac33ff -->
<!-- thread_id: 19fff11f21ac33ff -->
<!-- subject: GenericChess — F17: Native Delta Semantic Position Runtime + Transactional Undo Certification -->
<!-- from: W D <icywoods.1@gmail.com> -->
<!-- attachment: GenericChess_F17_Native_Delta_Position_Runtime.md -->
<!-- fetched_at: 2026-08-14 Asia/Tokyo -->
<!-- processing_state: complete-authoritative-attachment -->
<!-- end Gmail provenance -->
# GenericChess — F17: Native Delta Semantic Position Runtime + Transactional Undo Certification

## 0. AUTHORITATIVE TASK

This is the authoritative F17 task for `WD-nanophotonics/GenericChess`.

F16 concluded:

```text
F16_RESULT = AUDIT_ONLY_PASS
H16B_RETAINED = false
SELECTED_NEXT_BOUNDARY = NATIVE_DELTA_POSITION_RUNTIME
```

F16 isolated the blocker precisely:

```text
sizeof(GCSemanticPosition) = 27,296 bytes
sizeof(GCSemanticUndo)     = 27,296 bytes
estimated full-copy traffic per push+pop = 109,184 bytes

F15 immutable lifecycle median = 38.61 us
F16 full-position mutable trial median = 23.89 us
precomputed action packing speedup = 8.84x
```

The full-position mutable design was semantically correct but failed the frozen lifecycle gate.

F17 implements exactly the selected boundary:

> Replace full-position undo for the Native semantic search-runtime path with a bounded transactional delta journal that records only actually modified board, hand, aux, side/ply, and history-tail state, while preserving the exact frozen IR-v2 make semantics including parent/pre-state reads, effect ordering, invariants, S4 postconditions, triggers, history, and fail-closed rollback.

F17 is still a runtime-foundation phase.

Python `SearchPathRuntime` remains production authority.

F17 MUST NOT route production Python attack/check, legal generation, terminal, evaluator, TT, or AlphaBeta policy to Native.

Valid successful outcomes:

```text
F17_RESULT = DELTA_RUNTIME_PASS
```

or:

```text
F17_RESULT = AUDIT_ONLY_PASS
```

Do not force retention if the delta runtime is not both exact and materially cheaper.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before work:

1. locate this task using GenericChess/Gmail fuzzy subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. only then begin audit/implementation.

Do not execute from subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
a9c63a02c07376fb61636607cf88f16867bb1cee

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

# 3. F13–F16 FROZEN AUTHORITY

Treat the following as closed.

## F13

```text
Standard Shogi native_executable = true
action_delivers_check Native parity = PASS
uchifuzume parity = PASS
```

## F14

```text
public Native semantic attack/check = certified
packed attack speedup ~9.19x
packed check speedup ~8.47x
per-query pack = REJECT
```

## F15

Immutable child-capsule mirror:

```text
correctness = PASS
Profile A shadow overhead = 9.28%
Profile B shadow overhead = 6.25%
retention = REJECT
```

## F16

Full-position mutable runtime probe:

```text
position size = 27,296 B
undo size = 27,296 B
push+pop copy estimate = 109,184 B
mutable push+pop median = 23.89 us
F15 immutable median = 38.61 us
G1 = FAIL
```

Precomputed exact semantic action packing:

```text
~3.21 us median
~8.84x faster than rebuild-every-call maps
```

Keep that action-packing lesson.

Do not revive the F15 immutable child-capsule architecture.

---

# 4. CURRENT NATIVE MAKE SEMANTICS — FREEZE BEFORE REFACTOR

The current Native semantic checked make is authoritative together with Python SemanticEngine.

Current implementation shape:

```text
validate exact action on parent
copy parent -> work
expire next-turn aux values in work
apply pattern effects in declared order
apply promotion
check S3 invariants
apply trigger mutations
apply aux effects
flip side / increment ply
check S4 postconditions if enabled
compute semantic position SHA-256 digest
append exactly one history entry
publish child
```

Important parent/pre-state behavior:

- action validation reads parent;
- effect square references resolve against parent/pre-state;
- trigger event detection reads parent/pre-state;
- `squares_not_attacked` invariant square refs resolve against parent/pre-state;
- effect execution itself is sequential on the child/work state;
- S3 attack truth observes child state;
- S4 postconditions observe child state;
- history appends one exact tail entry only after semantic success.

F17 MUST preserve all of this exactly.

Do not reorder effect semantics merely because a different order is easier to journal.

---

# 5. CORE ARCHITECTURE INVARIANT

Hard constraint:

```text
Core remains Native-unaware.
```

F17 MUST NOT add Native imports or Native fields to:

```text
generic_chess.core.*
SearchPathRuntime
SearchPathRuntime._Frame
semantic_executor
terminal
core history / identity
```

Native delta runtime belongs under:

```text
generic_chess.native
```

and may be exercised through opt-in AI/native shadow plumbing only.

If correct delta integration requires Core ownership:

```text
ARCHITECTURE_BOUNDARY_VIOLATION
F17_RESULT = AUDIT_ONLY_PASS
```

---

# 6. OWNERSHIP MODEL — FROZEN

For F17:

```text
Python Position / SearchPathRuntime = AUTHORITATIVE
Native delta runtime                = MUTABLE SHADOW FOUNDATION
```

No production game/search decision may depend on Native state in F17.

Future F18 may separately authorize attack/check routing if F17 passes all gates.

---

# 7. PHASE STRUCTURE

Use three provenance stages.

## H17A — WRITE-SET / PRE-STATE / DELTA AUDIT

Before retained production delta support:

1. derive the exact maximum write set from frozen IR-v2 limits;
2. classify every effect kind by board/hand/aux writes;
3. identify every parent/pre-state read that could be invalidated by in-place mutation;
4. build a test-only transactional delta prototype;
5. prove byte/semantic rollback on success and on every reachable failure stage;
6. benchmark delta push/pop and delta size against F16 full-copy trial.

H17A may contain audit/test-only C hooks.

H17A MUST NOT retain AlphaBeta routing.

Commit and push H17A.

Record exact SHA.

## H17B — OPTIONAL RETAINED DELTA RUNTIME

H17B is authorized only if every gate in Section 17 passes.

Implement the retained Native delta runtime and minimal public/private wrapper.

Do not route production attack/check.

Commit and push H17B before final formal evidence.

## E17 — CERTIFICATION CLOSURE

Run full semantic differential, failure atomicity, memory/lifetime, shadow parity, performance, tests/build, and evidence/docs.

If H17B final retention gates fail, cleanly revert retained runtime integration and close audit-only.

---

# 8. FROZEN STATIC LIMITS

Current Native semantic IR-v2 constants include:

```text
GC_SEM_MAX_EFFECTS   = 4
GC_SEM_MAX_AUX_SLOTS = 8
GC_MAX_SQUARES       <= 256
GC_MAX_TYPES         = current frozen Native limit
```

F17 must derive bounded delta capacity from these actual constants, not from Standard Shogi assumptions.

Do not add an unbounded heap journal per move.

---

# 9. REQUIRED DELTA WRITE-SET MODEL

The delta journal must capture a cell's **old value before its first write** during the transaction.

Repeated writes to the same cell in one action must not create ambiguous stacked old values.

At minimum journal these state classes.

## 9.1 Board

Effects currently capable of board mutation include at least:

```text
move / shift-like from->to effects
remove/capture
place/create
change type
promotion at action target
```

Derive a static safe unique-square capacity from `GC_SEM_MAX_EFFECTS` plus promotion.

Expected upper-bound form:

```text
<= 2 * GC_SEM_MAX_EFFECTS + 1
```

but verify actual effect contracts before freezing the C array size.

Journal per unique modified square:

```text
square index
old GCPiece
```

Use a small bitset/mask or equivalent to guarantee first-write capture.

## 9.2 Hands

Journal each unique modified:

```text
(owner, type_index, old_count)
```

Derive a bounded capacity from effect count.

No full `hand_counts[2][GC_MAX_TYPES]` copy.

## 9.3 Aux

Aux writes can arise from:

```text
expire-next-turn reset
trigger mutation
explicit aux effects
```

Because storage is bounded by:

```text
GC_SEM_MAX_AUX_SLOTS × 3 physical cells
```

journal unique physical aux cells:

```text
(slot_index, owner_index, old GCSemAuxValue)
```

A fixed bounded mask/array is acceptable.

No full Position copy.

## 9.4 Scalar state

Save exact old:

```text
side_to_move
ply
history_len
history_exact
```

Fingerprint is immutable and must not be journaled as mutable state.

## 9.5 History tail

Successful semantic make appends exactly one history slot.

Journal enough to restore the exact pre-call raw state:

```text
old history_len
old history_exact
old history_lo[old_len]
old history_hi[old_len]
old history_digest[old_len][4]
```

Even though entries beyond `history_len` are normally unobservable, restore the overwritten tail bytes for deterministic raw rollback certification.

Do NOT copy all history arrays.

---

# 10. PRE-STATE SEMANTICS — HARD DESIGN OBLIGATION

Naive in-place mutation is forbidden because current semantics deliberately read both parent/pre-state and sequential child/work state.

F17 must implement one exact frozen strategy for parent/pre-state observation.

Preferred strategies are:

## Strategy A — Pre-resolve parent-dependent inputs

Before the first mutation, resolve/cache every parent-dependent value needed later in this action, such as:

```text
effect square references
invariant square references
trigger firing decisions / trigger reference results
aux-backed square references needed by later effects
```

Then perform sequential mutations using these frozen resolved values.

OR

## Strategy B — Transactional pre-view overlay

Implement parent/pre-state reads through a view that returns:

```text
journal old value for already-written cells
current value for untouched cells
```

for all parent-observable board/aux/hand state.

### Selection rule

H17A must select exactly one strategy before H17B.

Do NOT implement both and benchmark-shop.

Choose the simpler strategy that can prove exact equivalence over all frozen IR-v2 effect/trigger/invariant semantics.

If neither strategy can be implemented locally without a broad semantic rewrite:

```text
DELTA_PRESTATE_MODEL_NOT_LOCAL
F17_RESULT = AUDIT_ONLY_PASS
```

---

# 11. SINGLE SEMANTIC EXECUTION AUTHORITY

Do not create a second divergent semantic executor.

Preferred architecture:

```text
shared semantic checked-apply core
    -> copy-based make_checked wrapper (existing public behavior)
    -> delta in-place runtime wrapper
```

The shared core may operate on:

```text
mutable work state + transaction/pre-state context
```

or equivalent.

Requirements:

- `semantic_make_checked()` behavior remains exactly unchanged;
- delta runtime uses the same validation/effect/invariant/S4 logic;
- no duplicated hand-maintained effect switch in a second file if avoidable;
- future compiler enum additions must not silently update one executor but not the other.

If refactoring the shared core becomes too broad, H17A may keep a narrower transactional helper, but H17B must include direct differential tests for every effect kind.

---

# 12. FAILURE ATOMICITY — HARD GATE

For any failed delta make:

```text
current position bytes/state = exact pre-call state
delta depth unchanged
undo stack unchanged
```

Test failure after progressively later stages:

```text
invalid action validation
bad target / path / guard
first effect succeeds, later effect fails
hand underflow / overflow
board destination conflict
promotion failure where constructible
S3 invariant failure after board mutation
trigger-related invalid metadata where test-only constructible
aux effect failure after prior writes
S4 postcondition rejection after full child construction
history-full failure
position-key/digest failure if a deterministic test hook can induce it
```

Do not rely only on legal-action success paths.

For every failure, compare:

```text
snapshot
position key where defined
history bytes/tail
side/ply
board/hands/aux
runtime depth
```

---

# 13. DELTA UNMAKE CONTRACT

For successful push:

```text
delta frame stores exactly one transaction's old state
runtime depth += 1
```

For pop:

Restore exactly:

```text
board cells
hand cells
aux cells
side
ply
history tail
history_len
history_exact
```

Order of restore may be implementation-specific but final state must be byte/semantically exact.

Pop underflow must fail closed.

No scanning of entire board/hand/history on pop.

---

# 14. DELTA SIZE / MEMORY MODEL

H17A must report:

```text
sizeof(GCSemanticPosition)
sizeof(old full GCSemanticUndo)
sizeof(new delta undo)
```

Also report theoretical/max payload:

```text
board delta capacity
hand delta capacity
aux delta capacity
history bytes
metadata/masks
padding
```

Memory at depths:

```text
1
8
16
32
64
128
512
```

Hard authorization requirement:

```text
sizeof(delta undo) <= 2048 bytes
AND
sizeof(delta undo) <= 10% of 27,296 bytes
```

If compiler padding or a justified fixed table pushes slightly above 2048 B but remains <=10%, STOP H17B authorization and report the exact reason rather than silently weakening the threshold.

---

# 15. PRECOMPUTED ACTION MAPS — RETAIN F16 LESSON

A retained Native delta runtime wrapper must precompute once per runtime:

```text
type_id -> index
pattern_id -> index
geometry_id -> index
```

Lossless public semantic action packing remains identical to F15/F16.

No:

```text
guarded-action enumeration
coordinate-only matching
first-match fallback
per-push map reconstruction
```

Re-run all-actions packing differential on the four Standard Shogi prefixes.

Require:

```text
missing = 0
duplicates = 0
field mismatch = 0
```

---

# 16. H17A MICROBENCHMARK PROTOCOL

On the same fresh environment compare:

```text
F15 immutable child-capsule lifecycle reference = 38.61 us
F16 full-position mutable reference            = 23.89 us
F17 delta mutable prototype
```

Use already-packed legal actions.

At minimum:

```text
warm-up >= 100
measured repetitions >= 5000
median
p90
p99/max
```

Separate:

```text
delta push
unmake/pop
delta push+pop
action pack
position-key/history append share if measurable
```

Do not include snapshot verification.

---

# 17. H17B AUTHORIZATION GATES

All gates must pass before creating retained H17B.

## G1 — DELTA SIZE

Section 14 size gate PASS.

## G2 — PRE-STATE SEMANTIC PROOF

Selected Strategy A or B must pass all curated multi-effect/aux/trigger fixtures with zero mismatch.

## G3 — FAILURE ATOMICITY

Every Section 12 rollback fixture PASS.

## G4 — LIFECYCLE PERFORMANCE

Require aggregate Standard Shogi:

```text
delta push+pop median <= 18.0 us
```

AND:

```text
delta median <= 0.75 × F16 full-position mutable median
```

Using frozen F16 `23.89 us`, this means approximately:

```text
<= 17.92 us
```

The stricter measured comparison controls.

Also require stable:

```text
p90 <= 25 us
```

## G5 — ACTION PACK

Precomputed action packing remains:

```text
>= 5x faster than F15 rebuild-per-call reference
```

F16 measured ~8.84x; large regression is not acceptable.

## G6 — RAW DIFFERENTIAL

Standard Shogi and generic semantic raw push/pop differential = zero mismatch.

If any gate fails:

```text
F17_RESULT = AUDIT_ONLY_PASS
H17B_CREATED = false
```

Do not invent a broader optimization.

---

# 18. RETAINED NATIVE RUNTIME SURFACE

If H17B is authorized, retain one Native semantic runtime capsule with:

```text
one current GCSemanticPosition
O(depth) bounded delta-undo frames
current depth / capacity
```

Preferred Python/private surface:

```python
NativeSemanticPositionRuntime.from_position(...)
push_packed(...)
pop()
depth
snapshot()
position_key()
is_square_attacked(...)
in_check(...)
```

The exact wrapper may be function-based.

Requirements:

```text
one runtime PyCapsule
no child position PyCapsule per push
no Python parent-capsule stack
```

Do not expose legal/search authority.

---

# 19. STANDARD SHOGI DELTA DIFFERENTIAL

Hard assert fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

Use four frozen reachable prefixes.

For each prefix:

1. exact root runtime creation;
2. enumerate all Python legal depth-1 actions;
3. direct-pack action;
4. Native delta push;
5. compare Native current vs Python authoritative child;
6. Native pop;
7. compare exact root restoration.

Then bounded deterministic depth-2 subsets.

Cover explicitly where reachable:

```text
ordinary move
capture
promotion
checking move
non-checking move
drop
checking drop
```

Require zero:

```text
push mismatch
pop mismatch
depth mismatch
history mismatch
```

---

# 20. GENERIC IR-V2 EFFECT DIFFERENTIAL

This is mandatory because Standard Shogi does not cover every generic effect/aux combination.

Use the existing frozen semantic corpus plus targeted fixtures so every currently-supported effect kind is exercised.

At minimum cover:

```text
move / shift
remove/capture
hand spend
place/create
change type
all aux effect kinds 5–8
promotion
```

Also cover:

```text
expire-next-turn aux reset
global aux
per-owner aux
trigger event fires
trigger event does not fire
multiple effects touching same board square
multiple effects touching same aux cell
multiple effects touching same hand entry
S3 own_anchor_safe
S3 squares_not_attacked
S4 action_delivers_check
S4 opponent_checked
S4 no_legal_reply
multi-condition S4 conjunction
```

For every accepted action:

```text
Python child == Native delta child
pop == exact parent
```

For every rejected candidate:

```text
Native state unchanged
```

---

# 21. RAW-BYTE / SEMANTIC ROLLBACK CERTIFICATION

Where test hooks permit, compare the full raw Native semantic position snapshot/serialized debug representation before and after:

```text
push -> pop
failed push
nested push -> push -> pop -> pop
```

At minimum semantic snapshot must include:

```text
board
hands
side
ply
aux
history len
history exactness
history entries
position key
```

Stale bytes beyond logical history length must also be restored if a raw-memory/hash test hook is added.

Do not expose raw memory as a production API.

---

# 22. RUNTIME ATTACK/CHECK DIFFERENTIAL

Using the current delta runtime position directly, with zero repack:

For every Standard Shogi frozen root and selected children:

```text
81 squares × 2 owners
in_check side 0
in_check side 1
```

Compare Python authority vs Native runtime.

Require:

```text
attack mismatches = 0
check mismatches = 0
```

This certifies future F18 routing capability only.

F17 MUST NOT route production Python calls.

---

# 23. F13–F16 REGRESSION

Re-run at minimum:

```text
F13 action_delivers_check witnesses
checking/non-checking drop
uchifuzume
S4 truth table

F14 648 attack differential
F14 in_check differential
curated generic attack corpus

F15 lossless action-packing oracle
F15 history/fallback expectations

F16 full-position make/unmake baseline differential
```

Existing public `make_checked` behavior must remain exact.

---

# 24. AI-LAYER DELTA SHADOW DRIVER

If H17B is authorized, add only the smallest opt-in AI/native shadow driver needed to exercise actual AlphaBeta DFS.

Core remains untouched.

Combined lifecycle:

```text
Python SearchPathRuntime.push(action)
Native delta runtime.push_packed(exact action)
...
Native delta runtime.pop()
Python SearchPathRuntime.pop()
```

Python remains authority for:

```text
legal generation
attack/check
terminal
history/TT
evaluator
search policy
```

Default product search does not construct the Native runtime.

---

# 25. COMBINED EXCEPTION / SIBLING SAFETY

Test:

## Python push fails

Native runtime unchanged.

## Python push succeeds, Native delta push fails

Rollback Python to exact parent before propagating.

## Body/search raises

Both restore exact parent.

## Nested pushes

Depths remain equal.

## Sibling A -> pop -> sibling B

No delta leakage.

## Native pop underflow

Fail closed.

After all tests/search:

```text
Python runtime depth = 0
Native runtime depth = 0
```

---

# 26. MEMORY / CAPACITY LIFETIME

Retained runtime must be:

```text
1 runtime capsule
+ O(depth) delta frames
```

Instrument:

```text
runtime capsules created
undo frame size
capacity
capacity growth count
peak depth
peak live frames
```

No O(nodes) retention.

Prefer dynamic capacity growth.

Do not eagerly allocate 512 frames without explicit evidence.

Allocation failure during growth must leave current/depth unchanged.

---

# 27. INTERRUPTIBILITY

Preserve Python search:

```text
node budget
time budget
CancellationToken
checkpoint behavior
root fallback
exception rollback
```

Native delta push/pop are atomic synchronous calls.

Measure:

```text
push median/p90/p99/max
pop median/p90/p99/max
runtime attack/check max
```

If any individual runtime operation has a stable observed latency:

```text
> 10 ms
```

record:

```text
NATIVE_DELTA_RUNTIME_INTERRUPTIBILITY_RISK
```

and do not retain H17B unless safely mitigated within scope.

Do not add C callbacks/checkpoints in F17.

---

# 28. FORMAL ALPHABETA SHADOW PERFORMANCE

If H17B is authorized, use frozen profiles.

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

For each of four Standard Shogi semantic cases:

```text
1 warm-up
5 measured repetitions
```

Compare:

```text
baseline Python
Python + delta Native runtime shadow
```

Snapshot verification OFF during timing.

Report:

```text
wall time
root runtime creation
action pack time
native delta push time
native delta pop time
push/pop counts
undo capacity grows
peak depth
```

---

# 29. SEARCH PARITY — HARD GATE

Baseline vs delta-shadow must exactly match:

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
runtime history evidence
runtime TT eligibility
runtime_child_external_key_computations
```

PV must remain legal.

Timing/native counters may differ.

F17 MUST NOT reintroduce child external SHA computations.

---

# 30. FINAL RETENTION GATE

For:

```text
F17_RESULT = DELTA_RUNTIME_PASS
```

require all correctness gates plus:

## R1 — Core boundary

```text
Core Native imports = 0
Core Native fields = 0
```

## R2 — Delta size

Section 14 PASS.

## R3 — Exact semantics / rollback

All:

```text
Standard Shogi
Generic IR-v2
failed-action atomicity
nested push/pop
attack/check
history
```

zero mismatch.

## R4 — Raw lifecycle

H17B authorization G4 remains PASS on final build.

## R5 — Shadow overhead

Aggregate delta-shadow overhead:

```text
Profile A <= 3.5%
Profile B <= 3.5%
```

and:

```text
no semantic case stable overhead > 6%
```

This must be materially better than F15:

```text
A 9.28%
B 6.25%
```

## R6 — Projected F18 net headroom

Using frozen F11/F15 attack/check shares, F14 packed speedup, and measured F17 shadow overhead, compute a conservative projection.

Require:

```text
Profile A projected net gain >= 12%
Profile B projected net gain >= 12%
```

No fabricated precision.

If R5 or R6 fails after H17B:

1. do not retain AI shadow integration;
2. retain standalone delta runtime only if it has a separately demonstrated immediate use within the already-selected Native migration path and its API is fully certified;
3. otherwise cleanly revert H17B production runtime and close audit-only.

Preferred conservative result on economic failure:

```text
F17_RESULT = AUDIT_ONLY_PASS
H17B_RETAINED = false
```

---

# 31. SELECT EXACTLY ONE NEXT BOUNDARY

F17 must choose exactly one future boundary:

```text
NATIVE_ATTACK_CHECK_ROUTING
NATIVE_LEGALITY_KERNEL
NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION
SEARCH_STRENGTH_EVALUATOR_PHASE
```

## Select `NATIVE_ATTACK_CHECK_ROUTING` only if

```text
F17_RESULT = DELTA_RUNTIME_PASS
R5 = PASS
R6 = PASS
```

## Select `NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION` only if

delta mutation itself becomes cheap, but the measured SHA-256 position-key/history append is now the dominant Native lifecycle blocker.

Do not implement it in F17.

## Select `NATIVE_LEGALITY_KERNEL` if

delta runtime is correct but maintaining duplicate Python+Native transitions still makes attack-only routing uneconomic, while a broader Native legality boundary has a stronger measured amortization case.

## Select `SEARCH_STRENGTH_EVALUATOR_PHASE` if

Native runtime migration no longer has credible material end-to-end benefit.

Do not begin the selected phase.

---

# 32. VERSION / SEMANTIC INVARIANTS

Must remain unchanged:

```text
Standard Shogi fingerprint
Semantic IR version = 2
SEMANTIC_PAYLOAD_VERSION = 2
NATIVE_SCHEMA_VERSION = native-0.5.0

semantic action bit layout
semantic position-key canonical format
history digest representation

S3 semantics
S4 semantics
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

Changing the internal `GCSemanticUndo` representation does not by itself require schema/payload version changes.

If frozen serialized payload/state formats must change:

```text
VERSION_CONTRACT_BLOCKED
STOP
```

---

# 33. F4–F16 EVIDENCE IMMUTABILITY

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
artifacts/f16_native_position_runtime/**

docs/architecture/F4_EVIDENCE.md through F16_EVIDENCE.md
ADR-022 through ADR-033
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f17_native_delta_position_runtime/
```

---

# 34. REQUIRED F17 EVIDENCE

At minimum:

```text
artifacts/f17_native_delta_position_runtime/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    frozen_make_semantics.json
    effect_write_set.json
    parent_prestate_reads.json
    delta_capacity.json
    delta_memory_model.json

    prestate_strategy_decision.json
    h17a_delta_probe.json
    rollback_failure_matrix.json

    f15_f16_reference.json
    delta_microbench.json
    action_pack_microbench.json
    h17b_authorization_gate.json

    runtime_api_contract.json
    runtime_failure_contract.json

    standard_shogi_delta_rows.jsonl
    standard_shogi_delta_summary.json
    generic_irv2_delta.json
    runtime_attack_check_differential.json
    raw_rollback_certification.json

    f13_f14_f15_f16_regression.json
    push_pop_exception_sibling.json
    runtime_memory_lifetime.json
    interruptibility.json

    profile_a_baseline.jsonl
    profile_a_delta_shadow.jsonl
    profile_b_baseline.jsonl
    profile_b_delta_shadow.jsonl

    shadow_overhead.json
    projected_net_headroom.json
    final_retention_gate.json
    selected_next_boundary.json

    old_evidence_before.sha256
    old_evidence_after.sha256

    focused_tests.txt
    full_pytest.txt
    final_native_build.txt

    final_verdict.json
    manifest.json
```

If H17B is not authorized, H17B-only files must contain explicit:

```text
NOT_RUN_NOT_AUTHORIZED
```

rather than fabricated results.

Create:

```text
docs/architecture/F17_EVIDENCE.md
docs/architecture/ADR-034-native-delta-semantic-position-runtime.md
```

ADR-034 must document:

- why F16 full-position undo failed;
- exact IR-v2 write-set bounds;
- selected pre-state strategy;
- delta undo layout/size;
- failure atomicity;
- history-tail rollback;
- shared semantic execution authority strategy;
- measured lifecycle improvement;
- shadow overhead;
- projected Native attack/check headroom;
- selected next boundary.

---

# 35. TESTS

Focused tests must include at least:

```text
all delta journal unit tests
first-write-only logging
duplicate write to same board cell
duplicate write to same hand cell
duplicate write to same aux cell
history-tail restore
side/ply restore

failed action after partial effects
S3 rollback
S4 rollback
history-full rollback
nested push/pop
sibling isolation
capacity growth / allocation failure where testable

Standard Shogi all depth-1 delta sync
bounded depth-2 sync
generic IR-v2 effect corpus
runtime attack/check differential

actual AlphaBeta delta-shadow
PVS
aspiration
qsearch
root tactical where applicable
node budget
time budget
cancel
exception rollback

F14 648 attack regression
F13 action_delivers_check / uchifuzume
F16 baseline regression
F3 history/TT
F4–F16 frozen regression suites
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

# 36. RUNTIME SAFETY

Hard limits:

```text
single focused/differential subprocess <= 60 s
single Profile A/B run <= 120 s
single microbenchmark process <= 120 s
```

No multi-hour workload.

On breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve evidence.

---

# 37. FORBIDDEN SCOPE

F17 must not:

```text
import Native from Core
put Native runtime/delta in SearchPathRuntime

route Python attack/check authority to Native
route legal generation to Native
route terminal authority to Native
route evaluator to Native
route AlphaBeta search policy to Native

change TT/history semantics
change evaluator weights/features
change move ordering/search heuristics

add attack cache
add terminal cache
add bitboards
add incremental attack map

change IR/payload/schema versions
change fingerprint
change action layout
change position-key canonical format
```

No F18 work.

---

# 38. GIT / PROVENANCE

Successful path:

```text
E16 baseline
  -> H17A delta audit/probe
  -> H17B retained delta runtime
  -> E17 certification closure
```

Audit-only path:

```text
E16 baseline
  -> H17A
  -> E17 audit closure
```

If H17B is created but final retention fails:

```text
cleanly revert non-qualifying production/runtime integration
retain diagnostic evidence
close E17 audit-only
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

# 39. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
ARCHITECTURE_BOUNDARY_VIOLATION
VERSION_CONTRACT_BLOCKED
DELTA_PRESTATE_MODEL_NOT_LOCAL

DELTA_WRITESET_OVERFLOW
DELTA_ROLLBACK_MISMATCH
DELTA_HISTORY_ROLLBACK_MISMATCH
DELTA_FAILURE_ATOMICITY_FAILURE
STANDARD_SHOGI_DELTA_MISMATCH
GENERIC_IRV2_DELTA_MISMATCH
RUNTIME_ATTACK_CHECK_MISMATCH

SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
RUNTIME_MEMORY_LIFETIME_FAILURE

F13_F14_F15_F16_REGRESSION
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance gate failure is not a correctness STOP.

Close audit-only.

---

# 40. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. Frozen Native make semantics
6. IR-v2 effect write-set audit
7. Parent/pre-state read audit
8. Delta journal capacity / memory model
9. Pre-state strategy decision
10. H17A provenance
11. Delta rollback/failure atomicity probe
12. F15/F16 lifecycle reference
13. Delta lifecycle microbenchmark
14. Precomputed action-pack benchmark
15. H17B authorization gate
16. Retained delta runtime design or rejection
17. Standard Shogi delta differential
18. Generic IR-v2 delta differential
19. Runtime attack/check differential
20. Raw rollback/history certification
21. F13/F14/F15/F16 regression
22. Push/pop/exception/sibling isolation
23. Runtime memory/lifetime
24. AlphaBeta shadow search parity
25. Interruptibility
26. Shadow-mode overhead
27. Projected Native routing headroom
28. Final retention gate
29. Selected next boundary
30. Tests
31. Evidence / manifest
32. Git
33. Deferred
34. Final verdict

Successful retained verdict:

```text
F17_RESULT = DELTA_RUNTIME_PASS

CORE_NATIVE_UNAWARE = PASS
DELTA_UNDO_SIZE = PASS
PRESTATE_SEMANTICS = PASS
DELTA_FAILURE_ATOMICITY = PASS

DELTA_PUSH_POP_SYNC = PASS
DELTA_HISTORY_ROLLBACK = PASS
GENERIC_IRV2_DELTA_PARITY = PASS
RUNTIME_ATTACK_CHECK_DIFFERENTIAL = PASS

SEARCH_SHADOW_PARITY = PASS
INTERRUPTIBILITY = PASS
RUNTIME_MEMORY_LIFETIME = PASS

DELTA_LIFECYCLE_GATE = PASS
SHADOW_OVERHEAD_GATE = PASS
PROJECTED_NET_HEADROOM = PASS

SELECTED_NEXT_BOUNDARY =
<NATIVE_ATTACK_CHECK_ROUTING |
 NATIVE_LEGALITY_KERNEL |
 NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Audit-only verdict:

```text
F17_RESULT = AUDIT_ONLY_PASS
H17B_RETAINED = false
reason = <exact failed gate>

SELECTED_NEXT_BOUNDARY =
<NATIVE_LEGALITY_KERNEL |
 NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

---

# 41. FINAL STOP

F17 ends after E17 closure.

Do not begin F18.

Do not route production attack/check to Native.

The selected next boundary must be separately reviewed and separately authorized.

