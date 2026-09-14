# F82 C2 Arena2 partial-prefix protocol closeout

- Published implementation SHA: `9870b6903a4aac078be985ef0bcb5a8b9467a0ac`
- Focused regression: `tests/test_f63r1_game_atomic_arena.py`, `tests/test_f82_c2_parent_anchored_repeatability.py`
- Verification: `17 passed`

## Delivered behavior

The resumable Arena runner now writes an atomic `partial-game-XXXXXX-owner-X.json` record whenever a bounded game is interrupted. The record is bound to the existing semantic game identity and carries the replayable in-game action prefix, ply count, cumulative searched nodes, and any per-search elapsed/termination telemetry. A later invocation validates that identity, replays the opening and prefix history, resumes the same role-swapped game, and removes the partial record only after a terminal game file is atomically written. Completed-game identity remains separate from operational wall-time caps.

The focused regression covers owner-0 completion, owner-1 cap interruption, partial-prefix persistence, and owner-1 continuation to a complete pair without restarting the recorded prefix. Existing cap, identity, pause, and paired-statistics tests remain green.

No candidate, parent, corpus, seed, search parameter, resource envelope, or promotion state changed. No Heavy was launched under this checkpoint: the registered Supervisor rejected the uninstrumented v8 wall extension and required this reusable long-game protocol first. A new exact continuation plan and approvals are required before any compute.
