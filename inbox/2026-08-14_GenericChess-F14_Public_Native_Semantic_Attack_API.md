<!-- Gmail provenance -->
<!-- message_id: 19ffe41faa97edcd -->
<!-- thread_id: 19ffe41faa97edcd -->
<!-- subject: GenericChess — F14: Public Native Semantic Attack/Check API Certification + Integration Boundary Decision -->
<!-- from: W D <icywoods.1@gmail.com> -->
<!-- attachment: GenericChess_F14_Public_Native_Semantic_Attack_API.md -->
<!-- fetched: 2026-08-14 -->
<!-- processing: authoritative attachment persisted before implementation -->
# GenericChess — F14: Public Native Semantic Attack/Check API Certification + Integration Boundary Decision

## 0. AUTHORITATIVE TASK

This is the authoritative F14 task for `WD-nanophotonics/GenericChess`.

F13 closed the last known Standard Shogi semantic compilation gap:

```text
F13_RESULT = CAPABILITY_CLOSURE_PASS
STANDARD_SHOGI_NATIVE_EXECUTABLE = true
FULL_NATIVE_SEARCH_READY = false
```

The current Native semantic runtime already contains exact internal semantic attack/check machinery:

```text
semantic_attacked_by(...)
gc_semantic_runtime_in_check(...)
```

but no certified public Python-facing semantic attack/check API exists.

F14 has two goals only:

1. expose and certify a fail-closed Native semantic `is_square_attacked` / `in_check` API over an **already-packed Native semantic position capsule**;
2. measure the real packed-capsule call cost and decide the one correct next integration boundary.

F14 MUST NOT route production Python `SemanticEngine` or AlphaBeta search through Native.

Valid successful result:

```text
F14_RESULT = API_CERTIFICATION_PASS
```

A true correctness/build failure is:

```text
F14_RESULT = BLOCKED
```

Performance may determine the next boundary, but poor speed alone does not invalidate a correct API certification.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before work:

1. locate this task using GenericChess/Gmail fuzzy subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. only then begin implementation/audit.

Do not execute from the subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
9b745662f13849e50f37c2391da9d039235505af

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

# 3. F12/F13 FROZEN AUTHORITY

Treat the following as closed.

## F12

Established:

```text
Python-local runtime headroom = LIMITED
dominant Python-local hotspot = semantic attack/check

public Native semantic attack/check API = absent
internal Native semantic attack/check = implemented but not certified
Python -> Native full position pack is expensive relative to cheap toy attack calls
production Native semantic search = not ready
```

F12 representative boundary evidence included approximately:

```text
toy Python semantic attack query ~10 us
Python Position -> Native semantic pack ~1.09 ms
```

Therefore F14 MUST distinguish:

```text
kernel/call speed on an already-packed Native position
```

from:

```text
end-to-end Python Position -> pack -> Native attack call
```

Never conflate them.

## F13

Closed:

```text
action_delivers_check = native postcondition code 2
Standard Shogi native_executable = true
S4 conjunction parity = PASS
uchifuzume parity = PASS
```

Do not change F13 semantics.

---

# 4. PYTHON ATTACK/CHECK AUTHORITY — FREEZE EXACT CONTRACT

The authoritative behavior is:

```text
SemanticEngine.is_square_attacked(...)
SemanticEngine.in_check(...)
```

Native must match exactly.

## 4.1 `is_square_attacked`

Freeze these semantics:

1. ruleset fingerprint must match;
2. input `square` is a board index;
3. `by_owner` is exactly 0 or 1;
4. only semantic patterns with:

```text
pattern.target.kind == "target_enemy"
```

participate;
5. actor current type must belong to pattern type IDs;
6. geometry must:
   - exist;
   - not be `drop`;
   - respect exact `geometry.atom_source` type compatibility;
7. geometry uses owner-relative compiled path semantics;
8. target must equal queried square;
9. exact path predicates are evaluated;
10. exact state guards are evaluated;
11. exact slot guards are evaluated;
12. attacker-relative SELF/OPPONENT perspective is used;
13. S3 own-anchor safety is NOT recursively evaluated;
14. S4 postconditions are NOT recursively evaluated;
15. S4-bearing capture patterns still contribute their S0/S1 pseudo-attack projection;
16. first matching exact binding returns true;
17. otherwise false.

## 4.2 `in_check`

Freeze:

```text
resolve side's own anchor
if no anchor -> false
else query opponent pseudo-attack on anchor
```

Use current Python behavior as exact oracle.

---

# 5. F14 PHASE STRUCTURE

