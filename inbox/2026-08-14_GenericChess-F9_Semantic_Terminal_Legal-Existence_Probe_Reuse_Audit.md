<!-- Gmail inbox record -->
<!-- Received: Thu, 13 Aug 2026 13:42:31 -0400 -->
<!-- Subject: GenericChess — F9: Semantic Terminal Legal-Existence Probe Reuse Audit + Evidence-Gated Continuation -->
<!-- Sender: W D icywoods.1@gmail.com -->
<!-- Message ref: 19ffc37ebf582577 -->
<!-- Status: authoritative task captured; processing in sandbox worktree -->
<!-- Source note: Gmail fuzzy-title protocol; exact GenericChess F9 match -->
# GenericChess — F9: Semantic Terminal Legal-Existence Probe Reuse Audit + Evidence-Gated Continuation

## 0. AUTHORITATIVE TASK

This is the authoritative F9 task for `WD-nanophotonics/GenericChess`.

F9 begins from the certified F8 audit-only closure and has one narrow question:

> When `terminal_from_search_runtime()` probes `SemanticEngine.has_legal_action()` for a newly-pushed child, how much of that exact semantic legality-generation work is immediately repeated when the same child enters search and `SearchPathRuntime.legal_actions()` generates the full legal set?

F9 must first measure the duplication. It may retain **one** production optimization family only if frozen correctness and performance gates pass.

Valid successful outcomes:

```text
F9_RESULT = OPTIMIZATION_PASS
```

or

```text
F9_RESULT = AUDIT_ONLY_PASS
```

`AUDIT_ONLY_PASS` is a complete successful phase. Do not invent an optimization if the measured work is not reusable, not material, or unsafe to carry across the terminal/search boundary.

---

## 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol. Save this complete task to `inbox/` before execution. The complete Gmail body is authoritative; do not execute from subject/snippet alone.

---

## 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox = a0de0f6bd227d8c67356b0dc60cff1b3f757cf93
origin/master  = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat    = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three. If sandbox moved:

```text
BASELINE_MOVED
STOP
```

Work only on `sandbox`. `master` and `chat` are read-only. No reset, force-push, or history rewrite.

---

## 3. F4–F8 FROZEN FINDINGS

Closed findings:

- F4 checkpoint dispatch optimization accepted.
- F5 position-local `(owner, current_type_id)` semantic source dispatch accepted. Preserve exact action order.
- F6 target-directed geometry audited and rejected. Do not revive it.
- F7 generic exact attack memoization audited and rejected. Do not revive it.
- F8 exact push→terminal duplicate check was proven at 100%, but the isolated `known_checked` candidate failed final performance and was reverted:

```text
Profile A ≈ +1.81%
Profile B ≈ +8.76%
H8B_RETAINED = false
```

Do not reintroduce F8 `known_checked` forwarding in F9.

---

## 4. CURRENT SOURCE HYPOTHESIS

Confirm current source first. Expected semantic path:

```text
SearchPathRuntime._push_impl(action)
    -> transition child
    -> history/runtime updates
    -> terminal_from_search_runtime(runtime, checkpoint)
         -> engine.has_legal_action(child, checkpoint)
              -> engine.iter_legal_actions(...)
                   -> engine.iter_legal_action_bindings(...)
                   -> stop at first legal action
```

If child is ONGOING and enters negamax/qsearch, later:

```text
ctx.runtime.legal_actions(ctx.checkpoint)
    -> engine.iter_legal_action_bindings(child, checkpoint)
    -> generate complete legal action set
    -> populate runtime._legal_cache / _bindings
```

Hypothesis: terminal existence may redo an expensive prefix of the same canonical legality traversal that the next search node restarts from the beginning.

Do not assume it. Prove it.

---

## 5. QUESTIONS H9A MUST ANSWER

1. How many semantic pushes call terminal `has_legal_action()`?
2. How many children are terminal vs ongoing?
3. How many ongoing children later call `runtime.legal_actions()` before pop?
4. How many are pushed only for tactical/order/diagnostic work and never request the full legal set?
5. For children that do request full legal generation, how much exact traversal prefix was already performed by terminal existence?
6. How many semantic candidate/S3 trials are repeated?
7. How much wall-clock time is attributable to that repeated prefix?
8. Does Profile A and Profile B show the same reuse pattern?
9. Can the work be reused without changing action order, S3/S4, terminal precedence, checkpoint/cancellation, or rollback isolation?

---

## 6. PHASE STRUCTURE

### H9A — HARNESS / AUDIT ONLY

H9A may add tracing, scripts, counters, test-only wrappers/probes, process-isolated candidate probes, and evidence schemas. H9A must not retain production runtime/semantic changes.

