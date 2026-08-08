# ADR-013: Semantic Executor Support Data, State Identity, and Runtime Ownership

Status: proposed/frozen for Phase 1.9B-2 specification

## Context

IR v2 closed pattern-local operand ambiguity but does not yet contain every generic datum needed to execute an entire game. Legacy `CompiledRuleSet` still owns promotion/drop/type/terminal support data. Using `_legacy_compiled` from the new executor would recreate a second semantic source and violate the IR executable contract.

## Decision

1. `CompiledSemanticRuleset` SHALL own two explicit compiled products:
   - canonical action/constraint IR;
   - typed generic Core support data.
2. Support data SHALL be compiler-produced and immutable. It may contain precomputed masks/tables and stripped type metadata, but SHALL NOT require an executor to reinterpret `PieceType.movement_atoms`.
3. `_legacy_compiled` remains inspection-only and MUST be removable (`None`) without changing semantic execution.
4. Normalized patterns SHALL include anchor movement. `is_anchor` is support metadata, not a reason to omit movement patterns.
5. Auxiliary legality state SHALL live in `Position`, not Session/UI/AI/executor locals.
6. Position identity SHALL include aux values for semantic rulesets. Legacy empty-aux rulesets retain their historical position-key behavior.
7. Existing pseudo-attack semantics remain a separate lower-level query. An enemy anchor square may be attacked, but capturing an anchor is never a legal action.
8. S4 postconditions are not part of Phase 1.9B-2 execution.

## Consequences

- The executor has a complete, explicit dependency surface.
- Native Phase 1.9C can lower the same support payload without reading Python high-level rules.
- Promotion/drop/terminal semantics do not leak through `_legacy_compiled`.
- Position/hash/undo work in later Native phases has a clear state-ownership contract.
