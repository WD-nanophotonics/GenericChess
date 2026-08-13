<!-- Gmail inbox record -->
<!-- Received: Thu, 13 Aug 2026 11:35:07 -0400 -->
<!-- Subject: GenericChess — F8: Runtime Push / Terminal Check Deduplication -->
<!-- Sender: W D icywoods.1@gmail.com -->
<!-- Message ref: 19ffbc34992f0fe4 -->
<!-- Status: authoritative task captured; processing in sandbox worktree -->
<!-- Source note: Gmail fuzzy-title protocol; exact GenericChess F8 match -->
# GenericChess — F8: Runtime Push / Terminal Check Deduplication

## 0. AUTHORITATIVE TASK

This is the authoritative F8 task for `WD-nanophotonics/GenericChess`.

F8 has one narrow goal:

> Audit whether `SearchPathRuntime._push_impl()` computes the same semantic checked-state for the same newly-created child more than once during one push, and if so, eliminate only that redundant work by passing an already-computed exact boolean into terminal evaluation.

This is deliberately narrower than F7.

F8 is NOT permission to implement:
- a general attack cache;
- a general `in_check` cache;
- a general terminal cache;
- incremental attack maps;
- bitboards;
- Native migration;
- search-strength changes;
- TT/history/evaluator changes;
- broad runtime refactors.

There are only two successful outcomes:

```text
F8_RESULT = OPTIMIZATION_PASS
```

or

```text
F8_RESULT = AUDIT_ONLY_PASS
```

`AUDIT_ONLY_PASS` is a complete successful phase if the suspected duplicate does not exist, is not exact, is not material, or the low-risk candidate fails the frozen performance gate.

Do not invent a broader optimization merely to obtain an optimization result.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local Gmail/inbox protocol.

Before any implementation:

1. locate this task through the GenericChess Gmail entry;
2. read the complete authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record message/thread metadata and processing state;
5. then begin the repository audit.

Do not execute from the email subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
f6d1bdad4bbe405e5a55a8683cdb711ec90c7405

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three before work.

If `origin/sandbox` has moved:

```text
BASELINE_MOVED
STOP
```

Do not reset, rewrite, force-push, or overwrite another task.

Work only on `sandbox`.

`master` and `chat` are read-only.

---

# 3. F4–F7 FROZEN FINDINGS

These findings are closed and MUST NOT be reopened in F8.

## F4 — checkpoint dispatch
Accepted and closed.

## F5 — semantic source dispatch
Accepted and closed.

Do not alter `_sources_by_owner_type()` behavior/order.

## F6 — target-directed geometry
Audited and rejected for production.

Do not promote or revisit the F6 candidate.

## F7 — generic exact attack memoization
Audited and rejected for production.

F7 found:

```text
Profile A exact duplicate rate ≈ 25.19%
Profile B exact duplicate rate ≈ 54.72%

generic memoization candidate:
Profile A ≈ -4.70%
Profile B ≈ +23.90%
```

No H7B exists.

Therefore F8 MUST NOT implement:
- 4096-entry attack caches;
- exact-Position attack memoization;
- hash-key attack caches;
- cross-call attack reuse;
- any generalized replacement of F7.

F7 is closed.

---

# 4. SUSPECTED LOCAL DUPLICATION

At baseline, inspect and confirm the exact current call chain.

The suspected sequence is:

```text
SearchPathRuntime._push_impl(action)
    -> transition creates exact child Position
    -> gave_check = self._gave_check(child, checkpoint)
         -> semantic engine.in_check(child, child.side_to_move, checkpoint)
    -> history/context update
    -> self.position = child
    -> terminal_from_search_runtime(self, checkpoint)
         -> semantic engine.has_legal_action(...)
         -> semantic engine.in_check(position, position.side_to_move, checkpoint)
```

The hypothesis is:

```text
_gave_check(child)
```

and the terminal-path check are the SAME semantic truth query for the SAME exact child:

```text
engine.in_check(child, child.side_to_move)
```

Do not assume this. Prove it from current source and runtime traces.

