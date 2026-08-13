<!-- Gmail inbox record -->
<!-- Received: Thu, 13 Aug 2026 10:52:14 -0400 -->
<!-- Subject: GenericChess — F7: Semantic Attack / Check Query Reuse Audit + Evidence-Gated Memoization -->
<!-- Sender: W D icywoods.1@gmail.com -->
<!-- Message ref: 19ffb9c07e07f0ca -->
<!-- Transport note: 19ffb9c6bb1fb327 confirms full task is in previous email body -->
<!-- Status: authoritative task captured; processing in sandbox worktree -->
<!-- Source note: Gmail fuzzy-title protocol; exact GenericChess F7 match -->
# GenericChess — F7: Semantic Attack / Check Query Reuse Audit + Evidence-Gated Memoization

## 0. AUTHORITATIVE TASK

This is the authoritative F7 task for `WD-nanophotonics/GenericChess`.

F7 begins only from the certified F6 closure baseline and has one narrow question:

> After F5 removed repeated full-board owner/type filtering, does the current semantic search still repeat the **same exact attack/check query on the same exact Position** often enough that bounded position-local memoization is both safe and materially useful?

F7 is **not** permission to implement a general attack map, bitboards, Native move generation, evaluator changes, TT changes, or search-strength heuristics.

There are only two valid successful outcomes:

```text
F7_RESULT = OPTIMIZATION_PASS
```

or

```text
F7_RESULT = AUDIT_ONLY_PASS
```

`AUDIT_ONLY_PASS` is a complete successful phase when the evidence does not justify a production cache.

Do not create a production optimization merely because this task mentions memoization.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before work:

1. locate this task by GenericChess/Gmail subject matching;
2. read the full authoritative attachment;
3. persist the complete task to `inbox/`;
4. record Gmail metadata and processing state;
5. then begin the repository audit.

Do not rely on the email snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

The required starting refs are:

```text
origin/sandbox =
11498c79f866ae02dd51de0f0570fad8143578d4

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert these before any implementation.

If `origin/sandbox` has moved:

```text
BASELINE_MOVED
STOP
```

Do not reset, rewrite, force-push, or overwrite another task.

Work only on `sandbox`.

`master` and `chat` are read-only for this phase.

---

# 3. F4–F6 FROZEN FINDINGS

Treat these as established facts unless the current baseline contradicts them.

## F4

Fixed-node checkpoint dispatch overhead was a real hot path and was already optimized.

Do not reopen it.

## F5

Position-local `(owner, current_type_id)` source dispatch reuse was accepted and produced a very large speedup.

Do not remove, weaken, redesign, or replace it.

## F6

Target-directed geometry equivalence was proven, but the candidate failed usefulness:

```text
Profile A ≈ +1.87%
Profile B ≈ -2.48%
```

No H6B exists.

Therefore F7 MUST NOT:

- promote the F6 target-directed candidate;
- redesign `geometry_candidates()` merely to revisit F6;
- claim that avoiding unrelated candidate tuples is itself sufficient evidence;
- perform another target-directed geometry experiment disguised as attack caching.

F6 is closed.

---

# 4. CURRENT PERFORMANCE QUESTION

The F6 post-F5 profile showed roughly:

```text
~300 principal search nodes

~1858 semantic in_check / attack calls
~2.38 s cumulative semantic is_square_attacked
~1.76 s cumulative S3 legality trial
~1.46 s runtime push
~0.95 s terminal runtime
```

These are nested/cumulative observations, not additive wall-clock shares.

The key F7 question is:

```text
How many semantic attack/check queries are exact repeats of:

(exact Position semantics,
 queried square,
 attacking owner,
 certified ruleset)
