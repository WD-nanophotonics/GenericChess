# GenericChess Runtime Foundation F2 evidence

Status: COMPLETE — implementation, validation, and sandbox push verified on 2026-08-12.

## Scope

F2 adds only the Core-owned search-path runtime and AlphaBeta integration on
the exact promoted F1 baseline `4f1d03a308f5fd04a01bbd980c7411888ea1ed9d`.
It does not modify AlphaSho, the chat worktree, Standard-Shogi TT policy, or
F3 work.

## Contracts demonstrated

- Public immutable `GameState` and `reference_minimax` remain unchanged.
- Root import validates the compiled ruleset fingerprint and complete
  imported history; continuous-check paths without history fail closed.
- Runtime `push`/`pop` is exception-safe and balanced under normal search and
  cancellation.
- Occurrence counts and linked repetition snapshots update without copying a
  full public repetition tuple per child.
- Runtime hash is 128-bit, incrementally updated from identity-component
  deltas, and guarded by exact external SHA keys.  The forced-collision test
  exercises the fallback counter.
- Negamax, PVS re-search, aspiration, qsearch (ordinary and in-check), root
  tactical scan, lazy/eager controls, and cancellation use the runtime.
- Standard-Shogi TT remains disabled for continuous-check paths.

## Focused validation

```text
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_search_path_runtime.py tests\test_lazy_successors.py tests\test_search_upgrades.py tests\test_qsearch_correctness.py
```

Focused result: PASS (44 tests).

Full validation:

- True full pytest: PASS, 850 tests.
- Fresh Zig native build: PASS, all 17 configured C sources, 333312-byte
  `generic_chess/_native_core.cp313-win_amd64.pyd`.
- Runtime/native/identity/history focused subset: PASS, 32 tests.
- Temporary build cache was removed; logs and process output are not formal
  evidence artifacts.

## Remote closure

- F1 exact baseline promoted to `origin/master`: `4f1d03a308f5fd04a01bbd980c7411888ea1ed9d`.
- F2 implementation is pushed only to `origin/sandbox` after commit.
- `origin/chat` remains `d6b0d5720efe23019a7a2b4cce72e05beee2e6c4` and AlphaSho
  was not accessed or modified.
