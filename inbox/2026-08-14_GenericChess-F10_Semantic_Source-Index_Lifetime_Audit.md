<!-- Gmail inbox record -->
<!-- Received: Thu, 13 Aug 2026 14:13:53 -0400 -->
<!-- Subject: GenericChess — F10: Semantic Source-Index Lifetime Audit + Evidence-Gated Operation-Local Reuse -->
<!-- Sender: W D icywoods.1@gmail.com -->
<!-- Message ref: 19ffc54a708cbc5d -->
<!-- Attachment: GenericChess_F10_Source_Index_Lifetime.md -->
<!-- Status: authoritative task captured; processing in sandbox worktree -->
<!-- Source note: Gmail fuzzy-title protocol; exact GenericChess F10 match -->
# GenericChess — F10: Semantic Source-Index Lifetime Audit + Evidence-Gated Operation-Local Reuse

## 0. AUTHORITATIVE TASK

This is the authoritative F10 task for `WD-nanophotonics/GenericChess`.

F10 starts from the certified F9 audit-only closure.

Its single narrow question is:

> F5 introduced `_sources_by_owner_type(position)` to eliminate repeated full-board owner/type filtering, but current production legality code rebuilds that exact position-local index inside `_iter_board_candidates(pattern, ...)`, which is invoked once per pattern. Is the same immutable source index therefore being rebuilt repeatedly inside one semantic legality operation, and can its lifetime be lifted from **per-pattern** to **per-legality-operation** without changing semantics?

Valid successful outcomes:

```text
F10_RESULT = OPTIMIZATION_PASS
```

or:

```text
F10_RESULT = AUDIT_ONLY_PASS
```

`AUDIT_ONLY_PASS` is a complete successful phase.

Do not broaden F10 into a general Position cache, attack cache, terminal cache, bitboard system, Native migration, or search-strength work.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before implementation:

1. locate this task through GenericChess Gmail subject matching;
2. read the full authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record message/thread metadata and processing state;
5. then begin audit/execution.

Do not act from the subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
7f83ef8c7c10381cdf712d884d359cacf9bdf0f4

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

Do not reset, force-push, rewrite, or overwrite another task.

Work only on `sandbox`.

`master` and `chat` are read-only.

---

# 3. F4–F9 FROZEN FINDINGS

All prior phases are closed.

## F4
Fixed-node checkpoint dispatch optimization accepted.

## F5
Position-local `(owner, current_type_id)` source dispatch accepted.

F5 production helper:

```text
_sources_by_owner_type(position)
```

is authoritative for the current optimization family.

F10 may change only its **construction lifetime / plumbing**, not its semantics or ordering.

## F6
Target-directed geometry audited and rejected.

Do not revisit.

## F7
Generic attack-query memoization audited and rejected.

Do not revisit.

## F8
Push→terminal known-checked forwarding audited, authorized, then reverted for insufficient final performance.

Do not reintroduce.

## F9
Terminal legal-existence continuation/eager materialization audited and rejected.

Do not revisit.

F9 established roughly:

```text
full legal reuse eligibility ≈ 10%
first legal action rank median/p90/max = 1
```

Do not attempt to cache or continue terminal legal generators in F10.

---

# 4. CURRENT SOURCE FACT — VERIFY BEFORE WORK

At baseline, verify the current production structure.

Expected:

```python
def _iter_candidates(pattern, position, checkpoint=None):
    ...
    yield from self._iter_board_candidates(
        pattern, position, checkpoint=checkpoint
    )

def _iter_board_candidates(pattern, position, checkpoint=None):
    side = position.side_to_move
    sources_by_owner_type = _sources_by_owner_type(position)
    ...
```

and callers:

```text
iter_legal_action_bindings(position)
    -> for pattern in self._patterns
         -> _iter_candidates(pattern, position)
              -> _iter_board_candidates(...)
                   -> rebuild source index

_exists_s3_reply(position)
    -> for pattern in self._patterns
         -> _iter_candidates(pattern, position)
              -> _iter_board_candidates(...)
                   -> rebuild source index
```

`is_square_attacked()` already builds its source index once per attack query; F10 does not assume that path needs modification.

The F10 hypothesis is specifically:

> A single canonical legality/reply operation on one exact Position may rebuild the same source index once per board-move pattern.

Do not assume the magnitude. Measure it.

---

# 5. PHASE STRUCTURE

## H10A — HARNESS / AUDIT ONLY

Create H10A first.

Allowed:
- audit scripts;
- counters;
- low-overhead tracing;
- process-isolated benchmarks;
- test-only candidate probes;
- evidence schema.

Forbidden in H10A:
- retained production source changes;
- global cache;
- Position cache;
- persistent source index.

Commit and push H10A before production authorization.

