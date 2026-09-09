# GenericChess F63 R1 R9 Calibrated Caps and Carry-Forward Closeout

- Work order: `GENERICCHESS-F63-R1-R9-COMMON4-CALIBRATED-CAPS-AND-PROGRESS-CARRYFORWARD`
- Parent SHA: `47b1c77bd232dba692c7e4ee9211f19cd02f19c1`
- Implementation base SHA: `2041500dbdd68029167d859b486334f71661fe8d`
- Scientific route: retain candidates `59011`, `59012`, `59013`, four pairs per
  candidate, equal color-swapped play, and 2,000 nodes/move.
- Heavy, new games, teacher rerun, selected-8/32 rerun, compute-plan approval,
  and common-4 execution: **not performed**.

## Implemented scope

Common-4 candidate stages now use the R8 evidence-derived execution caps:

- per-game plies: `512`
- per-game total searched nodes: `1,000,000`
- per-game wall: `10,000` seconds
- four-pair candidate-stage wall: `10,800` seconds
- logical CPU declaration: `10`
- effective common-stage game lanes: `4`

The selected-8 and selected-32 paths retain their prior caps and scientific
logic. The change is isolated to the F63 candidate-stage helper; the Arena
implementation and game-v1 schema were not changed.

## R6 carry-forward

The completed R6 game remains immutable at:

`.generic_chess_flow/f63-champion-loop-causal-triage/progress/candidate-59011-common-4-seed-630403/game-000000-owner-0.json`

Its SHA-256 remains
`e205dcfab1b4eff012ac496919ae80b4ab93b882e310fcf59c52f42b504c92f2`.
Its source manifest SHA-256 is
`9668d1c38d490f4275916e0a2968461968f2220ed1a8b433af645ce4427e8004` and its
source identity SHA-256 is
`ec802b9492a36d86c9c4be4644e652afb136e7754c0dfc1dc919b6b45a15f1bf`.

Before reuse, the narrow importer verifies the pinned source hashes and
manifest, all scientific stage/game identity fields, checkpoint IDs, opening
identity, pair/owner, 2k parent/child budgets, depth, TT, telemetry, legal
replay, terminal result, final position, declaration semantics, and monotonic
cap relaxation. It writes a new calibrated game-v1 namespace and never
overwrites the R6 directory. The calibrated runner therefore sees one valid
completed game and schedules only the seven missing games for that stage.

## Tests

Bounded focused validation passed: **33 tests** in
`tests/test_f63_champion_loop_causal_triage.py` and
`tests/test_f63r1_game_atomic_arena.py`; `py_compile` also passed for the F63
runner and Arena module. Tests cover source byte preservation, valid import,
cap rejection, checkpoint/opening/owner/budget/depth/TT/telemetry identity
rejection, selected-stage cap preservation, and the existing game-atomic
missing-game/partial-pair behavior.

## Next authorized action

Prepare a fresh current-SHA common-4 compute-plan request using the calibrated
envelope: maximum 24 games, 24,000,000 nodes, 12,288 plies, four concurrent
games, 10,000 seconds/game, 1,000,000 nodes/game, 512 plies/game, 10,800
seconds per candidate substage, three serial substages; expected wall about
2.5–5 hours and expected occupied-lane/CPU proxy about 10–20 hours, with hard
ceilings of 9 wall hours and 40 lane-hours. This is a planning request only.
The plan must bind to the final published sandbox SHA and carry-forward
provenance; it must not be executed or approved in R9.
