# GenericChess Runtime Foundation F1 evidence

Status: implementation complete pending final remote/worktree verification.

## Baseline and promotion

- Task baseline: `origin/master=1303c03b114434cc6dc05bc94abe23cec8940437`.
- Task baseline: `origin/sandbox=ab7a8b3b07af46336ee2d6796f79e48a7b1af355`.
- Gate A P0 defect: `pyproject.toml` listed 14 native C sources while the
  supported Zig build consumed 17.  The three missing sources were
  `native_semantic_key.c`, `native_semantic_runtime.c`, and `native_sha256.c`.
- Minimal correction: commit `0b6196b` plus
  `tests/test_native_build_manifest.py`.
- Gate A promotion: ordinary fast-forward `1303c03..0b6196b` to `master`;
  the same exact SHA was pushed to `sandbox`.  No force push was used.

## F1 implementation commits

- `6277ddc` — canonical identity authority and focused contract tests.
- `2d66fa1` — Core, Session, UI, AI, diagnostics, learning, and Native
  differential consumer migration.
- Final documentation/evidence commit: the tip verified by the final
  `git rev-parse HEAD` and remote SHA audit.

## Authority contract

`generic_chess.core.identity` owns `PositionIdentity`,
`RepetitionIdentity`, `SearchStateIdentity`, `ExternalStableKey`, and the
reserved `RuntimeHash` boundary.  Semantic dispatch is derived from the
compiled ruleset type.  Existing legacy and semantic SHA-256 encodings are
unchanged.  Semantic slot defaults canonicalize with omitted entries and
unknown physical auxiliary entries remain identity-relevant.

Search identity retains position identity, `ply_count`, the complete
repetition-count tuple, and the existing continuous-check context.  Standard
Shogi TT remains disabled; no history redesign or incremental/runtime hash was
implemented.

## Validation

Commands run on the F1 sandbox tip:

```text
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest -q tests\test_native_action_validation.py tests\test_native_differential.py tests\test_native_hardening.py tests\test_native_kernel.py tests\test_native_readiness_suite.py tests\test_native_readiness_instrumentation.py tests\test_native_semantic_position.py tests\test_native_semantic_randomized_closure.py tests\test_native_semantic_stress_differential.py tests\test_rule_semantics_ir_foundation.py tests\test_rule_semantics_ir_hardening.py tests\test_round4_corrective_audit.py tests\test_round5_corrective_r1_harness.py tests\test_identity_contract.py
.venv\Scripts\python.exe scripts\build_native_zig.py
.venv\Scripts\python.exe -m pip wheel . --no-deps --no-build-isolation --wheel-dir <temporary-directory>
```

- Full suite: 850 collected, all passed.
- Native/semantic/identity subset: 108 collected, all passed.
- Zig build: passed; all 17 native C sources compiled.
- Native version: `0.5.0`.
- Native capabilities: semantic position state, exact action identity,
  complete history replay, repetition context, cancellation, and fixed-depth
  search all reported available; production dynamic evaluator/search remain
  explicitly false.
- Certified Standard-Shogi fingerprint:
  `5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345`.
- Packaging manifest: 17 configured / 17 actual / complete.
- Wheel metadata: built successfully as `generic_chess-0.8.0a9`.

## Scope and deferred work

AlphaSho was not accessed or modified.  Evaluators, search tuning, UI
productization, Native production backend selection, history storage redesign,
incremental/runtime hashing, Standard-Shogi TT enablement, F2, and F3 remain
out of scope.

The old `core.keys` functions and the Native semantic exact-key bridge remain
for compatibility and parity fixtures.  Production callers no longer choose
legacy versus semantic identity independently; the complete matrix is in
`F1_CALL_SITE_MIGRATION.md`.