Record exact H10A SHA.

## H10B — OPTIONAL PRODUCTION OPTIMIZATION

H10B may be created only if every gate in Section 11 passes.

If any gate fails:

```text
F10_RESULT = AUDIT_ONLY_PASS
H10B_CREATED = false
```

Create E10 closure evidence and STOP.

Do not weaken thresholds after seeing results.

---

# 6. CERTIFIED CORPUS

Reuse the deterministic F5–F9 corpus.

Hard assert Standard Semantic Shogi fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

At minimum:
- four reachable nonterminal Semantic Shogi prefixes;
- legacy draw control;
- continuous-check control;
- existing S4 fixtures.

Also retain witnesses for:
- board moves;
- drops;
- promotion;
- capture;
- own-anchor safety;
- `squares_not_attacked`;
- S3 reply existence;
- no-legal-reply;
- nifu;
- uchifuzume.

Do not introduce outcome-selected random corpus changes.

---

# 7. H10A SOURCE-INDEX LIFETIME AUDIT

Create a bounded reproducible audit, preferably:

```text
scripts/audit_f10_source_index_lifetime.py
```

Instrument `_sources_by_owner_type(position)` without changing production outcomes.

For every semantic legality operation assign an audit-local operation id.

Classify operation type:

```text
FULL_LEGAL_BINDINGS
HAS_LEGAL_ACTION
S3_REPLY_EXISTENCE
ATTACK_QUERY
OTHER
```

For every operation record:

```text
operation_id
operation_type
exact Position identity summary

source_index_build_calls
source_index_entries
source_index_build_time_s

patterns_visited
board_patterns_visited
drop_patterns_visited

S0/S1 candidates
S3 trials
S3 accepted
legal actions yielded
```

Aggregate:

```text
total semantic operations
total source-index builds

builds_per_operation median/p90/max
FULL_LEGAL builds/op
HAS_LEGAL_ACTION builds/op
S3_REPLY builds/op
ATTACK_QUERY builds/op

redundant_same_position_builds
redundant_build_rate

source_index_total_time
source_index_time_by_operation_type
```

Important:

A build is "redundant within operation" only when:

```text
same exact Position
same operation_id
same source-index semantics
```

Do not call two builds redundant merely because Position hashes match.

---

# 8. EXACT INDEX EQUIVALENCE

For each operation where the index is rebuilt multiple times, compare all rebuilt values exactly.

Require:

```text
same keys
same source order
same Piece object/value semantics
same tuple ordering
```

Forced hash collisions are irrelevant because the candidate should not use hash authority.

Preferred candidate does not require any cache key at all.

---

# 9. COST ATTRIBUTION

Measure the actual cost, not just call counts.

For Profile A/B report:

```text
source-index build calls
source-index inclusive time

legal generation wall time
terminal has-legal wall time
S3 reply wall time
whole-search wall time
```

Use low-overhead instrumentation for formal attribution.

Use cProfile only as supporting evidence.

Do not sum nested timings as exclusive wall shares.

Also report:

```text
estimated avoidable index builds
estimated avoidable build time
```

where "avoidable" means all but the first exact build in one operation.

---

# 10. ONLY ALLOWED CANDIDATE FAMILY

F10 authorizes only:

```text
operation-local source-index reuse
```

Preferred shape:

```text
iter_legal_action_bindings(position):
    sources = _sources_by_owner_type(position)
    for pattern:
        _iter_candidates(..., sources_by_owner_type=sources)
```

and similarly, where justified:

```text
_exists_s3_reply(position):
    sources = _sources_by_owner_type(position)
    for pattern:
        _iter_candidates(..., sources_by_owner_type=sources)
```

`_iter_candidates()` / `_iter_board_candidates()` may accept an optional already-built index.

If no index is supplied, semantics must remain current and self-contained.

### Attack path

Do NOT automatically change `is_square_attacked()`.

It already constructs once per attack query.

Only touch it if required for signature consistency and with zero semantic/performance scope expansion.

### Drop path

Do not build a source index solely for a drop-only operation if evidence shows it is unnecessary.

A local lazy construction inside the operation is allowed if it remains deterministic and simple.

---

# 11. H10B AUTHORIZATION GATES

All gates must pass.

## G1 — REDUNDANT BUILD FREQUENCY

For at least one major operation family:

```text
FULL_LEGAL_BINDINGS
HAS_LEGAL_ACTION
S3_REPLY_EXISTENCE
```

require:

```text
median source-index builds per operation >= 3
```

AND aggregate:

```text
redundant within-operation builds >= 50%
```

If not:

```text
REDUNDANCY_NOT_MATERIAL
AUDIT_ONLY_PASS
```

## G2 — MATERIAL COST

Require source-index construction to account for at least:

```text
>= 5% of Profile A semantic wall time
OR
>= 5% of Profile B semantic wall time
```

and measurable positive cost in the other profile.

Alternatively, a candidate probe may satisfy G4 strongly enough to demonstrate materiality directly.

## G3 — EXACT SEMANTICS

Operation-local reuse must preserve:

```text
pattern order
type order
source board order
geometry order
target order
promotion order
public action order
semantic binding identity
```

No mutation of the shared operation-local index.

## G4 — PROBE PERFORMANCE

Before H10B, an opt-in candidate probe must achieve either:

Route A:

```text
Profile A semantic aggregate >= +6%
Profile B semantic aggregate >= +6%
```

or Route B:

```text
one profile >= +10%
other profile >= +2%
```

No semantic case stable regression >3%.

If G4 fails:

```text
F10_RESULT = AUDIT_ONLY_PASS
H10B_CREATED = false
```

## G5 — INTERRUPTIBILITY

Checkpoint semantics must remain bounded.

Reusing a prebuilt index must not skip long semantic loops without checkpoint opportunities.

Building the index itself currently has no search-policy knowledge; do not add AI/search imports into Core.

## G6 — LOCALITY

No reused source index may outlive the current semantic operation.

No:
- cross-operation retention;
- cross-Position retention;
- cross-game retention;
- global mutable state;
- LRU;
- weakref cache;
- Position-attached memo.

---

# 12. LEGAL ACTION PARITY — HARD GATE

For every certified prefix and curated fixture compare baseline/candidate full canonical legal bindings.

Require exact parity on:

```text
legal action count
legal action order
public action serialization

pattern_id
geometry_id
actor_type
source
target
promotion_target
binding path
```

Require:

```text
mismatches = 0
order mismatches = 0
```

---

# 13. ATTACK / CHECK PARITY

Even though F10 should not alter attack semantics, run regression differential:

For each certified Semantic Shogi prefix:

```text
81 squares × 2 owners
```

Require:

```text
attack mismatches = 0
check mismatches = 0
```

This catches accidental signature/plumbing regressions.

---

# 14. S3 / S4 PARITY

Require exact baseline/candidate parity for:

```text
S3 acceptance/rejection
own_anchor_safe
squares_not_attacked

S3 reply existence

S4 action_delivers_check
opponent_checked
no_legal_reply

nifu
uchifuzume
promotion
forced promotion
capture/drop
```

No S3/S4 semantic restructuring is authorized.

---

# 15. TERMINAL / HISTORY / TT PARITY

Require exact parity for:

```text
terminal status
winner
repetition
continuous_check_loss
max ply

RuntimeHistoryRecord
gave_check
runtime hash
occurrence counts
history context

TT on/off action/score/PV
persistent TT across moves
TT probes/hits/stores where deterministic
```

F10 must not alter F3 history-aware TT identity.

---

# 16. SEARCH PARITY

For every Profile A/B formal row baseline/candidate must exactly match:

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

---

# 17. PUSH / POP / EXCEPTION / SIBLING ISOLATION

Because the candidate is operation-local, isolation should be simple, but still test:

```text
parent legal operation
push child
child legal operation uses child-local index
pop

sibling A
pop
sibling B
no index leakage

exception during legal generation
no retained state

exception during S3 reply probe
no retained state

PVS re-search
aspiration re-search
runtime balanced
```

No operation-local index may be stored in a mutable engine singleton across calls.

---

# 18. PERFORMANCE PROTOCOL

Use the same deterministic search profiles as F9.

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

Current production/default AlphaBeta tuning:

```text
max_nodes = 256
deterministic node budget
no wall-clock search limit
```

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

