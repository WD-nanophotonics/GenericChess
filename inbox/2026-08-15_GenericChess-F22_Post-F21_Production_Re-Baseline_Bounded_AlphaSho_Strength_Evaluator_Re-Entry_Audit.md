<!-- Gmail provenance
message_id: 1a0047545f0790f7
thread_id: 1a0047545f0790f7
subject: GenericChess — F22: Post-F21 Production Re-Baseline + Bounded AlphaSho Strength/Evaluator Re-Entry Audit
from: W D <icywoods.1@gmail.com>
to: icywoods.1@gmail.com
received: 2026-08-15T01:06:29-07:00
attachment: GenericChess_F22_Post_F21_Rebaseline_Strength_Audit.md
attachment_id: ANGjdJ_iK-KXWCqcMfKH404lhBpMAgmWJ5t09UlWX0DUe3tJ2EGg5TdYxDKRpRmkIa7VzRtiV_Jc1f_ssw10pG4vNgTeE2oYvDNPLSwdrup-qcB2PAWaQk2ayM8bOChsydrvGF1TANCmw9Fl_7lB8TgPXDHUr7PGxm5BJ55PGyIHTQBfdNLxQFhCc7TasrDnqvxTdAnISa4h6GewLuYk-CBZcRyARLlVNA1UqpS-gkOUyy11U_he4vbq7QCqX6y2q2ObLrtjA7-7oT6pKAO-okocC6S0cUkIzltmtKGqze_9j13xFXJJ-tfJxzW7__4CiUacuHzXP8iydaKKJ7GKn420kuRtN6mKICh9UdxgQzAeDJroSNotZgieUQ4GGrHAqN2NlCVVF5x8d1KIT6eA
attachment_bytes: 25240
fetched_at: 2026-08-15 Asia/Tokyo
processing_state: complete-authoritative-attachment
-->

# Gmail record — GenericChess F22

## Gmail body (complete)

Authoritative F22 task attached. Execute now after persisting the full Gmail body/attachment to the repository inbox. Work only on the locked sandbox baseline; do not modify master/chat; do not begin F23. F22 is audit/decision only: fresh post-F21 production runtime attribution plus bounded AlphaSho strength/evaluator re-entry. Do not restart any long formal rollout or full-game strength suite.

## Complete authoritative attachment

# GenericChess — F22: Post-F21 Production Re-Baseline + Bounded AlphaSho Strength/Evaluator Re-Entry Audit

## 0. AUTHORITATIVE TASK — EXECUTE NOW

This is the authoritative F22 task for `WD-nanophotonics/GenericChess`.

F21 closed as:

```text
F21_RESULT = PRODUCTION_ROUTING_PASS
NATIVE_LEGALITY_DEFAULT_ON = true
STANDARD_SHOGI_PROVIDER_PARITY = PASS
GENERIC_PROVIDER_PARITY = PASS
PROFILE_A_GAIN = 31.73%
PROFILE_B_GAIN = 33.25%
FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
F22_STARTED = false
```

F21 is a major runtime boundary closure. Native transient S0–S4 legality is now the default production semantic legal-action path, while Python remains authoritative for transition, terminal, repetition/history, runtime identity, TT, evaluator, ordering, qsearch, and search policy.

F22 MUST NOT immediately continue optimizing the old F11/F14 hotspot list. Those profiles are now stale because F21 removed a large fraction of Python semantic legality work.

F22 has two audit goals only:

1. produce a fresh **post-F21 production runtime attribution** using the default-on Native legality route;
2. resume the previously deferred **bounded AlphaSho strength/evaluator benchmark** without restarting any long game/formal rollout, and decide whether the next phase should target evaluator quality, search depth/heuristics, a newly proven runtime winner, or more strength evidence.

F22 is audit/decision only.

No production evaluator/search/runtime optimization may be retained in F22.

Successful result:

```text
F22_RESULT = AUDIT_PASS
```

A true correctness/provenance/build failure:

```text
F22_RESULT = BLOCKED
```

Do not begin F23.

---

# 1. GMAIL / INBOX PROTOCOL