F8 must answer:

1. Are these booleans semantically identical on all applicable semantic pushes?
2. Are they evaluated twice on ordinary ongoing children?
3. How often does the second computation occur?
4. How much wall-clock cost does it represent?
5. Can terminal evaluation consume the exact already-computed boolean without changing terminal precedence or interruptibility?

---

# 5. SECONDARY OBSERVATION — DIAGNOSTIC ONLY

Current `terminal_from_search_runtime()` may compute:

```text
has_legal
checked
```

even when `has_legal == true`.

The checked result is only needed to distinguish:

```text
CHECKMATE
vs
STALEMATE
```

when no legal action exists.

This is a valid diagnostic observation, but F8 MUST NOT independently optimize this path unless it is logically part of the exact same one-value reuse design.

Do NOT introduce a second optimization family such as:

```text
if has_legal:
    never compute check
```

unless the implementation naturally follows from consuming an already-known `checked` boolean and changes no additional search/terminal behavior.

If eliminating an independent terminal check requires a separate semantic redesign, defer it.

F8 authorizes one coherent optimization family only.

---

# 6. PHASE STRUCTURE

## H8A — AUDIT / HARNESS ONLY

Create a harness-only commit first.

H8A may contain:
- audit scripts;
- tracing;
- counters;
- call-site probes;
- differential tests;
- opt-in monkeypatch candidate;
- evidence schema.

H8A MUST NOT change production runtime/terminal behavior.

Commit and push H8A before production optimization authorization.

Record exact SHA.

## H8B — OPTIONAL PRODUCTION OPTIMIZATION

H8B is allowed only if every authorization gate in Section 11 passes.

If any gate fails:

```text
F8_RESULT = AUDIT_ONLY_PASS
H8B_CREATED = false
```

Produce E8 evidence closure and STOP.

Do not weaken thresholds after seeing results.

---

# 7. CERTIFIED CORPUS

Reuse the exact deterministic corpus from F5/F6/F7.

Hard assert Semantic Standard Shogi fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

At minimum:

- four certified reachable nonterminal Semantic Shogi prefixes;
- legacy draw control;
- continuous-check control;
- curated S4 fixtures already used by F5–F7.

Also require explicit terminal witnesses:

```text
ordinary ongoing child
child in check but with legal reply
checkmate
stalemate
ordinary repetition
continuous_check_loss
max-ply terminal
promotion child
capture child
drop child
```

If any witness cannot be expressed in Semantic Shogi, use the existing deterministic semantic/legacy fixture that exercises the same terminal contract and label it clearly.

Do not introduce outcome-selected random positions.

---

# 8. H8A DUPLICATE-CHECK AUDIT

Create a bounded reproducible audit, preferably:

```text
scripts/audit_f8_push_terminal_check.py
```

For every semantic runtime push, record:

```text
push_id
parent exact identity summary
child exact identity summary
child side_to_move

gave_check_called
gave_check_result

terminal_check_called
terminal_check_result

same_exact_child
same_side
boolean_equal

has_legal_result
terminal_status
```

Aggregate:

```text
semantic_pushes
gave_check_calls
terminal_check_calls

pushes_with_both_calls
exact_duplicate_pairs
duplicate_pair_rate

duplicate_true_true
duplicate_false_false
boolean_mismatches

terminal_check_avoided_if_known_count
terminal_check_required_for_no_legal_count
```

Also record approximate time:

```text
gave_check_inclusive_s
terminal_check_inclusive_s
duplicate_second_check_s
```

Instrumentation must be diagnostic-only and excluded from formal before/after performance where it materially perturbs runtime.

No stack inspection in formal performance runs.

---

# 9. EXACT SEMANTIC EQUIVALENCE — HARD PROOF OBLIGATION

Before any candidate is authorized, prove that the reused value is exactly the value terminal evaluation needs.

For semantic runtime pushes:

```text
gave_check = engine.in_check(child, child.side_to_move, checkpoint)
```

must be equivalent to terminal's:

```text
checked = engine.in_check(runtime.position, runtime.position.side_to_move, checkpoint)
```

