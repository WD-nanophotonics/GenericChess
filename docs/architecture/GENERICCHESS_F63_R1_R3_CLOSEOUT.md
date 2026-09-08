# F63-R1-R3 resume harness and compute-plan closeout

Status: integration and plan preparation complete; the candidate Heavy remains
unapproved and was not started.

Corrective parent: `acc74ac9063530da7137b460d2bc035858d30809`

Integration checkpoint: `c97dd22fa7d25307f48512119cc361bc9d73a6cd`

## Delivered

- Added and committed the machine-readable frozen teacher decision artifact
  for exactly seven preserved teacher-8 pair-v1 files. Local replay and
  identity/hash validation returned `PASS_LOCKED`, 7 completed pairs, and
  total 4.75; no eighth pair was invented.
- Added the fail-closed F63 `--resume-only` entry path. It validates the frozen
  teacher decision, F62 stage/records identities, exact persisted seed-59012
  Gen2, and all three candidate identities before any Arena call. The
  expensive resume path cannot call the teacher stage.
- Routed candidate stages through game-v1 with explicit per-game and stage
  caps, bounded concurrency, stable stage IDs, pause-file propagation, and
  explicit partial status. Common 4-pair comparison keeps all three
  candidates equal unless a catastrophic stop occurs.
- Wired decision-aware stopping for selected stages while retaining
  `strength_estimate_complete=false` for decision-only partial output and
  preserving the actual 32-pair confirmation statistic requirement.
- Prepared the exact runtime compute envelope and versioned compute plan:
  `.generic_chess_flow/f63-r3-candidate-resource-envelope.json` and
  `.generic_chess_flow/f63-r3-candidate-compute-plan.json`.

## Verification

The bounded focused suite passed 34 tests:

```text
tests/test_f63_champion_loop_causal_triage.py
tests/test_f63r1_game_atomic_arena.py
tests/test_learning_arena_integrity.py
tests/test_learning_selfplay_arena.py
```

The real local teacher-evidence validation returned `PASS_LOCKED 7 4.75`.
`compute-plan-status` returned `compute_size=large`, plan SHA
`06d0a438ca9218c6e45b65e8cdd4bab5b53c8b21b48aa30e20864af6a58899da`, envelope
SHA `d3ea5cd5b807acc3d8a9fc3a3f8e3af710378ad2c14b9d8194e5b7304ba2b5cd`, and
no approval. The published sandbox SHA is exactly
`c97dd22fa7d25307f48512119cc361bc9d73a6cd`; master remains unchanged.

No teacher rerun, candidate game, Heavy, promotion, master write, or compute
approval was performed. The plan is ready for Chat and registered-Supervisor
review; this closeout does not authorize execution.