Follow the repository-local GenericChess Gmail/inbox workflow.

Before work:

1. locate this F22 task using fuzzy GenericChess/F22 subject matching;
2. read the complete authoritative body/attachment;
3. persist it under top-level `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. execute immediately after persistence.

Do not execute from subject/snippet alone.

---

# 2. BASELINE HARD LOCK

Required refs:

```text
origin/sandbox =
f8cf111ccc985a58cfaac1c763080a8b06d4d4a1

origin/master =
4f1d03a308f5fd04a01bbd980c7411888ea1ed9d

origin/chat =
d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Hard assert all three.

If sandbox moved:

```text
BASELINE_MOVED
STOP
```

Work only on sandbox.

Do not modify master/chat.

Do not force-push.

---

# 3. F21 FROZEN PRODUCTION AUTHORITY

Treat F21 as closed and certified.

## 3.1 Production routing

Default:

```python
AlphaBetaPlayer(..., use_native_semantic_legality=True)
```

For executable semantic rules:

```text
Native semantic rules compile once per AlphaBetaPlayer
SearchPathRuntime receives a Core-neutral legal-binding provider
provider performs state-only pack + transient Native legality
provider decodes exact action identity
provider rebuilds exact Python binding
SearchPathRuntime caches actions/bindings normally
Python push/transition remains authoritative
```

## 3.2 Python authority remains

Do not change in F22:

```text
SearchPathRuntime transition
terminal
repetition
continuous-check history
RuntimeSearchKey / RuntimeHistoryContext
TT
Evaluator
ordering
qsearch
PVS
aspiration
root tactical
node/time/cancel behavior
```

## 3.3 F21 final build

F21 evidence reports final optimized Native build around:

```text
338,432 bytes
```

The earlier F20 3.38 MB discrepancy was resolved/provenance-audited in F21.

Record current fresh build size again, but do not hard-fail on exact byte equality if toolchain metadata differs.

---

# 4. HISTORICAL STRENGTH AUTHORITY — DO NOT ERASE IT

The AlphaSho benchmark line was not abandoned. It was deferred because runtime work and an overlong formal game runner dominated execution time.

Freeze the known historical conclusions from the Round5/R1.4 evidence if the exact source artifacts are present:

```text
10 frozen Standard Shogi positions
20 LOW/HIGH move records
agreement = 2
move disagreement = 8
legal failures = 0
budget failures = 0

C LOW 0.5 s correctness = 20/20
C HIGH 1.0 s correctness = 12/12

paired score historically = 0.0
```

The old ~189-minute formal rollout is permanently sealed:

```text
ABORTED_FOR_RUNTIME
```

F22 MUST NOT restart it.

Do not restart any B/B2 64-ply or multi-hour match runner.

If historical source artifacts differ from the summary above, the repository/local preserved artifact is authoritative; record the exact discrepancy rather than rewriting history.

---

# 5. ALPHASHO ACCESS POLICY

AlphaSho is a separate mature Shogi engine/control.

F22 may access the existing locally configured AlphaSho checkout/artifacts **read-only** for benchmark/oracle purposes.

F22 MUST NOT:

```text
modify AlphaSho source
commit to AlphaSho
push AlphaSho
train AlphaSho
change its checkpoint
change its search settings merely to improve GenericChess results
```

Preferred order of authority:

1. reuse frozen Round5 AlphaSho oracle outputs if preserved;
2. if a local AlphaSho adapter/checkpoint is already available, revalidate only the bounded required positions;
3. do not clone/download/reconfigure a new external AlphaSho environment merely to satisfy F22.

If neither frozen reference outputs nor existing local AlphaSho access is available:

```text
ALPHASHO_REFERENCE_UNAVAILABLE
```

Strength diagnosis becomes limited/inconclusive, but post-F21 runtime rebaseline may continue.

Do not fabricate oracle moves.

---

# 6. PHASE STRUCTURE

Use:

```text
E21 baseline
  -> H22A post-F21 runtime rebaseline
  -> H22B bounded strength/evaluator audit
  -> E22 evidence/decision closure
```

