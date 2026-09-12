# GenericChess F94-R2 Stage-0 executor checkpoint

Status: Stage-0 implementation and result-free PREP are published; no Arena
or Heavy computation has run.

## Published scope

The independent staged PREP is
`docs/architecture/GENERICCHESS_F94_R2_STAGE0_PREP.json`. It preserves the
original F94-R2 READY candidate checkpoint, evaluator, ruleset, and three tape
corpora identities, while selecting opening index 0 on every tape. It fixes
4096-vs-256 nodes per move, depth 12, 8 MiB TT, one role-swapped pair per tape,
workers=1, six invocations, and twelve games. The boundary candidate remains
an A/C prerequisite short-circuit with compute zero.

The executor is
`scripts/f94_r2_strength_calibration.py --stage0`. It rechecks both the source
PREP and staged PREP before every candidate/tape, replays the selected opening
identity, and reuses the existing paired `run_arena`. It records role-swapped
game evidence, pair scores, per-tape direction, pooled descriptive effect/CI,
wall time, searched nodes/NPS, completed depth, fallback, and operational
errors in the independent Stage-0 schema. It cannot emit complete Layer-D
authority or PASS.

Focused Stage-0, strength-response, and F87A tests pass (23 tests). The exact
runtime command is:

```text
.venv\Scripts\python.exe scripts/f94_r2_strength_calibration.py --stage0 --prep docs/architecture/GENERICCHESS_F94_R2_STAGE0_PREP.json --stage0-result-output .generic_chess_flow/f94-r2-stage0-result.json
```

## Approval boundary

The final published checkpoint is the commit containing this closeout. A new
small/medium resource envelope and versioned compute plan must bind to that
exact SHA and command before Stage 0 is launched. Stage 0 is the only allowed
next computation; Stage 1 and the original full F94-R2 schedule require a new
review after Stage-0 evidence.
