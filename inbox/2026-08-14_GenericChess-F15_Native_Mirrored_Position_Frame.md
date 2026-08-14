<!-- Gmail provenance
message_id: 19ffe778e6de46ba
thread_id: 19ffe778e6de46ba
subject: GenericChess — F15: Native Mirrored Semantic Position Frame + Search-Lifecycle Certification
from: W D <icywoods.1@gmail.com>
attachment: GenericChess_F15_Native_Mirrored_Position_Frame.md
fetched_at: 2026-08-14 Asia/Tokyo
processing_state: complete-authoritative-attachment
-->

# GenericChess — F15: Native Mirrored Semantic Position Frame + Search-Lifecycle Certification

## 0. AUTHORITATIVE TASK

This is the authoritative F15 task for `WD-nanophotonics/GenericChess`.

F14 closed with:

```text
F14_RESULT = API_CERTIFICATION_PASS
PACKED_CAPSULE_NATIVE_SPEEDUP = 9.19x attack / 8.47x check
PER_QUERY_PACK = REJECT
SELECTED_NEXT_BOUNDARY = NATIVE_MIRRORED_POSITION_FRAME
```

F15 implements exactly that boundary.

The narrow goal is:

> Build and certify an optional Native semantic position mirror that stays exactly synchronized with the Python-authoritative `SearchPathRuntime` DFS lifecycle, allowing future Native attack/check routing to reuse an already-packed Native position instead of repacking per query.

F15 MUST NOT route production attack/check/legal/terminal/evaluation/search truth to Native yet.

Python remains the sole authority.

Valid outcomes:

```text
F15_RESULT = MIRROR_FOUNDATION_PASS
```

or:

```text
F15_RESULT = AUDIT_ONLY_PASS
```

Do not begin F16.

---

## 1. BASELINE LOCK

Hard assert before work:

```text
origin/sandbox = 4e6bff47c4d30d926d5d8aa3e810afa968849bff
origin/master  = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat    = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

If sandbox moved:

```text
BASELINE_MOVED
STOP
```

No reset/rebase/force-push. Work only on sandbox. master/chat read-only.

---

## 2. GMAIL / INBOX PROTOCOL

Before implementation:

1. locate this task through GenericChess Gmail fuzzy subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task under top-level `inbox/`;
4. record Gmail message/thread metadata and status;
5. then execute.

Do not execute from subject/snippet alone.

---

## 3. F14 FROZEN AUTHORITY

Hard assert Standard Shogi fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

Freeze these facts:

```text
STANDARD_SHOGI_NATIVE_EXECUTABLE = true
PUBLIC_NATIVE_SEMANTIC_ATTACK = PASS
PUBLIC_NATIVE_SEMANTIC_IN_CHECK = PASS

packed Native attack ~= 9.19x Python
packed Native check  ~= 8.47x Python
per-query full pack  = REJECT
```

F13/F14 semantic truth and API contracts are immutable in F15.

---

## 4. HARD ARCHITECTURE RULE — CORE REMAINS NATIVE-UNAWARE

F15 MUST NOT add any import from `generic_chess.native` into:

```text
generic_chess/core/search_runtime.py
generic_chess/core/semantic_executor.py
generic_chess/core/terminal.py
any generic_chess/core module
```

Do NOT put Native capsules or Native-specific fields into `SearchPathRuntime`, `_Frame`, `RuntimeSearchState`, history, TT identity, or Position.

Dependency remains:

```text
Core <- AI / Native integration layer
```

not:

```text
Core -> Native
```

If the mirror cannot be implemented without violating this boundary:

```text
ARCHITECTURE_BOUNDARY_VIOLATION
F15_RESULT = AUDIT_ONLY_PASS
```

---

## 5. AUTHORITY / OWNERSHIP CONTRACT

Always:

```text
Python Position + SearchPathRuntime = authoritative
Native semantic position capsule   = synchronized shadow only
```

In F15, no search decision may depend on Native mirror results.

A mismatch is a certification failure, never a reason to overwrite Python.

---

## 6. TARGET LIFECYCLE

Conceptually:

```text
root GameState
  -> SearchPathRuntime(root)
  -> NativeSemanticPositionMirror(root capsule)  # one exact root pack

push(action):
  Python runtime push
  mirror exact-action pack
  Native make_checked(parent_capsule, packed_action)
  child_capsule becomes mirror current

pop():
  discard child capsule
  restore parent capsule reference