No production candidate phase exists in F22.

Any temporary instrumentation must be removed before E22.

---

# 7. H22A — FRESH PRODUCTION PERFORMANCE REBASELINE

The measured production path must be:

```text
use_native_semantic_legality = true
```

Do not use forced-Python legality as the new baseline.

Forced-Python may be measured only as a historical/control comparison.

Use the same four frozen Semantic Standard Shogi prefixes used in F20/F21.

---

# 8. FROZEN PROFILE A / B

## Profile A

```text
TT = on
ordering = off
qsearch max depth = 0
root tactical = off
max_depth = 2
max_nodes = 512
fresh TT per measured run
no wall-clock limit
Native semantic legality = default ON
```

## Profile B

Use current production/default AlphaBeta tuning with:

```text
max_nodes = 256
deterministic node budget
no wall-clock limit
Native semantic legality = default ON
```

For each of the four semantic cases:

```text
1 warm-up
5 formal measured runs
```

No trace/cProfile in formal timing.

---

# 9. POST-F21 ATTRIBUTION — REQUIRED

Run separate non-formal attribution using:

```text
AuditRecorder category timing
cProfile
structural counters
```

At minimum distinguish:

```text
Native legality provider total
  payload pack
  Native transient kernel
  decode + binding rebuild

Python transition / push
Python semantic component-diff runtime hash
runtime repetition/snapshot/history context
terminal computation
_gave_check / check work outside legality
TT key/probe/store
Evaluator total
  material/hand
  dynamic mobility
  anchor escape
  check penalties
ordering
qsearch
root tactical
checkpoint/budget dispatch
misc Python overhead
```

Do not double-count nested inclusive time as exclusive attribution.

For cProfile report both:

```text
cumulative/inclusive
self/exclusive
```

for the top functions.

---

# 10. POST-F21 SINGLE-WINNER RULE

A new runtime optimization is eligible for the next phase only if H22A identifies exactly one narrow winner satisfying all:

```text
>= 15% of post-F21 aggregate inclusive wall time in both Profile A and B
clear non-overlapping root cause
local semantics-preserving implementation boundary
credible projected end-to-end gain >= 8% in both A and B
not a previously rejected F6–F9/F15–F19 architecture
```

Previously rejected approaches remain rejected unless F21 fundamentally changed the relevant premise:

```text
F6 target-directed geometry
F7 generic attack memoization
F8 known_checked forwarding alone
F9 terminal legal continuation
F15 immutable Native mirror
F16 full-position undo runtime
F17 exact-history delta runtime
F18 same-architecture SHA micro-optimization
fine-grained Native attack routing
```

If no unique winner exists:

```text
POST_F21_RUNTIME_SINGLE_WINNER = false
```

Do not manufacture one.

---

# 11. NATIVE LEGALITY POST-PRODUCTION HEALTH CHECK

Record current production provider metrics on the four frozen cases:

```text
native_legality_calls
native_legality_actions
native_legality_seconds
payload_seconds
decode_binding_seconds
fallbacks
operational_failures
```

Require:

```text
fallbacks = 0
operational_failures = 0
```

for the certified Standard Shogi corpus.

Reconfirm search parity with forced-Python legality on a focused subset.

This is not another F21 recertification; it is a guardrail for the new baseline.

---

# 12. H22B — BOUNDED STRENGTH RE-ENTRY

The strength audit must use **positions**, not long full games.

Primary corpus:

```text
exact frozen Round5 Standard Shogi position set
prefer the historical 10 positions used for LOW/HIGH move agreement
```

Do not silently replace the corpus with easier/new positions.

If the old corpus is missing, stop the AlphaSho subtest with:

```text
ROUND5_POSITION_CORPUS_MISSING
```

and record provenance failure.

---

# 13. CURRENT GENERIC BASELINE ON THE FROZEN STRENGTH CORPUS

For each frozen position run current production GenericChess with Native legality default ON.

Run both:

## 13.1 Historical-compatible wall-time budgets

Reuse the exact preserved LOW/HIGH wall-time profiles if available.

