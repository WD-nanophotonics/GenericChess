# Profile normalization under other presets — evidence copy

Public copy of the evidence behind
`docs/research/PROFILE_NORMALIZATION_PRESETS_20261018.md`.

Provenance: **DEEPSEEK_AUX**, branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18, run against Git HEAD
`31878037`. Auxiliary result; no other role has rerun it. No strength,
playing-quality, utility or price claim.

Private originals remain in
`.local_agent/profile-normalization-presets-20261018/`; the replay copy is in
`.local_agent/profile-presets-replay-20261018/`.

## Files

| file | bytes | SHA-256 |
|---|---|---|
| `plan.json` | 3128 | `ec1e8d355c37013f99adb56ea8069853332cd83a97e5aa61e4750a04c5d4496a` |
| `plan-log.json` | 197 | `9a52febb203f24fec0e86960f7fb76c844cee061d4b99a302cd6cae97c40c3fc` |
| `scan_profile_presets.py` | 6498 | `b8d5879f1ca083215c33e6a15a0a27bbfa46a6a1a92bf243863420f6a5b435bf` |
| `results_profile_presets.json` | 335442 | `a65013c73e968c13ed5e3addeaaf0e566790c144b6c46b325263d55874d76137` |
| `results_profile_presets.first-attempt.json` | 335442 | `840a266002f1ac82d85ad4dad3affdb9e79fe288ab918cafcd9cf421fdcf4ac3` |
| `validation_report.json` | 2659 | `cd0bf4026a50ede281c6a88482c6e265b582f8a56a748534387f239db48fda39` |
| `replay_check.json` | 2981 | `7cd440babadc964c0af8c648f80779429d3ba61308761f2b22db65442a02285a` |
| `classic_like_check.json` | 2956 | `f1ca145e83afa26989a19d177a1c59a01eb0aea3447d75562aef6516ead8c45f` |

`plan.json` carries the pre-written endpoints and decision rule; its hash is
`ec1e8d35...`, recorded in `plan-log.json` with `status: written_before_run`
and `recorded_at_utc 2026-10-18T12:57:43Z`, before the scan executed. The
stored result carries that plan hash, the imported endpoint script hash, the
source-file hashes and Git HEAD `31878037`.

## Preserved defect

The first execution wrote `results_profile_presets.first-attempt.json` and
then failed in the console summary with `KeyError: 'material_tie_groups'` (a
summary-printing key name, not a computation). Its `blocks` array is identical
to the fixed run; only `generated_at_utc` differs. Both outputs are kept so
the failure stays auditable.

## Reproduction

```
python .local_agent/profile-normalization-presets-20261018/scan_profile_presets.py
```

The script resolves the checkout root as `Path(__file__).parents[1]`, so it
must sit one directory below the repository root. Deterministic, zero search,
about 1.8 s for both presets; it re-derives the same `blocks`, plan hash and
source hashes. It imports the published
`.local_agent/profile-normalization-20261018/scan_profile_normalization.py`
unchanged and only substitutes `setup_preset` through `dataclasses.replace`.

## Validation performed

- Replay in `.local_agent/profile-presets-replay-20261018/`: `blocks`,
  `design`, `plan_sha256`, `source_sha256` and `overall_decision` identical to
  the stored run — see `replay_check.json` and `validation_report.json`.
- First attempt versus fixed run: `blocks` identical,
  `results_profile_presets.first-attempt.json` kept.
- Across 400 type rows / 199 distinct movement signatures, no signature
  carries more than one raw capability value.
- Post-hoc (not pre-registered) `classic_like` re-check of seeds 293010,
  293021 and 293033 at board size 8 in `classic_like_check.json`: seed 293033
  reproduces its rounding tie, the other two do not tie.
- The scan script byte-compiles; every JSON here parses.

## Limits

- Two presets, one board size, one seed block, one evaluator weight.
- Preset substitution only partially re-draws capability signatures (23 of 40
  seeds identical across the two presets), so the 80 rules are not 80
  independent draws.
- A tie group is integer compression, not evidence of strategic equality; no
  strength, utility or human-price claim is made.
- Files contain project-relative paths, role/session identifiers, seed numbers
  and measurements only.
