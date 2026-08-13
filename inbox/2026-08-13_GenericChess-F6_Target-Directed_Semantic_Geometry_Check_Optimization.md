<!-- Gmail inbox record -->
<!-- Received: 2026-08-13T08:39:45-05:00 -->
<!-- Subject: GenericChess — F6: Target-Directed Semantic Geometry / Check Optimization -->
<!-- Sender: W D icywoods.1@gmail.com -->
<!-- Message ref: 19ffb59ad569788d -->
<!-- Attachment: GenericChess_F6_Target_Directed_Semantic_Geometry.md (19521 bytes) -->
<!-- Status: authoritative task captured; processing in sandbox worktree -->
<!-- Source note: Gmail fuzzy-title protocol; exact GenericChess F6 match -->
# GenericChess — F6: Target-Directed Semantic Geometry / Check Optimization

## 0. AUTHORITATIVE TASK / STOP BOUNDARY

This is the next and only authorized GenericChess engineering phase after F5 closure.

F5 is closed. Do **not** reopen F4/F5, do not stack unrelated optimizations, and do not start F7 after finishing this task.

The purpose of F6 is narrowly defined:

> Determine whether semantic attack/check and S3 legality still waste material runtime by enumerating all geometry targets when the caller asks about one exact target square, then — only if strict evidence gates pass — implement one generic, semantics-preserving target-directed geometry optimization.

A valid outcome is either:

```text
F6_RESULT = OPTIMIZATION_PASS
```

or, if the optimization gate is not met:

```text
F6_RESULT = AUDIT_ONLY_PASS
```

Do not force an optimization merely to obtain `OPTIMIZATION_PASS`.

---

## 1. BASELINE LOCK

Before changing anything, fetch and hard-assert:

```text
origin/sandbox = b4372c077c2bce7bada05257a50e518807bf6f71
origin/master  = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat    = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Expected starting commit message on sandbox:

```text
docs: close F5 semantic attack optimization evidence
```

If `origin/sandbox` has moved because another authorized task already advanced it:

```text
BASELINE_MOVED
```

Record the actual refs and STOP. Do not reset, rebase, force-push, or overwrite another task.

Use only the `sandbox` worktree for implementation. `master` and `chat` are read-only in F6.

The existing Gmail/inbox protocol is already accepted. Preserve it. Do not redesign the workflow in this phase.

---

## 2. F5 INVARIANTS — FROZEN

F5 established a position-local source dispatch index in `generic_chess/core/semantic_executor.py` keyed by:

```text
(owner, current_type_id)
```

This source index and its ordering semantics are frozen.

F6 must preserve exactly:

```text
pattern order
→ type_id order
→ source board order
→ geometry_id order
→ target order
→ promotion order
```

Also frozen:

- public semantic action identity;
- ruleset fingerprint and public serialization;
- Standard Shogi certified fingerprint;
- S0/S1/S3/S4 semantics;
- `action_delivers_check` semantics;
- `no_legal_reply` / S3 reply existence semantics;
- nifu / uchifuzume behavior;
- promotion and forced-promotion behavior;
- transition effects/triggers;
- repetition and continuous-check adjudication;
- F3 history-aware TT identity and eligibility;
- F4 fixed-node checkpoint fast path;
- interactive deadline/cancellation semantics;
- qsearch policy;
- TT bound/generation/replacement/mate normalization;
- Core remains AI-unaware.

No fingerprint bump is authorized.

---

## 3. WHY F6 EXISTS

F5 removed repeated full-board owner/type filtering and produced large improvements:

```text
Profile A semantic aggregate:
6016.505 ms -> 809.884 ms