At minimum, where they correspond to the frozen historical C profiles:

```text
LOW  = 0.5 s
HIGH = 1.0 s
```

Do not invent a different meaning for LOW/HIGH if the archived profile says otherwise.

Record:

```text
move
score
PV
completed depth
nodes
qnodes
termination reason
fallback
elapsed
```

## 13.2 Deterministic node ladder

Run:

```text
128
256
512
1024
2048
```

nodes where each position stays within runtime limits.

If 2048 exceeds the per-process cap, stop at the highest safe level and record it.

Purpose:

```text
determine whether the chosen move converges as search budget increases
```

No production setting is changed.

---

# 14. NATIVE-ON / NATIVE-OFF CONTROL

At fixed deterministic node counts:

```text
Native legality ON
vs
Native legality OFF
```

must produce exact:

```text
move
score
PV
nodes/qnodes
search logical stats
```

for the frozen strength positions.

This proves F21 changed runtime, not node-budget chess semantics.

At fixed wall time, record the additional depth/nodes obtained by Native ON.

Do not interpret fixed-wall-time move differences as correctness differences.

---

# 15. ALPHASHO MOVE-ORACLE COMPARISON

For every frozen position with an authoritative AlphaSho reference move, compare:

```text
Generic LOW move
Generic HIGH move
Generic node-ladder moves
AlphaSho reference move
```

Record:

```text
exact agreement
first node budget at which Generic matches AlphaSho, if any
whether Generic move stabilizes to a non-AlphaSho move
whether deeper Generic search oscillates
```

Summary metrics:

```text
LOW agreement
HIGH agreement
agreement by node budget
persistent disagreement count
resolved-by-depth count
unstable count
```

No claim that AlphaSho's move is mathematical ground truth.

It is the frozen mature-engine control/oracle for diagnosis.

---

# 16. SEARCH-LIMITED VS EVALUATOR-LIMITED CLASSIFICATION

For each historical disagreement classify:

## SEARCH_DEPTH_LIMITED

if increasing Generic search budget eventually reaches and then stably retains the AlphaSho move.

## EVALUATOR_OR_HORIZON_PERSISTENT

if Generic reaches a stable move different from AlphaSho across the highest safe node budgets.

## UNSTABLE

if the move continues to oscillate with search budget.

## REFERENCE_INVALID_OR_UNAVAILABLE

if AlphaSho reference cannot be verified.

This is diagnostic classification only.

---

# 17. CURRENT EVALUATOR AUTHORITY AUDIT

Audit the exact current evaluator architecture.

Current known baseline includes:

```text
RuleSetEvaluationProfile
movement-capability-derived board values
hand_weight-derived hand values
promotion gain

dynamic mobility
anchor escape
check penalty
promotion potential
```

For semantic Standard Shogi, explicitly determine:

```text
which evaluator inputs come from semantic support/IR
which still come from _legacy_compiled / movement atoms
which Standard Shogi legality concepts are invisible to generic-v1 valuation
```

Do not call `_legacy_compiled` an execution dependency if it is only evaluation/inspection.

But document whether the evaluator is semantically shallower than the legal engine.

---

# 18. PIECE-VALUE PROFILE AUDIT

For Standard Shogi output the complete current Generic profile:

```text
type_id
board value
hand value
promotion gain
raw capability score
coverage
reachability/path metrics if available
drop freedom/drop mobility
```

This is descriptive evidence.

Do not replace values with hand-authored Shogi values in F22.

Do not change `EvaluationConfig`.

---

# 19. EVALUATOR COMPONENT DECOMPOSITION

For each frozen strength position and at least:

```text
AlphaSho reference move
Generic LOW move
Generic HIGH move
```

where distinct and legal, build the authoritative Python child and compute an audit-only component decomposition of the current evaluator:

```text
board material
hand material
promotion potential
mobility
anchor escape
check penalty
TOTAL
```

The component sum must exactly equal current `Evaluator.evaluate(child)` under the same side-to-move convention.

Do not modify production Evaluator solely to expose this; use an audit helper if possible.