at the point `runtime.position is/equivalent to child`.

Verify at minimum:

```text
exact child Position equality
same ruleset/fingerprint
same side_to_move
same aux state
same board/hands
same promotion state
```

No hash-only proof is accepted.

Add a targeted test that forces a fast-hash collision if any fast identity discriminator is introduced.

Prefer passing the boolean directly rather than introducing any new identity key.

---

# 10. ALLOWED CANDIDATE FAMILY

The only allowed production family is:

```text
single-push exact checked-state forwarding
```

Examples:

```python
gave_check = self._gave_check(child, checkpoint)
...
self.terminal_status = terminal_from_search_runtime(
    self,
    checkpoint,
    known_checked=gave_check,
)
```

or an equivalent design with the same narrow semantics.

The preferred API shape should make optional knowledge explicit, e.g.:

```text
known_checked: bool | None
```

with:

```text
None = terminal function computes authoritative check itself
bool = caller has already computed the exact same authoritative query
```

The public/general terminal API must retain its current semantics.

### Forbidden candidate forms

Do NOT implement:

- memoization dict;
- LRU;
- global/cache object;
- RuntimeHash attack reuse;
- Position-key cache;
- attack map;
- in-check map;
- bitboards;
- Native helper;
- TT extension;
- history-key change;
- evaluator shortcut;
- Shogi-specific special case.

This phase is about forwarding one already-computed exact boolean.

---

# 11. H8B AUTHORIZATION GATES

H8B may be created only if ALL gates pass.

## G1 — EXACT DUPLICATION

Require:

```text
boolean_mismatches = 0
```

and:

```text
exact_duplicate_pairs / semantic_pushes >= 50%
```

The threshold is intentionally high because this candidate is only justified if the duplicate is structurally routine.

## G2 — MATERIAL COST

The second check must be nontrivial.

Require at least one:

```text
duplicate second-check time >= 5% of semantic Profile A wall time
duplicate second-check time >= 5% of semantic Profile B wall time
```

AND the other profile must show a measurable positive cost, not merely counter equality.

Use low-overhead or cProfile-supported attribution.

Do not sum nested times as exclusive shares.

## G3 — TERMINAL SEMANTICS

Baseline vs candidate terminal status must match exactly for all witnesses:

```text
ONGOING
CHECKMATE
STALEMATE
REPETITION
MAX_PLY
continuous-check loss
```

Terminal precedence must remain unchanged.

## G4 — HISTORY SEMANTICS

`RuntimeHistoryRecord.gave_check` must remain exactly unchanged.

Continuous-check adjudication must remain exactly unchanged.

F3 history-aware TT eligibility/context must remain unchanged.

## G5 — INTERRUPTIBILITY

If a known checked value is supplied, eliminating the second `in_check()` call must not create an unbounded cancellation/deadline blind spot.

At minimum:

- interactive `checkpoint` behavior remains bounded;
- cancellation can still be observed after transition/history work;
- time-limit tests continue to pass.

It is NOT required to preserve identical checkpoint call counts.

It IS required to preserve the responsiveness contract.

## G6 — PROBE PARITY

An opt-in H8A candidate probe must pass Sections 12–15 before H8B.

## G7 — PROBE PERFORMANCE

Before H8B, require:

```text
Profile A semantic aggregate >= +5%
Profile B semantic aggregate >= +5%
```

OR:

```text
one profile >= +8%
other profile >= +2%
```

No semantic case may have stable regression >3%.

If this fails:

```text
F8_RESULT = AUDIT_ONLY_PASS
H8B_CREATED = false
```

---

# 12. TERMINAL DIFFERENTIAL — HARD GATE

Baseline vs candidate for every curated terminal witness:

```text
terminal status
winner
checked state where observable
has_legal existence
repetition outcome
continuous-check outcome
max-ply precedence
```

must match exactly.

Explicitly verify:

### Ongoing in-check child
A position may be checked and still have legal replies.

Must remain:

```text
ONGOING
```

### Checkmate
Must remain:

```text
CHECKMATE
winner = opposite side_to_move
```

### Stalemate
Must remain:

```text
STALEMATE
```

### Repetition / continuous-check
No reordering of precedence.

### Max ply
No reordering of precedence.

---

# 13. HISTORY / GAVE-CHECK DIFFERENTIAL — HARD GATE

For the formal semantic corpus, baseline vs candidate must match every newly appended runtime history record on:

```text
actor
action signature
gave_check
child exact identity
runtime hash
external key behavior
```

For continuous-check fixtures, compare the full relevant cycle evidence.

Require:

```text
gave_check mismatches = 0
continuous_check_result mismatches = 0
```

---

# 14. SEARCH PARITY — HARD GATE

For every Profile A/B formal row, baseline vs candidate must exactly match:

```text
action
score
PV
nodes
qnodes
completed depth
termination reason
terminal state
TT probes/hits/stores/cutoffs where deterministic
```

PV must remain legal.

F3 TT on/off parity remains mandatory.

Persistent TT across moves remains mandatory.

F8 must not affect TT identity or contents except indirectly through identical search execution.

---

# 15. PUSH / POP / EXCEPTION / SIBLING ISOLATION

Add explicit tests for:

```text
push child
history gave_check correct
terminal status correct
pop restores parent

sibling A
pop
sibling B
no carried checked-state

exception during transition
rollback exact

exception after history append
rollback exact

PVS re-search
aspiration re-search
runtime depth balanced
```

No per-frame `known_checked` state should survive past the computation that consumes it unless the chosen API explicitly requires it.

Prefer local variable forwarding.

---

# 16. PERFORMANCE PROTOCOL

Use the same deterministic fixed-node profiles as F7/F6.

## Profile A

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

## Profile B

Use current production/default AlphaBeta configuration with:

```text
max_nodes = 256
deterministic node budget
no wall-clock search limit
```

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
semantic pushes
gave_check calls
terminal check calls
duplicate second checks removed
```

Formal performance runs must not include heavy call-site tracing.

Use process isolation.

### Runtime safety

Hard limits:

```text
cProfile single case <= 60 s
normal fixed-node single case <= 120 s
```

If exceeded:

```text
RUNTIME_SAFETY_ABORT
```

Preserve diagnostics and stop that measurement.

No multi-hour runner.

---

# 17. FINAL PERFORMANCE GATE

For:

```text
F8_RESULT = OPTIMIZATION_PASS
```

require all correctness gates plus either:

## Route A

```text
Profile A semantic aggregate >= +6%
Profile B semantic aggregate >= +6%
```

or:

## Route B

```text
one profile >= +10%
other profile >= +3%
```

Additionally:

```text
at least 3/4 semantic cases in each profile >= +3%
no semantic case stable regression >3%
```

If H8B is created but final formal performance fails:

1. cleanly revert the production optimization;
2. keep H8A/E8 audit evidence;
3. final result:

```text
F8_RESULT = AUDIT_ONLY_PASS
H8B_CREATED = true
H8B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
```

Do not retain a non-qualifying production change.

---

# 18. F4–F7 EVIDENCE IMMUTABILITY

Preserve byte-identically:

```text
artifacts/f4_runtime_cost/**
artifacts/f5_semantic_attack_s3/**
artifacts/f6_target_directed_semantic/**
artifacts/f7_semantic_attack_query_reuse/**

docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
docs/architecture/F7_EVIDENCE.md

ADR-022
ADR-023
ADR-024
```

Generate before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f8_push_terminal_check_dedup/
```

---

# 19. REQUIRED F8 EVIDENCE

At minimum:

```text
artifacts/f8_push_terminal_check_dedup/
    baseline.json
    corpus.json
    source_call_chain.json
    duplicate_check_trace.jsonl
    duplicate_summary.json
    timing_attribution.json
    exact_equivalence.json
    optimization_gate.json
    terminal_differential.json
    history_gave_check_parity.json
    continuous_check_parity.json
    search_parity.json
    interruptibility.json
    rollback_sibling_isolation.json
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

If no candidate is authorized, candidate performance files may contain explicit:

```text
NOT_RUN_NOT_AUTHORIZED
```

rather than fabricated rows.

Create:

```text
docs/architecture/F8_EVIDENCE.md
docs/architecture/ADR-025-runtime-push-terminal-check-dedup.md
```

ADR-025 must state:
- whether exact duplication was proven;
- whether the boolean-forwarding design was authorized;
- whether production code retained the change;
- why.

---

# 20. TESTS

Focused suites must include at least:

- F8 harness/tests;
- terminal runtime;
- search runtime push/pop;
- continuous-check/repetition;
- F7 audit regression;
- F6 geometry regression;
- F5 source-dispatch regression;
- F4 interruptibility/time controls;
- semantic executor;
- S4;
- Standard Shogi parity;
- F3 TT/history;
- Native readiness/stress.

Then:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then:

```text
python scripts/build_native_zig.py
```

Require fresh supported Zig build PASS.

Do not use AlphaSho.

Do not run long game matches.

---

# 21. FORBIDDEN SCOPE

F8 must not modify:

```text
ruleset fingerprint
semantic IR version
public serialization
promotion/drop semantics
nifu
uchifuzume
S4 truth table
repetition policy
continuous-check adjudication
TT identity/bounds/generation/replacement
mate normalization
qsearch TT policy
evaluator
move ordering
PVS/LMR/null move
Native production search
UI
master
chat
AlphaSho
```

No general attack cache.
No terminal cache.
No bitboards.
No incremental attack map.
No target-directed F6 optimization.
No F7 memoization revival.
No F9 work.

---

# 22. GIT / PROVENANCE

Audit-only path:

```text
E7 baseline
  -> H8A audit/harness
  -> E8 audit closure
```

Optimization path:

```text
E7 baseline
  -> H8A audit/harness
  -> H8B production source + tests
  -> E8 evidence closure
```

Requirements:

```text
HEAD == origin/sandbox
sandbox worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

Record exact SHAs.

---

# 23. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
EXACT_CHECK_EQUIVALENCE_FAILURE
TERMINAL_PARITY_FAILURE
HISTORY_GAVE_CHECK_PARITY_FAILURE
CONTINUOUS_CHECK_PARITY_FAILURE
SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
ROLLBACK_ISOLATION_FAILURE
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
NATIVE_BUILD_FAILURE
RUNTIME_SAFETY_ABORT that invalidates required evidence
```

Do not repair unrelated architecture inside F8.

---

# 24. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Corpus
5. Source call-chain audit
6. Exact duplicate-check diagnosis
7. Timing attribution
8. H8A provenance
9. Optimization authorization gate
10. Candidate design or rejection
11. Terminal differential
12. History / gave-check parity
13. Continuous-check parity
14. Search parity
15. Interruptibility
16. Push/pop/rollback/sibling isolation
17. Performance
18. Tests
19. Evidence / manifest
20. Git
21. Deferred
22. Final verdict

Optimization success:

```text
F8_RESULT = OPTIMIZATION_PASS
PUSH_TERMINAL_CHECK_DEDUP = PASS
TERMINAL_PARITY = PASS
HISTORY_GAVE_CHECK_PARITY = PASS
CONTINUOUS_CHECK_PARITY = PASS
SEARCH_PARITY = PASS
INTERRUPTIBILITY = PASS
ROLLBACK_ISOLATION = PASS
PERFORMANCE_GATE = PASS
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

Audit-only:

```text
F8_RESULT = AUDIT_ONLY_PASS
H8B_CREATED = false
reason = <frozen gate that failed>
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

Reverted candidate:

```text
F8_RESULT = AUDIT_ONLY_PASS
H8B_CREATED = true
H8B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

---

# 25. FINAL STOP

F8 ends after E8 closure.

Do not begin F9.

Do not automatically optimize `has_legal_action()` / terminal existence.

Do not automatically alter S3 attack/check behavior.

Do not automatically migrate to Native.

The next phase, if any, will be separately audited and separately authorized.
