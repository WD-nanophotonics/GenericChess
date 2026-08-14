<!-- Gmail provenance
message_id: 19fff64c9728b3cd
thread_id: 19fff64c9728b3cd
subject: GenericChess — F18: Native Semantic Position-Key / History Hot-Path Optimization + Delta-Runtime Requalification
from: W D <icywoods.1@gmail.com>
attachment: GenericChess_F18_Native_Position_Key_History.md
fetched_at: 2026-08-14 Asia/Tokyo
processing_state: complete-authoritative-attachment
-->

# Gmail body

EXECUTE NOW.

The attached Markdown is the complete authoritative F18 task. Follow the repository-local Gmail/inbox protocol: persist the full attachment and Gmail provenance under top-level inbox/ before execution, hard-lock the specified SHAs, work only on sandbox, and do not begin F19.

This task has two stages: first, certify and optimize the exact Native semantic external-key/history path while preserving every canonical SHA-256 byte; second, only if that production optimization is retained, reconstruct the frozen F17 H17A delta prototype for audit-only lifecycle requalification. Do not retain or integrate the delta runtime in F18.

# Complete authoritative attachment

# GenericChess — F18: Native Semantic Position-Key / History Hot-Path Optimization + Delta-Runtime Requalification

## 0. AUTHORITATIVE TASK

This is the authoritative F18 task for `WD-nanophotonics/GenericChess`.

F17 concluded:

```text
F17_RESULT = AUDIT_ONLY_PASS
H17B_CREATED = false
SELECTED_NEXT_BOUNDARY = NATIVE_POSITION_KEY_HISTORY_OPTIMIZATION
```

F17 proved that the delta undo design itself is small and semantically correct:

```text
sizeof(GCSemanticDeltaUndo) = 656 bytes
board delta capacity = 9
hand delta capacity = 10
aux delta capacity = 24
depth-512 delta memory = 335,872 bytes
```

but the measured lifecycle still failed:

```text
delta push+pop median = 31.39 us
p90 = 32.09 us
required absolute gate = 18.0 us
required F16-relative gate = 17.92 us
```

The selected next boundary is therefore the exact Native semantic position-key / history append path.

F18 has two goals:

1. optimize the existing Native semantic external-key/history hot path **without changing a single canonical external SHA-256 result**;
2. after that production optimization is independently certified, re-run the frozen F17 delta-runtime probe against the optimized key/history path to determine whether the delta runtime now qualifies for a later production certification phase.

F18 MUST NOT retain a delta runtime, mirror, Native attack routing, legality routing, or production Native search.

Valid successful outcomes:

```text
F18_RESULT = KEY_HISTORY_OPTIMIZATION_PASS
```

or:

```text
F18_RESULT = AUDIT_ONLY_PASS
```

A retained key/history optimization is allowed even if the F17 delta runtime still fails requalification, provided the key/history optimization independently clears its own frozen gates.

Do not begin F19.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before work:

1. locate this task by GenericChess/Gmail fuzzy subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. only then begin audit/execution.

Do not execute from the email subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
4999be31b6fc91655d7d0df9c948ef3bbdb43408

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

# 3. F13–F17 FROZEN AUTHORITY

Treat all earlier decisions as closed.

## F13

```text
action_delivers_check Native support = PASS
Standard Shogi native_executable = true
```

## F14

```text
public Native semantic attack/check = PASS
packed Native attack speedup = 9.19x
packed Native check speedup = 8.47x
per-query pack = REJECT
```

## F15

Immutable child-capsule mirror:

```text
correct = true
retained = false
Profile A overhead = 9.28%
Profile B overhead = 6.25%
```

## F16

Full-position mutable undo:

```text
sizeof position = 27,296 bytes
sizeof full undo = 27,296 bytes
estimated push+pop copy = 109,184 bytes
mutable trial = 23.89 us
retained = false
```

## F17

Transactional delta prototype:

```text
Strategy B pre-view overlay
delta frame = 656 bytes
semantic differential = PASS
rollback differential = PASS
delta push+pop = 31.39 us
retained = false
```

F18 MUST NOT revive F15/F16/F17 runtime infrastructure as production code.

The F17 prototype may be reconstructed from H17A commit:

```text
87fb25e
```

for audit-only requalification after H18B.

---

# 4. CURRENT NATIVE KEY/HISTORY PATH — FREEZE BASELINE

