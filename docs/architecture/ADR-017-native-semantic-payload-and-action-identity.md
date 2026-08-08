# ADR-017 — Native Semantic Payload and Exact Action Identity Contract

Status: **FROZEN for Phase 1.9C-1**

Baseline: `d9c00ad1617e846273b14e0ec6c14cd480487aeb`

Python semantic reference verdict: `PYTHON_S0_S4_REFERENCE_EXECUTOR_READY`

Phase 1.9C reconnaissance verdict: `PHASE_1_9C_RECONNAISSANCE_READY`

## 1. Decision

Phase 1.9C-1 implements only the static Native semantic compilation contract:

```text
CompiledSemanticRuleset
    ↓
deterministic semantic-native lowering
    ↓
plain Python payload
    ↓
CPython bridge
    ↓
C-owned GCSemanticRules capsule
```

C-1 does not implement Native semantic position, move generation,
make/unmake, hash, perft, terminal logic, AlphaBeta, SearchBackend, or S4.

The Python S0-S4 executor remains the executable correctness oracle.

## 2. Why C-1 is separate

Existing Native state is legacy-action based: `GCRules`, `GCPosition`,
`GCUndo`, and `GCPackedAction` know legacy atoms/masks/state but not semantic
patterns, aux, effects, triggers, or exact pattern/geometry identity.

C-1 freezes the static contract before state/execution changes.

## 3. ABI/version transition

C-1 is an additive Native interface extension and MUST bump:

```text
native_version()       == "0.4.0"
NATIVE_SCHEMA_VERSION  == "native-0.4.0"
native_capabilities()["native_schema"] == "native-0.4.0"
```

Required additive capability keys:

```text
semantic_ir_v2_compile         = True
semantic_payload_version       = 1
semantic_exact_action_identity = True
semantic_position_state        = False
semantic_s0_s4_executor        = False
```

C-1 MUST NOT claim semantic execution capability.

`CompiledSemanticIR.capabilities.native_executable` remains `False`.

## 4. Separate semantic capsule

C-1 MUST introduce a separate C-owned semantic rules object/capsule.

Normative conceptual names:

```text
GCSemanticRules
GC_SEM_RULES_CAPSULE
```

Exact private helpers may differ, but the semantic object MUST NOT be a
reinterpretation of legacy `GCRules`.

Legacy structure field layouts are frozen in C-1:

```text
GCRules
GCPosition
GCUndo
GCTTEntry
```

No field may be added, removed, or repurposed there in C-1.

## 5. Source authority

The only Python lowering authorities are:

```text
CompiledSemanticRuleset.ir
CompiledSemanticRuleset.support
```

Forbidden as semantic lowering/execution authority:

```text
high-level RuleSet
PieceType.movement_atoms
CompiledSemanticRuleset._legacy_compiled
game/debug/fixture names
```

Replacing `_legacy_compiled` by an unrelated sentinel MUST NOT change payload.

## 6. Deterministic numeric identity

### Type

```text
type_ids = tuple(sorted(semantic.support.type_metadata))
```

Native max remains 64.

### Pattern

Preserve normalized IR tuple order:

```text
pattern_ids = tuple(p.pattern_id for p in semantic.ir.patterns)
```

Max 256, therefore logical pattern index is 8 bits.

### Geometry

```text
geometry_ids = tuple(sorted(semantic.ir.geometry))
```

Native semantic capacity:

```text
GC_SEM_MAX_GEOMETRIES = 4096
```

Larger inputs fail closed.

### Zone

```text
zone_ids = tuple(sorted(semantic.ir.zones))
```

Storage may be dynamic with checked size arithmetic.

Compiled aux `slot_id` values and trigger tuple order are preserved exactly.

## 7. Geometry contract

Native lowering consumes already-compiled exact geometry.

For leap/ray, executable authority is `CompiledGeometry.paths`: ordered
per-owner/per-source path squares.

Native MUST NOT regenerate semantic paths from direction, offset, legacy
movement atoms, board heuristics, or game knowledge.

Payload preserves at least:

```text
kind
min_steps
optional atom_source type index + atom index
exact owner/source ordered path squares
```

String `geometry_id` remains reversible through Python `geometry_ids`.

## 8. Static payload closure

C-owned semantic payload MUST losslessly represent every runtime-relevant
field of current IR v2/support.

Support:

```text
fingerprint
board size
repetition_limit
max_ply
type metadata:
  anchor/promotable/promotion targets
drop masks
promotion allowed pairs
promotion forced masks
alive promotion-target masks
```

IR:

```text
geometries
zones
patterns:
  type indices
  geometry indices
  target predicate
  path predicates
  state guards
  slot guards
  effects
  invariants
  postconditions
  promotion mode / explicit promotion target
  cost class
  stratum
aux slots
transition triggers
```