Use three states:

## H14A — HARNESS / INTERNAL BASELINE

Before adding public API:

- add audit/differential harness;
- prove baseline public API is absent;
- call existing internal/test-only mechanisms only where already available;
- freeze Python attack/check outputs for all certification fixtures;
- record current internal C symbols and wrapper surface.

H14A MUST NOT modify production Native API.

Commit and push H14A.

Record exact SHA.

## H14B — PUBLIC API IMPLEMENTATION

Add exactly one production API family:

```text
Native semantic is_square_attacked
Native semantic in_check
```

No search integration.

Commit and push H14B before final evidence.

## E14 — CERTIFICATION CLOSURE

Run full differential, performance boundary analysis, tests, builds, and produce docs/evidence.

Push final E14.

---

# 6. ALLOWED PRODUCTION SURFACE

Preferred Python API:

```python
generic_chess.native.semantic.is_square_attacked(
    native_rules,
    position,
    square: int,
    by_owner: int,
) -> bool

generic_chess.native.semantic.in_check(
    native_rules,
    position,
    side: int,
) -> bool
```

`position` is an already-packed Native semantic position capsule.

Preferred extension entry points:

```text
semantic_is_square_attacked(...)
semantic_in_check(...)
```

Use existing exact `GCSemanticRules` + `GCSemanticPosition`.

Do not expose legacy movement-atom attack as semantic authority.

---

# 7. FAIL-CLOSED INPUT CONTRACT

The public API must reject invalid use.

At minimum:

```text
native extension unavailable
invalid/non-semantic rules capsule
invalid/non-semantic position capsule
rules/position fingerprint mismatch
square < 0
square >= board_squares
owner/side not in {0,1}
malformed capsule
```

Do not silently return false for structurally invalid API inputs when the existing Native Python boundary normally raises.

Internal semantic truth may return false for a valid position with no anchor.

Preserve consistent project Native exception style.

---

# 8. CAPABILITY CONTRACT

Do NOT overload or weaken:

```text
NativeSemanticCompiledRules.native_executable
```

F14 public attack/check API is certified only for rulesets whose current Native semantic compile path has succeeded.

At minimum require:

```text
native_rules.native_executable == true
```

for certification fixtures.

If current architecture naturally allows calling the API on another valid compiled semantic capsule that is not full-executable, do NOT claim support unless separately proven.

No partial-capability redesign in F14.

---

# 9. IMPLEMENTATION RULES

Reuse existing exact Native semantic runtime.

Preferred:

```text
semantic_attacked_by(...)
gc_semantic_runtime_in_check(...)
```

If `semantic_attacked_by` must become non-static or gain a thin public runtime wrapper, do the smallest change.

Do NOT:

```text
duplicate semantic attack logic in native_module.c
use legacy native_attack.c
introduce attack cache
introduce attack map
introduce bitboards
change source iteration semantics
change path/guard behavior
```

There must remain one Native semantic attack authority.

---

# 10. STANDARD SHOGI CERTIFICATION CORPUS

Hard assert fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

Use the same four frozen reachable Standard Shogi semantic prefixes from F4–F13.

For every prefix:

```text
81 squares × 2 attacking owners = 162 attack queries
```

Total minimum:

```text
648 exact attack queries
```

Compare Python vs Native:

```text
bool result
```

Require:

```text
attack mismatches = 0
```

Also for every prefix compare:

```text
in_check(side=0)
in_check(side=1)
```

Require:

```text
check mismatches = 0
```

---

# 11. CURATED ATTACK/CHECK DIFFERENTIAL

Retain/add deterministic generic semantic fixtures covering at minimum:

```text
leap attack
ray attack
ray blocker
long ray
min_steps
owner-relative geometry

path_clear
path_count_eq
path_count_range
path_first_blocker_owner
path_last_blocker_owner

state guard:
  owner self/opponent/any
  action_base/action_current/explicit type
  promoted selector
  same_file
  same_rank
  exact
  adjacent
  path_between
  zone

slot guard
aux square/bool where applicable

promotion current type
capture target
friendly target must not count
empty target must not count
drop geometry must not count as board pseudo-attack

S4-bearing capture pattern contributes S0/S1 projection
S3 own-anchor safety is ignored by pseudo-attack

side has anchor
side has no anchor
multiple non-anchor pieces
```

Require exact Python/Native parity.

---

# 12. F13 ACTION-WITNESS REGRESSION

Because F13 `action_delivers_check` depends on related semantic attack primitives, rerun its witness suite.

Require:

```text
direct actor check = PASS
discovered check distinction = PASS
checking drop = PASS
non-checking drop = PASS
promotion current-type witness = PASS
path/state/slot witness = PASS
S4 projection witness = PASS
uchifuzume = PASS
```

F14 public attack API must not alter F13 actor-witness semantics.

---

# 13. CANDIDATE/GUARDED/MAKE NO-REGRESSION

For the four Standard Shogi prefixes compare before/after H14B:

```text
candidate action tuple/order
guarded action tuple/order
make_checked child snapshot
position key
terminal
```

Require zero mismatch.

The API addition must not change legal semantic execution.

---

# 14. EXISTING 10-CASE NATIVE CORPUS

Re-run:

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

Require:

```text
native_executable = true
position runtime = PASS
candidate/guarded = PASS
make/unmake = PASS
terminal = PASS
fixed-depth smoke = PASS
```

---

# 15. PUBLIC API DIFFERENTIAL SHAPE

For every recorded query preserve enough evidence to identify:

```text
case_id
position fingerprint
position key
square
by_owner
python_result
native_result
```

For `in_check`:

```text
side
python_anchor location if available
python_result
native_result
```

Do not store only aggregate counts.

Machine-readable row-level evidence is required.

---

# 16. PERFORMANCE: TWO DISTINCT BENCHMARKS

F14 MUST run both benchmark classes and keep them separate.

## 16.1 PACKED-CAPSULE KERNEL/CALL BENCHMARK

Native position is packed ONCE before timing.

Then measure repeated:

```text
native semantic is_square_attacked(native_position)
native semantic in_check(native_position)
```

Compare against Python SemanticEngine on the corresponding immutable Python Position.

Use Standard Shogi prefixes, not only toy fixtures.

At minimum:

```text
warm-up >= 50
measured repetitions >= 1000 per cheap query family
median
p90
min/max
```

For attack, use a fixed deterministic set containing both true and false queries.

Report:

```text
python_us/query
native_us/query
speedup
```

This measures:

```text
already-packed Native call viability
```

only.

## 16.2 END-TO-END PER-CALL PACK BENCHMARK

Measure:

```text
Python Position
-> pack_position
-> one Native attack/check query
```

Compare with one Python attack/check query.

Report separately:

```text
pack_us
native_call_us
total_us
python_us
```

Do not claim this is the intended final integration design.

Its purpose is to prove/disprove that per-query repacking is viable.

---

# 17. BREAK-EVEN MODEL

Using F12/F14 measurements, compute a simple break-even model.

For an already-packed/mirrored Native position:

```text
N = attack/check queries performed before the position changes
```

Estimate:

```text
Python total(N)
Native pack-once + N*native_call
```

Solve approximate break-even `N`.

Also use F11 structural counts to estimate realistic:

```text
attack/check queries per searched position / runtime frame
```

if available.

Do not fabricate missing counts.

State assumptions explicitly.

---

# 18. PRODUCTION INTEGRATION FEASIBILITY

After API certification, classify these possible future designs:

## A — PER-QUERY PACK

```text
Python Position -> pack -> native attack
```

Expected likely result:

```text
REJECT
```

unless F14 measurements unexpectedly prove otherwise.

## B — MIRRORED NATIVE POSITION FRAME

```text
Python SearchPathRuntime remains authority
+
each runtime frame owns synchronized Native semantic position
+
attack/check calls use existing capsule
```

Analyze:

```text
root pack
child make/unmake/sync
push/pop
exception rollback
sibling isolation
history/aux synchronization
fingerprint
cancellation/checkpoint
```

## C — NATIVE LEGALITY KERNEL

Move more of S0-S4 legality into Native per frame.

## D — FULL NATIVE SEMANTIC SEARCH

Still outside F14.

For each classify:

```text
boundary overhead
semantic risk
implementation size
expected benefit
```

---

# 19. SELECT EXACTLY ONE NEXT BOUNDARY

F14 must select exactly one:

```text
NATIVE_ATTACK_INTEGRATION_DIRECT
NATIVE_MIRRORED_POSITION_FRAME
NATIVE_LEGALITY_KERNEL
NATIVE_POSITION_RUNTIME
FULL_NATIVE_SEMANTIC_SEARCH
SEARCH_STRENGTH_EVALUATOR_PHASE
```

Selection rules:

## Select `NATIVE_ATTACK_INTEGRATION_DIRECT` only if

a production-safe implementation can avoid repeated full packing **without** first creating a new mirrored/frame ownership layer.

Do not choose this if the only implementation is per-query pack.

