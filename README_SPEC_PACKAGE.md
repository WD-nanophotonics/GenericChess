# GenericChess Phase 1.9B-2 Specification Package

Baseline commit:

`6d6ddd4f00d059e6647a37664044a7030a4f802d`

Intended workflow:

1. Create `spec/phase-1.9b2-python-reference-executor` from the baseline commit.
2. Copy this package into the repository root, preserving paths.
3. Commit these specification files **without implementing production code**.
4. Push the spec branch.
5. Create `impl/phase-1.9b2-python-reference-executor` from the spec branch.
6. Implement the task described in `docs/tasks/phase-1.9b2-python-reference-executor.md`.
7. Treat the specification files listed below as frozen unless a genuine
   `SPECIFICATION_BLOCKER` is found.

Frozen specification:

- `docs/audits/2026-08-phase-1.9b2-pre-executor-audit.md`
- `docs/architecture/ADR-013-semantic-executor-support-and-identity.md`
- `docs/tasks/phase-1.9b2-python-reference-executor.md`
- `tests/specification/test_phase19b2_pre_executor_contract.py`

The tests under `tests/specification/` are intentionally allowed to fail on
the baseline commit. They define requirements for Phase 1.9B-2 and must not be
weakened merely to make the implementation pass.

This package contains no production executor implementation.