```

Mirror live state must scale as:

```text
O(search depth)
```

not O(nodes).

No sibling child retention after pop.

---

## 7. PHASE STRUCTURE

### H15A — harness / architecture audit

Before retained plumbing:

- audit exact semantic root packing;
- audit public semantic Action -> packed Native Action;
- audit SearchPathRuntime push/pop/exception ordering;
- build sync/differential harness;
- measure root-pack and Native make costs;
- no default-search behavior change.

Commit/push H15A and record SHA.

### H15B — mirror foundation

Only if H15A proves a local clean design.

Add a reusable private mirror implementation outside Core, preferably under `generic_chess/native/` or a narrow AI/native integration module.

Add only opt-in/shadow AlphaBeta plumbing required to exercise the exact production DFS lifecycle.

Default search must remain pure Python and unchanged.

Commit/push H15B.

### E15 — evidence/docs closure

Run certification, overhead, tests/build and push E15.

---

## 8. EXACT ROOT PACK

Implement/reuse one semantic root pack path:

```text
GameState + CompiledSemanticRuleset + NativeSemanticCompiledRules
    -> Native semantic position capsule
```

It must preserve all Native-observable state:

```text
fingerprint
side_to_move
ply_count
board occupancy
piece owner/base/current/promoted
hands
aux_state
exact history transport when available
```

Do NOT use legacy movement-atom `NativeCompiledRules` packing as authority.

Use semantic `pack_position` semantics.

---

## 9. HISTORY TRANSPORT / FALLBACK

Where public history contains full SHA-256 `HistoryRecord.position_key`, translate it losslessly into the exact four-word Native semantic history format.

Forbidden:

```text
truncated two-word history as authority
fabricated history
invented repetition evidence
```

If a valid Python root cannot be represented safely as an exact Native semantic mirror because history is opaque/incomplete:

```text
mirror_available = false
normal search = Python-only fallback
```

Do NOT weaken F3 history-aware TT or F12/F13 Native fail-closed history rules.

Test:

```text
complete certified history -> mirror available
custom/imported opaque history -> Python fallback
malformed mirror input -> mirror reject; Python authority preserved
```

---

## 10. NO CHILD EXTERNAL SHA REINTRODUCTION

F2/F3 intentionally removed child external SHA from the Python search hot path.

F15 production mirror MUST NOT call:

```text
position_identity_key(child)
SHA-256 external child key
```

on every push.

Native may maintain its existing internal key/history during `make_checked`.

Audit-only sync verification may compute Python exact keys outside formal performance runs.

Require Python runtime metric:

```text
child_external_key_computations unchanged
```

---

## 11. LOSSLESS SEMANTIC ACTION PACKER

Implement a direct exact packer for public semantic actions.

Public board action already carries:

```text
pattern_id
geometry_id
actor_type_id
from_square
to_square
promotion_target_id
```

Public drop action carries:

```text
pattern_id
geometry_id
base_type_id
to_square
```

The packer may read the authoritative Python parent Position to obtain/verify:

```text
actor base type
actor current type
```

Use frozen Native mappings:

```text
type_ids
pattern_ids
geometry_ids
```

Precompute local ID maps once per mirror if useful.

### Forbidden hot-path packing strategy

Do NOT:

```text
enumerate guarded_actions per push
search for a coordinate match
choose first matching geometry/pattern
re-infer semantic identity
```

No coordinate-only fallback.

---

## 12. PACKED ACTION CERTIFICATION

For every legal action in all four frozen Standard Shogi prefixes:

1. direct-pack from public semantic action;
2. independently enumerate Native guarded actions for audit only;
3. require the direct packed action appears exactly once;
4. unpack/decode and compare identity.

Compare:

```text
kind
pattern
geometry
base type
current type
source
target
promotion
```

Require:

```text
missing = 0
duplicate = 0
field mismatches = 0
```

Audit enumeration must never enter mirror push hot path.

---

## 13. MIRROR CLASS CONTRACT

Preferred conceptual API:

```python
class NativeSemanticPositionMirror:
    @classmethod
    def from_state(compiled, native_rules, state): ...
    @property
    def position(self): ...
    @property
    def depth(self): ...
    def push(self, action, python_parent_position): ...
    def pop(self): ...
    def assert_balanced(self): ...
```

Exact naming may differ.

Allowed retained state:

```text
compiled semantic metadata
native rules
current capsule
parent capsule stack
precomputed ID maps
mirror-only counters
```

Forbidden:

```text
global singleton
cross-game cache
LRU
Core-owned capsule
```

---

## 14. ATOMIC AI-LAYER COMBINED PUSH

Provide opt-in AI/native plumbing that follows the real DFS lifecycle without modifying Core `SearchPathRuntime.pushed()`.

Conceptual behavior:

```text
with mirrored_pushed(runtime, mirror, action, checkpoint):
    ...
