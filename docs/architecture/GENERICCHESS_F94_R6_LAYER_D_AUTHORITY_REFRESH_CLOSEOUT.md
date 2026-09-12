# F94 R6 Layer-D Authority Refresh PREP Closeout

Work order: `GENERICCHESS-F94-R6-LAYER-D-AUTHORITY-REFRESH-PREP`

This checkpoint implements only the result-free R6 protocol, PREP artifact,
fail-closed executor, and tests. No Arena, Heavy, native compile, Layer-D
calibration, or compute approval request was run or created.

## Frozen authority

- Protocol/executor/tests provenance commit:
  `621ea925952fb0189e97f59f2e5bba255eed6e9f`
- PREP artifact:
  `docs/architecture/GENERICCHESS_F94_R6_LAYER_D_AUTHORITY_REFRESH_PREP.json`
- PREP byte SHA256:
  `1cc910c3339a9a3c6407fd2860fe1fe63414ec26f8bd845257b57eaab3028696`
- Published sandbox checkpoint: recorded by the Courier closeout command.

The PREP freezes Western qualification control
`western_chess_qualification_control_v1` and Built-in Standard Shogi as the
two positive semantic controls; authoritative tapes are exactly 9801/9802/9803
and explicitly exclude all 9401–9703 historical seeds. The fixed ladder is
256/1024/4096 with matchups 1024-vs-256, 4096-vs-1024, and 4096-vs-256.
Each control has 9 invocations, 54 pairs, 108 games, and 108 traces; the two
controls together have 18/108/216/216. The A/C prerequisite boundary remains
zero Layer-D compute.

## Classification and evidence guarantees

The executor validates every opening corpus and identity before selecting an
Arena runner. It enforces role-swapped games, opening-position identity,
complete action/ply traces, trace hashes, and role-aware search telemetry.
Operational, fallback, explicit-censor, and evidence-integrity failures take
precedence; depth/horizon censoring is inclusive at 0.5. Each matchup uses an
independent bootstrap over only its current 18 pair scores, and historical
P0/R2/R3/R5/qualification-pilot/Stage-1 observations are explicitly
non-poolable.

## Verification

`.venv\\Scripts\\python.exe -m pytest -q tests/test_f94_r6_layer_d_authority_refresh.py`

Result: `7 passed`. Python bytecode compilation also passed. The checkpoint was
published to `origin/sandbox` at the exact synchronized SHA reported with this
closeout.