Profile B semantic aggregate:
37220.352 ms -> 4707.074 ms
```

But the F5 post-optimization evidence still shows substantial semantic geometry work. In attack/check existence queries the code currently conceptually performs:

```text
source
→ geometry
→ geometry_candidates(source)
→ generate reachable target candidates
→ compare each candidate target with the one queried square
```

For `is_square_attacked(position, square, by_owner)`, the caller needs an answer about **one exact target square**. Therefore F6 investigates whether a generic target-directed primitive can answer:

```text
Does this compiled geometry reach this exact target from this source?
If yes, what is the exact canonical intermediate path?
```

without manufacturing unrelated target candidates.

Do not assume this is beneficial. Measure it first.

---

## 4. CANONICAL AUTHORITY

The existing function:

```python
geometry_candidates(geometry, owner, source)
```

in `generic_chess/rules/ir.py` is the **F6 oracle** for geometry semantics.

Current compiled geometry kinds are:

```text
leap
ray
drop
```

The compiled IR already stores canonical ordered per-owner/per-source paths. F6 may exploit that compiled representation, but it must not reinterpret high-level movement rules.

### Hard rule

Any target-directed candidate must be proven equivalent to `geometry_candidates()`.

For each tested `(geometry, owner, source, target)` define the baseline exactly as:

```python
baseline_matches = tuple(
    (candidate_target, candidate_path)
    for candidate_target, candidate_path
    in geometry_candidates(geometry, owner, source)
    if candidate_target == target
)
```

The candidate target-directed result must equal `baseline_matches` **exactly as a tuple**.

Do not compare only booleans. This gate protects:

- reachability;
- multiplicity;
- canonical intermediate path;
- ordering.

For `drop` geometry the target-directed board-geometry result must be empty unless the existing oracle defines otherwise. Do not smuggle drop legality into the target-directed board geometry helper.

---

## 5. H6A — HARNESS FIRST, NO PRODUCTION OPTIMIZATION

Before any production optimization, implement and commit a harness-only state `H6A`.

`H6A` may add:

- audit scripts;
- tests;
- opt-in monkeypatch/probe implementations;
- counters;
- evidence schema;
- benchmark helpers.

`H6A` must **not** alter the production geometry/semantic execution path.

Push `H6A` to `origin/sandbox` and record its full SHA.

The parent of H6A must descend directly from the F5 closure baseline without unrelated product changes.

---

## 6. TARGET-DIRECTED EQUIVALENCE MATRIX

Build an exhaustive bounded equivalence harness for all compiled geometry actually present in the certified corpus plus curated generic fixtures.

At minimum, for every relevant `CompiledGeometry`:

```text
owner = 0, 1
source = every board square
query target = every board square
```

Compare the exact tuple defined in Section 4.

Required geometry coverage:

- leap;
- short ray;
- long ray;
- ray with `min_steps > 1` if representable in current fixtures;
- owner-relative orientation for both owners;
- blocked/unblocked paths at semantic predicate level where relevant;
- edge/corner sources;
- unreachable target;
- source == target negative case;
- every geometry used by certified Semantic Standard Shogi.

If the repository contains any currently executable compiled geometry shape not covered by the above list, include it automatically rather than silently excluding it.

Required machine-readable fields:

```text
geometry_id
kind
owner
source
target
baseline_matches
candidate_matches
exact_match
```

Gate:

```text
TARGET_DIRECTED_GEOMETRY_EQUIVALENCE = PASS
mismatches = 0
```

Any mismatch blocks production optimization.

---

## 7. SEMANTIC ATTACK DIFFERENTIAL

Reuse the F5 certified Semantic Standard Shogi corpus:

```text
4 reachable nonterminal deterministic prefixes
```

Hard assert fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

For each prefix query:

```text
81 board squares × 2 owners = 162 attack queries
```

Compare baseline and candidate:

```text
is_square_attacked(position, square, owner)
in_check(position, side)
```

Required:

```text
attack mismatches = 0
check mismatches = 0
```

Also reuse/extend the curated F5 attack/S3 witnesses covering at least:

- leaper attack;
- sliding attack;
- blocker;
- capture;
- promotion;
- drop-related S4-bearing attack contribution;
- discovered attack;
- check relief;
- own-anchor exposure;
- both owners/orientations.

---

## 8. S3 / S4 / LEGALITY PARITY

A target-directed attack optimization is not accepted merely because attack truth matches on the initial positions.

Compare baseline vs candidate for the certified corpus and curated fixtures:

### Full legal action stream

Exact tuple equality is required:

```text
public action identity
public action order
```

### S3

Required exact parity for:

- S0/S1 candidate order;
- S3 accepted/rejected result;
- own-anchor safety;
- `squares_not_attacked` invariant;
- S3 reply existence (`_exists_s3_reply`).

### S4

Required parity for:

- `action_delivers_check`;
- `opponent_checked`;
- `no_legal_reply`;
- uchifuzume fixture;
- any existing generic S4 fixtures.

No shortcut may use terminal/repetition/history inside `_exists_s3_reply`; preserve the current semantic stratum contract.

---

## 9. CHECKPOINT / INTERRUPTIBILITY CONTRACT

Target-directed geometry may reduce the amount of work, and therefore may naturally reduce checkpoint call count. Exact checkpoint-count parity is **not** required.

However all of the following are hard requirements:

- interactive cancellation remains cooperative;
- time-budget searches retain the existing deadline contract;
- deterministic ProbeAbort tests still abort within bounded semantic work;
- abort never corrupts state;
- GameSession remains unmodified on aborted search;
- runtime push/pop/context remains balanced;
- no long uninterruptible geometry scan is introduced.

If a target-directed path scans a compiled ray/path, place generic caller-owned checkpoints at reasonable bounded units. Core must not know why the callback exists.

Run the existing interruptibility/time-control regression suites.

---

## 10. F6 DIAGNOSIS / COUNTERS

Before authorizing production change, quantify the remaining work after F5.

At minimum record per certified semantic case:

```text
attack_queries
in_check_calls
geometry_candidate_calls
geometry_candidates_generated
queried_targets_found
queried_targets_not_found
path_entries_inspected
unrelated_candidates_avoided (candidate probe)
S3 trial transitions
S3 accepted
S3 rejected
S4 reply probes
wall time
nodes / qnodes
```

Do not fabricate counters that cannot be measured faithfully.

Use both:

1. deterministic whole-search runs;
2. bounded `cProfile` / `pstats` evidence.

Explicitly report whether, after F5, target enumeration is still a material fraction of runtime.

---

## 11. ALLOWED OPTIMIZATION FAMILY

If and only if the H6A evidence gate passes, F6 may authorize **one coherent optimization family**:

```text
target-directed compiled geometry lookup for semantic attack/check existence work
```

Potential implementations may include, after measurement:

### Option A — direct compiled-path target lookup

Use the already-compiled ordered path to derive only the queried target/path pair rather than constructing all candidate tuples.

### Option B — derived immutable runtime reachability index

A non-authoritative derived index from immutable compiled geometry may be considered if it is demonstrably faster and does not change serialized IR/fingerprint.

The index must be generic, deterministic, ruleset-derived, and must not contain Shogi-specific knowledge.

### Selection rule

Choose the smallest design that passes the performance gate.

Do not implement A and B sequentially as two separate production optimizations in the same phase. F6 allows one final coherent family only.

---

## 12. FORBIDDEN IN F6

Do **not** implement:

- global mutable attack cache;
- incremental attack map;
- bitboards;
- Shogi-specific attack tables;
- Shogi-specific piece shortcuts;
- Native migration;
- TT redesign;
- history/repetition redesign;
- evaluator changes;
- move ordering changes;
- PVS/LMR/null-move changes;
- qsearch policy changes;
- search depth/budget changes to make benchmarks look better;
- source-index redesign beyond what F5 already established;
- public IR serialization/fingerprint changes;
- board representation rewrite;
- parallel search;
- second unrelated optimization after the target-directed family.

Record these as deferred where relevant.

---

## 13. OPTIMIZATION GATE — BEFORE H6B

Production optimization is authorized only if **all** gates pass:

```text
EQUIVALENT
MATERIAL
EXPLAINED
GENERIC
LOCAL
SEMANTICS_PRESERVING
TESTABLE
LIKELY_USEFUL
```

Interpretation:

### EQUIVALENT
Exact geometry target/path oracle comparison has zero mismatches.

### MATERIAL
The F5 post-optimization profile shows unrelated-target generation is still a meaningful cost in at least 3 of 4 semantic prefixes.

### EXPLAINED
Counters/cProfile connect the cost directly to generating/scanning irrelevant geometry targets, rather than merely correlating with `is_square_attacked`.

### GENERIC
The candidate depends only on compiled generic geometry, owner/source/target and existing predicates; no Shogi names/types/rules.

### LOCAL
No board/history/TT/search architecture rewrite.

### SEMANTICS_PRESERVING
Attack/check/legal/S3/S4 probe parity passes before production merge.

### TESTABLE
A deterministic before/after corpus exists.

### LIKELY_USEFUL
The candidate probe must show at least one of:

```text
>= 2.0x median speedup in the 162-query attack microbenchmark
```

or

```text
>= 15% median whole-search improvement on at least 3/4 Profile A semantic cases
```

before production authorization.

If any gate fails:

```text
F6_OPTIMIZATION_AUTHORIZED = false
```

Do not change production runtime. Complete evidence as `AUDIT_ONLY_PASS`.

---

## 14. H6B — PRODUCTION OPTIMIZATION

If authorized, implement the single selected family and commit it as `H6B`.

H6B must contain production source + tests only. Do not include final after-outcome evidence in the same commit.

Record and push full H6B SHA.

After H6B, run the frozen before/after protocol without changing corpus, depth, nodes, tuning, warm-ups, repetition count, or thresholds.

---

## 15. SEARCH PERFORMANCE PROFILES

Reuse the same basic F4/F5 deterministic corpus and preserve comparability.

### Profile A — semantic/core cost isolation

```text
TT = on
ordering = off
quiescence_max_depth = 0
root tactical scan = off
max_depth = 2
max_nodes = 512
no wall-clock search limit
fresh TT per measured run
```

### Profile B — product-like fixed-node

Use current production/default search feature combination from F5.

```text
max_nodes = 256
no wall-clock search limit
```

Do not disable qsearch or production features to make F6 look favorable.

For each case/profile:

```text
1 warm-up
5 measured repetitions
```

Report:

```text
median
p90
min
max
nodes
qnodes
completed depth
termination reason
```

Logical outputs across repetitions must be deterministic.

---

## 16. PERFORMANCE CLOSURE GATE

To claim:

```text
F6_RESULT = OPTIMIZATION_PASS
```

all correctness gates must pass and the production optimization must satisfy:

### Profile A

```text
semantic aggregate median improvement >= 15%
```

and at least:

```text
3 / 4 semantic cases improve >= 10%
```

### Profile B

```text
semantic aggregate median improvement >= 10%
```

### Regression guard

No semantic representative case may show a stable median regression greater than 10%.

Generic legacy/continuous-check controls must retain logical parity and remain within normal process-noise expectations; do not require them to become faster.

If correctness passes but the performance gate fails:

- revert the production optimization cleanly;
- retain H6A audit evidence;
- record the rejected candidate and reason;
- final result is:

```text
F6_RESULT = AUDIT_ONLY_PASS
```

Do not tune thresholds post hoc.

---

## 17. RUNTIME SAFETY

No F6 diagnostic may become another multi-hour runner.

Hard controller limits:

```text
cProfile single case: <= 60 s
ordinary fixed-node single measured case: <= 120 s
attack microbenchmark worker: <= 60 s
```

If a worker exceeds the controller limit:

```text
RUNTIME_SAFETY_ABORT
```

Terminate only that worker chain, save diagnostics, and continue only where protocol-valid. Do not silently increase limits.

No long games are part of F6.

---

## 18. REQUIRED REGRESSION TESTS

At minimum run:

- F6 target-directed geometry equivalence tests;
- exhaustive/certified attack differential;
- legal action order parity;
- S3 reply-probe parity;
- S4 / uchifuzume regression;
- Round 4 Standard Shogi semantic certification regression;
- F5 regression suite;
- F4 profiling/search regression where applicable;
- F3 history-aware TT tests;
- ordinary repetition and continuous-check tests;
- interruptibility/time-control tests;
- semantic stress differential;
- Native readiness/instrumentation/stress suites;
- full pytest;
- fresh supported Zig build.

Hard requirements:

```text
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