```

Hard cases:

### Python push fails

```text
mirror unchanged
Python existing rollback contract preserved
```

### Python push succeeds, mirror push fails

Before propagating:

```text
Python runtime popped to exact parent
mirror at exact parent
```

### search body raises / cancellation / deadline

`finally` restores both to parent exactly once.

### normal exit

Both pop exactly once.

After every successful combined push:

```text
mirror.depth == runtime.depth
```

---

## 15. EXACT SYNC ORACLE

In certification mode, after root/push/pop compare Native snapshot against Python authority.

Compare exactly:

```text
side_to_move
ply
board occupancy
owner/base/current/promoted
hands
aux state
```

Where exact history transport is available, also verify:

```text
history length
Native current position key vs audit-only Python exact key
terminal status when current Native API is authoritative
```

Any mismatch:

```text
MIRROR_SYNC_FAILURE
STOP
```

Production shadow mode must not compute Python child SHA for this check.

---

## 16. STANDARD SHOGI DFS SYNC

Fingerprint hard assert as above.

Use four frozen Standard Shogi prefixes.

Exercise deterministic DFS with:

```text
all depth-1 legal actions
bounded deterministic depth-2 subset
```

Ensure corpus contains where available:

```text
ordinary board move
capture
promotion
drop
checking action
non-checking action
```

For every push:

```text
Python child == Native mirrored child
```

For every pop:

```text
exact parent restored
```

Zero mismatch.

---

## 17. GENERIC SEMANTIC SYNC CORPUS

Exercise representative actions from:

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

Cover at least:

```text
aux mutation
trigger lifetime
capture-to-hand
drop
promotion
special move/shift effects
S3 invariant
S4 postcondition
```

Require exact mirror snapshot parity.

---

## 18. F13/F14 REGRESSION

Re-run:

```text
action_delivers_check witnesses
checking/non-checking drop
uchifuzume
648 Standard Shogi attack differential
8 Standard Shogi in_check differential
curated F14 generic semantic attack corpus
```

Zero regression.

---

## 19. ALPHABETA SHADOW MODE

Add the smallest opt-in test/audit hook needed to maintain the mirror during the real Python AlphaBeta search.

In shadow mode, Python remains authority for:

```text
legal generation
attack/check
terminal
evaluator
TT/history/repetition
search policy
```

Mirror only:

```text
packs root once
mirrors push
mirrors pop
collects cost counters
optionally sync-verifies in audit mode
```

Default search must not construct a mirror.

No public product option is required in F15.

---

## 20. SEARCH PARITY

For frozen Profile A/B and four Standard Shogi cases compare:

```text
baseline Python search
vs opt-in shadow-mirror search
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
legal-action order
TT probes/hits/stores/cutoffs where deterministic
runtime TT eligibility/history evidence
```

Only mirror timing/counters may differ.

---

## 21. INTERRUPTIBILITY / EXCEPTION SAFETY

Shadow mode must preserve:

```text
node budget
time budget
CancellationToken
root fallback
PVS re-search
aspiration re-search
qsearch paths
exception rollback
```

Measure Native mirror `make_checked` latency.

If any stable single mirror make >10 ms:

```text
NATIVE_MIRROR_INTERRUPTIBILITY_RISK
```

Do not add C callbacks/checkpoints in F15.

---

## 22. CAPSULE LIFETIME / MEMORY

Verify live capsules are O(depth).

Record:

```text
root capsules
push-created capsules
live capsule peak
mirror peak depth
```

After full search and forced exception:

```text
mirror.depth == 0
runtime.depth == 0
```

No sibling child retention after pop.

No node-count proportional growth.

---

## 23. MIRROR COST MICROBENCH

Measure separately on Standard Shogi:

```text
exact root semantic pack
direct semantic action pack
Native make_checked child creation
mirror stack push
mirror pop/restore
```

Report median/p90/min/max.

Use >=1000 reps for cheap operations where practical.

Do not include snapshot verification in formal timing.

---

## 24. SHADOW-MODE END-TO-END OVERHEAD

Use frozen profiles.

### Profile A

```text
TT on
ordering off
qsearch depth 0
root tactical off
max_depth 2
max_nodes 512
fresh TT
no wall-clock limit
```

### Profile B

Current production/default AlphaBeta configuration:

```text
max_nodes 256
no wall-clock limit
```

For each semantic case:

```text
1 warm-up
5 measured
```

Compare:

```text
baseline Python
shadow mirror with sync verification OFF
```

Report:

```text
wall time
root packs
mirror pushes/pops
Native make time
action-pack time
peak depth
```

---

## 25. RETENTION GATES

For `MIRROR_FOUNDATION_PASS`, ALL must pass.

### G1 Architecture

```text
Core Native imports = 0
Core Native-specific state = 0
```

### G2 Exact sync

```text
root mismatches = 0
action-pack mismatches = 0
push mismatches = 0
pop mismatches = 0
```

### G3 Search parity

Exact logical parity.

### G4 Failure safety

Push/pop/exception/cancel/sibling isolation all PASS.

### G5 Mirror-only overhead

Aggregate shadow overhead:

```text
Profile A <= 7%
Profile B <= 7%
```

and no semantic case stable regression >10%.

### G6 Projected routing headroom

Use F11 attack/check wall share + F14 packed speedup + measured mirror overhead.

Compute a conservative lower-bound projection:

```text
expected Native attack/check saving - mirror overhead
```

Require projected net:

```text
Profile A >= 8%
Profile B >= 8%
```

If G5/G6 fail:

```text
F15_RESULT = AUDIT_ONLY_PASS
H15B_RETAINED = false
```

Do not keep a mirror foundation whose measured cost consumes the expected routing gain.

---

## 26. NO F15 SPEEDUP CLAIM

F15 does not accelerate production search.

Do not claim search speedup.

Report only:

```text
mirror overhead
mirror synchronization cost
projected future routing headroom
```

---

## 27. SELECT EXACTLY ONE NEXT BOUNDARY

Choose exactly one:

```text
NATIVE_ATTACK_CHECK_ROUTING
NATIVE_LEGALITY_KERNEL
NATIVE_POSITION_RUNTIME
SEARCH_STRENGTH_EVALUATOR_PHASE
```

Select `NATIVE_ATTACK_CHECK_ROUTING` only if:

```text
MIRROR_FOUNDATION_PASS
F14 attack/check certification remains PASS
shadow overhead gate PASS
projected net >=8% A and B
```

Select `NATIVE_LEGALITY_KERNEL` if mirror sync is correct but duplicate Python+Native transition cost makes attack-only routing economically weak and a broader legality unit is the smallest sensible amortization boundary.

Select `NATIVE_POSITION_RUNTIME` if immutable child-capsule lifecycle itself is too costly and a stronger Native runtime position stack is required first.

Select `SEARCH_STRENGTH_EVALUATOR_PHASE` only if Native integration no longer has credible material runtime benefit.

Do not implement the selected boundary.

---

## 28. FALLBACK CONTRACT

If:

```text
native unavailable
semantic rules not native_executable
fingerprint mismatch
root history not safely transportable
mirror root pack unavailable
```

normal search remains pure Python with unchanged outputs.

No stale mirror may be used.

Mandatory-shadow tests may fail closed; product/default search may simply disable mirror.

---

## 29. VERSION / SEMANTIC INVARIANTS

Must remain unchanged:

```text
Standard Shogi fingerprint
Semantic IR = 2
semantic payload = 2
native schema = native-0.5.0
action bit layout
position-key format
history digest format
S3/S4
nifu/uchifuzume
promotion/drop
repetition/continuous_check_loss
F3 history-aware TT
TT bounds/generation/replacement
qsearch policy
evaluator
move ordering/search heuristics
```

---

## 30. OLD EVIDENCE IMMUTABILITY

Preserve byte-identically all F4–F14 artifacts/docs/ADRs.

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f15_native_mirrored_position/
```

