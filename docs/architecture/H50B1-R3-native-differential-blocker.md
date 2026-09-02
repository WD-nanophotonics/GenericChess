# H50B1-R3 Native differential blocker

Status: `F50B1_R3_CERTIFICATION_BLOCKER`

Checkpoint under audit: `H50B1-R3_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION`

Parent authority: `cec77739c75d42d19e34507696c23cf8223fcfd2`

## Blocking finding

The first real Native/Python lockstep transition in the Standard Shogi
matrix diverges on a promoted pawn.  The position is:

```text
8k/7+P1/9/9/9/9/9/9/4K4 b - 1
```

For the same legal move `from=64` to `to=73` (`b8-b9`), the Python semantic
executor emits:

```text
pattern=legacy_094 geometry=g51 actor=TP promotion_target_id=None
```

Native emits the same source, target, pattern, geometry, and actor-current
identity, but sets the packed promotion field to type index `11` (`TP`):

```text
{"to":73,"from":64,"promotion":11,"base":5,"kind":2,
 "pattern":94,"geometry":47,"actor_current":11}
```

Therefore Native's public action is `legacy_094:g51:b8-b9=TP`, while the
Python public action is `legacy_094:g51:b8-b9`.  This is an action-identity
and transition-parity failure, not an ordering-only difference.

## Reproduction

The finding was reproduced from the R2 parent with the project interpreter:

```text
.venv\\Scripts\\python.exe scripts/audit_h50b1_r3_native_differential.py
```

The executable audit harness is retained at
`scripts/audit_h50b1_r3_native_differential.py`.  The harness packs the exact
Core position into `GCSemanticPosition`, enumerates Native guarded actions,
decodes each with `public_action()`, and compares it with the Python semantic
action identity.

## Likely production cause

`generic_chess/_native/native_semantic_runtime.c`, in `promotion_choices()`,
derives promotion choices from the piece's base type and promotion zone but
does not exclude a piece whose current type is already promoted.  The Python
executor does exclude that action variant.  R3 is not authorized to patch
this production surface, so certification stops here.

## Scope and disposition

- No file under `generic_chess/` was modified during R3.
- No R3 checkpoint is claimed complete.
- H50B1-R3 matrix expansion, historical H50A isolation, state-size
  measurement, and final provenance closure remain pending behind this fix.
- A new corrective order must repair the Native promotion-choice behavior,
  add a regression test, rebuild the Native extension, and then resume the
  R3 lockstep certification.
