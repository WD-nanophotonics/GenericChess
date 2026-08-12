# GenericChess Runtime Foundation F2 Corrective R2 evidence

Status: IN PROGRESS — Corrective R2 implementation and focused validation are
being completed on 2026-08-12.

## Scope and baseline

The candidate is based on the required sandbox starting point:

```text
origin/sandbox baseline: fbe72a37eebd2b1c159377015adb176e04089deb
origin/master (preserved): 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat (preserved): d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Only the sandbox worktree is in scope.  AlphaSho was not accessed.

## Corrective R2 contracts

The R2 blocker is the inability of a SHA-only imported non-root history
record to compare equal to a future exact runtime position.  The bridge uses
private Session/replay witnesses when available and a conditional,
instrumented external-key fallback for opaque custom-root histories.  A
resolved key is aliased into runtime history so ordinary repetition and
continuous-check evidence include the pre-root occurrence.  The bridge state
is restored on sibling pop and exception rollback.

Focused regression coverage now includes a real legal pre-root cycle, forced
runtime-hash collision, incomplete-history fallback, Session witness import,
unreplayable custom history fallback, and sibling restoration.  Full R2
performance, differential, and native-build receipts are recorded below only
after they have been rerun from this baseline.

## Corrective R1 contracts retained

* Legacy children use a 128-bit runtime hash updated from only changed
  components; child external-key computations are zero.
* Semantic children use stable-address component-map delta fallback, including
  auxiliary add/remove coverage; child external-key computations are zero.
* RuntimeHash buckets retain exact in-memory positions, so forced collisions
  cannot merge distinct occurrences.
* Imported history rejects nonpositive counts, ghost keys, mismatched
  multiplicities, and a history whose final key is not the imported root.
* Repetition snapshots are order independent and verify exact maps after a
  digest collision.
* Capture, promotion, and drop transitions match the full hash oracle.
* A terminal/transition exception restores the complete parent runtime.
* Public immutable state, reference transitions, public SHA identity, and TT
  policy boundaries are unchanged.

## Focused validation

```text
python -m pytest -q -p no:cacheprovider tests/test_search_path_runtime.py tests/test_identity_contract.py tests/test_repetition.py tests/test_lazy_successors.py tests/test_native_history.py tests/test_session.py
```

Result: PASS, 64 tests.

The full project command also passed under the test-required sandbox write
permission:

```text
python -m pytest -q -p no:cacheprovider
862 passed
```

## Blocking finding E reproduction

The reproduction uses the legal deterministic cycle from
`tests/test_native_history.py`, with a root at ply 3 and a non-root historical
position already present in `repetition_counts`.  Loading the exact
`fbe72a37` implementation in memory, without changing the worktree, produced:

```text
pre_root_key_in_counts=True
same_position_reached=True
baseline_runtime_count=1
immutable_oracle_count=2
corrected_runtime_count=2
```

The corrected focused regression is
`test_pre_root_non_root_repetition_merges_with_runtime_identity`; it also
covers forced runtime-hash collision and push/pop restoration.

The bounded Standard-Shogi `continuous_check_loss` fixture also passes through
the runtime bridge: immutable and runtime paths both reach
`perpetual_check` on the same move after the relevant occurrences began before
the search root.  This is covered by
`test_complete_history_continuous_check_pre_root_parity`.

## Performance harness

Five warmed repetitions were run with fixed depth, `use_tt=False`,
`use_ordering=False`, and `use_root_tactical=False`.

| Case | Warmed median | Nodes | Child external keys | Root/import bridge |
|---|---:|---:|---:|---:|
| Legacy 4x4 rooks, depth 3 | 44.91 ms | 137 | 0 | 1 reconstruction key |
| Semantic nifu fixture, depth 2 | 22.61 ms | 17 | 0 | 1 reconstruction key |
| Cycle session with exact witnesses, depth 1 | 1.18 ms | 2 | 0 | 4 witness hits |
| Cycle custom opaque history, depth 1 | 1.48 ms | 2 | conditional; 2 on two pushes | witness miss + key fallback |

All fresh-root cases reported zero ordinary child external-key work, zero
history/repetition tuple copies, and balanced push/pop.  Legacy reported 134
incremental updates; semantic reported 15 component-diff fallbacks.  The
history-bearing rows report bridge work honestly and do not count it as fresh
root child work.

## Native validation

```text
Zig 0.16 via the sibling GenericChess .venv
python scripts/build_native_zig.py
PASS; _native_core_r2.cp312-win_amd64.pyd; 333312 bytes
```

The cache and temporary output were placed outside the sandbox worktree
because its pre-existing cache directory is access-denied; no tracked master
or chat file was changed.