---

## 31. REQUIRED EVIDENCE

At minimum:

```text
artifacts/f15_native_mirrored_position/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    architecture_audit.json
    core_dependency_check.json
    root_pack_contract.json
    history_transport.json
    action_pack_contract.json
    action_pack_differential.json

    standard_shogi_dfs_sync.jsonl
    standard_shogi_sync_summary.json
    generic_semantic_sync.json

    push_pop_exception_matrix.json
    sibling_isolation.json
    opaque_history_fallback.json
    capsule_lifetime.json
    interruptibility.json

    f13_f14_regression.json

    profile_a_baseline.jsonl
    profile_a_shadow.jsonl
    profile_b_baseline.jsonl
    profile_b_shadow.jsonl

    mirror_cost_microbench.json
    shadow_overhead.json
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

Create:

```text
docs/architecture/F15_EVIDENCE.md
docs/architecture/ADR-032-native-mirrored-semantic-position.md
```

ADR-032 must document:

- Python authority / Native mirror ownership;
- Core remains Native-unaware;
- root history transport;
- lossless semantic action packing;
- combined push/pop atomicity;
- O(depth) capsule lifetime;
- measured mirror overhead;
- projected Native attack-routing headroom;
- selected next boundary.

---

## 32. TESTS

Focused coverage at minimum:

```text
F15 root pack
action direct pack + all-actions membership differential
mirror root/push/pop sync
sibling isolation
exception rollback
opaque history fallback
capsule lifetime
AlphaBeta shadow mode
node/time/cancel
PVS
aspiration
qsearch
root tactical path where applicable

