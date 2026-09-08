# F63-R1-R5 stage-scoped compute closeout

This checkpoint implements the Supervisor correction that rejected one
aggregate candidate-compute approval. The F63 candidate resume entry point now
accepts exactly one stage per invocation: `common-4`, `selected-8`, or
`selected-32`.

The three stages have separate versioned resource envelopes and compute plans:

- `common-4`: all three frozen candidates, four equal pairs each;
- `selected-8`: the reviewed common-stage winner, eight fresh pairs;
- `selected-32`: conditional confirmation, only after selected-8 review shows
  a positive continuation and that additional precision remains decision-
  relevant.

Each stage preserves game-v1 atomic progress, explicit per-game and
stage-level caps, pause/resume behavior, and decision-aware stopping. The
teacher result remains frozen evidence and is not rerun. No candidate Heavy
was started by this checkpoint.

Validation completed before closeout:

- `tests/test_f63r1_game_atomic_arena.py` and
  `tests/test_f63_champion_loop_causal_triage.py`: 22 passed;
- `py_compile` passed for the updated arena and F63 harness;
- `heavy-status` showed no running GenericChess Heavy;
- all three stage plans reported `compute_size=large` with `approval=null`.

The implementation checkpoint preceding this report is
`a85a59613125210ccb3c1fe5f74abd0d48067ccd`. After this report is committed
and published, the three ignored runtime plans must be rebound to that final
published sandbox SHA and rechecked. This report and the plan files authorize
no execution; each stage still requires separate Chat and registered-
Supervisor approval bound to its exact plan, envelope, and sandbox SHA.
