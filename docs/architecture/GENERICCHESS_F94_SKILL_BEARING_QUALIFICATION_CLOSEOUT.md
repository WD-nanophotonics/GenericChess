# GenericChess F94 Layer-D skill-bearing qualification

## Scope

F94 adds the missing Layer-D strength-response protocol as a compact adapter
around the existing `learning.arena` paired runner and
`learning.openings` evaluator-neutral corpus. It does not create a second
match runner, alter the evaluator, tune search, or start learning.

The public entry points are:

- `prepare_strength_response(...)`, which freezes a result-free PREP;
- `measure_strength_response(...)`, which consumes that PREP and emits a
  stable RESULT;
- `QualificationReport.with_strength_response(...)`, which attaches Layer D
  while preserving the existing A-C meanings.

## Frozen protocol

The default ladder is 256 / 1024 / 4096 nodes per move (1:4:16), with one
fixed evaluator, transposition-table size, max-depth ceiling, and opening
corpus across all three paired comparisons: 4x-vs-1x, 16x-vs-4x, and
16x-vs-1x. Each pair uses the same opening in both role-swapped games. The
PREP records ruleset, candidate, evaluator, budget, depth, pair, corpus,
opening/tape seeds, bootstrap, classification, and experiment identities.

RESULT retains pair scores, role swaps, per-opening/tape evidence, paired
bootstrap intervals, search telemetry, and compute usage. Missing pairs,
fallbacks, depth-censored searches, mixed tape effects, uncertain curves, and
inverted responses are `DEFER`; no single quality score is substituted.

Layer D remains diagnostic for the legacy `PLAYABILITY` target. Selecting
`SKILL_BEARING` makes D a blocking admission layer, so A/C failures do not
consume Layer-D compute and an unmeasured D result cannot admit a skill suite.

## Verification

Focused F94 protocol tests and the existing F87A qualification contract tests
pass: 16 passed. Tests use deterministic synthetic Arena summaries for the
classification and fail-closed cases; no real calibration RESULT is claimed
by this checkpoint. A real Western Chess / Standard Shogi / boundary pilot
must remain a separately frozen PREP/RESULT bounded experiment.

`QualificationReport` continues to expose Layers A-E and retains the existing
PLAYABILITY behavior when Layer D is not selected.