source-index builds
source-index build time
legal generation calls
terminal legal probes
S3 reply probes
```

Formal runs must not include heavy trace logging.

Use process isolation.

Runtime limits:

```text
cProfile single case <= 60 s
normal fixed-node single case <= 120 s
```

On timeout:

```text
RUNTIME_SAFETY_ABORT
```

Preserve diagnostics and STOP that measurement.

---

# 19. FINAL PERFORMANCE GATE

For:

```text
F10_RESULT = OPTIMIZATION_PASS
```

require all correctness gates and either:

Route A:

```text
Profile A aggregate >= +7%
Profile B aggregate >= +7%
```

or Route B:

```text
one profile >= +12%
other profile >= +3%
```

Also:

```text
at least 3/4 semantic cases in each profile improve >= 3%
no semantic case stable regression >3%
```

If H10B was created but final formal performance fails:

1. cleanly revert H10B;
2. retain H10A/E10 evidence;
3. final:

```text
F10_RESULT = AUDIT_ONLY_PASS
H10B_CREATED = true
H10B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
```

Do not retain a non-qualifying optimization.

---

# 20. F4–F9 EVIDENCE IMMUTABILITY

Preserve byte-identically:

```text
artifacts/f4_runtime_cost/**
artifacts/f5_semantic_attack_s3/**
artifacts/f6_target_directed_semantic/**
artifacts/f7_semantic_attack_query_reuse/**
artifacts/f8_push_terminal_check_dedup/**
artifacts/f9_terminal_legal_probe_reuse/**

docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
docs/architecture/F7_EVIDENCE.md
docs/architecture/F8_EVIDENCE.md
docs/architecture/F9_EVIDENCE.md

ADR-022
ADR-023
ADR-024
ADR-025
ADR-026
```

Create before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f10_source_index_lifetime/
```

---

# 21. REQUIRED F10 EVIDENCE

At minimum:

```text
artifacts/f10_source_index_lifetime/
    baseline.json
    corpus.json
    source_call_chain.json

    source_index_trace.jsonl
    lifetime_summary.json
    operation_breakdown.json
    exact_index_equivalence.json
    timing_attribution.json

    candidate_design.json
    optimization_gate.json

    legal_action_parity.json
    attack_check_parity.json
    s3_s4_parity.json
    terminal_history_tt_parity.json
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

If no candidate is authorized, candidate files may explicitly contain:

```text
NOT_RUN_NOT_AUTHORIZED
```

rather than fabricated data.

Create:

```text
docs/architecture/F10_EVIDENCE.md
docs/architecture/ADR-027-operation-local-semantic-source-index.md
```

ADR-027 must state:
- measured rebuild frequency;
- measured cost;
- chosen operation-local plumbing;
- whether production optimization was retained.

---

# 22. TESTS

Focused suites must include:

- F10 harness;
- semantic legal generation;
- source-index F5 regression;
- F9 terminal probe regression;
- F8 regression;
- F7 regression;
- F6 regression;
- F4 interruptibility;
- S3/S4;
- Standard Shogi semantic parity;
- F3 TT/history;
- repetition / continuous-check;
- search runtime rollback;
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

# 23. FORBIDDEN SCOPE

F10 must not modify:

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

evaluator
move ordering
PVS/LMR/null move

Native production search
UI
master
chat
AlphaSho
```

No global Position cache.
No source-index LRU.
No attack cache.
No terminal cache.
No bitboards.
No incremental attack map.
No F6/F7/F8/F9 revival.
No F11 work.

---

# 24. GIT / PROVENANCE

Audit-only:

```text
E9 baseline
  -> H10A audit/harness
  -> E10 audit closure
```

Optimization:

```text
E9 baseline
  -> H10A audit/harness
  -> H10B production source + tests
  -> E10 evidence closure
```

Final requirements:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

Record exact SHAs.

---

# 25. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
SOURCE_INDEX_EQUIVALENCE_FAILURE
LEGAL_ACTION_ORDER_PARITY_FAILURE
ATTACK_CHECK_PARITY_FAILURE
S3_PARITY_FAILURE
S4_PARITY_FAILURE
TERMINAL_HISTORY_TT_PARITY_FAILURE
SEARCH_PARITY_FAILURE
INTERRUPTIBILITY_FAILURE
ROLLBACK_ISOLATION_FAILURE
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
NATIVE_BUILD_FAILURE
RUNTIME_SAFETY_ABORT that invalidates required evidence
```

Do not repair unrelated architecture inside F10.

---

# 26. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Corpus
5. Source call-chain audit
6. Source-index lifetime diagnosis
7. Operation breakdown
8. Timing attribution
9. H10A provenance
10. Optimization authorization gate
11. Candidate design or rejection
12. Exact index equivalence
13. Legal-action parity
14. Attack/check parity
15. S3/S4 parity
16. Terminal/history/TT parity
17. Search parity
18. Interruptibility
19. Push/pop/rollback/sibling isolation
20. Performance
21. Tests
22. Evidence / manifest
23. Git
24. Deferred
25. Final verdict

Optimization success:

```text
F10_RESULT = OPTIMIZATION_PASS
OPERATION_LOCAL_SOURCE_INDEX = PASS
SOURCE_INDEX_EQUIVALENCE = PASS
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
```

Audit-only:

```text
F10_RESULT = AUDIT_ONLY_PASS
H10B_CREATED = false
reason = <frozen gate that failed>
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

Reverted candidate:

```text
F10_RESULT = AUDIT_ONLY_PASS
H10B_CREATED = true
H10B_RETAINED = false
reason = PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED
FULL_PYTEST = PASS
NATIVE_BUILD = PASS
```

---

# 27. FINAL STOP

F10 ends after E10 closure.

Do not begin F11.

Do not automatically move to Native.

Do not automatically change evaluator/search strength.

The next phase, if any, will be separately audited and authorized.

