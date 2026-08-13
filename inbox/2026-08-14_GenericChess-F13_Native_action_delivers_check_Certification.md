<!-- Gmail provenance
message_id: 19ffccc8a96a2bb2
thread_id: 19ffccc8a96a2bb2
subject: GenericChess — F13: Native action_delivers_check Capability Gap Closure + Standard Shogi Native-Executable Certification
received: 2026-08-13T16:24:51-04:00
processing: authoritative body saved before execution
-->

# GenericChess — F13: Native `action_delivers_check` Capability Gap Closure + Standard Shogi Native-Executable Certification

## 0. AUTHORITATIVE TASK

This is the authoritative F13 task for `WD-nanophotonics/GenericChess`.

F12 concluded:

```text
F12_RESULT = AUDIT_PASS
STANDARD_SHOGI_NATIVE_EXECUTABLE = false
SELECTED_NEXT_BOUNDARY = NATIVE_CAPABILITY_GAP_CLOSURE
```

The blocking capability is narrow and explicit:

```text
semantic postcondition: action_delivers_check
```

F13 has one implementation goal:

> Add exact Native semantic support for `action_delivers_check`, preserving the frozen Python SemanticEngine contract, and certify that the existing certified Semantic Standard Shogi ruleset becomes fail-closed **native-executable** without changing any game semantics.

F13 is a capability-closure phase, not a production migration phase.

Successful result:

```text
F13_RESULT = CAPABILITY_CLOSURE_PASS
```

A correctness/build failure is:

```text
F13_RESULT = BLOCKED
```

Do not declare partial capability as success.

---

# 1. GMAIL / INBOX ENTRY

Follow the repository-local GenericChess Gmail/inbox protocol.

Before work:

1. locate this task using GenericChess/Gmail fuzzy subject matching;
2. read the complete authoritative body/attachment;
3. persist the complete task to `inbox/`;
4. record Gmail message/thread provenance and processing state;
5. only then begin implementation/audit.

Do not execute from the email subject/snippet alone.

---

# 2. BASELINE LOCK — HARD GATE

Required refs:

```text
origin/sandbox =
32031d187b0cd6132f86eb31561b6a41c7116e6c

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

# 3. F12 AUTHORITY / FROZEN FINDINGS

Treat F12 as authoritative unless current source directly contradicts it.

F12 established:

```text
native schema = native-0.5.0
semantic payload version = 2
IR version = 2

