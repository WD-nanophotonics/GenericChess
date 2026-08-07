# GenericChess Phase 1.9B-2 — Independent Review R2 Package

Specification-only review package.

Reviewed:
- spec branch `3e21484`
- impl `3f3affd`

Workflow:
1. update `spec/phase-1.9b2-python-reference-executor`;
2. copy this package into repo root;
3. commit only these review-spec files and push spec;
4. merge updated spec into existing impl branch;
5. fix production only on impl;
6. do not merge master until independent review passes.

R0, R1 and R2 specification files are frozen.
