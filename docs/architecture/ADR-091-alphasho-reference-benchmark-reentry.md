# ADR-091: AlphaSho reference benchmark re-entry

## Status

Accepted for F30 audit execution.

## Decision

AlphaSho is an external, read-only reference.  F30 records its exact Git
identity, interpreter dependencies, source hashes, and checkpoint identity
before invoking the existing heuristic entry point.  Every Git query uses a
per-command `safe.directory` override; no global Git configuration or
external worktree mutation is permitted.

The frozen F22 ten-position USI references are replayed against the current
Standard Shogi product through the existing SFEN/USI adapter.  GenericChess
uses fixed node budgets 128, 256, 512, 1024, and 2048 with two fresh players
per position/budget.  Fresh AlphaSho probing, when the local environment is
stable, uses the current FULL heuristic profile for three independent 0.50 s
searches per position.  These measurements are descriptive reference
evidence only; they do not authorize evaluator tuning, coefficient fitting,
opening-book changes, or production rule/search changes.

If the external entry point cannot be reproduced, F30 still freezes the
historical replay and records the exact recovery boundary F30A.  A paired
strength result is never inferred from historical move agreement.

## F30 result

The local reference was reproducible at AlphaSho HEAD
`61c35fa70ca1f59264045ad1425d6757ad6666a2`, with a clean worktree, Python
3.13.2, cshogi 1.0.4, Torch 2.13.0+cpu, and the recorded checkpoint hash
`65204194f06e60c2d66955967e55595b514816300f4d576f1c981f1cfc50b4f1` (the
heuristic entry point does not load that checkpoint).  The ten F22 historical
references were all legal in the F29 product and reproduced deterministically
at all five budgets.  Fresh 0.50 s selection was complete and stable for all
ten positions in both engines.  The 20-game paired run completed without
technical failures: 18 games ended in checkmate and 2 in GenericChess's
stalemate result; no strength claim is made from this small audit.

The durable evidence is in
`tests/fixtures/f30_alphasho_reference_benchmark.json`.