existing native certified paths = PASS
10 frozen semantic corpus cases = native executable
Standard Shogi = FAIL_CLOSED_UNSUPPORTED
blocking gap = action_delivers_check lowering/runtime support
```

Existing Native semantic runtime already has internal:

```text
semantic_attacked_by(...)
gc_semantic_runtime_in_check(...)
semantic_has_s3_reply(...)
postconditions_hold(...)
```

Do not redesign these wholesale.

F12 also established:

```text
public semantic attack/check API = absent
production semantic search backend = absent
```

F13 MUST NOT add either.

---

# 4. PYTHON `action_delivers_check` — FROZEN SEMANTIC AUTHORITY

The authoritative Python implementation is:

```text
SemanticEngine._action_delivers_check(...)
SemanticEngine._violates_postconditions(...)
```

Freeze the exact meaning.

`action_delivers_check` asks:

> After the action is applied, does the **action's actor itself**, now located on `action.target`, attack the reply side's anchor under semantic pseudo-attack S0/S1 rules?

It is NOT equivalent to:

```text
child is checked
```

because a child may be checked by a different piece or by a discovered/pre-existing line.

The exact Python witness semantics are:

1. Resolve the reply side's own anchor in `child`.
2. If no anchor: false.
3. Actor source in child is exactly:

```text
source = action.target
```

4. Read:

```text
piece = child.board[source]
```

5. Require:

```text
piece exists
piece.owner == parent.side_to_move
```

6. Iterate all semantic patterns in canonical IR order.
7. Only capture-eligible patterns participate:

```text
pattern.target.kind == "target_enemy"
```

8. Require actor current type in pattern type IDs.
9. Iterate pattern geometries in canonical order.
10. Ignore missing/drop geometries.
11. Respect exact `geometry.atom_source` compatibility.
12. Enumerate geometry from the actor's **new child square** toward the anchor.
13. Only the exact anchor target matters.
14. Build the exact semantic binding using child actor base/current/promoted state.
15. Evaluate on `child`:

```text
path predicates
state guards
slot guards
```

with attacker-relative owner perspective.
16. If any exact compatible binding holds: true.
17. Otherwise false.

Important:

- no S3 own-anchor-safety recursion;
- no S4 postcondition recursion;
- S4-bearing capture patterns still contribute their S0/S1 projection;
- actor current type after promotion is authoritative;
- this is an action-witness primitive, not generic position-check truth.

Do not simplify this to `gc_semantic_runtime_in_check(child, reply_side)`.

---

# 5. S4 CONJUNCTION CONTRACT — FROZEN

Python S4 postconditions are forbidden-condition conjunctions.

For a pattern with postcondition kinds:

```text
action_delivers_check
opponent_checked
no_legal_reply
```

the candidate is rejected only when **every present forbidden condition is true**.

Semantically:

```text
violates = AND(all present conditions)
```

If any present condition is false:

```text
candidate survives S4
```

Source field order must not determine semantics.

The existing cheap-first behavior may remain:

```text
action_delivers_check
then opponent_checked
then no_legal_reply
```

but this is an implementation detail.

`semantic_has_s3_reply()` remains the S4 reply oracle with S4 disabled.

Do not change S4 truth-table meaning.

---

# 6. F13 PHASE STRUCTURE

Use three provenance states.

## H13A — HARNESS / NEGATIVE BASELINE

Before production support:

- add tests/audit harness only;
- prove baseline Standard Shogi fails closed specifically on `action_delivers_check`;
- add Python semantic oracle fixtures;
- add Native expected-failure tests where appropriate;
- record current payload/postcondition code table and C parser behavior.

H13A MUST NOT make Standard Shogi native executable.

Commit and push H13A.

Record exact SHA.

## H13B — PRODUCTION CAPABILITY CLOSURE

Implement exactly one capability family:

```text
Native semantic action_delivers_check support
```

Allowed production files are normally limited to:

```text
generic_chess/native/compiler.py
generic_chess/_native/native semantic rule parsing/storage files
generic_chess/_native/native_semantic_runtime.c/.h
generic_chess/_native/native_module.c only if required for parser/compile plumbing
focused tests
```

Do not touch unrelated Native search architecture.

Commit and push H13B before final certification evidence.

## E13 — CERTIFICATION CLOSURE

Run full differential/certification/tests/builds.

Create evidence/docs closure.

Push final E13.

---

# 7. ENUM / PAYLOAD CONTRACT

Freeze existing codes:

```text
opponent_checked = 0
no_legal_reply = 1
```

Add exactly:

```text
action_delivers_check = 2
```

Do not renumber existing values.

F13 should keep:

```text
NATIVE_SCHEMA_VERSION = "native-0.5.0"
SEMANTIC_PAYLOAD_VERSION = 2
IR version = 2
```

This is an additive supported enum value, not a serialized structural redesign.

If current C parser makes this impossible without a version change:

```text
VERSION_CONTRACT_BLOCKED
STOP
```

Do not silently bump schema/payload versions in F13.

Update all fail-closed enum validation so:

```text
0, 1, 2
```

are accepted and unknown values still fail closed.

Malformed/unknown postcondition kinds must remain rejected.

---

# 8. NATIVE RUNTIME IMPLEMENTATION CONTRACT

Implement a private Native semantic helper equivalent to Python:

```text
action_delivers_check(parent, child, action, pattern context as required)
```

The helper must determine whether the moved/dropped/promoted actor itself attacks the opponent anchor.

Preferred inputs should remain local to the current make operation:

```text
rules
parent
child/work
packed action
actor side
source/target if already decoded
```

Do not introduce:
- global cache;
- position cache;
- attack map;
- new public API.

Reuse existing exact Native semantic primitives where they are genuinely semantically identical:

```text
pattern_has_type
path_entry
target_ok
path_ok
state_guards_hold
slot_guards_hold
```

Do NOT reuse legacy movement-atom `native_attack.c` as authority.

---

# 9. CRITICAL WITNESS DISTINCTION TESTS

Add explicit differential fixtures proving Native does not collapse `action_delivers_check` into `opponent_checked`.

At minimum:

## W1 — actor gives direct check

After action:

```text
actor itself attacks opponent anchor
```

Expected:

```text
action_delivers_check = true
```

## W2 — discovered check by another piece

The action opens a line so a different friendly piece checks.

Actor itself does not attack anchor.

Expected:

```text
opponent_checked = true
action_delivers_check = false
```

## W3 — already-checked / unrelated checking piece

Child is checked by another piece, actor does not attack anchor.

Expected:

```text
action_delivers_check = false
```

## W4 — promotion creates checking actor

Actor promotes on the move and the promoted current type attacks anchor.

Expected:

```text
action_delivers_check = true
```

Use child current type exactly.

## W5 — promotion removes checking geometry

If a valid generic fixture can express it, actor before promotion has an attack pattern but resulting current type does not.

Expected based on child current type.

## W6 — blocked/path predicate

Geometry nominally reaches anchor but path predicate fails.

Expected false.

## W7 — state guard blocks actor attack

Geometry reaches anchor but semantic state guard fails.

Expected false.

## W8 — slot guard blocks actor attack

Expected false.

## W9 — S4-bearing attack pattern projection

A capture pattern with S4 postconditions must still contribute S0/S1 actor attack truth.

No recursive S4 evaluation.

## W10 — checking drop witness

A dropped actor at `action.target` checks the anchor.

Expected true.

This is particularly important for Standard Shogi checking-drop restrictions.

---

# 10. S4 TRUTH-TABLE DIFFERENTIAL

Create generic semantic fixtures covering every relevant postcondition set:

```text
{action_delivers_check}
{opponent_checked}
{no_legal_reply}