Do not use AlphaSho as a writable dependency. F6 does not require modifying AlphaSho.

---

## 19. EVIDENCE / PROVENANCE

Create:

```text
artifacts/f6_target_directed_semantic/
```

At minimum include:

```text
baseline.json
corpus.json
geometry_equivalence.jsonl
attack_differential.json
check_differential.json
s3_s4_parity.json
legal_order_parity.json
profile_a_before.jsonl
profile_b_before.jsonl
cprofile_before_cumulative.txt
cprofile_before_self.txt
hotspot_analysis.json
optimization_gate.json
candidate_probe.json
```

If H6B is authorized, additionally include:

```text
profile_a_after.jsonl
profile_b_after.jsonl
cprofile_after_cumulative.txt
cprofile_after_self.txt
search_parity.json
performance_comparison.json
```

Always include:

```text
final_verdict.json
manifest.json
```

`manifest.json` must SHA-256 bind every closure artifact and be verified before final report.

Old Round 5 / F3 / F4 / F5 evidence is immutable. Do not rewrite old evidence directories.

Write an ADR, expected next number if available:

```text
docs/architecture/ADR-023-target-directed-semantic-geometry.md
```

and:

```text
docs/architecture/F6_EVIDENCE.md
```

---

## 20. GIT PROTOCOL