```

and where do those repeats originate?

Possible sources include, but are not limited to:

- S3 `own_anchor_safe`;
- S3 `squares_not_attacked`;
- S4 `opponent_checked`;
- S4 reply probing;
- `SearchPathRuntime._gave_check`;
- qsearch check/noisy classification;
- root tactical paths;
- terminal/legal-existence work;
- repeated legality calls within one runtime node.

Do not assume any source is dominant before measurement.

---

# 5. PHASE STRUCTURE

F7 has two possible stages.

## H7A — HARNESS / AUDIT ONLY

First create a harness-only state.

H7A may add:

- audit scripts;
- test-only probes;
- tracing;
- machine-readable evidence schema;
- differential tests;
- candidate monkeypatch/probe code.

H7A MUST NOT change production attack/check semantics or retain a production cache.

Commit and push H7A before examining candidate performance as a production decision.

Record exact H7A SHA.

## H7B — OPTIONAL PRODUCTION OPTIMIZATION

H7B is authorized only if every gate in Section 11 passes.

If any authorization gate fails:

```text
F7_RESULT = AUDIT_ONLY_PASS
H7B_CREATED = false
```

Produce evidence, commit E7, push, STOP.

Do not weaken thresholds after seeing results.

---

# 6. CERTIFIED CORPUS

Reuse the deterministic certified Semantic Standard Shogi corpus from F5/F6.

Hard assert fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

At minimum use the four reachable nonterminal semantic prefixes already frozen by F5/F6.

Also retain:

- legacy draw control;
- continuous-check control;
- curated S4 witnesses;
- anchor exposure/relief;
- capture;
- drop;
- promotion;
- sliding attacker;
- leaper attacker;
- blocker;
- `squares_not_attacked`;
- checking-drop / no-legal-reply witnesses where already available.

Do not introduce random corpus selection after seeing performance outcomes.

---

# 7. QUERY IDENTITY — AUTHORITATIVE DEFINITION

For audit purposes, two attack queries are duplicates only if all semantic inputs are exactly equivalent:

```text
same exact Position semantics
same ruleset fingerprint
same queried square
same attacking owner
```

The Position equivalence must include everything attack semantics can observe, including:

- board pieces;
- current/base type state;
- owner;
- promotion state;
- side-to-move where relevant to semantic guards;
- hands if any guard can observe them;
- aux state;
- ruleset fingerprint.

A fast hash/digest MAY be used to bucket audit records, but it is never authoritative.

Forced hash/digest collisions must fall back to exact equality.

Do not define cache correctness from RuntimeHash alone.

History/repetition context is NOT part of attack truth unless current production semantics explicitly consult it. Do not unnecessarily bind attack truth to F3 history context.

---

# 8. H7A DUPLICATION AUDIT

Create a reproducible audit, preferably:

```text
scripts/audit_f7_attack_query_reuse.py
```

Instrument semantic attack/check queries without altering production outcomes.

For each profile/case record at least:

```text
total_attack_queries
unique_exact_attack_queries
duplicate_exact_attack_queries
duplicate_rate

positive_queries
negative_queries

unique_positions_queried
queries_per_position median/p90/max

same-position duplicate count
same-square-owner duplicate count

in_check_calls
is_square_attacked_calls

first-query cost
repeat-query cost estimate

top repeated exact query multiplicities
```

Where feasible, classify origin/call-site into stable categories such as:

```text
S3_OWN_ANCHOR_SAFE
S3_SQUARES_NOT_ATTACKED
S4_OPPONENT_CHECKED
S4_REPLY_PROBE
RUNTIME_GAVE_CHECK
QSEARCH_CHECK_CLASSIFICATION
ROOT_TACTICAL
OTHER
```

Call-site classification is diagnostic only and must not modify Core production semantics.

If precise low-overhead classification requires stack inspection, use it only in a bounded diagnostic run, not in formal performance runs.

---

# 9. SEARCH PROFILES

Use the same deterministic search profiles used in F6 unless repository evidence proves they were encoded differently.

## Profile A — Core semantic cost

Freeze:

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

## Profile B — Product-like fixed-node

Use current production/default AlphaBeta feature combination.

Freeze:

```text
max_nodes = 256
deterministic node budget
no wall-clock search limit
```

Record complete tuning/config.

For every case/profile:

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
```

Logical outputs must be deterministic.

---

# 10. CANDIDATE FAMILY — ONLY IF AUDIT SUPPORTS IT

The only F7 optimization family allowed is:

```text
bounded exact position-local semantic attack/check query reuse
```