Current Native external semantic key authority is:

```text
gc_semantic_position_key_digest(...)
```

in:

```text
generic_chess/_native/native_semantic_key.c
```

Current behavior includes:

1. sort public type IDs on every key computation;
2. sort aux slots on every key computation;
3. dynamically grow a heap string buffer with `realloc`;
4. serialize the exact canonical JSON bytes matching Python `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True)`;
5. SHA-256 the completed JSON buffer;
6. hex encode the 32-byte digest to 64 lowercase hex chars.

Current successful semantic make then:

1. calls `gc_semantic_position_key_digest(...)`;
2. receives the 64-char hex digest;
3. parses each hex nibble back into four 64-bit words;
4. appends those words to:
   `history_lo`, `history_hi`, and `history_digest`;
5. increments `history_len`.

This is the target.

Do not change the canonical external-key definition.

---

# 5. EXTERNAL KEY CONTRACT — ABSOLUTE HARD INVARIANT

The following must remain byte-for-byte unchanged:

```text
Python semantic_position_key(...)
Native semantic_position_key(...)
HistoryRecord.position_key
repetition identity
Native full SHA-256 history digest
F3 external key semantics
```

For every valid position:

```text
old Native hex digest
==
new Native hex digest
==
Python semantic_position_key
```

No migration.
No new key version.
No alternate internal repetition identity.
No truncated authoritative key.
No Zobrist replacement.

Runtime/internal accelerators may exist only if exact SHA-256 remains the externally authoritative value.

---

# 6. ALLOWED OPTIMIZATION FAMILY

F18 authorizes one coherent family:

```text
canonical semantic key streaming + direct raw-digest history append
```

This family may include all of the following because they remove overhead from the same exact serialization/digest pipeline:

### A. Stream canonical bytes directly into SHA-256

Instead of:

```text
build full heap JSON buffer
-> hash buffer
-> free buffer
```

use:

```text
canonical serializer
-> gc_sha256_update(...)
-> gc_sha256_final(...)
```

The byte stream must be exactly identical to the old canonical JSON bytes.

### B. Raw digest API internally

Add an internal function such as:

```c
int gc_semantic_position_key_digest_raw(
    const GCSemanticRules *rules,
    const GCSemanticPosition *position,
    uint8_t digest[32]
);
```

or equivalent.

The existing public hex function may become:

```text
raw digest
-> gc_sha256_hex
```

### C. Direct history append from raw bytes

Successful semantic make may consume the raw 32-byte digest directly.

Do not:

```text
raw digest -> hex string -> parse hex -> words
```

in the internal hot path.

The public `semantic_position_key()` API must still return the same lowercase 64-char hex string.

### D. Precompute immutable canonical ordering

Because Native rules are immutable after compile, F18 may precompute once:

```text
type indices sorted by public type_id
aux slot indices sorted by slot_id
```

inside owned Native rules metadata.

Do not sort these on every key.

### E. Precompute immutable canonical fragments if local

F18 may precompute immutable escaped fragments that are part of every key, for example:

```text
escaped public type IDs
escaped ruleset fingerprint
canonical aux logical key names
```

only if:
- ownership is simple;
- rules cleanup is exact;
- no payload/schema version changes;
- direct byte-equivalence is tested.

Do not turn this into a generalized serializer framework.

---

# 7. FORBIDDEN KEY OPTIMIZATIONS

F18 must not implement:

```text
incremental SHA under arbitrary board edits
Merkle tree identity
Zobrist as external identity
collision-probabilistic repetition
64/128-bit replacement for SHA-256
history digest truncation
lazy history omission
per-position key cache
global key cache
LRU
hash table memoization
```

Do not change Python `semantic_position_key()`.

Do not change external serialization.

---

# 8. PHASE STRUCTURE

Use three provenance phases.

## H18A — AUDIT / BASELINE / BYTE ORACLE

Before production optimization:

1. profile the current key/history path;
2. create an exact canonical-byte oracle;
3. measure sorting, serialization/allocation, SHA, hex, hex-reparse/history append separately where practical;
4. freeze old Native key outputs over the certification corpus;
5. build a test-only streaming/raw-digest candidate.

H18A MUST NOT change retained production key behavior.

Commit and push H18A.

Record exact SHA.

## H18B — PRODUCTION KEY/HISTORY OPTIMIZATION

