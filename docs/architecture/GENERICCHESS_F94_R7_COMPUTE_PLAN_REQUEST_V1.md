# F94 R7 Layer-D compute-plan request (plan-only)

This is a prospective, result-free checkpoint. It requests review of an exact
compute plan and resource envelope; it does not authorize Heavy, Arena, native
compilation, or opening any R7 tape.

## Scope and immutable inputs

- Candidate sandbox checkpoint: `9696301a9773556d501a1fc48e00cc6f8db161b6`
- Frozen preregistration: `docs/architecture/GENERICCHESS_F94_R7_PREREGISTRATION_V1.json`
  (SHA256 `0bb5b352ab027e818d6dede058ff9d543b8f8c643b4805fa642783ec68c00237`)
- Frozen endpoint rule: `docs/architecture/GENERICCHESS_F94_R7_ENDPOINT_ACCEPTANCE_RULE_V1.json`
- Fresh R7 tape seeds: `9811`, `9812`, `9813`; R6 seeds `9801`, `9802`, `9803` are excluded.
- Matchups: primary `4096_vs_256`; diagnostics `1024_vs_256`, `4096_vs_1024`.
- Controls: `western_chess_qualification_control_v1`, `standard_shogi`.

The fixed sample is two controls × three tapes × three matchups × six
role-swapped pairs × two games: 18 invocations, 108 pairs, 216 games, and 216
action traces. Complete pair checkpoints are the only units eligible for
aggregation; all identity, fallback, digest, and operational failures stop the
run fail-closed.

## Exact runtime artifacts

- Plan: `.generic_chess_flow/compute-plans/f94-r7-layer-d-authority-20260913-v1.json`
- Envelope: `.generic_chess_flow/compute-plans/f94-r7-layer-d-authority-20260913-envelope-v1.json`
- Inner argv:
  `.venv\\Scripts\\python.exe -m scripts.f94_r7_layer_d_authority_executor --result --preregistration docs/architecture/GENERICCHESS_F94_R7_PREREGISTRATION_V1.json --result-output .generic_chess_flow/f94-r7-layer-d-authority-result.json`

The runtime plan binds its `sandbox_sha`, plan SHA, envelope digest, command
argv, preregistration SHA, endpoint-rule SHA, tape seeds, and workload counts to
the final published checkpoint. The envelope declares 20 logical CPUs, four
bounded lanes, 35 expected / 120 hard wall minutes, 12 expected / 24 hard
CPU-hours, 800,000,000 maximum nodes, 163,296 maximum plies, and 216 maximum
games. No nested native threads are enabled.

## Approval boundary

`compute-plan-status` must classify this as large. Chat scientific approval and
registered-Supervisor approval must independently bind the exact plan SHA,
envelope digest, current sandbox SHA, and argv before any `heavy` invocation.
The endpoint rule remains prospective-design-only and R6
`DEFER_CONTROL_NOT_READY` remains immutable. A smaller or partial run cannot
establish the fixed-sample authority rule and is not an allowed alternative.
