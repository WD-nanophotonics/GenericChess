# F63-R1 game-atomic Arena progress

Status: accepted implementation design for the F63-R1 Arena hardening order.

The existing `generic-chess-arena-progress-v1` pair files remain readable and
unchanged. New runs use `generic-chess-arena-game-progress-v1` and persist one
completed game in `game-<pair>-owner-<child-owner>.json` with an atomic replace.
The file identity binds the stage, Arena corpus and full opening row, pair and
child-owner, both checkpoint IDs and role budgets, depth, transposition-table
size, telemetry mode, and every hard execution cap.

Only validated game files are reused. Validation replays the opening and all
actions, checks legality, owner and pair identity, terminal/declaration result,
final position, and telemetry shape. A pair enters statistics only after both
owner files validate. Aggregation is sorted by pair index, so completion order
and a crash between the two games cannot alter the summary or create a draw.

The game scheduler uses at most
`min(logical_cpu_count, 2 * requested_pairs, 16, requested_workers,
max_concurrent_games)` lanes and never nests pair-level executors. Pause,
stage-wall, stage-game, per-game-wall, per-game-node, and per-game-ply limits
stop new launches or return an explicit `PAUSED`/`INCOMPLETE` result. A cap-hit
game is not converted into an Arena result. When a hard wall is declared, the
minimum remaining game/stage wall budget is also passed into
`SearchLimits.max_time_seconds`; time-limited or deadline-expired search
results are rejected before applying a move.

`arena_decision_bound` reports conservative best and worst totals and means for
unfinished pairs. `decision_sufficient` can become true before
`strength_estimate_complete` and exposes `PASS_LOCKED`, `FAIL_LOCKED`, or
`UNRESOLVED` for a predeclared simple mean or F63 mean-plus-class criterion.
This is the intended distinction for the F63 7/8 evidence (total 4.75, worst
mean 0.59375, worst classes 4/2/2).
