# GenericChess F83-R1 Durable F62 Provenance and Cost-Bound Corrective

## Scope

This corrective order repairs the durable semantics of F83 C1 relative-evidence
artifacts. It does not change production code, resample roots, rerun teacher
probes, enter C2, run Arena, or start Heavy compute.

Baseline checkpoint: `255fa14aee514537a80d735f79e43441c485e4e6`.

## F62 historical provenance

The historical F62 root identity set is reconstructed from the tracked
`scripts/f62_learned_champion_repeatability.py` `_fresh_records(compiled,
smoke=False)` contract. The durable manifest is
`artifacts/f83_c1_relative_evidence/f62_historical_root_identity_manifest.json`.

It records the 630101 opening seed, 630102 corpus seed, 32 source groups,
three roots per group, and the 48/24/24 split. The reconstructed set contains
96 unique canonical position keys and verifies:

- F62 stage identity SHA: `e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70`
- F62 records SHA: `b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61`
- Manifest content SHA: `38b7a9e41caaf6e1f7ce3bc07084f75239c893a93af140f5db25cc61356c8c88`

The existing 54-root F83 corpus was replayed with `GameSession`; every root
remains ongoing, every canonical position key matches, and all 54 keys are
unique. Its root-set identity is
`c197799729877dc836116740d0827de0b02cfabde42e45c8e53e19f61c3ee108`.
Overlap with F62, F75, F77, F78/F80, and F81 is zero in every set.

## Cost-bound correction

The six original resource probes remain exactly six `TIME_CAP` observations,
with the original probe artifact SHA preserved as
`3b05ff6d999928f97906b4eedae611b5c15b50ae06786cbb674cfaef3063e2ab`.
Because all probes terminated at the wall cap, teacher-call counts and search
telemetry are unknown; no capped observation is treated as a teacher label.

The corrected probe artifact is explicitly lower-bound-only:

- CPU lower bound for 48 roots: 2.4 hours.
- Wall lower bounds by lanes: 144, 72, 36, and 18 minutes for 1, 2, 4, and 8 lanes.
- Calibration geometry: at most 2 concurrent roots; higher concurrency is unmeasured.
- Each result retains its replay-derived legal-action count and marks candidate-action count, teacher calls, and search telemetry unavailable.

Classification remains
`C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_LOWER_BOUND_ONLY`.

## Verification

The focused F83 contract suite passes, including tracked-record reconstruction
and fresh root replay/disjointness checks. The implementation and
durable artifacts contain no `.generic_chess_flow` dependency and use POSIX
repository paths for durable references.

F84 may extend calibration on the existing resource roots with a larger cap;
that work is outside this corrective order.