## Select `NATIVE_MIRRORED_POSITION_FRAME` if

Native packed-capsule attack/check is materially faster, but Python→Native pack cost makes per-query integration uneconomic.

## Select `NATIVE_LEGALITY_KERNEL` if

attack/check alone is not enough, but existing Native guarded/make machinery plus boundary costs show a broader per-position legality call is the smallest sensible unit.

## Select `SEARCH_STRENGTH_EVALUATOR_PHASE` if

Native semantic attack/check provides no material packed-capsule speed benefit and no runtime boundary is currently justified.

Do not select full Native search simply because it has the highest theoretical ceiling.

Do not implement the selected next boundary in F14.

---

# 20. PERFORMANCE DECISION THRESHOLDS

For decision purposes only:

### Material packed-capsule Native attack speed

Consider materially faster if aggregate Standard Shogi:

```text
native attack/check call speedup >= 2.0x
```

and no query class shows pathological stable regression >25%.

This is not an API correctness gate.

### Direct per-query pack viability

Consider viable only if:

```text
pack + native query <= 0.8 × Python query
```

aggregate.

Otherwise:

```text
PER_QUERY_PACK = REJECT
```

### Mirrored-frame motivation

If:

```text
packed native >= 2x faster
AND
per-query pack rejected
```

then `NATIVE_MIRRORED_POSITION_FRAME` should be strongly preferred unless a more local zero-pack integration already exists.

---

# 21. INTERRUPTIBILITY CONTRACT

F14 API calls are synchronous atomic native calls.

Measure worst-case observed call latency across certification corpus.

Require no individual semantic attack/check call to become a practical long-running uninterruptible region.

Record:

```text
median
p90
p99/max if feasible
```

Future production integration must still preserve bounded cancellation/deadline observation between Native calls.

Do NOT add callback checkpoints inside the C attack loop in F14 unless required by an actual >10ms single-call latency witness.

If such a witness exists:

```text
NATIVE_ATTACK_INTERRUPTIBILITY_RISK
```

record it and defer integration.

---

# 22. GIL / THREADING AUDIT

Record whether the extension attack/check entrypoint:

```text
holds GIL
releases GIL
```

Do not change GIL policy in F14 unless required for correctness.

This is an integration evidence item only.

No threading architecture work.

---

# 23. VERSION / IDENTITY INVARIANTS

Must remain unchanged:

```text
Standard Shogi fingerprint
Semantic IR version = 2
SEMANTIC_PAYLOAD_VERSION = 2
NATIVE_SCHEMA_VERSION = native-0.5.0
semantic action bit layout
native semantic position-key format
history digest format
```

No RuleSet semantics change.

No public game serialization change.

---

# 24. F4–F13 EVIDENCE IMMUTABILITY

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

docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
docs/architecture/F7_EVIDENCE.md
docs/architecture/F8_EVIDENCE.md
docs/architecture/F9_EVIDENCE.md
docs/architecture/F10_EVIDENCE.md
docs/architecture/F11_EVIDENCE.md
docs/architecture/F12_EVIDENCE.md
docs/architecture/F13_EVIDENCE.md

ADR-022
ADR-023
ADR-024
ADR-025
ADR-026
ADR-027
ADR-028
ADR-029
ADR-030
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f14_native_semantic_attack_api/
```

---

# 25. REQUIRED F14 EVIDENCE

At minimum:

```text
artifacts/f14_native_semantic_attack_api/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    public_api_before.json
    python_attack_contract.json
    native_attack_authority.json

    standard_shogi_attack_rows.jsonl
    standard_shogi_attack_summary.json
    standard_shogi_in_check.json

    curated_attack_differential.json
    f13_action_witness_regression.json
    standard_shogi_candidate_guarded_make_regression.json
    existing_10case_regression.json

    fail_closed_api.json

    packed_capsule_microbench.json
    per_query_pack_microbench.json
    break_even_model.json
    interruptibility_latency.json
    gil_audit.json

    integration_options.json
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
docs/architecture/F14_EVIDENCE.md
docs/architecture/ADR-031-public-native-semantic-attack-check-api.md
```

ADR-031 must document:

- Python attack/check authority;
- Native API shape;
- fail-closed behavior;
- 648+ Standard Shogi differential;
- packed-capsule speed;
- per-query packing result;
- break-even reasoning;
- selected next integration boundary;
- why production search remains unchanged.

---

# 26. TESTS

Focused tests must include:

```text
F14 public semantic attack/check API
invalid input/fingerprint bounds
81×2 Standard Shogi differential
curated semantic attack fixtures
F13 action_delivers_check / uchifuzume
S4 truth table