Commit and push H9A before production authorization. Record exact SHA.

### H9B — OPTIONAL PRODUCTION OPTIMIZATION

H9B may be created only if every authorization gate below passes.

If any gate fails:

```text
F9_RESULT = AUDIT_ONLY_PASS
H9B_CREATED = false
```

Create E9 evidence closure and STOP.

---

## 7. CERTIFIED CORPUS

Reuse deterministic F5–F8 corpus. Hard assert Semantic Standard Shogi fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

At minimum:

- four reachable nonterminal Semantic Shogi prefixes;
- legacy draw control;
- continuous-check control;
- existing S4 curated fixtures.

Explicit terminal witnesses:

```text
ongoing
in-check with legal reply
checkmate
stalemate
repetition
continuous_check_loss
max-ply
promotion child
capture child
drop child
```

No outcome-selected random cases.

---

## 8. H9A TERMINAL→SEARCH REUSE TRACE

Create preferably:

```text
scripts/audit_f9_terminal_legal_probe_reuse.py
```

Assign each runtime push an audit-local `push_id`.

For every semantic push record at least:

```text
push_id
exact child identity summary
child side_to_move
terminal status

terminal_probe_started
terminal_probe_has_legal
terminal_probe_first_action identity if any

terminal patterns visited
terminal type ids visited
terminal sources visited
terminal geometry ids visited
terminal geometry candidates
terminal S0/S1 candidates
terminal S3 trials
terminal S3 accepted

full_legal_requested_before_pop
full_legal_action_count

full patterns visited
full type ids visited
full sources visited
full geometry ids visited
full geometry candidates
full S0/S1 candidates
full S3 trials
full S3 accepted

repeated-prefix candidate count
repeated-prefix S3 trial count
```

Where feasible record exact first legal action/binding identity:

```text
pattern_id
geometry_id
actor_type
source
target
promotion_target
```

Do not change canonical identity or order.

---

## 9. REUSE CLASSIFICATION

Classify pushes into:

```text
TERMINAL_NO_LEGAL
ONGOING_FULL_LEGAL_LATER
ONGOING_NO_FULL_LEGAL_BEFORE_POP
TERMINAL_OTHER
```

For `ONGOING_FULL_LEGAL_LATER` calculate:

```text
reuse_eligible_pushes
reuse_eligible_rate
terminal_probe_work_repeated_rate
repeated_S3_trials
repeated_geometry_candidates
repeated_candidate_bindings
estimated_repeated_probe_time
```

Also report median/p90/max first-legal rank in canonical full legal order.

Do not infer cost from call counts alone.

---

## 10. SEARCH-PATH ATTRIBUTION

Where feasible classify why pushed ongoing child later does or does not request full legal actions:

```text
NEGAMAX_RECURSION
PVS_RESEARCH
ASPIRATION_RESEARCH
QUIESCENCE
ROOT_TACTICAL
ORDERING_ONLY
OTHER
```

Diagnostic only. No expensive stack inspection in formal performance runs.

---

## 11. ALLOWED CANDIDATE FAMILY

Only this family is authorized:

```text
same-position terminal legal-existence work reuse
```

Exactly one candidate route may be selected after H9A using this frozen decision matrix.

### Candidate A — ONE-SHOT CONTINUATION REUSE

Allowed only if H9A proves:

- terminal probe and later full generation operate on the exact same Position;
- canonical traversal can safely continue without restart;
- current caller checkpoint is honored, not a stale captured callback;
- cursor/iterator state is frame-local, bounded, single-use, and destroyed on pop/rollback;
- no state survives across unrelated API calls or games.

A raw generator that captures a stale checkpoint callback is NOT automatically safe.

If safe continuation requires broad semantic-executor redesign:

```text
CANDIDATE_A_NOT_LOCAL
```

Reject it.

### Candidate B — EAGER FULL LEGAL MATERIALIZATION DURING TERMINAL PROBE

Allowed only if H9A proves:

```text
>= 85% of ongoing semantic pushed children request full legal actions before pop
```

and a probe shows the extra cost for non-recursed children is still beneficial.

Candidate B may populate the existing runtime legal cache/bindings for the exact child. It must not change public APIs or action order.

### Route selection rule

```text
if Candidate A is local + checkpoint-safe:
    Candidate A may be probed
elif Candidate B eligibility >= 85%:
    Candidate B may be probed
else:
    no production candidate authorized
```

Do NOT probe both and choose whichever benchmarks better.

---

## 12. H9B AUTHORIZATION GATES

All must pass.

