# Gmail provenance

- Subject: GenericChess — F11: Post-F10 Semantic Search Re-Baseline + Evidence-Gated Single-Winner Optimization
- Message ID: 19ffc98a5c4d7faa
- Thread ID: 19ffc98a5c4d7faa
- From: W D <icywoods.1@gmail.com>
- To: icywoods.1@gmail.com
- Date: Thu, 13 Aug 2026 15:28:09 -0400
- Retrieved: 2026-08-14
- Processing state: authoritative body persisted before execution

# Complete authoritative body
# GenericChess — F11: Post-F10 Semantic Search Re-Baseline + Evidence-Gated Single-Winner Optimization

## 0. AUTHORITATIVE TASK

This is the authoritative F11 task for `WD-nanophotonics/GenericChess`.

F4–F10 substantially changed the runtime cost structure. In particular, F5 and F10 removed large amounts of repeated semantic source-dispatch work. Therefore all hotspot rankings from F4/F6 are now stale for optimization selection.

F11 has two goals only:

1. establish a fresh, reproducible post-F10 semantic-search cost baseline on the current production tree;
2. if and only if the new evidence identifies one clearly dominant, local, semantics-preserving optimization family, implement one winner only and close it with full parity/performance evidence.

Valid successful outcomes:

```text
F11_RESULT = OPTIMIZATION_PASS
```

or:

```text
F11_RESULT = AUDIT_ONLY_PASS
```

`AUDIT_ONLY_PASS` is a complete successful phase. It is the required result if no remaining Python-local candidate clears the frozen gates.

F11 is also a decision boundary:

> If no Python-local semantic/runtime optimization is clearly worth retaining after F10, say so explicitly. Do not keep shaving 1–3% micro-hotspots indefinitely. The next separately-authorized phase may instead be Native execution work or search-strength/evaluator work.

Do not begin either of those in F11.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before work:

1. locate this task through GenericChess Gmail subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. then begin audit/execution.

Do not execute from the subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
83b921a07277ca7186f66a65ecc95fb040838a34

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three before H11A.

If `origin/sandbox` moved:

```text
BASELINE_MOVED
STOP
```

Do not reset, force-push, rewrite, or overwrite another task.

Work only on `sandbox`.

`master` and `chat` remain read-only.

---

# 3. F4–F10 FROZEN RESULTS

Treat all previous phase decisions as closed.

## Accepted production optimizations

### F4
Fixed-node checkpoint dispatch optimization.

### F5
Position-local semantic source dispatch by `(owner, current_type_id)`.

### F10
Operation-local source-index reuse inside semantic legality/S3-reply operations.

F10 final no-trace semantic medians:

```text
Profile A semantic cases:
~0.45–0.62 s each

Profile B semantic cases:
~1.85–2.36 s each
```

F10 aggregate improvement over its baseline:

```text
Profile A: +9.79%
Profile B: +17.76%
```

Do not remove or weaken these optimizations.

## Rejected / closed candidates

### F6
Target-directed geometry:
rejected.

### F7
Generic exact attack/check memoization:
rejected.

### F8
Push→terminal `known_checked` forwarding:
authorized experimentally, failed final gate, reverted.

### F9
Terminal legal-probe continuation/eager reuse:
rejected.

F11 MUST NOT resurrect any of those under a new name.

---

# 4. F11 PRINCIPLE

Do not start from a candidate.

Start from measurement.

The first formal output of F11 must be a post-F10 hotspot ranking produced from the current production tree.

Only after that ranking is frozen may one candidate family be selected.

No "I noticed this code could be cleaner" optimization is allowed without measured materiality.

---

# 5. PHASE STRUCTURE

## H11A — RE-BASELINE / AUDIT ONLY

H11A must be created first.

Allowed:
- low-overhead whole-search instrumentation;
- cProfile/pstats;
- call-count instrumentation;
- bounded microbenchmarks;
- test-only probes;
- candidate sketches in evidence only.

H11A MUST NOT retain production runtime/semantic changes.

Commit and push H11A before candidate selection.

Record exact H11A SHA.

## H11B — OPTIONAL SINGLE-WINNER OPTIMIZATION

H11B may be created only if one candidate family passes every gate in Section 13.

Only one family may be implemented.

If no family qualifies:

```text
F11_RESULT = AUDIT_ONLY_PASS
H11B_CREATED = false
```

Create E11 closure and STOP.

Do not lower thresholds after seeing results.

---

# 6. CERTIFIED CORPUS

Reuse the deterministic corpus frozen through F10.