H18B may be created only if H18A passes the authorization gate in Section 14.

Implement only the allowed optimization family in Sections 6–7.

Commit and push H18B before F17 requalification.

## E18 — FINAL CERTIFICATION / DELTA REQUALIFICATION

After H18B:

1. certify external key parity;
2. certify Native semantic runtime/search regressions;
3. benchmark production key/history improvement;
4. reconstruct the F17 H17A delta prototype in audit-only form against H18B;
5. rerun the frozen F17 lifecycle benchmark;
6. select exactly one next boundary;
7. create evidence/docs closure.

---

# 9. H18A BASELINE COST ATTRIBUTION

Create a bounded audit, preferably:

```text
scripts/audit_f18_native_position_key.py
```

Measure on already-packed Native positions from the four frozen Standard Shogi prefixes.

At minimum measure:

```text
full gc_semantic_position_key_digest hex call

canonical ordering:
    type sort
    aux-slot sort

canonical serialization:
    numeric formatting
    string escaping
    dynamic buffer allocation/reallocation/copy

SHA-256 update/final
hex encoding
hex -> 4x uint64 parse

history tail append
```

If exact independent decomposition would require invasive changes, use test-only variants and report:

```text
MEASURED
ESTIMATED_FROM_SUBTRACTION
NESTED_ONLY
```

honestly.

Do not fabricate exclusive percentages.

At minimum answer:

```text
how many us of F17's ~31.39 us are key/history related?
```

---

# 10. CANONICAL BYTE ORACLE

The old Native serializer is currently certified against Python key output, but F18 changes its internal construction.

Before H18B, add a test-only way to capture or compare the exact canonical byte stream.

For deterministic fixtures, require:

```text
old Native canonical bytes
==
new streaming canonical bytes
==
Python json.dumps canonical bytes
```

where practical.

If exposing the entire old C buffer is unnecessarily invasive, use a test-only old/new dual-digest oracle plus independent Python canonical raw bytes.

At minimum include:

```text
ASCII type IDs
non-ASCII/escaped type IDs
quotes
backslashes
control characters where compiler allows them
empty hands
non-empty hands
promoted/unpromoted pieces
global aux
per-owner aux
bool aux
square aux
null/default aux
multiple aux slots
owner 0/1
side-to-move 0/1
```

Canonical JSON escaping is part of the external identity contract.

---

# 11. KEY DIFFERENTIAL CORPUS

Hard assert Standard Shogi fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

Use:

- four frozen Standard Shogi prefixes;
- every legal depth-1 child from each prefix;
- bounded deterministic depth-2 subset;
- the frozen generic semantic 10-case corpus;
- F13/F14/F17 curated fixtures;
- explicit aux-state variants;
- promotion/drop/capture variants.

For every position compare:

```text
Python semantic_position_key
old Native baseline key frozen by H18A
new Native public semantic_position_key
new Native raw digest -> hex
```

Require:

```text
mismatches = 0
```

Store row-level evidence.

---

# 12. HISTORY APPEND DIFFERENTIAL

For every successful checked semantic make:

Compare old baseline vs new optimized path:

```text
history_len
history_exact
history_lo appended word
history_hi appended word
history_digest appended [4]
full public position key
repetition occurrence behavior
terminal behavior where repetition matters
```

Require exact equality.

Test:

```text
history_len = 0/1/mid
history_len near GC_MAX_PLY
history full rejection
history_exact true
history_exact false where current valid semantics allow
ordinary repetition
continuous_check_loss control
```

Failure before history append must leave history unchanged.

---

# 13. FAILURE ATOMICITY

The optimized raw-digest path must remain failure-safe.

Test at minimum:

```text
invalid position data
invalid type index
invalid UTF-8 type ID if compiler can construct it
allocation failure for any newly precomputed rules metadata where testable
history full
checked make rejection before key
S3 rejection
S4 rejection
```

Requirements:

```text
failed make does not append history
failed make does not mutate authoritative parent
public key API raises/fails consistently with baseline
```

Do not weaken fail-closed behavior.

---

# 14. H18B AUTHORIZATION GATE

All gates must pass before production optimization.

## G1 — EXACT KEY PARITY

```text
old Native == candidate Native == Python
mismatches = 0
```

## G2 — MATERIAL KEY SPEEDUP

