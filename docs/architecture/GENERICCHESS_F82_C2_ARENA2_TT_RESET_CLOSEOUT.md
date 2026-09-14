# F82 C2 Arena2 symmetric TT-reset protocol closeout

- Published implementation SHA: `6bd367d19a381d518ee9a17a504fa7b1efead7cb`
- Focused regression: `tests/test_f63r1_game_atomic_arena.py`, `tests/test_f82_c2_parent_anchored_repeatability.py`
- Verification: `18 passed`

## Protocol boundary

The Arena configuration now exposes an explicit `tt_reset_each_move` contract. When enabled, both parent and child engines are recreated before every move, so a full game and a partial-prefix continuation use the same TT-reset rule. The F82 pair-0 harness binds this flag in its semantic progress identity and uses a new `f82-c2-arena2-tt-reset` progress namespace; the prior persistent-TT owner-0 checkpoint remains untouched and is not mixed into this protocol.

The existing atomic partial-game checkpoint still carries action/history, cumulative nodes, and telemetry. A resumed owner-1 game therefore replays the same prefix while applying the same explicit TT-reset behavior as its paired owner-0 run. Candidate, parent, corpus, seed, 512 nodes/move, depth 12, TT capacity (8 MiB), and one lane remain unchanged. Wall bounds are back to the previously approved 7200-second values.

No Heavy was launched under this checkpoint. A fresh Chat compute plan and exact Supervisor approval are required for the two-game pair-0 run under the symmetric TT-reset protocol.