{action_delivers_check, opponent_checked}
{action_delivers_check, no_legal_reply}
{opponent_checked, no_legal_reply}

{action_delivers_check, opponent_checked, no_legal_reply}
```

For each, exercise truth assignments sufficient to prove conjunction semantics.

Compare exact Python vs Native:

```text
candidate accepted/rejected
guarded action presence/order
child identity when accepted
```

Do not rely only on Standard Shogi to prove generic truth-table correctness.

---

# 11. STANDARD SHOGI COMPILE GATE

Use the certified Semantic Standard Shogi fingerprint:

```text
5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345
```

After H13B require:

```text
build_semantic_compile_payload = PASS
compile_native_semantic_rules = PASS
report.native_executable = true
```

This is a hard F13 success gate.

Record:

```text
type_count
pattern_count
geometry_count
zone_count
aux_slot_count
trigger_count
payload version
schema version
fingerprint
```

If another unsupported primitive appears after closing `action_delivers_check`:

```text
SECONDARY_NATIVE_GAP_DISCOVERED
F13_RESULT = BLOCKED
```

Do NOT broaden F13 to fix the new gap.

Preserve the exact evidence for the next planning round.

---

# 12. STANDARD SHOGI DIFFERENTIAL CORPUS

Once Standard Shogi is native executable, run exact Python-vs-Native differential.

At minimum use the four frozen reachable prefixes from F4–F11.

For every prefix compare:

```text
candidate action tuple/order
guarded/legal semantic action tuple/order
packed <-> Python action identity
make_checked child snapshot
side_to_move
board
hands
promotion
aux state
position key
terminal status where applicable
```

Require zero mismatch.

---

# 13. CHECKING-DROP / UCHIFUZUME CERTIFICATION

This is mandatory because `action_delivers_check` exists to support a generic checking-action witness and Standard Shogi uses it in the checking-drop restriction path.

Use the existing certified Standard Shogi uchifuzume fixtures plus new focused cases.

Require Python/Native exact parity on:

```text
checking pawn drop that is illegal because forbidden conjunction holds
checking pawn drop with a legal reply
non-checking pawn drop
drop that gives discovered check but dropped pawn itself does not check, if expressible
nifu interaction
promotion-independent nearby controls
```

Compare:

```text
candidate presence
guarded/legal presence
exact action identity/order
child when accepted
```

Do not use cshogi as production authority.

cshogi may remain an external certified regression oracle only where existing tests already use it.

---

# 14. ACTION-DELIVERS-CHECK MICRO DIFFERENTIAL

Create a direct test-only audit hook if needed.

For each witness, record:

```text
python_action_delivers_check
native_action_delivers_check-derived outcome
opponent_checked
expected distinction
```

A public production semantic attack/check API is still forbidden.

If direct Native helper exposure is required solely for test certification, prefer a test-only/native-debug entrypoint clearly marked non-production.

Do not add it to `generic_chess/native/semantic.py` public production surface unless absolutely required for certification.

If an entrypoint is added, it must be private/debug-only and documented as such.

---

# 15. EXISTING 10-CASE NATIVE CORPUS — NO REGRESSION

Re-run the F12 frozen native semantic corpus:

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

Require all remain:

```text
native_executable = true
position runtime checks = PASS
candidate/guarded/terminal/fixed-depth smoke = PASS
```

Existing supported rules must not regress.

---

# 16. NATIVE POSITION / HISTORY / TERMINAL PARITY

For Standard Shogi and existing supported semantic fixtures, verify:

```text
pack -> snapshot exactness
position_key exactness
history exactness
history_occurrences
make/unmake roundtrip
terminal
repetition
continuous-check where Native semantic path currently certifies it
max-ply
```

Do not weaken fail-closed history requirements.

Inexact/truncated history must remain terminal/search-ineligible exactly as before.

---

# 17. FIXED-DEPTH NATIVE SEARCH SMOKE — CERTIFICATION ONLY

After Standard Shogi becomes native executable, run bounded fixed-depth semantic Native search smoke.

This is NOT production search certification.

Use:

```text
depth 1
depth 2 only if safely bounded
```

on a small deterministic subset.

Verify:

```text
best action belongs to Python legal set
PV fully replays through Python authority
score deterministic
nodes deterministic
termination sane
```

Do NOT require equality with Python production AlphaBeta score/PV if evaluator/search algorithms differ.

Label result:

```text
NATIVE_FIXED_DEPTH_STANDARD_SHOGI_SMOKE = PASS
```

not:

```text
PRODUCTION_SEARCH_PARITY
```

---

# 18. INTERRUPTIBILITY — DO NOT OVERCLAIM

F13 does not make Native semantic search production-ready.

Do not add:
- node budget;
- deadline;
- cancellation;
- qsearch;
- TT;
- production evaluator.

Record explicitly:

```text
FULL_NATIVE_SEARCH_READY = false
```

unless F12 state was already different, which it was not.

F13 only closes a semantic capability gap.

---

# 19. PERFORMANCE / REGRESSION SMOKE

F13 is correctness-first.

No end-to-end Python-vs-Native speed claim is required.

However, run a bounded no-trace regression benchmark on the existing F12 10-case Native semantic corpus.

Compare pre-H13B baseline vs H13B:

```text
candidate_actions
guarded_actions
make_checked
terminal
fixed_depth_1
```

Requirement:

```text
no stable aggregate regression > 10%
```

for cases not using `action_delivers_check`.

If timing is noisy, repeat sufficiently and report distributions.

Do not reject a semantically correct capability closure for a <10% noisy single-case outlier; aggregate and stability matter.

---

# 20. FAIL-CLOSED NEGATIVE TESTS

Add/update tests proving:

```text
unknown postcondition code -> reject
code > 2 -> reject
malformed action_delivers_check payload -> reject
wrong fingerprint -> reject
unsupported future postcondition -> reject
invalid position/action -> reject
inexact history restrictions unchanged
```

Standard Shogi must become executable because support exists, not because fail-closed validation was weakened.

---

# 21. VERSION / FINGERPRINT INVARIANTS

Must remain unchanged:

```text
Semantic Standard Shogi fingerprint
Semantic IR version = 2
SEMANTIC_PAYLOAD_VERSION = 2
NATIVE_SCHEMA_VERSION = native-0.5.0
```

No RuleSet/compiler semantic change.

No public serialization change.

No action bit-layout change.

No native position-key format change.

No repetition-key format change.

---

# 22. F4–F12 EVIDENCE IMMUTABILITY

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

docs/architecture/F4_EVIDENCE.md
docs/architecture/F5_EVIDENCE.md
docs/architecture/F6_EVIDENCE.md
docs/architecture/F7_EVIDENCE.md
docs/architecture/F8_EVIDENCE.md
docs/architecture/F9_EVIDENCE.md
docs/architecture/F10_EVIDENCE.md
docs/architecture/F11_EVIDENCE.md
docs/architecture/F12_EVIDENCE.md

ADR-022
ADR-023
ADR-024
ADR-025
ADR-026
ADR-027
ADR-028
ADR-029
```