Require:

```text
component_sum_mismatch = 0
```

---

# 20. ONE-PLY REFERENCE-MOVE RANK

For every frozen position:

1. enumerate current exact legal actions;
2. apply each through the existing Python authoritative transition;
3. evaluate each child with the current evaluator;
4. rank from the root actor's perspective;
5. record the rank of:
   - AlphaSho reference move;
   - current Generic selected move.

This is **not** a replacement for search.

It is an evaluator diagnostic.

Record:

```text
reference move rank
reference move percentile
score gap to evaluator-best move
Generic move rank
```

If branching is too large, this still remains bounded because the frozen corpus is only ~10 positions.

---

# 21. OPTIONAL SHALLOW SEARCH EVALUATOR SENSITIVITY

Run only if it fits the runtime cap.

Compare root move rankings at:

```text
depth 1
depth 2 or a small deterministic node budget
```

Purpose:

```text
separate pure leaf evaluation from shallow tactical effects
```

Do not add new heuristics.

---

# 22. NO FULL-GAME STRENGTH RUN IN F22

F22 MUST NOT run:

```text
64-ply B2 games
120-ply paired suite against AlphaSho
189-minute formal rollout
large self-play tournament
5000/20000 evaluator calibration
```

The goal is a bounded diagnosis, not an Elo estimate.

---

# 23. STRENGTH DIAGNOSIS GATES

Compute:

```text
A = historical/reference move agreement at HIGH
B = highest-safe-node agreement
C = resolved-by-depth fraction among initial disagreements
D = persistent disagreement fraction
E = fraction of persistent disagreements where AlphaSho move is outside current evaluator top-3 one-ply ranking
```

Do not fabricate metrics if reference data are missing.

---

# 24. SELECT EXACTLY ONE NEXT BOUNDARY

Choose exactly one:

```text
RULE_DERIVED_EVALUATOR_V2
SEARCH_DEPTH_HEURISTIC_PHASE
POST_F21_RUNTIME_SINGLE_WINNER
STRENGTH_BENCHMARK_EXPANSION
```

## 24.1 Select `RULE_DERIVED_EVALUATOR_V2` if

all of the following hold:

```text
AlphaSho reference corpus is valid
persistent disagreements remain material at the highest safe node budget
>= 50% of the initial disagreements remain persistent
and
>= 50% of persistent disagreements place the AlphaSho move outside current evaluator top-3 at one ply
```

AND the component/profile audit identifies a coherent generic evaluator deficiency rather than one game-specific special case.

The future evaluator must remain generic/rule-derived; no hard-coded Shogi piece tables.

## 24.2 Select `SEARCH_DEPTH_HEURISTIC_PHASE` if

```text
>= 50% of initial disagreements are resolved by deeper Generic search
```

or agreement improves by at least 30 percentage points from low to the highest safe node budget, while evaluator reference-move ranking is generally reasonable.

This indicates runtime/search horizon remains the dominant strength limiter.

## 24.3 Select `POST_F21_RUNTIME_SINGLE_WINNER` only if

Section 10 identifies exactly one new runtime hotspot meeting its strict gate AND strength evidence does not more strongly justify evaluator/search work.

## 24.4 Select `STRENGTH_BENCHMARK_EXPANSION` if

10 positions are statistically/diagnostically inconclusive and neither evaluator nor search-depth classification reaches the gates above.

Do not implement the selected next boundary in F22.

---

# 25. IF ALPHASHO REFERENCE IS UNAVAILABLE

If:

```text
ALPHASHO_REFERENCE_UNAVAILABLE
```

or:

```text
ROUND5_POSITION_CORPUS_MISSING
```

then F22 may still close runtime rebaseline, but must not select `RULE_DERIVED_EVALUATOR_V2` solely from intuition.

Allowed selection becomes:

```text
POST_F21_RUNTIME_SINGLE_WINNER
or
STRENGTH_BENCHMARK_EXPANSION
```

unless independent preserved reference evidence fully supports another decision.

---

# 26. PRODUCTION CODE POLICY

