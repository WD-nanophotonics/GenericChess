# F94-R5 horizon-aware result-free PREP closeout

This checkpoint freezes the next Layer-D protocol without running Arena,
changing a checkpoint, tuning search/evaluation, or interpreting R3 as a
RESULT.  The machine-readable PREP is
`GENERICCHESS_F94_R5_HORIZON_AWARE_PREP.json`.

R5 keeps the fixed 256/1024/4096 node ladder, depth 12, 8 MB TT, six
seat-swapped pairs per tape, and the existing three deterministic opening
corpora.  It freezes each candidate's compiled `max_ply` rather than raising
the depth ceiling or changing a ruleset.  The F86N-R1 boundary stays an A/C
short-circuit and spends zero Layer-D compute.

The new schema makes three observations independently auditable:

- The depth-ceiling gate uses only the 4096-node `child` telemetry from the
  strongest-vs-weakest matchup.  Raw `child` and `parent` hit/count records
  remain available, but parent hits do not enter that fraction.
- For every game it records termination status, actual plies, `max_ply` and a
  `max_ply_hit` flag.  Horizon fractions are emitted per tape, per matchup,
  and pooled for strongest-vs-weakest.
- Every game has a deterministic action trace bound to tape/corpus, matchup,
  game/pair index, role ownership, parent/child node budgets, opening and final
  identity keys, and a trace SHA-256.  This is observational telemetry only:
  it does not alter action choice, search order, TT, evaluator, or termination.

The child ceiling and strongest-vs-weakest pooled horizon gates are both
`>= 0.5 => DEFER`.  They are explicitly labeled GenericChess-specific empirical
gates, not externally validated game-quality criteria.  Sparse child depth
hits below the gate remain descriptors; explicit censor flags take precedence.

Focused protocol tests pass without calling Arena: `tests/test_strength_response.py`,
`tests/test_f94_r5_horizon_aware_prep.py`, and `tests/test_f94_r2_stage0.py`.
No R5 RESULT, Arena run, Heavy job, training, Layer E, Stage 1, Gen1→GenN,
AlphaSho benchmark, promotion, or search/evaluator/ruleset change is included.