Create canonical before/after SHA-256 manifests.

Any mutation:

```text
OLD_EVIDENCE_MUTATED
STOP
```

New evidence only under:

```text
artifacts/f13_native_action_delivers_check/
```

---

# 23. REQUIRED F13 EVIDENCE

At minimum:

```text
artifacts/f13_native_action_delivers_check/
    baseline.json
    environment.json
    fresh_native_build_before.txt

    baseline_gap.json
    postcondition_code_contract.json
    python_action_delivers_check_contract.json

    witness_matrix.json
    s4_truth_table.json
    fail_closed_negative.json

    standard_shogi_compile_before.json
    standard_shogi_compile_after.json

    standard_shogi_candidate_parity.json
    standard_shogi_guarded_parity.json
    standard_shogi_make_parity.json
    standard_shogi_terminal_history_parity.json
    standard_shogi_uchifuzume_parity.json

    existing_10case_regression.json
    native_fixed_depth_standard_shogi_smoke.json

    performance_regression_smoke.json

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
docs/architecture/F13_EVIDENCE.md
docs/architecture/ADR-030-native-action-delivers-check.md
```

ADR-030 must document:

- exact Python action-witness semantics;
- why `opponent_checked` is insufficient;
- frozen numeric code `2`;
- Native implementation strategy;
- Standard Shogi compile transition false -> true;
- fail-closed behavior;
- why public attack API and production search integration remain deferred.