F22 is audit-only.

Do NOT retain changes to:

```text
Evaluator
EvaluationConfig
RuleSetEvaluationProfile
AlphaBeta search logic
SearchPathRuntime
Native legality provider
Native C runtime
TT
qsearch
ordering
```

Allowed retained files:

```text
audit scripts/harnesses
tests only if they encode permanent non-production regression value
evidence
docs/ADR
inbox record
```

Temporary instrumentation in production modules must be reverted before E22.

---

# 27. F21 PRODUCTION REGRESSION GATE

Before final closure re-run focused F21 production tests:

```text
Native legality default-on
forced Python fallback
unsupported semantic fallback
operational fallback
84-state Standard Shogi parity
10-case generic parity
binding/child parity
cancel/root fallback
repeated-search TT/history
```

No regression.

---

# 28. F13/F14/F19/F20 REGRESSION

Re-run the bounded focused semantic Native regressions needed to prove the audit harness did not disturb prior behavior:

```text
action_delivers_check
uchifuzume
S4 conjunction
attack/check differential
history-independent transient legality
zero child key/history in Native legality
exact-history public Native paths
```

All PASS.

---

# 29. FULL TEST / BUILD

Run:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then:

```text
python scripts/build_native_zig.py
```

Require PASS.

Record final binary size and SHA-256.

---

# 30. RUNTIME SAFETY

Hard limits:

```text
single focused/differential subprocess <= 60 s
single profiler subprocess <= 120 s
single AlphaSho oracle call/process <= 60 s
single Generic position budget <= 5 s
```

Total benchmark design must remain bounded.

No multi-hour run.

If a runner exceeds the cap:

```text
RUNTIME_SAFETY_ABORT
```

terminate it, preserve partial evidence, and do not automatically restart it.

---

# 31. F4–F21 EVIDENCE IMMUTABILITY

Preserve byte-identically all previous evidence and architecture docs:

```text
artifacts/f4_runtime_cost/**
...
artifacts/f21_native_legality_routing/**

docs/architecture/F4_EVIDENCE.md
...
docs/architecture/F21_EVIDENCE.md

ADR-022 through ADR-038
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f22_post_f21_rebaseline_strength/
```

---

# 32. REQUIRED F22 EVIDENCE

At minimum:

```text
artifacts/f22_post_f21_rebaseline_strength/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    f21_health_check.json

    profile_a_formal.jsonl
    profile_b_formal.jsonl
    post_f21_formal_summary.json

    audit_recorder_attribution.json
    cprofile_a.txt
    cprofile_b.txt
    structural_counts.json
    post_f21_hotspot_ranking.json
    runtime_single_winner_gate.json

    round5_provenance.json
    round5_frozen_positions.json
    alphasho_reference_provenance.json

    generic_walltime_low_high.jsonl
    generic_node_ladder.jsonl
    native_on_off_node_parity.json
    native_on_off_walltime_capacity.json

    alphasho_move_agreement.json
    disagreement_classification.json

    evaluator_architecture.json
    standard_shogi_piece_value_profile.json
    evaluator_component_rows.jsonl
    evaluator_component_summary.json
    one_ply_reference_rank.json
    shallow_sensitivity.json

    strength_diagnosis_metrics.json
    selected_next_boundary.json

    f21_regression.txt
    semantic_native_regression.txt

    old_evidence_before.sha256
    old_evidence_after.sha256

    full_pytest.txt
    final_native_build.txt
    final_verdict.json
    manifest.json
```

For unavailable/not-authorized subtests, write explicit machine-readable:

```text
NOT_RUN_<reason>
```

Do not fabricate empty PASS files.

Create:

```text
docs/architecture/F22_EVIDENCE.md
docs/architecture/ADR-039-post-f21-runtime-strength-rebaseline.md
```

ADR-039 must document:

- post-F21 production runtime attribution;
- whether a unique runtime winner remains;
- historical Round5 strength provenance;
- bounded AlphaSho move-oracle methodology;
- node-budget convergence behavior;
- current generic evaluator architecture and semantic limitations;
- evaluator component/reference-move ranking evidence;
- selected next boundary and why alternatives were rejected.

