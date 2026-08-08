# Task — Phase 1.9C-1 Native Semantic Payload Contract

Read first:

- `docs/architecture/ADR-017-native-semantic-payload-and-action-identity.md`
- ADR-013 / ADR-014 / ADR-015 / ADR-016
- Phase 1.9B-3 R1/R2 audits
- `tests/specification/test_phase19c1_native_semantic_payload_contract.py`
- `tests/phase19c1_native_semantic_fixtures.py`

## Goal

Implement the compile-only Native semantic contract frozen by ADR-017.

Input:

`CompiledSemanticRuleset.ir + .support`

Output:

`C-owned semantic rules capsule`

No semantic position or executor is implemented in this phase.

## Expected production areas

Likely Python:

```text
generic_chess/native/compiler.py
generic_chess/native/__init__.py
```

Likely C:

```text
generic_chess/_native/native_module.c
new semantic-specific .h/.c under generic_chess/_native/
```

`scripts/build_native_zig.py` already glob-builds all `.c`; do not edit it
only to add new semantic C files.

Small common-header edits are allowed only for additive version/capability/
action-layout definitions.

## Frozen legacy structures

Do not change field layout of:

```text
GCRules
GCPosition
GCUndo
GCTTEntry
```

## Forbidden scope

Do not implement:

```text
semantic position packing
semantic move generation
semantic make/unmake
semantic pseudo-attack
semantic S3/S4
semantic perft/terminal/search
evaluation changes
SearchBackend
Learner
Session
UI
```

No high-level RuleSet or `_legacy_compiled` semantic dependency.

## Version

Exactly:

```text
0.3.0 → 0.4.0
native-0.3.0 → native-0.4.0
```

## Required Python surface

```text
NativeSemanticCompilationReport
NativeSemanticCompiledRules
build_semantic_compile_payload
compile_native_semantic_rules
```

## Required CPython surface

```text
compile_semantic_rules
semantic_rules_info
semantic_action_layout
```

## Static payload oracle

For every frozen semantic corpus item:

```text
payload, report = build_semantic_compile_payload(semantic)
native = compile_native_semantic_rules(semantic)
assert semantic_rules_info(native.capsule) == payload
```

Info MUST be reconstructed from C-owned state.

## Deterministic identity

```text
type_ids     = sorted support type IDs
pattern_ids  = normalized IR tuple order
geometry_ids = sorted geometry IDs
zone_ids     = sorted zone IDs
```

## Test gates

### Gate A

```bash
python -m pytest \
  tests/specification/test_phase19c1_native_semantic_payload_contract.py \
  -p no:cacheprovider
```

Target: `12 passed`.

### Gate B

```bash
python -m pytest tests/specification -p no:cacheprovider
```

Target: `55 passed` (43 previous + 12 C-1).

### Gate C — Python semantic

Run at minimum:

```text
tests/test_phase19b3_s4_executor.py
tests/test_semantic_executor.py
tests/test_rule_semantics_ir_foundation.py
tests/test_rule_semantics_ir_hardening.py
```

All green.

### Gate D — legacy Native

Run focused existing Native compile/correctness/action/hash/perft tests touched
by the extension/version/capability changes.

Legacy behavior unchanged except explicit version/schema bump plus additive
semantic capability keys.

### Gate E — full suite

Run once. The known machine-sensitive
`test_tiny_time_budget_aborts_before_clock_expiry` may be reported separately
only if baseline-equivalent.

Do not run blind repeated native/UI stress loops.

## Freeze audit

C-1 frozen spec files are immutable.

Zero production diff required in:

```text
generic_chess/core/**
generic_chess/ai/**
generic_chess/learning/**
generic_chess/ui/**
generic_chess/session/**
```

No `GCPosition`/`GCUndo` layout changes.
No semantic legal/perft/search entry point.

## Implementation branch

`impl/phase-1.9c1-native-semantic-payload-contract`

Do not push master.

## Verdicts

Only:

```text
NATIVE_SEMANTIC_PAYLOAD_CONTRACT_READY
NATIVE_SEMANTIC_PAYLOAD_REQUIRES_REVISION
SPECIFICATION_BLOCKER
```

Then STOP. Do not begin C-2.
