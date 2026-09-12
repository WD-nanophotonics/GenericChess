# GenericChess F94-R3 Western telemetry audit

Status: read-only audit of the completed R3 runtime result. No Arena rerun,
production change, tuning, Stage 1, full schedule, or promotion occurred.

The ignored raw result is
`.generic_chess_flow/f94-r3-nonbinding-depth-calibration-result.json`, SHA-256
`5d254cde8539f0c305a0df0f44cfb7cc9de08c903394dfacccc1f17fd7f3ac82`.

## Finding

The frozen R3 rule classified Western Chess as `DEPTH_CENSORED` because two
individual child search metrics reported completed depth 64. Telemetry shows
these are not ordinary searches exhausting the 4096-node budget:

| Tape | Games | Max completed depth | Depth-64 metrics | Relevant depth-64 telemetry |
| --- | --- | --- | --- | --- |
| 9401 | checkmate at 28 plies; `max_ply` at 995 | 64 | 1 / 1,023 | child: 2,624 / 4,096 nodes, `termination_reason=completed`, selective depth 1, score 0 |
| 9402 | `max_ply` at 997; checkmate at 31 | 56 | 0 / 1,028 | no depth-64 metric |
| 9403 | `max_ply` at 995; `max_ply` at 995 | 64 | 1 / 1,990 | child: 1,280 / 4,096 nodes, `termination_reason=completed`, selective depth 1, score 0 |

The two depth-64 observations appear in long-game tail positions and ended
`completed` well below the node budget. They are therefore false-positive
censor signals under the current rule `completed_depth >= max_depth`, not
evidence that the node-budget comparison was depth limited.

## Next bounded diagnostic route

Before any Arena rerun, cheaply repair and test the censor predicate so it
uses termination reason and node-exhaustion evidence rather than depth alone.
Separately diagnose why four of six Western role-swapped games reached roughly
995--997 plies (`max_ply`), including termination/repetition behavior. Neither
task needs additional Arena samples. A later computation would require a new
explicit Chat and registered-Supervisor review.
