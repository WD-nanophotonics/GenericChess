# GenericChess Runtime Foundation F2 Corrective R1 evidence

Status: IN PROGRESS until the final full-test, fresh-build, and sandbox-push
gates are recorded below.

## Scope and baseline

The candidate is based on the required sandbox starting point:

```text
origin/sandbox baseline: 90f7c9ad8e2c19af5750b989d4932b8d0f0d93a3
origin/master (preserved): 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat (preserved): d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Only the sandbox worktree is in scope.  AlphaSho was not accessed.

## Corrective contracts demonstrated

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
python -m pytest tests/test_search_path_runtime.py tests/test_repetition.py tests/test_ai_search.py -q
```

Result during implementation: PASS, 38 tests.

## Performance harness

Five warmed repetitions were run with fixed depth, `use_tt=False`,
`use_ordering=False`, and `use_root_tactical=False`.

| Case | Required baseline median | Corrective R1 median | Nodes | Child external keys |
|---|---:|---:|---:|---:|
| Legacy 4x4 rooks, depth 3 | 37.690 ms | 39.163 ms | 137 / 137 | 134 / 0 |
| Semantic nifu fixture, depth 2 | 21.264 ms* | 19.571 ms | 17 / 17 | 15 / 0 |

Both candidate cases reported zero history/repetition tuple copies and
balanced push/pop.  Candidate legacy reported 134 incremental updates; the
semantic case reported 15 full component-diff fallbacks.  The baseline
semantic row uses a harness-only terminal metadata compatibility shim because
the required baseline's `CompiledSemanticRuleset` exposes limits under
`support`; the shim does not alter transition, identity, or search-path code.

## Pending final receipt fields

The final commit SHA, push result, fresh Zig build artifact, full pytest count,
and final clean-worktree check are appended when those gates complete.