Possible implementations MAY include:

1. a frame-local attack cache bound to the current exact runtime Position;
2. a bounded semantic-operation query context;
3. another equally local mechanism proven to have identical scope and safety.

Prefer the narrowest mechanism that captures the measured duplicates.

### Explicitly forbidden candidate designs

Do NOT implement:

- global mutable unbounded attack cache;
- cache keyed only by RuntimeHash;
- cross-ruleset cache;
- persistent cross-game cache;
- bitboards;
- incremental attack map;
- generalized attack-map invalidation architecture;
- Native attack engine;
- target-directed F6 geometry promotion;
- Shogi-specific attack shortcuts;
- TT/history changes;
- evaluator cache;
- move-ordering/search-strength changes.

---

# 11. H7B AUTHORIZATION GATES

H7B may be created only if ALL gates below pass.

## G1 — DUPLICATION

Exact duplicate attack queries must be material.

Require at least one:

```text
Profile A aggregate exact duplicate rate >= 25%
Profile B aggregate exact duplicate rate >= 25%
```

AND the other profile must have:

```text
exact duplicate rate >= 15%
```

If not:

```text
LIKELY_REUSE = false
AUDIT_ONLY_PASS
```

## G2 — MATERIAL HOTSPOT

Current post-F6 profiling must still show semantic attack/check as a material cost.

Evidence may be cumulative/nested, but must demonstrate that attack/check remains a meaningful search cost rather than a tiny residual.

## G3 — EXACT SCOPE

A safe cache scope must be demonstrated.

The design must guarantee:

- no collision-authority shortcut;
- no stale result after Position change;
- no sibling leakage;
- no cross-ruleset leakage;
- no aux-state leakage;
- no cross-game unbounded retention.

## G4 — INTERRUPTIBILITY

A cache hit must not make interactive cancellation/deadline observation unbounded.

If `checkpoint` is provided, a cache-hit path must still provide a bounded cooperative observation point.

Do not require identical checkpoint call counts; require identical cancellation/deadline contract.

## G5 — PROBE CORRECTNESS

Before H7B, an opt-in candidate probe must pass the complete differential suite in Sections 12–14.

## G6 — PROBE PERFORMANCE

Before H7B, the candidate probe must satisfy either:

### Route A

```text
Profile A semantic aggregate improvement >= 7.5%
Profile B semantic aggregate improvement >= 7.5%
```

or:

### Route B

```text
one profile >= 12%
other profile >= -2% regression
```

No semantic case may show a stable regression >5%.

If probe performance fails:

```text
LIKELY_USEFUL = false
AUDIT_ONLY_PASS
```

Do not create H7B.

---

# 12. ATTACK / CHECK DIFFERENTIAL — HARD GATE

For each of the four certified Semantic Shogi prefixes:

Query:

```text
81 squares × 2 attacking owners = 162 attack queries
```

Compare baseline vs candidate:

```text
attack truth
in_check truth
```

Require:

```text
attack mismatches = 0
check mismatches = 0
```

Also run curated fixtures covering:

- ray attacks;
- leap attacks;
- blockers;
- discovered attack;
- check relief;
- capture;
- promotion;
- drops;
- owner-relative semantics;
- S4-bearing capture patterns contributing to pseudo-attack;
- `squares_not_attacked`.

Negative cache entries are as authoritative as positive entries and require the same exact parity.

---

# 13. LEGALITY / S3 / S4 DIFFERENTIAL — HARD GATE

Baseline vs candidate must preserve exactly:

```text
legal action set
legal action order
semantic action identity
pattern_id
geometry_id
actor identity
promotion target
S3 acceptance/rejection
S3 reply existence
S4 postcondition truth
no_legal_reply behavior
```

Required curated regressions include:

```text
own_anchor_safe
squares_not_attacked
nifu
uchifuzume
promotion
forced promotion
capture-to-hand
promoted capture returns base to hand
ordinary repetition
continuous_check_loss
```

Do not weaken certified Round-4/F3 semantics.

---

# 14. SEARCH PARITY — HARD GATE

For every formal Profile A/B row, baseline and candidate must exactly match:

```text
action
score
PV
nodes
qnodes
completed depth
termination reason
terminal state
```

PV must remain legal.

TT on/off regression suites from F3 must continue to pass.

Persistent TT across moves must remain correct.

Attack memoization must not become part of TT identity.

---

# 15. CACHE LIFETIME / ROLLBACK TESTS

If a candidate uses runtime/frame-local memoization, add explicit tests for:

```text
parent cache state
push child
child cache state
pop
parent cache restored

sibling A cache
pop
sibling B
no sibling leakage

exception during push
full cache rollback

PVS re-search
aspiration re-search
runtime balance

two equal-but-independent Position objects
safe exact behavior

forced fast-hash collision
no incorrect reuse
```

If the design uses operation-local contexts instead, provide equivalent isolation tests.

A production cache must remain bounded.

For a cache bound to one exact board position, the natural maximum attack-key domain is approximately:

```text
board_square_count × 2 owners
```

Do not introduce unbounded growth.

---

# 16. PERFORMANCE MEASUREMENT

Use process-isolated deterministic measurements.

For each formal case:

```text
1 warm-up
5 measured
```

Report baseline and candidate:

```text
wall time
nodes/qnodes
attack queries
unique attack queries
cache hits
cache misses
hit rate
cache entries peak
in_check calls
legal generation calls
runtime pushes
```

Report aggregate and per-case medians.

Do not sum nested timers as exclusive wall-clock shares.

Use cProfile only as supporting evidence.

### Runtime safety

Hard controller limits:

```text
cProfile single case <= 60 s
normal fixed-node single case <= 120 s
```

If exceeded:

```text
RUNTIME_SAFETY_ABORT
```

Preserve diagnostics and STOP that measurement.

Do not let any F7 benchmark run for hours.

---

# 17. H7B PRODUCTION CHANGE RULES

If all authorization gates pass:

1. create H7B containing production source + tests only;
2. do not include after-outcome evidence in H7B;
3. push H7B;
4. require clean tracked source;
5. rerun the frozen formal corpus against H7A baseline and H7B candidate;
6. then create final E7 evidence closure commit.

The product optimization must remain one coherent family.

No second optimization in F7.

---

# 18. FINAL PERFORMANCE GATE

For:

```text
F7_RESULT = OPTIMIZATION_PASS
```

require all correctness gates plus:

```text
Profile A semantic aggregate median improvement >= 8%
Profile B semantic aggregate median improvement >= 8%
```

and:

```text
at least 3/4 semantic cases in each profile improve >= 5%
no semantic case has stable regression >5%
```

If H7B was created but the final formal gate fails:

- revert the production optimization cleanly;
- retain audit evidence;
- final result becomes:

```text
F7_RESULT = AUDIT_ONLY_PASS
PERFORMANCE_GATE = FAIL_CANDIDATE_REVERTED
```

Do not leave a non-qualifying cache in production.

---

# 19. F4/F5/F6 EVIDENCE IMMUTABILITY

Existing evidence is frozen.

At minimum preserve byte-identically:

```text
artifacts/f4_runtime_cost/**
artifacts/f5_semantic_attack_s3/**
artifacts/f6_target_directed_semantic/**
docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
ADR-022
ADR-023
```

Create SHA-256 before/after manifests proving old evidence is unchanged.

New F7 evidence goes only under:

```text
artifacts/f7_semantic_attack_query_reuse/
```

---

# 20. REQUIRED NEW EVIDENCE

Produce machine-readable evidence sufficient to reconstruct the decision.

At minimum:

```text
artifacts/f7_semantic_attack_query_reuse/
    baseline.json
    corpus.json
    query_reuse_profile_a.jsonl
    query_reuse_profile_b.jsonl
    duplicate_summary.json
    callsite_summary.json
    candidate_design.json
    optimization_gate.json
    attack_differential.json
    check_differential.json
    legal_order_parity.json
    s3_s4_parity.json
    search_parity.json
    interruptibility.json
    rollback_isolation.json
    profile_a_before.jsonl
    profile_a_candidate.jsonl
    profile_b_before.jsonl
    profile_b_candidate.jsonl
    performance_comparison.json
    old_evidence_before.sha256
    old_evidence_after.sha256
    full_pytest.txt
    native_build.txt
    final_verdict.json
    manifest.json
```