---

# 33. GIT / PROVENANCE

Expected:

```text
E21 baseline
  -> H22A audit harness/rebaseline
  -> H22B strength/evaluator audit
  -> E22 evidence/docs closure
```

No retained production behavior change.

Record exact commit SHAs.

Final:

```text
HEAD == origin/sandbox
worktree clean
origin/master unchanged
origin/chat unchanged
no force push
```

If push is blocked solely because the F22 inbox contains this authorized project-task Gmail record, stop before push and request the same narrowly-scoped export authorization used in F20/F21.

Do not omit inbox provenance.

---

# 34. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
OLD_EVIDENCE_MUTATED
F21_PRODUCTION_REGRESSION
SEARCH_LOGICAL_PARITY_FAILURE
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

These strength-provenance problems do not block runtime rebaseline but limit the final decision:

```text
ALPHASHO_REFERENCE_UNAVAILABLE
ROUND5_POSITION_CORPUS_MISSING
ROUND5_REFERENCE_PROVENANCE_MISMATCH
```

Never substitute guessed reference data.

---

# 35. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial Native build
5. F21 production health check
6. Profile A post-F21 baseline
7. Profile B post-F21 baseline
8. AuditRecorder attribution
9. cProfile attribution
10. Structural counts
11. Post-F21 hotspot ranking
12. Runtime single-winner gate
13. Round5 historical provenance
14. AlphaSho reference provenance
15. Frozen strength corpus
16. Current LOW/HIGH Generic results
17. Deterministic node-ladder results
18. Native-on/native-off fixed-node parity
19. Native-on wall-time capacity gain
20. AlphaSho move agreement
21. Disagreement classification
22. Current evaluator architecture
23. Standard Shogi piece-value profile
24. Evaluator component decomposition
25. One-ply AlphaSho reference-move rank
26. Shallow search sensitivity
27. Strength diagnosis metrics
28. Selected next boundary
29. F21 / semantic Native regression
30. Full tests / final build
31. Evidence / manifest
32. Git / push status
33. Deferred
34. Final verdict

Successful result:

```text
F22_RESULT = AUDIT_PASS

F21_PRODUCTION_HEALTH = PASS
POST_F21_RUNTIME_REBASELINE = PASS
POST_F21_RUNTIME_SINGLE_WINNER = <true|false>

ALPHASHO_REFERENCE = <PASS|UNAVAILABLE>
ROUND5_CORPUS = <PASS|MISSING>
MOVE_AGREEMENT_LOW = <fraction|UNAVAILABLE>
MOVE_AGREEMENT_HIGH = <fraction|UNAVAILABLE>
MOVE_AGREEMENT_MAX_NODE = <fraction|UNAVAILABLE>
PERSISTENT_DISAGREEMENTS = <count|UNAVAILABLE>

EVALUATOR_COMPONENT_PARITY = PASS

SELECTED_NEXT_BOUNDARY =
<RULE_DERIVED_EVALUATOR_V2 |
 SEARCH_DEPTH_HEURISTIC_PHASE |
 POST_F21_RUNTIME_SINGLE_WINNER |
 STRENGTH_BENCHMARK_EXPANSION>

PRODUCTION_BEHAVIOR_CHANGED = false
FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
F23_STARTED = false
```

Blocked result:

```text
F22_RESULT = BLOCKED
reason = <exact stop condition>
PRODUCTION_BEHAVIOR_CHANGED = false
FULL_PYTEST = <PASS|FAIL>
FINAL_NATIVE_BUILD = <PASS|FAIL>
F23_STARTED = false
```

---

# 36. FINAL STOP

F22 ends after E22 closure and permitted sandbox push state.

Do not begin F23.

Do not implement a new evaluator, heuristic, or runtime optimization in F22.

The selected next phase must be separately reviewed and authorized.

## Integrity

- Body characters: 398
- Attachment characters: 25220
- Body/attachment exact match: no (body is the authoritative pointer; attachment is the full task)