---

# 24. TESTS

Run focused tests for:

```text
F13 action_delivers_check
S4 truth table
checking drop / uchifuzume
nifu
promotion
state guards
slot guards
S4 projection

native semantic compiler
native semantic payload validation
native position
native stress/randomized closure
native candidate/guarded
native make/unmake
native terminal
native probe/fixed-depth

Standard Shogi semantic certification
F12 regressions
F11-F3 core/runtime/history/TT regressions
```

Then:

```text
python -m pytest -q -p no:cacheprovider
```

Require 100% PASS.

Then fresh final build:

```text
python scripts/build_native_zig.py
```

Require PASS.

Do not use AlphaSho.

Do not run long games.

---

# 25. RUNTIME SAFETY

All F13 tests/benchmarks must remain bounded.

Hard controller limits:

```text
single focused/differential subprocess <= 60 s
single native fixed-depth smoke <= 120 s
```

If a fixed-depth depth-2 case exceeds the cap:

```text
RUNTIME_SAFETY_ABORT
```

Keep depth-1 evidence and do not retry for hours.

No multi-hour runner.

---

# 26. FORBIDDEN SCOPE

F13 must not:

```text
add public semantic attack/check production API
route Python SemanticEngine attack to Native
route AlphaBetaPlayer to Native
replace SearchPathRuntime
add Native TT
add Native qsearch
add Native node/time/cancel budgets
change evaluator
change search heuristics

add attack cache
add terminal cache
add bitboards
add incremental attack map

change public RuleSet semantics
change semantic fingerprint
change IR version
change payload version
change native schema version
change action bit layout
```