If no candidate is authorized, candidate-after files may be replaced by explicit:

```text
NOT_RUN_NOT_AUTHORIZED
```

records rather than fabricated data.

Create:

```text
docs/architecture/F7_EVIDENCE.md
docs/architecture/ADR-024-semantic-attack-query-reuse.md
```

ADR-024 must explicitly state whether production memoization was accepted or rejected and why.

---

# 21. TESTS

Run focused suites covering at least:

- F7 harness;
- F6 target-directed equivalence regression;
- F5 semantic source-index regression;
- F4 interruptibility/time controls;
- semantic executor;
- S4;
- Standard Shogi semantic parity;
- F3 history-aware TT;
- repetition / continuous check;
- search runtime rollback;
- Native readiness/stress.

Then run:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% pass.

Then run the supported fresh Zig build:

```text
python scripts/build_native_zig.py
```

Require PASS.

Do not use AlphaSho for F7.

Do not run long game matches.

---

# 22. INVARIANTS / FORBIDDEN SCOPE

F7 must not modify:

```text
public SHA/fingerprint
ruleset semantics
semantic IR version
promotion semantics
drop semantics
nifu / uchifuzume
S4 truth table
repetition rules
continuous-check adjudication
TT bounds
TT generation
TT replacement
mate normalization
history-aware TT identity
qsearch TT policy
evaluator features/weights
move ordering heuristics
PVS/LMR/null move policy
Native production search
UI
master
chat
AlphaSho
```

No bitboards.

No incremental attack map.

No global persistent attack cache.

No F6 target-directed production change.

No F8 work.

---

# 23. GIT / PROVENANCE

Expected structure:

Audit-only path:

```text
F6 E6 baseline
  -> H7A harness/audit
  -> E7 audit closure
```

Optimization path:

```text
F6 E6 baseline
  -> H7A harness/audit
  -> H7B production optimization + tests
  -> E7 evidence closure
```

Final requirements:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

Record all SHAs exactly.

---

# 24. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
ATTACK_PARITY_FAILURE
CHECK_PARITY_FAILURE
LEGAL_ORDER_PARITY_FAILURE
S3_PARITY_FAILURE
S4_PARITY_FAILURE
SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
ROLLBACK_ISOLATION_FAILURE
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
NATIVE_BUILD_FAILURE
RUNTIME_SAFETY_ABORT that invalidates required evidence
```

Do not repair unrelated architecture inside F7.

---

# 25. FINAL REPORT FORMAT

Return exactly these sections:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Corpus
5. Exact attack-query identity
6. Duplicate/reuse diagnosis
7. Call-site attribution
8. H7A provenance
9. Optimization authorization gate
10. Candidate design or rejection
11. Attack/check differential
12. S3/S4 legality parity
13. Search parity
14. Interruptibility
15. Rollback/sibling isolation
16. Performance
17. Tests
18. Evidence / manifest
19. Git
20. Deferred
21. Final verdict

For optimization success:

```text
F7_RESULT = OPTIMIZATION_PASS
ATTACK_QUERY_REUSE = PASS
SEMANTIC_ATTACK_PARITY = PASS
S3_LEGALITY_PARITY = PASS
S4_PARITY = PASS
SEARCH_PARITY = PASS
INTERRUPTIBILITY = PASS
ROLLBACK_ISOLATION = PASS
PERFORMANCE_GATE = PASS
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

For audit-only completion:

```text
F7_RESULT = AUDIT_ONLY_PASS
H7B_CREATED = false
reason = <frozen gate that failed>
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

If H7B was created and later reverted:

```text
F7_RESULT = AUDIT_ONLY_PASS
H7B_CREATED = true
H7B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

---

# 26. FINAL STOP

F7 ends after E7 closure.

Do not begin F8.

Do not automatically optimize runtime push/terminal processing.

Do not automatically migrate to Native.

The next phase, if any, will be separately audited and separately authorized.
