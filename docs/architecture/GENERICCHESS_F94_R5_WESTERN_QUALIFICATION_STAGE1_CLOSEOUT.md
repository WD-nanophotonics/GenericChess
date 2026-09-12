# F94-R5 Western Qualification-Control Stage 1 Closeout

Status: `STAGE1_RESULT_COMPLETE`.

This closeout records the one Chat- and registered-Supervisor-approved Stage-1
calibration run. It does not authorize Stage 2, full R5, tuning, training,
promotion, production mutation, or a Layer-D claim.

## Immutable run binding

- Sandbox SHA: `e2d0cb15a07f64799a4e66f654efe9b656d9ea48`
- Compute plan ID: `f94-r5-western-qualification-stage1-20260913-v4`
- Compute plan SHA256: `573d881acc6a6a7368b174dc9c44331a6613abe636fceb8f9117ce8ebc3dc0c6`
- Resource-envelope SHA256: `fced4b678bdf4eeeaea71c294404d1f7ba328820ae9a53f3d0700780092a1b1e`
- Heavy run ID: `f94-r5-western-qualification-stage1-20260913-v4-2cc133c8ad86`
- Result artifact: `.generic_chess_flow/f94-r5-western-qualification-stage1-result.json`
- Result artifact byte SHA256: `503f583621c8214a373be6f79d20ef29f8bcb9a298409093e5fbca00bc823d1f`
- Result executor SHA256: `b10383865464b32c287b2fd11d6f5e82683d39fbe8edc39c853f2885a7dcab77`
- PREP byte SHA256: `5b517ae9660928ad983cf8cf49280b35945f1a8fffcfbc87af8f946b93e1370f`
- PREP fingerprint: `a67911ccea9330a5596285ea3dc571e885805864247c25bd8b9ba12284280d31`
- Protocol source SHA: `ae70cf306af4bf406491863740506150d872d2a1`
- Heavy exit code: `0`

The exact approved child command was:

```text
.venv\Scripts\python.exe -m scripts.f94_r5_western_qualification_stage1_executor --result --prep docs/architecture/GENERICCHESS_F94_R5_WESTERN_QUALIFICATION_CONTROL_STAGE1_PREP.json --result-output .generic_chess_flow/f94-r5-western-qualification-stage1-result.json
```

## Frozen scope and accounting

- Tapes: `9701`, `9702`, `9703`
- Arena invocations: `3`
- Role-swapped pairs: `18` (six per tape)
- Games: `36`
- Action traces: `36`
- Nodes per move: `256` vs `4096`
- Max depth: `12`; TT: `8 MiB`
- Workers/concurrency: `1`/`1`
- Bootstrap: percentile bootstrap of pair score mean, `10,000` resamples,
  seed `9701001`, confidence level `0.95`

The result reports `control_only=true`, `production_changed=false`,
`no_tuning=true`, `not_layer_d_authority=true`, and `stage_2_authorized=false`.
All prior pilot, R2, R3, R5, and P0 observations remain unpooled.

## Observed result

- Direction: `STABLE_POSITIVE_CONTROL`
- Pooled pair count: `18`
- Pooled mean pair score: `0.8611111111111112`
- Tape means: `0.8333333333333334`, `0.875`, `0.875`
- Bootstrap 95% CI: `[0.7638888888888888, 0.9444444444444444]`
- Pooled censoring audit: child-depth-ceiling hits `2/3764` (`0.0005313496280552603`);
  strongest-vs-weakest horizon max-ply hits `1/36` (`0.027777777777777776`).

The raw result remains ignored runtime evidence. Any retry or scope expansion
requires fresh Chat scientific approval and registered-Supervisor approval
bound to new exact plan, envelope, sandbox, and evidence hashes.