native compiler
native semantic position
candidate/guarded
make/unmake
terminal
fixed-depth smoke
10-case native corpus

Standard Shogi semantic certification
F12/F13 regressions
F11-F3 history/TT/runtime regressions
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

Require fresh final build PASS.

No AlphaSho.

No long games.

---

# 27. RUNTIME SAFETY

Hard limits:

```text
single focused/differential subprocess <= 60 s
single microbenchmark process <= 120 s
```

No multi-hour runner.

If a benchmark exceeds the cap:

```text
RUNTIME_SAFETY_ABORT
```

retain correctness evidence and record performance decision as inconclusive if necessary.

---

# 28. FORBIDDEN SCOPE

F14 must not:

```text
modify SemanticEngine production attack/check path
modify SearchPathRuntime
route AlphaBetaPlayer to Native
create mirrored Native runtime frames
create Native search backend
add Native TT/qsearch
change node/time/cancel search policies

change evaluator
change move ordering
change search heuristics

add attack cache
add terminal cache
add bitboards
add incremental attack map

change IR/payload/schema versions
change fingerprint
change action layout
```

No F15 work.

---

# 29. GIT / PROVENANCE

Expected:

```text
E13 baseline
  -> H14A harness / public-API absence baseline
  -> H14B public Native semantic attack/check API
  -> E14 certification/evidence closure
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

# 30. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
NATIVE_ATTACK_AUTHORITY_DIVERGED
STANDARD_SHOGI_ATTACK_MISMATCH
STANDARD_SHOGI_IN_CHECK_MISMATCH
CURATED_ATTACK_DIFFERENTIAL_FAILURE
F13_ACTION_WITNESS_REGRESSION
CANDIDATE_GUARDED_MAKE_REGRESSION
EXISTING_NATIVE_CORPUS_REGRESSION
FAIL_CLOSED_API_FAILURE
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Performance weakness is NOT a stop-condition for API certification.

---

# 31. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial build
5. Public API baseline
6. Python attack/check authority
7. Native attack/check implementation
8. H14A provenance
9. H14B provenance
10. Fail-closed API validation
11. Standard Shogi 81×2 attack differential
12. Standard Shogi in-check differential
13. Curated semantic attack differential
14. F13 action-witness / S4 regression
15. Candidate/guarded/make regression
16. Existing 10-case Native regression
17. Packed-capsule microbenchmark
18. Per-query pack benchmark
19. Break-even model
20. Interruptibility latency / GIL
21. Integration option analysis
22. Selected next boundary
23. Tests
24. Evidence / manifest
25. Git
26. Deferred
27. Final verdict

Successful verdict:

```text
F14_RESULT = API_CERTIFICATION_PASS

PUBLIC_NATIVE_SEMANTIC_ATTACK = PASS
PUBLIC_NATIVE_SEMANTIC_IN_CHECK = PASS
FAIL_CLOSED_API = PASS

STANDARD_SHOGI_ATTACK_DIFFERENTIAL = PASS
STANDARD_SHOGI_IN_CHECK_DIFFERENTIAL = PASS
CURATED_ATTACK_DIFFERENTIAL = PASS

F13_ACTION_WITNESS_REGRESSION = PASS
EXISTING_NATIVE_CERTIFIED_PATHS = PASS

PACKED_CAPSULE_NATIVE_SPEEDUP = <numeric or INCONCLUSIVE>
PER_QUERY_PACK = <VIABLE|REJECT|INCONCLUSIVE>

SELECTED_NEXT_BOUNDARY =
<NATIVE_ATTACK_INTEGRATION_DIRECT |
 NATIVE_MIRRORED_POSITION_FRAME |
 NATIVE_LEGALITY_KERNEL |
 NATIVE_POSITION_RUNTIME |
 FULL_NATIVE_SEMANTIC_SEARCH |
 SEARCH_STRENGTH_EVALUATOR_PHASE>

FULL_NATIVE_SEARCH_READY = false
FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Blocked verdict:

```text
F14_RESULT = BLOCKED
reason = <exact stop reason>
H14B_RETAINED = false unless independently certified safe
FULL_PYTEST = <PASS|FAIL>
FINAL_NATIVE_BUILD = <PASS|FAIL>
```

---

# 32. FINAL STOP

F14 ends after E14 closure.

Do not begin F15.

Do not integrate the API into production Python search.

The next implementation boundary must be separately reviewed and authorized.