### G1 — MATERIAL REUSE OPPORTUNITY

Require:

```text
reuse_eligible_rate >= 60%
```

among ongoing semantic pushes, AND:

```text
repeated semantic legality work >= 10% of Profile A wall time
OR
repeated semantic legality work >= 10% of Profile B wall time
```

The other profile must show measurable positive repeated cost.

### G2 — CANONICAL EQUIVALENCE

Baseline/candidate must preserve exactly:

```text
legal action count
legal action order
public action identity
semantic action identity
pattern_id
geometry_id
actor_type
source
target
promotion_target
binding semantics
```

### G3 — S3/S4 SEMANTICS

Exact parity required for:

```text
S3 acceptance/rejection
own_anchor_safe
squares_not_attacked
S3 reply existence
S4 truth
no_legal_reply
nifu
uchifuzume
promotion
forced promotion
capture-to-hand
promoted capture -> base in hand
```

### G4 — TERMINAL SEMANTICS

Exact parity:

```text
ONGOING
CHECKMATE
STALEMATE
REPETITION
continuous_check_loss
MAX_PLY
```

Terminal precedence unchanged.

### G5 — INTERRUPTIBILITY

Current checkpoint policy must be honored. No stale callback. Cancellation/deadline tests must pass. Identical checkpoint call counts are not required; bounded responsiveness is required.

### G6 — FRAME / ROLLBACK SAFETY

Require child-local state, no sibling/parent leakage, exact exception rollback, pop destroys child probe state, no cross-game retention.

### G7 — PROBE PERFORMANCE

Before H9B require either:

```text
Profile A semantic aggregate >= +7%
Profile B semantic aggregate >= +7%
```

or:

```text
one profile >= +12%
other profile >= +3%
```

No semantic case stable regression >3%.

If G7 fails, H9B is not authorized.

---

## 13. SEARCH PROFILES

Use the same deterministic profiles as F8/F7.

### Profile A

```text
TT = on
ordering = off
quiescence_max_depth = 0
root tactical scan = off
max_depth = 2
max_nodes = 512
no wall-clock search limit
fresh TT per run
```

### Profile B

Use current production/default AlphaBeta tuning with:

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

Formal performance runs must exclude heavy diagnostic tracing.

---

## 14. LEGAL ACTION DIFFERENTIAL — HARD GATE

For four certified Shogi prefixes and curated fixtures, baseline vs candidate full legal actions must match exactly in canonical order.

For every action compare:

```text
public action serialization
pattern_id
geometry_id
actor identity
source
target
promotion target
```

Require zero mismatches and zero order mismatches.

---

## 15. SEARCH PARITY — HARD GATE

Every Profile A/B row must exactly match:

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

PV legality mandatory. Persistent TT across moves and F3 history-aware TT remain unchanged.

---

## 16. TERMINAL / HISTORY PARITY

Require exact parity for:

```text
terminal result
winner
history length
RuntimeHistoryRecord actor
action signature
gave_check
runtime hash
occurrence count
history context
continuous-check adjudication
```

F9 must not alter repetition/history identity.

---

## 17. PUSH / POP / SIBLING / EXCEPTION TESTS

Explicitly test:

```text
parent -> push child -> terminal probe state -> legal_actions consumes/reuses -> pop -> parent exact
sibling A consumes probe state -> pop -> sibling B independent
child never requests legal_actions -> pop safely discards probe state
exception during terminal probe -> rollback exact
exception during legal continuation/materialization -> rollback exact
PVS re-search
aspiration re-search
runtime depth balanced
```

No reuse state may survive its exact runtime frame.

---

## 18. PERFORMANCE MEASUREMENT

Formal output at minimum:

```text
wall time
nodes
qnodes
semantic pushes
terminal existence probes
ongoing pushes
full legal later requests
reuse eligible pushes
reuse consumed pushes
terminal probe S3 trials
full generation S3 trials
repeated S3 trials eliminated
geometry candidates eliminated
legal actions generated
successors materialized/searched
```

Do not treat nested timing as exclusive wall time.

Runtime safety:

```text
cProfile single case <= 60 s
normal fixed-node single case <= 120 s
```

On breach record `RUNTIME_SAFETY_ABORT`; no multi-hour runner.

---

## 19. FINAL PERFORMANCE GATE

For `OPTIMIZATION_PASS`, all correctness gates plus either:

```text
Profile A aggregate >= +8%
Profile B aggregate >= +8%
```

or:

```text
one profile >= +14%
other profile >= +4%
```

and:

```text
at least 3/4 semantic cases in each profile improve >= 4%
no semantic case stable regression >3%
```

If H9B exists but final formal performance fails, cleanly revert it and finish:

```text
F9_RESULT = AUDIT_ONLY_PASS
H9B_CREATED = true
H9B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
```

---

## 20. F4–F8 EVIDENCE IMMUTABILITY

Preserve byte-identically:

```text
artifacts/f4_runtime_cost/**
artifacts/f5_semantic_attack_s3/**
artifacts/f6_target_directed_semantic/**
artifacts/f7_semantic_attack_query_reuse/**
artifacts/f8_push_terminal_check_dedup/**

docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
docs/architecture/F7_EVIDENCE.md
docs/architecture/F8_EVIDENCE.md

ADR-022
ADR-023
ADR-024
ADR-025
```

Create before/after SHA-256 manifests. Any mutation: `OLD_EVIDENCE_MUTATED` and STOP.

New evidence only under:

```text
artifacts/f9_terminal_legal_probe_reuse/
```

---

## 21. REQUIRED F9 EVIDENCE

At minimum:

```text
artifacts/f9_terminal_legal_probe_reuse/
    baseline.json
    corpus.json
    source_call_chain.json
    terminal_probe_trace.jsonl
    reuse_classification.json
    repeated_work_summary.json
    callsite_summary.json
    timing_attribution.json
    candidate_route_decision.json
    candidate_design.json
    optimization_gate.json
    legal_action_parity.json
    s3_s4_parity.json
    terminal_parity.json
    history_parity.json
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

If candidate not authorized, candidate files may explicitly record `NOT_RUN_NOT_AUTHORIZED`.

Create:

```text
docs/architecture/F9_EVIDENCE.md
docs/architecture/ADR-026-terminal-legal-probe-reuse.md
```

---

## 22. TESTS

Focused suites must include F9 harness, terminal runtime, semantic legal generation, search runtime push/pop, F8/F7/F6/F5/F4 regressions, S3/S4, Standard Shogi parity, F3 TT/history, repetition/continuous-check, Native readiness/stress.

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

Do not use AlphaSho. Do not run long game matches.

---

## 23. FORBIDDEN SCOPE

F9 must not modify:

```text
ruleset fingerprint
semantic IR version
public serialization
promotion/drop semantics
nifu / uchifuzume
S4 truth table
repetition / continuous-check semantics
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

No attack cache. No terminal-result cache. No bitboards. No incremental attack map. No F6 target-directed optimization. No F7 memoization. No F8 known_checked forwarding. No F10 work.

---

## 24. GIT / PROVENANCE

Audit-only:

```text
E8 baseline -> H9A audit/harness -> E9 audit closure
```

Optimization:

```text
E8 baseline -> H9A audit/harness -> H9B production source+tests -> E9 evidence closure
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

## 25. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
LEGAL_ACTION_ORDER_PARITY_FAILURE
S3_PARITY_FAILURE
S4_PARITY_FAILURE
TERMINAL_PARITY_FAILURE
HISTORY_PARITY_FAILURE
CONTINUOUS_CHECK_PARITY_FAILURE
SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
ROLLBACK_ISOLATION_FAILURE
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
NATIVE_BUILD_FAILURE
RUNTIME_SAFETY_ABORT that invalidates required evidence
```

Do not repair unrelated architecture inside F9.

---

## 26. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Corpus
5. Source call-chain audit
6. Terminal-probe reuse diagnosis
7. Reuse classification
8. Repeated-work attribution
9. H9A provenance
10. Candidate route decision
11. Optimization authorization gate
12. Candidate design or rejection
13. Legal-action parity
14. S3/S4 parity
15. Terminal/history/continuous-check parity
16. Search parity
17. Interruptibility
18. Push/pop/rollback/sibling isolation
19. Performance
20. Tests
21. Evidence / manifest
22. Git
23. Deferred
24. Final verdict

Optimization success:

```text
F9_RESULT = OPTIMIZATION_PASS
TERMINAL_LEGAL_PROBE_REUSE = PASS
LEGAL_ACTION_PARITY = PASS
S3_S4_PARITY = PASS
TERMINAL_PARITY = PASS
HISTORY_PARITY = PASS
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
F9_RESULT = AUDIT_ONLY_PASS
H9B_CREATED = false
reason = <frozen gate that failed>
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

Reverted candidate:

```text
F9_RESULT = AUDIT_ONLY_PASS
H9B_CREATED = true
H9B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

---

## 27. FINAL STOP

F9 ends after E9 closure.

Do not begin F10. Do not automatically optimize transition/runtime hash/history. Do not automatically migrate semantic search to Native. Do not automatically alter evaluator or search strength. The next phase, if any, will be separately audited and authorized.