F14 648 attack differential
F14 in_check
F13 action_delivers_check
uchifuzume
native semantic compiler/position/make/terminal/fixed-depth
10-case Native corpus
F3 history/TT
repetition/continuous-check
F4-F11 regressions
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

Require PASS.

No AlphaSho. No long games.

---

## 33. RUNTIME SAFETY

Hard limits:

```text
focused/differential subprocess <= 60 s
single Profile run <= 120 s
single microbenchmark process <= 120 s
```

No multi-hour runner.

On cap breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve evidence.

---

## 34. FORBIDDEN SCOPE

F15 must not:

```text
import Native from Core
store Native capsule in SearchPathRuntime/_Frame
route Python attack/check to Native
route legal generation/terminal/evaluator to Native
replace SearchPathRuntime
make Native position authoritative
route AlphaBeta to Native search
add Native TT/qsearch/budgets
change evaluator/search heuristics
add attack/terminal cache
add bitboards/incremental attack map
change IR/payload/schema/fingerprint/action layout
```

No F16 work.

---

## 35. GIT / PROVENANCE

Expected success path:

```text
E14 baseline
  -> H15A harness/architecture audit
  -> H15B mirror foundation + opt-in shadow plumbing
  -> E15 evidence/docs closure
```

If retention gate fails, cleanly revert non-qualifying mirror production plumbing before E15 while keeping diagnostic evidence.

Final:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

---

## 36. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
ARCHITECTURE_BOUNDARY_VIOLATION
MIRROR_ROOT_MISMATCH
MIRROR_ACTION_PACK_MISMATCH
MIRROR_SYNC_FAILURE
MIRROR_POP_FAILURE
MIRROR_EXCEPTION_ROLLBACK_FAILURE
MIRROR_SIBLING_LEAK
SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
CAPSULE_LIFETIME_FAILURE
F13_F14_REGRESSION
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance-gate failure is not a correctness stop; close AUDIT_ONLY and select the next boundary.

---

## 37. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. Architecture boundary audit
6. Root semantic pack contract
7. History transport / fallback
8. Lossless semantic action packing
9. H15A provenance
10. H15B implementation
11. Standard Shogi DFS mirror sync
12. Generic semantic mirror sync
13. Push/pop/exception/sibling isolation
14. Capsule lifetime
15. F13/F14 regression
16. AlphaBeta shadow search parity
17. Interruptibility
18. Mirror cost microbenchmark
19. Shadow-mode overhead
20. Projected Native routing headroom
21. Retention gate
22. Selected next boundary
23. Tests
24. Evidence / manifest
25. Git
26. Deferred
27. Final verdict

Successful retained verdict:

```text
F15_RESULT = MIRROR_FOUNDATION_PASS
CORE_NATIVE_UNAWARE = PASS
ROOT_NATIVE_MIRROR = PASS
LOSSLESS_SEMANTIC_ACTION_PACK = PASS
MIRROR_PUSH_POP_SYNC = PASS
MIRROR_EXCEPTION_SAFETY = PASS
MIRROR_SIBLING_ISOLATION = PASS
CAPSULE_LIFETIME = PASS
SEARCH_SHADOW_PARITY = PASS
INTERRUPTIBILITY = PASS
MIRROR_OVERHEAD_GATE = PASS
PROJECTED_NET_HEADROOM = PASS
SELECTED_NEXT_BOUNDARY = <...>
FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Audit-only verdict:

```text
F15_RESULT = AUDIT_ONLY_PASS
H15B_RETAINED = false
reason = <exact failed architecture/performance gate>
SELECTED_NEXT_BOUNDARY = <NATIVE_LEGALITY_KERNEL | NATIVE_POSITION_RUNTIME | SEARCH_STRENGTH_EVALUATOR_PHASE>
FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

---

## 38. FINAL STOP

F15 ends after E15 closure.

Do not begin F16.

Do not route attack/check to Native.

The selected next boundary must be separately reviewed and authorized.
