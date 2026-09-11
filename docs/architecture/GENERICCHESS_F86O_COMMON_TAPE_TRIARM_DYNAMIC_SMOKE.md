# GenericChess F86O common-tape tri-arm dynamic smoke

Status: bounded dynamic smoke complete. The first F86O PREP executable exposed
a result-only aggregation defect before it could emit a result artifact. It
was superseded fail-closed by corrected PREP `dac3a4b269041a0c20b9cdaf02e6d5c845f6d62d`.
That corrected PREP is the sole RESULT authority. The immutable RESULT SHA and
report SHA are recorded by Courier closeout.

## Frozen contract

The corrected PREP freezes six serialized rulesets, four 32-value policy tapes,
canonical legal-action ordering, tape selection, seat assignments, terminal
labels, pair accounting, and the exact budget of 12 games at `max_ply=32`.
Manifest blob:
`1d16cf69a7ce5f7347352162dcbd351485e8c5af`.

The three arms are:

| Arm | Definition | V4-3 fingerprint | V5-3 fingerprint |
| --- | --- | --- | --- |
| L | `ORTHO4_LEGACY_ORDINARY`: F86C ordinary movements unchanged; Anchor changed only to ORTHO4 | `ea993a6147595b1ce740cc91ad426a96395edcb6de479c95c23ecc88800a0e17` | `1a256a4fcc763cb6f4e5ca1037a77b72885d4e85a4d5e46ccf88c69f552b266d` |
| F | `ORTHO4_FULL_REVERSE_ORDINARY`: exact F86I frozen candidates | `8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d` | `29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff` |
| N | `TRANSPORT_AWARE_SIGNED_R1`: exact F86N-R1 frozen candidates | `856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2` | `e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5` |

The shared tapes use
`python_random_mt19937_random_floor_index_v1`, with selection
`min(floor(u[k] * legal_count), legal_count - 1)` and independent per-policy
consumption. Seeds are V4-3 A/B `8624301/8624302` and V5-3 A/B
`8625301/8625302`. Every arm/sample uses A/B and B/A once.

RESULT deserialized only this manifest. The PREP→RESULT change set added the
compact `summary.json`, this report, and result-only tests; the runner,
manifest, six rulesets, four tape payloads, action ordering, and budget were
not changed after corrected PREP.

## Dynamic accounting

There were exactly 12 recorded games: 3 arms × 2 samples × 2 seat
assignments. Each compact game record stores arm, sample, seat assignment,
terminal label, winner, plies, branching sequence, tape consumption,
action-sequence SHA-256, and final-position digest. Full action dumps are not
tracked.

| Arm | Sample | A/B | B/A | Median length |
| --- | --- | --- | --- | ---: |
| L | V4-3 | ongoing@32 | stalemate@6 | 19 |
| L | V5-3 | ongoing@32 | stalemate@28 | 30 |
| F | V4-3 | ongoing@32 | ongoing@32 | 32 |
| F | V5-3 | ongoing@32 | ongoing@32 | 32 |
| N | V4-3 | ongoing@32 | ongoing@32 | 32 |
| N | V5-3 | ongoing@32 | ongoing@32 | 32 |

Per-arm terminal distributions are:

| Arm | Checkmate | Stalemate | Repetition | Ongoing@32 |
| --- | ---: | ---: | ---: | ---: |
| L | 0 | 2 | 0 | 2 |
| F | 0 | 0 | 0 | 4 |
| N | 0 | 0 | 0 | 4 |

The ARM-N route is therefore
`TRANSPORT_BACKBONE_DYNAMIC_NONTERMINATION_FAILURE`: all four ARM-N games
were `ongoing@32` or repetition. No pair was scoreable; any pair containing an
ongoing game remains unresolved, and no incomplete pair was assigned a draw
score. No checkmate or repetition was observed.

ARM-N versus ARM-L has one fewer stalemate in each sample and the same
32-ply median on both samples. ARM-N versus ARM-F has the same ongoing-or-
repetition count in both samples. These are bounded descriptive controls, not
strength evidence.

The shared F86 quality definition is recorded in `summary.json` for every arm
and sample. Aggregate median branching / p10 / p90 are L `3/2/4`, F `5/3/9`,
and N `5/3/7`; aggregate median lengths are L `30`, F `32`, and N `32`.

## Scope and verification

Real games: 12. Max ply: 32. Tactical nodes: 0. BFS game-state expansion: 0.
Teacher/training: 0. F85: 0. Heavy: 0. Default generator changed: false.
No AlphaSho benchmark, C2, admission threshold, or search-agent work was run.

Exact focused verification:

```text
.venv\Scripts\python.exe -m pytest tests/test_f86o_common_tape_triarm_dynamic_smoke.py
6 passed
```

The accepted conclusion is limited to this smoke: the transport-aware signed
candidate did not avoid the bounded nontermination mode in either targeted
sample under the common tapes. No claim about strength, skill discrimination,
or production-generator quality is made.