Hard assert Semantic Standard Shogi fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

Formal corpus:
- 4 reachable nonterminal Semantic Standard Shogi prefixes;
- legacy draw control;
- continuous-check control.

Retain curated semantic regression witnesses for:
- board moves;
- drops;
- capture;
- promotion/forced promotion;
- own-anchor safety;
- `squares_not_attacked`;
- nifu;
- uchifuzume;
- S4;
- repetition;
- continuous-check.

Do not change the semantic corpus after looking at results.

---

# 7. SEARCH PROFILES

Use the frozen deterministic profiles unless the repository evidence proves F10 encoded them differently.

## Profile A — semantic core-cost isolation

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

## Profile B — current product-like fixed-node profile

Use current production/default AlphaBeta feature combination.

Freeze:

```text
max_nodes = 256
deterministic node budget
no wall-clock search limit
```

Record the full tuning/config snapshot.

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
termination reason
```

Logical outputs must be deterministic.

---

# 8. WHOLE-SEARCH POST-F10 ATTRIBUTION

Create or extend a reproducible script, preferably:

```text
scripts/audit_f11_post_f10_runtime.py
```

Use opt-in instrumentation only.

At minimum record these categories:

```text
MOVE_GEN / semantic legal generation
S3_TRIAL_TRANSITION
S3_INVARIANT_CHECK
S4_POSTCONDITION
ATTACK_CHECK
TERMINAL_PROBE
RUNTIME_PUSH
RUNTIME_HASH_IDENTITY
RUNTIME_HISTORY_REPETITION
EVALUATION
ORDERING
QUIESCENCE
TT_KEY
TT_PROBE_STORE
CHECKPOINT
OTHER / RESIDUAL
```

If a category cannot be measured non-overlappingly, label it:

```text
NESTED_ONLY
```

Do NOT sum nested/inclusive timings and call the sum a wall-time decomposition.

For each category report where meaningful:

```text
calls
inclusive_ms
exclusive/nonoverlap_ms
% wall
us/call
us/node
```

Also report high-leverage structural counts:

```text
semantic patterns visited
geometry candidates
S3 trials
S3 accepted
attack queries
in_check calls

runtime pushes/pops
terminal probes
source-index builds

history-context updates
runtime search-key calls
semantic component-diff hash calls

legal actions generated
successors materialized
successors searched

evaluation calls
qnodes
TT probes/hits/stores
```

---

# 9. DEEP PROFILE — CURRENT TREE ONLY

Run bounded `cProfile`/`pstats` against the post-F10 production tree.

At minimum:
- one representative Semantic Shogi Profile A case;
- one representative Semantic Shogi Profile B case, if it stays within runtime cap.

Save:

```text
top 50 cumulative time
top 50 self time
call counts
```

Do not use old F4/F6 profiles as selection authority.

Inspect current functions including, but not limited to:

```text
SemanticEngine.iter_legal_action_bindings
SemanticEngine._iter_candidates
SemanticEngine._iter_board_candidates
SemanticEngine._iter_drop_candidates
SemanticEngine._trial_child_if_s3_legal
SemanticEngine.is_square_attacked
SemanticEngine.in_check
SemanticEngine._exists_s3_reply
SemanticEngine._transition

geometry_candidates
_promotion_choices
_path_holds
_guards_hold
_resolve_square_ref

SearchPathRuntime.push/_push_impl/pop
_semantic_component_diff_hash
RuntimeCountsSnapshot.updated
RuntimeHistoryContext.append
terminal_from_search_runtime

Evaluator.evaluate
_anchor_escape / pseudo_attacks

negamax
quiescence
_runtime_noisy_actions
checkpoint

TT key/probe/store
```

This list is diagnostic, not a predetermined answer.

---

# 10. HOTSPOT RANKING

Produce a machine-readable ordered ranking.

For every candidate hotspot/family record:

```text
rank
name
scope
representative functions

Profile A measured cost
Profile B measured cost

call count
cost per call
cost per node

whether cost is nested or non-overlap

root cause
why it still exists after F10