On Standard Shogi aggregate, already-packed positions:

```text
candidate public Native position-key median
<= 0.60 × baseline
```

OR:

```text
speedup >= 1.67x
```

## G3 — INTERNAL RAW-DIGEST BENEFIT

For the exact internal make-history path:

```text
raw digest + direct history append
```

must be at least:

```text
20% faster
```

than:

```text
hex digest + hex parse + history append
```

measured as the same internal stage.

## G4 — NO SEMANTIC VERSION CHANGE

Must remain:

```text
IR = 2
SEMANTIC_PAYLOAD_VERSION = 2
NATIVE_SCHEMA_VERSION = native-0.5.0
fingerprint unchanged
```

If any gate fails:

```text
F18_RESULT = AUDIT_ONLY_PASS
H18B_CREATED = false
```

Close with evidence and select the next boundary.

Do not broaden to a new identity architecture inside F18.

---

# 15. PRODUCTION IMPLEMENTATION RULES

If H18B is authorized:

- one Native key authority;
- no duplicate canonical serializer;
- public hex API delegates to the optimized raw/streaming authority;
- internal make/history uses raw digest directly;
- any sorted-index/preescaped metadata is owned by `GCSemanticRules` and freed exactly once;
- unknown/malformed state remains fail-closed.

Preferred internal shape:

```text
gc_semantic_position_key_digest_raw(...)
gc_semantic_position_key_digest(...)  // raw -> hex wrapper
```

Exact naming may differ.

Do not modify Python Core identity code.

---

# 16. PUBLIC API PARITY

Re-run:

```text
semantic_position_key
semantic_position_snapshot
pack_position
make_checked
candidate_actions
guarded_actions
terminal
fixed_depth search smoke
```

for Standard Shogi and frozen generic Native semantic corpus.

No output/order changes.

---

# 17. F3 / REPETITION / HISTORY REGRESSION

Re-run all relevant:

```text
F3 history-aware TT tests
ordinary repetition
continuous_check_loss
opaque history
complete exact history
wrong/malformed history
Native semantic terminal
Native semantic fixed-depth history behavior
```

F18 must not redefine search/runtime identity.

---

# 18. F13/F14 REGRESSION

Re-run:

```text
F13 action_delivers_check
S4 conjunction
checking drop / uchifuzume

F14 648 Standard Shogi attack differential
8 in_check differential
curated generic semantic attack corpus
```

The key optimization must not change semantic execution.

---

# 19. PRODUCTION KEY/HISTORY MICROBENCHMARK

After H18B, repeat exactly the H18A benchmark.

Report:

```text
baseline public key us
optimized public key us
speedup

baseline internal digest/history stage us
optimized raw digest/history stage us
speedup

allocation count/bytes if measurable
sort calls eliminated
hex parses eliminated
```

Use:

```text
warm-up >= 100
measured repetitions >= 5000
median
p90
p99/max where practical
```

No snapshot verification during timing.

---

# 20. NATIVE MAKE PERFORMANCE REGRESSION / IMPROVEMENT

Because the optimized key is used by semantic make, benchmark already-packed:

```text
make_checked
```

before vs after H18B on deterministic legal Standard Shogi actions.

Report:

```text
median
p90
```

A retained key optimization must not cause stable make regression.

Require:

```text
aggregate make_checked improvement >= 10%
```

OR, if key calls are a minority of make cost:

```text
no stable regression >3%
and key/history independent gates G2/G3 pass
```

---

# 21. F17 DELTA RUNTIME REQUALIFICATION — AUDIT ONLY

Only after H18B is retained and certified:

Reconstruct the exact F17 H17A delta runtime prototype from:

```text
87fb25e
```

Do not redesign it.

Freeze:

```text
Strategy B pre-view overlay
delta capacities 9/10/24
delta frame semantics
precomputed action pack
```

The only intended material difference is:

```text
optimized H18B key/history path
```

No additional delta optimization is authorized.

Run the same F17 Standard Shogi lifecycle benchmark:

```text
warm-up = same as F17
repetitions = 5000
same packed action/corpus
```

Report:

```text
F17 baseline delta median = 31.39 us
F17 baseline p90 = 32.09 us

F18 requalified delta median
F18 requalified delta p90
```

---

# 22. DELTA REQUALIFICATION GATE

The F17 delta runtime is considered eligible for a future production-certification phase only if:

```text
median <= 18.0 us
AND
p90 <= 25.0 us
```

Also require:

```text
zero Standard Shogi raw differential mismatch
zero nested push/pop mismatch
zero invalid-action rollback mismatch
```

If it passes:

```text
DELTA_RUNTIME_REQUALIFIED = true
SELECTED_NEXT_BOUNDARY = NATIVE_DELTA_POSITION_RUNTIME_CERTIFICATION
```

Do NOT retain or productionize the delta runtime in F18.

If it fails:

```text
DELTA_RUNTIME_REQUALIFIED = false
```

and choose the next boundary from Section 23.

---

# 23. SELECT EXACTLY ONE NEXT BOUNDARY

F18 must select exactly one:

```text
NATIVE_DELTA_POSITION_RUNTIME_CERTIFICATION
NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT
NATIVE_LEGALITY_KERNEL
SEARCH_STRENGTH_EVALUATOR_PHASE
```

Selection rules:

## `NATIVE_DELTA_POSITION_RUNTIME_CERTIFICATION`

Only if:

```text
H18B retained
DELTA_RUNTIME_REQUALIFIED = true
```

## `NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT`

Only if:
- H18B streaming/raw-digest optimization is correct and retained;
- key/history is still the measured dominant blocker;
- delta lifecycle still misses 18 us materially;
- further improvement would require a new identity architecture beyond exact streaming SHA.

Do not implement it.

## `NATIVE_LEGALITY_KERNEL`

Select if optimized key/history is no longer the main blocker and a broader Native legality unit is now the smallest plausible way to amortize runtime transition cost.

## `SEARCH_STRENGTH_EVALUATOR_PHASE`

Select if the Native runtime route no longer has credible material value versus product-strength work.

Do not begin the selected phase.

---

# 24. CORE BOUNDARY

Core remains Native-unaware.

F18 MUST NOT modify:

```text
generic_chess/core/search_runtime.py
generic_chess/core/semantic_executor.py
generic_chess/core/terminal.py
generic_chess/core/identity.py
generic_chess/core/keys.py
```

except tests may import these as Python authorities.

If production optimization requires Core change:

```text
ARCHITECTURE_BOUNDARY_VIOLATION
STOP
```

---

# 25. NO PRODUCTION RUNTIME ROUTING

F18 must not:

```text
retain F17 delta runtime
retain F16 mutable runtime
retain F15 mirror

route attack/check to Native
route legal generation to Native
route terminal to Native
route evaluator to Native
route AlphaBeta to Native search
```

The only allowed retained production change is the Native semantic key/history optimization family.

---

# 26. VERSION / IDENTITY INVARIANTS

Must remain unchanged:

```text
Standard Shogi fingerprint
Semantic IR version = 2
SEMANTIC_PAYLOAD_VERSION = 2
NATIVE_SCHEMA_VERSION = native-0.5.0

public semantic_position_key hex bytes
public action bit layout
position snapshot format
history digest semantic meaning

repetition policy
continuous_check_loss
F3 TT identity/context
```

No version bump in F18.

If impossible:

```text
VERSION_CONTRACT_BLOCKED
STOP
```

---