No F14 work.

---

# 27. GIT / PROVENANCE

Expected:

```text
E12 baseline
  -> H13A harness + baseline fail-closed proof
  -> H13B production action_delivers_check support
  -> E13 certification evidence/docs
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

# 28. STOP CONDITIONS

Immediately STOP and preserve evidence for:

```text
BASELINE_MOVED
RULESET_FINGERPRINT_MISMATCH
VERSION_CONTRACT_BLOCKED
PYTHON_NATIVE_ACTION_WITNESS_MISMATCH
S4_TRUTH_TABLE_MISMATCH
STANDARD_SHOGI_STILL_NOT_NATIVE_EXECUTABLE
SECONDARY_NATIVE_GAP_DISCOVERED
STANDARD_SHOGI_CANDIDATE_ORDER_MISMATCH
STANDARD_SHOGI_GUARDED_ORDER_MISMATCH
STANDARD_SHOGI_CHILD_MISMATCH
UCHIFUZUME_PARITY_FAILURE
EXISTING_NATIVE_CORPUS_REGRESSION
HISTORY_TERMINAL_PARITY_FAILURE
OLD_EVIDENCE_MUTATED
FULL_PYTEST_FAILURE
FINAL_NATIVE_BUILD_FAILURE
MASTER_OR_CHAT_CHANGED
```

Do not broaden scope to repair a secondary gap.

---

# 29. FINAL REPORT FORMAT

Return exactly:

1. Status
2. Baseline
3. Gmail / inbox provenance
4. Environment / initial native build
5. Baseline capability gap
6. Python action_delivers_check authority
7. Native postcondition code contract
8. H13A provenance
9. H13B implementation
10. Witness differential
11. S4 truth-table differential
12. Fail-closed negative tests
13. Standard Shogi compile transition
14. Standard Shogi candidate/guarded parity
15. Standard Shogi make/position parity
16. Uchifuzume / checking-drop parity
17. Terminal/history parity
18. Existing 10-case Native regression
19. Fixed-depth Standard Shogi smoke
20. Performance regression smoke
21. Tests
22. Evidence / manifest
23. Git
24. Deferred
25. Final verdict

Successful verdict:

```text
F13_RESULT = CAPABILITY_CLOSURE_PASS

ACTION_DELIVERS_CHECK_NATIVE = PASS
S4_TRUTH_TABLE = PASS
FAIL_CLOSED_VALIDATION = PASS

STANDARD_SHOGI_NATIVE_EXECUTABLE = true
STANDARD_SHOGI_NATIVE_DIFFERENTIAL = PASS
UCHIFUZUME_NATIVE_PARITY = PASS

EXISTING_NATIVE_CERTIFIED_PATHS = PASS
FULL_NATIVE_SEARCH_READY = false

FULL_PYTEST = PASS
FINAL_NATIVE_BUILD = PASS
```

Blocked verdict:

```text
F13_RESULT = BLOCKED
reason = <exact frozen stop reason>
H13B_RETAINED = false unless the retained subset is independently safe and explicitly authorized by this task
FULL_PYTEST = <PASS|FAIL>
FINAL_NATIVE_BUILD = <PASS|FAIL>
```

If blocked after H13B, prefer cleanly revert unsafe/incomplete production support while retaining H13A/E13 diagnostic evidence.

---

# 30. FINAL STOP

F13 ends after E13 closure.

Do not begin F14.

Do not add the public semantic attack/check API.

Do not migrate production search.

The next phase will be separately audited and authorized.