possible local optimization
semantic risk
architectural risk
expected benefit
```

The ranking must distinguish:

```text
algorithmic/repeated work
Python dispatch/object overhead
necessary semantic work
search-policy work
```

Do not label necessary work as avoidable merely because it is expensive.

---

# 11. ALLOWED CANDIDATE CLASSES

After H11A, candidate selection may consider ONLY a local semantics-preserving implementation optimization.

Examples of potentially eligible classes:

```text
A. remove repeated immutable semantic preprocessing within one operation
B. avoid repeated pure conversion/object construction
C. make an existing incremental runtime update genuinely incremental
D. eliminate duplicated exact local computation with no cache architecture
E. reduce Python dispatch in a hot inner loop while preserving exact ordering
F. exact evaluator implementation optimization preserving score bit-for-bit
```

These are examples, not mandates.

Explicitly forbidden:
- F6 target-directed geometry;
- F7 attack cache/memoization;
- F8 known_checked forwarding;
- F9 terminal continuation/eager legal materialization;
- general Position cache;
- terminal cache;
- bitboards;
- incremental attack map;
- Shogi-specific shortcut;
- Native migration;
- new search heuristic;
- PVS/LMR/null-move policy change;
- evaluator feature/weight change;
- move-ordering policy change;
- TT/history semantic redesign.

If the best remaining opportunity belongs to a forbidden class, document it as a recommended future phase, not F11 work.

---

# 12. SINGLE-WINNER SELECTION RULE

H11A may rank many candidates.

It must select at most one.

The selected candidate must be the highest-ranked family that passes all Section 13 authorization gates.

Do not:
- implement several candidates and choose the best afterward;
- bundle multiple unrelated micro-optimizations;
- use outcome-dependent candidate shopping.

If two candidates are close and neither clearly dominates:

```text
NO_CLEAR_SINGLE_WINNER
AUDIT_ONLY_PASS
```

---

# 13. H11B AUTHORIZATION GATES

All gates must pass.

## G1 — DOMINANT / MATERIAL

The candidate must explain at least one of:

```text
>= 12% of Profile A semantic wall time
>= 12% of Profile B semantic wall time
```

AND at least:

```text
>= 5% measurable positive cost in the other profile
```

OR it must have a bounded probe demonstrating material end-to-end benefit under G6.

Do not authorize from microbenchmark speedup alone.

## G2 — EXPLAINED

The root cause must be explicitly demonstrated by:
- call counts;
- exact repeated work;
- object/dispatch counts;
- or another direct structural witness.

No speculative optimization.

## G3 — LOCAL

The candidate should normally touch no more than:

```text
3 production modules
```

If it requires a broad API/semantic architecture rewrite:

```text
NOT_LOCAL
```

Reject.

## G4 — SEMANTICS PRESERVING

The candidate must preserve:
- ruleset semantics;
- canonical action order;
- S3/S4 truth;
- terminal precedence;
- history/repetition;
- TT identity;
- evaluator score if evaluator implementation is optimized;
- search policy.

## G5 — TESTABLE / ROLLBACK SAFE

There must be a direct differential oracle and clean rollback/isolation story.

## G6 — PROBE PERFORMANCE

Before H11B, an opt-in candidate probe must achieve either:

### Route A

```text
Profile A semantic aggregate >= +7%
Profile B semantic aggregate >= +7%
```

or:

### Route B

```text
one profile >= +12%
other profile >= +3%
```

Also:

```text
no semantic case stable regression >3%
```

If G6 fails:

```text
F11_RESULT = AUDIT_ONLY_PASS
H11B_CREATED = false
```

Do not create production code.

---

# 14. H11B PRODUCTION RULES

If authorized:

1. create H11B with the single production optimization + focused tests;
2. do not include final after-outcome evidence in H11B;
3. push H11B;
4. require clean tracked source;
5. run full frozen before/after formal corpus;
6. create E11 evidence closure.

No second optimization may be added to H11B.

If implementation uncovers another hotspot:

```text
DEFER_TO_FUTURE_PHASE
```

---

# 15. CORRECTNESS GATES

At minimum all of the following remain mandatory.

Legal action parity:
- count;
- order;
- public action serialization;
- pattern_id;
- geometry_id;
- actor_type;
- source;
- target;
- promotion target.

Attack/check parity:
for each certified Semantic Shogi prefix:

```text
81 squares × 2 owners
```

Require:

```text
attack mismatches = 0
check mismatches = 0
```

S3/S4 parity:
- S3 acceptance/rejection;
- own-anchor safety;
- squares-not-attacked;
- reply existence;
- no-legal-reply;
- nifu;
- uchifuzume;
- promotion;
- capture/drop;
- S4 truth.

Terminal/history parity:
- terminal status/winner;
- repetition;
- continuous-check;
- max-ply;
- RuntimeHistoryRecord.gave_check;
- runtime occurrence counts;
- history context.

TT parity:
- TT on/off differential;
- persistent TT across moves;
- collision exactness regressions.

Search parity:
for all formal Profile A/B rows exact:

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

If evaluator implementation is optimized:

```text
evaluator score exact equality
```

is mandatory on the full evaluator corpus.

---

# 16. INTERRUPTIBILITY / RUNTIME SAFETY

Any retained candidate must preserve:
- cooperative checkpoint contract;
- cancellation;
- deadline behavior;
- push/pop exception safety;
- sibling isolation;
- runtime balance.

Identical checkpoint call count is not required.

Bounded responsiveness is required.

Formal runtime caps:

```text
cProfile single case <= 60 s
normal fixed-node single case <= 120 s
```

On cap breach:

```text
RUNTIME_SAFETY_ABORT
```

Preserve diagnostics.

Do not run multi-hour benchmarks.

---

# 17. FINAL PERFORMANCE GATE

For:

```text
F11_RESULT = OPTIMIZATION_PASS
```

require all correctness gates plus either:

Route A:

```text
Profile A semantic aggregate >= +8%
Profile B semantic aggregate >= +8%
```

or:

Route B:

```text
one profile >= +14%
other profile >= +4%
```

Additionally:

```text
at least 3/4 semantic cases in each profile improve >= 4%
no semantic case stable regression >3%
```

If H11B was created but final formal gate fails:
1. cleanly revert H11B;
2. preserve H11A/H11B/E11 evidence;
3. final:

```text
F11_RESULT = AUDIT_ONLY_PASS
H11B_CREATED = true
H11B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
```

Do not retain a non-qualifying optimization.

---

# 18. PYTHON-LOCAL SATURATION DECISION

F11 must explicitly answer:

```text
PYTHON_LOCAL_RUNTIME_HEADROOM =
    CLEAR
    LIMITED
    INCONCLUSIVE
