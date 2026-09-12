# F94 R6 Layer-D Authority Compute Plan (Plan-Only Checkpoint)

This is a plan-only checkpoint. It does not authorize or run Heavy, Arena,
native compilation, or any Layer-D computation.

## Exact binding

The proposed run is bound to the already published code checkpoint
`81a70abdd48e67b2aa0e903a8547984653a926b3` and the frozen PREP byte SHA
`30d4405e1eccdd0f321a8e7c60594bb38defe294f8532063cdac4b2daceb7210`.

Runtime plan artifact:
`.generic_chess_flow/compute-plans/f94-r6-layer-d-authority-refresh-20260913-v1.json`

Runtime resource envelope:
`.generic_chess_flow/compute-plans/f94-r6-layer-d-authority-refresh-20260913-envelope-v1.json`

Plan SHA256:
`4a36f01fbb7d8c979b8d8c82aad8d5bd30d7fec6ffd36a6bb2d43acd9d640805`

Envelope digest:
`55ecc9411dfd8674139a745950268253bb61211d74da07cf2d8206b7399e8154`

The exact inner argv is:

```text
.venv\\Scripts\\python.exe -m scripts.f94_r6_layer_d_authority_refresh_executor --result --prep docs/architecture/GENERICCHESS_F94_R6_LAYER_D_AUTHORITY_REFRESH_PREP.json --result-output .generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json
```

The wrapper declaration, if later authorized, is:

```text
.\\generic-chess-flow.cmd heavy --resource-envelope .generic_chess_flow/compute-plans/f94-r6-layer-d-authority-refresh-20260913-envelope-v1.json --compute-plan .generic_chess_flow/compute-plans/f94-r6-layer-d-authority-refresh-20260913-v1.json -- <inner argv above>
```

## Fixed sample and resources

The plan covers exactly 18 invocations, 108 pairs, 216 games, and 216 action
traces: two controls × three tapes × three matchups × six role-swapped pairs ×
two games. This is decision-relevant because the frozen authority classifier
requires each control to pass all three independent matchup bootstrap tests;
an omitted matchup or early stop would create selection bias and cannot support
`CALIBRATION_READY`.

The envelope declares 20 logical CPUs, one intended lane, 90 expected wall
minutes / 240 hard wall minutes, 12 expected / 24 hard CPU-hours, 4 GiB
expected / 8 GiB hard peak RAM, 800,000,000 maximum nodes, and 163,296 maximum
plies. The executor remains `workers=1` because its frozen protocol preserves
deterministic invocation ordering and avoids nested native-search contention;
this is a concrete technical constraint, not an unexamined default. The
envelope records four lanes as a future capacity bound only; no parallel lane
is enabled by this plan.

Checkpointing is pair-granular and retains only ignored runtime evidence. Any
identity, telemetry, cap, fallback, censor, evidence-integrity, or operational
failure stops the run. Later matchups must still not be selected from
intermediate results. Staged, one-control, 108-game, or early-stop alternatives
are insufficient for the fixed-sample authority rule.

The plan was validated read-only with `compute-plan-status`; it is classified
large and has no approval. Chat scientific approval and registered Supervisor
approval must bind this exact plan SHA, envelope digest, argv, PREP SHA, and
sandbox SHA before any Heavy command may be considered.