# 27. F4–F17 EVIDENCE IMMUTABILITY

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
artifacts/f17_native_delta_position_runtime/**

docs/architecture/F4_EVIDENCE.md through docs/architecture/F17_EVIDENCE.md
ADR-022 through ADR-034
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f18_native_position_key_history/
```

---

# 28. REQUIRED F18 EVIDENCE

At minimum:

```text
artifacts/f18_native_position_key_history/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    key_pipeline_audit.json
    key_cost_attribution.json
    old_key_corpus.jsonl

    canonical_byte_oracle.json
    key_differential.jsonl
    key_differential_summary.json

    history_append_differential.json
    failure_atomicity.json

    h18b_authorization_gate.json
    optimization_design.json

    public_api_regression.json
    repetition_history_regression.json
    f13_f14_regression.json

    key_microbench_before.json
    key_microbench_after.json
    key_microbench_comparison.json

    make_checked_before.json
    make_checked_after.json
    make_checked_comparison.json

    f17_delta_requalification.json
    delta_requalification_gate.json

    selected_next_boundary.json

    old_evidence_before.sha256
    old_evidence_after.sha256

    focused_tests.txt
    full_pytest.txt
    final_native_build.txt

    final_verdict.json
    manifest.json
```

If H18B is not authorized, after-only and delta-requalification artifacts may explicitly contain:

```text
NOT_RUN_NOT_AUTHORIZED
```

rather than fabricated values.

Create:

```text
docs/architecture/F18_EVIDENCE.md
docs/architecture/ADR-035-native-semantic-key-history-hotpath.md
```

ADR-035 must document:

- frozen external key contract;
- old heap-buffer/hex-reparse pipeline;
- streaming/raw-digest implementation or rejection;
- exact byte/digest parity;
- key/history performance;
- F17 delta requalification result;
- selected next boundary.

---

# 29. TESTS

Focused tests must include at least:

```text
Native semantic key exact parity
canonical escaping
type sort ordering
aux slot ordering
raw digest -> public hex
history append words
history full
repetition
continuous_check_loss

pack/snapshot/make_checked
candidate/guarded/terminal
fixed-depth semantic search

F13 action_delivers_check / uchifuzume
F14 attack/check
F17 delta raw differential requalification if H18B retained

F3 history/TT
F4-F17 frozen regressions
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

# 30. RUNTIME SAFETY

Hard limits:

```text
single focused/differential subprocess <= 60 s
single microbenchmark subprocess <= 120 s
single delta requalification subprocess <= 120 s
```

No multi-hour workload.

On breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve evidence.

---

# 31. GIT / PROVENANCE

If optimization is retained:

```text
E17 baseline
  -> H18A audit/byte oracle
  -> H18B key/history production optimization
  -> E18 certification + delta requalification
```

If H18B is not authorized:

```text
E17 baseline
  -> H18A
  -> E18 audit-only closure
```

If H18B is trialed but later fails correctness/final retention:

```text
cleanly revert H18B production source
retain diagnostic evidence
close E18 audit-only
```

Record exact SHAs.

Final requirements:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

---

# 32. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
ARCHITECTURE_BOUNDARY_VIOLATION
VERSION_CONTRACT_BLOCKED

CANONICAL_BYTE_MISMATCH
POSITION_KEY_MISMATCH
RAW_HEX_DIGEST_MISMATCH
HISTORY_APPEND_MISMATCH
REPETITION_REGRESSION
CONTINUOUS_CHECK_REGRESSION
FAILURE_ATOMICITY_FAILURE

F13_F14_REGRESSION
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance failure is not a correctness STOP.

Close audit-only where applicable.

---

# 33. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. Current key/history pipeline
6. Baseline cost attribution
7. Canonical-byte oracle
8. Key differential
9. History append differential
10. Failure atomicity
11. H18A provenance
12. H18B authorization gate
13. Production optimization design or rejection
14. Public API parity
15. Repetition/history regression
16. F13/F14 regression
17. Key microbenchmark
18. make_checked benchmark
19. F17 delta-runtime requalification
20. Delta requalification gate
21. Selected next boundary
22. Tests
23. Evidence / manifest
24. Git
25. Deferred
26. Final verdict

Successful optimization verdict:

```text
F18_RESULT = KEY_HISTORY_OPTIMIZATION_PASS

EXTERNAL_POSITION_KEY_PARITY = PASS
CANONICAL_BYTE_PARITY = PASS
RAW_DIGEST_HISTORY_APPEND = PASS

KEY_PERFORMANCE_GATE = PASS
MAKE_CHECKED_REGRESSION_GATE = PASS

DELTA_RUNTIME_REQUALIFIED = <true|false>

SELECTED_NEXT_BOUNDARY =
<NATIVE_DELTA_POSITION_RUNTIME_CERTIFICATION |
 NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT |
 NATIVE_LEGALITY_KERNEL |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Audit-only verdict:

```text
F18_RESULT = AUDIT_ONLY_PASS
H18B_CREATED = false
reason = <exact failed gate>

DELTA_RUNTIME_REQUALIFIED = false

SELECTED_NEXT_BOUNDARY =
<NATIVE_POSITION_KEY_ARCHITECTURE_REASSESSMENT |
 NATIVE_LEGALITY_KERNEL |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

---

# 34. FINAL STOP

F18 ends after E18 closure.

Do not begin F19.

Do not retain or integrate the delta runtime.

Do not route attack/check to Native.

The selected next boundary must be separately reviewed and authorized.