```

Use:

CLEAR:
At least one retained or clearly-gated local candidate remains capable of material gains.

LIMITED:
No allowed Python-local candidate explains enough current wall time or clears performance gates.

INCONCLUSIVE:
Instrumentation or runtime safety prevented a reliable conclusion.

If:

```text
PYTHON_LOCAL_RUNTIME_HEADROOM = LIMITED
```

the final report must recommend exactly one next boundary from:

```text
NATIVE_SEMANTIC_EXECUTION_AUDIT
SEARCH_STRENGTH_EVALUATOR_PHASE
OTHER_EXPLICIT_BOUNDARY
```

Do not start it.

The recommendation must be evidence-based.

---

# 19. F4–F10 EVIDENCE IMMUTABILITY

Preserve byte-identically:

```text
artifacts/f4_runtime_cost/**
artifacts/f5_semantic_attack_s3/**
artifacts/f6_target_directed_semantic/**
artifacts/f7_semantic_attack_query_reuse/**
artifacts/f8_push_terminal_check_dedup/**
artifacts/f9_terminal_legal_probe_reuse/**
artifacts/f10_source_index_lifetime/**

docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
docs/architecture/F7_EVIDENCE.md
docs/architecture/F8_EVIDENCE.md
docs/architecture/F9_EVIDENCE.md
docs/architecture/F10_EVIDENCE.md

ADR-022
ADR-023
ADR-024
ADR-025
ADR-026
ADR-027
```

Create before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f11_post_f10_rebaseline/
```

---

# 20. REQUIRED F11 EVIDENCE

At minimum:

```text
artifacts/f11_post_f10_rebaseline/
    baseline.json
    corpus.json
    tuning.json
    whole_search_profile_a.jsonl
    whole_search_profile_b.jsonl
    category_attribution.json
    structural_counts.json
    cprofile_a.prof
    cprofile_a_cumulative.txt
    cprofile_a_self.txt
    cprofile_b.prof OR cprofile_b_safety_abort.json
    cprofile_b_cumulative.txt
    cprofile_b_self.txt
    hotspot_ranking.json
    candidate_matrix.json
    single_winner_decision.json
    optimization_gate.json
    candidate_design.json
    legal_action_parity.json
    attack_check_parity.json
    s3_s4_parity.json
    terminal_history_parity.json
    tt_parity.json
    search_parity.json
    interruptibility.json
    rollback_sibling_isolation.json
    profile_a_before.jsonl
    profile_a_candidate.jsonl
    profile_b_before.jsonl
    profile_b_candidate.jsonl
    performance_comparison.json
    python_local_headroom.json
    old_evidence_before.sha256
    old_evidence_after.sha256
    full_pytest.txt
    native_build.txt
    final_verdict.json
    manifest.json
```

If no candidate is authorized, candidate files may contain explicit:

```text
NOT_RUN_NOT_AUTHORIZED
```

records rather than fabricated results.

Create:

```text
docs/architecture/F11_EVIDENCE.md
docs/architecture/ADR-028-post-f10-runtime-rebaseline.md
```

ADR-028 must document:
- why old hotspot rankings are stale;
- the new post-F10 ranking;
- whether one Python-local optimization was selected;
- whether Python-local runtime headroom is CLEAR/LIMITED/INCONCLUSIVE;
- recommended next boundary if LIMITED.

---

# 21. TESTS

Focused suites must include at least:
- F11 harness;
- F10 operation-local source-index regressions;
- F9 terminal-probe regressions;
- F8 regressions;
- F7 regressions;
- F6 regressions;
- F5 source-dispatch regressions;
- F4 interruptibility/runtime;
- semantic executor;
- S3/S4;
- Standard Shogi semantic parity;
- F3 TT/history;
- repetition/continuous-check;
- search runtime rollback;
- Native readiness/stress.

Then run:

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

# 22. FORBIDDEN SCOPE

F11 must not modify:

```text
ruleset fingerprint
semantic IR version
public serialization
promotion/drop semantics
nifu
uchifuzume
S4 truth table
repetition
continuous-check
TT identity
TT bounds
TT generation
TT replacement
mate normalization
qsearch TT policy
search heuristics
evaluator features/weights
move-ordering policy
Native production search
UI
master
chat
AlphaSho
```

No global cache.
No bitboards.
No incremental attack map.
No revival of F6/F7/F8/F9.
No F12 work.

---

# 23. GIT / PROVENANCE

Audit-only path:

```text
E10 baseline
  -> H11A post-F10 rebaseline
  -> E11 audit closure
```

Optimization path:

```text
E10 baseline
  -> H11A post-F10 rebaseline
  -> H11B single production optimization
  -> E11 evidence closure
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

# 24. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
LEGAL_ACTION_ORDER_PARITY_FAILURE
ATTACK_CHECK_PARITY_FAILURE
S3_S4_PARITY_FAILURE
TERMINAL_HISTORY_PARITY_FAILURE
TT_PARITY_FAILURE
SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
ROLLBACK_ISOLATION_FAILURE
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
NATIVE_BUILD_FAILURE
RUNTIME_SAFETY_ABORT that invalidates required evidence
```

Do not repair unrelated architecture inside F11.

---

# 25. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Corpus / tuning
5. Post-F10 whole-search attribution
6. Deep profile
7. Structural counts
8. Hotspot ranking
9. H11A provenance
10. Candidate matrix
11. Single-winner decision
12. Optimization authorization gate
13. Candidate design or rejection
14. Legal-action parity
15. Attack/check parity
16. S3/S4 parity
17. Terminal/history/TT parity
18. Search parity
19. Interruptibility
20. Rollback/sibling isolation
21. Performance
22. Python-local runtime headroom
23. Tests
24. Evidence / manifest
25. Git
26. Deferred
27. Final verdict

Optimization success:

```text
F11_RESULT = OPTIMIZATION_PASS
SINGLE_WINNER_OPTIMIZATION = PASS
LEGAL_ACTION_PARITY = PASS
ATTACK_CHECK_PARITY = PASS
S3_S4_PARITY = PASS
TERMINAL_HISTORY_TT_PARITY = PASS
SEARCH_PARITY = PASS
INTERRUPTIBILITY = PASS
ROLLBACK_ISOLATION = PASS
PERFORMANCE_GATE = PASS
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
PYTHON_LOCAL_RUNTIME_HEADROOM = <CLEAR|LIMITED|INCONCLUSIVE>
```

Audit-only without H11B:

```text
F11_RESULT = AUDIT_ONLY_PASS
H11B_CREATED = false
reason = <NO_CLEAR_SINGLE_WINNER | AUTHORIZATION_GATE_FAIL | other frozen reason>
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
PYTHON_LOCAL_RUNTIME_HEADROOM = <CLEAR|LIMITED|INCONCLUSIVE>
```

Reverted H11B:

```text
F11_RESULT = AUDIT_ONLY_PASS
H11B_CREATED = true
H11B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
PYTHON_LOCAL_RUNTIME_HEADROOM = <CLEAR|LIMITED|INCONCLUSIVE>
```

---

# 26. FINAL STOP

F11 ends after E11 closure.

Do not begin F12.

If Python-local runtime headroom is LIMITED, recommend one next boundary but do not start it.

The next phase will be separately audited and separately authorized.