`name`, `composition`, and `replaced_pattern_ids` are post-normalization
provenance/debug metadata and MUST NOT affect Native execution.

## 9. Closed enum codes

```text
geometry: leap=0 ray=1 drop=2
target: empty=0 enemy=1 friendly=2 any=3

path:
  path_clear=0
  path_count_eq=1
  path_count_range=2
  path_first_blocker_owner=3
  path_last_blocker_owner=4

owner: self=0 opponent=1 any=2
aggregation: exists=0 count=1
comparison: eq=0 ne=1 lt=2 le=3 gt=4 ge=5
compare_field: base=0 current=1
promoted: yes=0 no=1 any=2

type_ref:
  action_base=0 action_current=1 explicit=2 any=3

square_ref:
  source=0 target=1 fixed=2 offset_from_source=3
  offset_from_target=4 path_step=5 aux_slot_square=6

spatial:
  same_file=0 same_rank=1 exact=2 adjacent=3 path_between=4 zone=5

aux_value: bool=0 square_or_none=1
aux_scope: global=0 per_owner=1
aux_lifetime: persistent=0 expire_next_turn=1

trigger_event:
  piece_leaves_square=0
  piece_removed_from_square=1

effect:
  move=0 remove=1 remove_from_hand=2 place=3 set_current_type=4
  set_bool=5 clear_right=6 set_token=7 clear_token=8 shift=9

disposition: capture_to_hand=0 remove_from_game=1
invariant: own_anchor_safe=0 squares_not_attacked=1
postcondition: opponent_checked=0 no_legal_reply=1
promotion_mode: none=0 inherit_compiled_masks=1 explicit=2
cost: C0=0 C1=1 C2=2 C3=3 C4=4
stratum: S0=0 S1=1 S2=2 S3=3 S4=4 S5=5
```

Unknown values fail closed.

## 10. C-owned payload round-trip

C-1 MUST expose:

```text
semantic_rules_info(capsule)
```

It reconstructs the normalized numeric payload from the **C-owned capsule**.

Frozen oracle:

```text
payload, report = build_semantic_compile_payload(semantic)
native = compile_native_semantic_rules(semantic)

payload == semantic_rules_info(native.capsule)
```

Returning a Python-cached original payload is insufficient.

## 11. Python API

Required under `generic_chess.native.compiler`:

```text
NativeSemanticCompilationReport
NativeSemanticCompiledRules
build_semantic_compile_payload
compile_native_semantic_rules
```

`NativeSemanticCompiledRules` exposes read-only:

```text
capsule
fingerprint
type_ids
pattern_ids
geometry_ids
zone_ids
report
```

Consistent lazy re-export from `generic_chess.native` is expected.

## 12. Exact semantic 64-bit action identity

Legacy lower layout remains:

```text
bits  0-7   to
bits  8-15  from
bits 16-23  promotion target
bits 24-31  base type
bits 32-35  kind
```

Legacy kinds:

```text
0 = legacy board
1 = legacy drop
```

Additive semantic kinds:

```text
2 = semantic board
3 = semantic drop
```

High 28 bits:

```text
bits 36-43  pattern_index      (8)
bits 44-55  geometry_index     (12)
bits 56-63  actor_current_type (8)
```

Semantic board carries exact pre-action base/current type, pattern, geometry,
source, target, and promotion binding.

Semantic drop uses:

```text
from=0xFF
promotion=0xFF
base=dropped base type
actor_current_type=dropped type
kind=3
```

C-1 exposes:

```text
semantic_action_layout()
```

with shifts, widths, kinds, and capacities.

C-1 does NOT generate or execute semantic actions.

Legacy checked make MUST reject semantic kinds rather than reinterpret them.

## 13. Native fail-closed limits

At minimum:

```text
board squares <= 256
types <= 64
patterns <= 256
geometries <= 4096
max_ply <= 512
aux slots <= 8
effects per pattern <= 4
squares_not_attacked refs <= 4
postcondition probe <= S3
```

No truncation, modulo indexing, first-match fallback, or feature dropping.

Dynamic size arithmetic must be overflow checked.

## 14. Legacy preservation

Existing legacy Native compile/pack/legal/perft/checked-make/search APIs remain
available and keep legacy behavior.

C-1 does not route legacy execution through semantic machinery.

## 15. Compile-only boundary

After C-1:

```text
semantic_ir_v2_compile=True
semantic_exact_action_identity=True
semantic_position_state=False
semantic_s0_s4_executor=False
```

There MUST NOT be public Native semantic:

```text
legal_actions
make
perft
terminal
search
```

entry points yet.

## 16. Exit

C-1 exit verdict:

`NATIVE_SEMANTIC_PAYLOAD_CONTRACT_READY`

Only after independent acceptance may C-2 freeze semantic Native
position/aux/hash/fixed-undo/S0-S3 execution.