Expected successful optimized sequence:

```text
F5 closure baseline
→ H6A  harness/tests/probe only
→ H6B  one production optimization + tests
→ E6   evidence/docs closure only
```

For audit-only closure:

```text
F5 closure baseline
→ H6A
→ E6 audit-only evidence/docs
```

No force push.

At final delivery require:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
```

Do not promote to master in F6.

---

## 21. FINAL VERDICT RULES

### Optimization success

Only if all correctness + performance + provenance gates pass:

```text
F6_RESULT = OPTIMIZATION_PASS
TARGET_DIRECTED_GEOMETRY_EQUIVALENCE = PASS
SEMANTIC_ATTACK_PARITY = PASS
S3_LEGALITY_PARITY = PASS
S4_PARITY = PASS
SEARCH_PARITY = PASS
PERFORMANCE_GATE = PASS
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

### Audit-only success

If diagnosis is complete but optimization is not authorized or fails the fixed performance threshold after clean rollback:

```text
F6_RESULT = AUDIT_ONLY_PASS
```

This is a valid completion, not a failure.

### Blocked

If a correctness/provenance/runtime condition prevents a valid audit:

```text
F6_RESULT = BLOCKED
reason = ...
```

Do not fabricate closure.

---

## 22. REQUIRED FINAL REPORT STRUCTURE

Return exactly these sections:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Corpus
5. Geometry equivalence
6. Attack/check differential
7. S3/S4 legality parity
8. Baseline diagnosis
9. Optimization gate
10. Optimization or rejection
11. Search parity
12. Performance
13. Interruptibility/runtime safety
14. Tests
15. Evidence
16. Git
17. Deferred
18. Final verdict

If optimized, explicitly state the exact production files/functions changed.

If audit-only, explicitly state why production code was not retained.

---

## 23. STOP

After F6 closure and push:

**STOP.**

Do not begin F7, Native migration, attack caching, bitboards, evaluator work, or search-strength work without a new Gmail instruction.
