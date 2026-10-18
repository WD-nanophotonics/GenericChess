# Static-profile normalization scan — evidence copy (2026-10-18)

Public copy of the evidence behind
`docs/research/PROFILE_NORMALIZATION_20261018.md`.

Provenance: produced by **DEEPSEEK_AUX** in the isolated
`codex/deepseek-aux` worktree, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, on Git HEAD `b1d13325`. This is an
auxiliary result; no other role has independently rerun it, and it makes no
strength, utility or game-outcome claim.

The files were copied byte-for-byte from the Git-ignored private directory
`.local_agent/profile-normalization-20261018/`. Private originals remain
there. The stored `results_profile_normalization.json` and `plan.json` are
unchanged since the run. `validate_profile_results.py` and its
`validation_report.json` were revised in the same session (2026-10-18) to
recompute two further aggregate fields; the stored result was re-validated,
not rewritten.

## Files

| file | bytes | SHA-256 |
|---|---|---|
| `plan.json` | 2180 | `eeadd8ca8f5c42f05f78d1f5bbecf734193ec1525b2156c7e172330611894c64` |
| `plan-log.json` | 204 | `b0ed2e4217e6c6ff2b2c334879226037367ead21558eb0478b0ce2ef588f8881` |
| `scan_profile_normalization.py` | 11048 | `2a8f630d919681d35c11c563d635c73b1ff01f5b31d4415cd65f6be0c331a397` |
| `results_profile_normalization.json` | 78662 | `900f31275e8e3fd628e948dcb00e94bfc61d80c1315393a5fcce9350391bcec1` |
| `validate_profile_results.py` | 7943 | `231bdaaa31160ff06f5b9416f60781bc8603304f403fe8f5c574e48f9febcad1` |
| `validation_report.json` | 1471 | `68bc00df9d50b27a78117470e824b0f55b93231cd75e987e6ac58fc2ecd60e0e` |

`plan.json` carries the pre-written endpoints and decision rule; its hash is
`eeadd8ca...`, recorded in `plan-log.json` with
`status: written_before_run` and `recorded_at_utc 2026-10-18T12:51:19Z`, before
the scan executed. `results_profile_normalization.json` stores that same plan
hash plus source-file hashes and the Git HEAD it ran against.

## Reproduction

```
python .local_agent/profile-normalization-20261018/scan_profile_normalization.py
python .local_agent/profile-normalization-20261018/validate_profile_results.py \
       .local_agent/profile-replay-20261018/results_profile_normalization.json
```

The scan is deterministic, zero-search and takes about 0.16 s on the recorded
machine. It regenerates seeds `291001-291040` with
`GeneratorConfig(board_size=4, setup_preset="classic_like")`, builds each
profile with `EvaluationConfig(hand_weight=0.9)`, and writes one JSON result.
A rerun reproduces the `rules` and `aggregate` blocks exactly; only
`generated_at_utc` (and therefore the whole-file hash) changes.

The script resolves the checkout root as `Path(__file__).parents[1]`, so it
must live one directory below the repository root (as it does in
`.local_agent/`). The first execution used `parents[2]`, failed on import
before writing any output, and produced no result file; the published run is
the only evidence.

## Validation performed

- Replayed from a copied script and plan in
  `.local_agent/profile-replay-20261018/`: `rules`, `aggregate`,
  `source_sha256` and `plan_sha256` were identical to the stored run.
- `validate_profile_results.py` recomputed every aggregate field from the
  stored per-rule rows, re-derived inversions, tie groups and ratio pairs
  directly from the raw rows, and re-checked the stored decision against the
  pre-written rule. `validation_report.json` records `problems: []`.
- That validator revision also re-derives `repeated_movement_signatures` and
  `signature_raw_mismatches` from the stored per-row `signature` and `raw`
  values (18 and 0 respectively), so the "every aggregate field" statement
  includes those two fields. A copy of the validator is published here; it
  accepts `--stored <result.json>` so it can run against the public copy:
  `python validate_profile_results.py --stored results_profile_normalization.json
  <replay.json>`.
- The scan script was byte-compiled and the result and plan JSON parsed
  successfully.

## Scope limits

- 40 rules from one generator family, board size 4, `classic_like`, three
  ordinary piece types per rule (120 types, 120 type pairs).
- Zero search: no strength, utility, playing-quality or human-price claim.
- The floor-of-1 endpoint was never reached because the weakest normalized
  value in the sample was 101; that endpoint is untested here, not passed.
- No seeds, thresholds or endpoints were retuned after seeing the result.

## Publication boundary

The copies contain project-relative paths, role/session identifiers, seed
numbers and technical measurements only. A scan of these files for personal
paths, account identifiers, tokens, passwords and API keys returned no hits.
