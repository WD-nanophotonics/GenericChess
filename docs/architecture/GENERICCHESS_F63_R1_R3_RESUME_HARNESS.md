# F63-R1-R3 candidate-resume harness

The expensive F63 entry point is resume-only. It first validates the frozen
seven-pair teacher decision artifact against the original pair-v1 manifest,
opening corpus, legal replay, terminal results, telemetry, pair scores, and
file hashes. It never calls the teacher stage and rejects a missing, stale, or
expanded teacher inventory.

After that validation, the harness verifies the frozen F62 stage and records
identities, reuses the exact persisted Gen2 checkpoint for seed 59012, fits
only seeds 59011 and 59013 from the already persisted F62 spectra, and writes
all three candidate identities before the first Arena call.

Every candidate stage uses game-v1 `run_arena_game_resumable` with explicit
per-game wall/node/ply caps, stage-game and stage-wall ceilings, bounded
concurrency, a stable pause path, and a stable stage ID. The common four-pair
comparison does not use positive decision stopping, preserving equal evidence
unless a catastrophic cap/pause occurs. Selected stages may use the frozen
F63 mean-plus-better-pairs decision criterion; the 32-pair stage still relies
on its actual planned confirmation statistic for positive classification.

The candidate-resume command is intentionally separate from the historical
teacher path and is not an approval or execution of the candidate Heavy. A
versioned compute plan is generated only after the integration checkpoint is
published and must pass the repository's Chat-plus-Supervisor gate before any
Heavy launch.
