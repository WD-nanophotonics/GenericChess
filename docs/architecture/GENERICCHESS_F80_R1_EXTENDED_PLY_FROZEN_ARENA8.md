# GenericChess F80-R1: extended-ply frozen Arena8

Status: `PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_SURVIVES`.

This order reran only the remaining frozen F78 corpus openings `[4, 5, 6, 7]`
against the fixed parent/child pair. It did not rerun openings 0–3, alter the
candidate, retrain, generate openings, use a teacher/deep gate, run self-play,
use an external engine, or change production search/evaluator/Arena semantics.

## Execution

The source corpus was
`artifacts/f78_parent_anchored_full_residual/openings.json`, corpus ID
`2923f457e56454520f89c682614b3b10d07da974f03040bfc6c3a831ab41da48`. A
temporary four-opening view mapped local indices `0,1,2,3` to source indices
`4,5,6,7`; source final-position keys and the mapping were recorded in the
runtime result. The stage used four swapped-owner pairs/eight games, 512
nodes per move for parent and child, depth 12, 8 MiB TT, workers 2, maximum two
concurrent games, fresh engines, and product root-window pruning.

The extended execution ceilings were 512 plies and 262,144 nodes per game,
with 3,600-second per-game and stage walls and eight maximum stage games. The
Heavy resource envelope was small/medium: expected wall 30 minutes / hard 60,
expected CPU 1 hour / hard 2, two lanes, and one stage.

## Result

The incremental pair scores for source openings `[4,5,6,7]` were
`[0.25, 0.5, 1.0, 0.5]`. Combining them with the durable Arena4 prefix
`[0.5, 1.0, 0.5, 0.5]` gives eight pair scores:

`[0.5, 1.0, 0.5, 0.5, 0.25, 0.5, 1.0, 0.5]`

The recomputed mean pair score is `0.59375`; child-better/tied/worse pairs are
`2/5/1`; the bootstrap diagnostic interval is `[0.4375, 0.78125]`; and the
combined child W/D/L is `9/1/6`. All 16 games and 8 pairs are complete.

Final identities are parent
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`, child
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`, model
`b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`, and the
F79 durable prefix artifact content SHA is
`888864459718cbc1d81cd0e4d1f9e3cae5e1eb116b9c3d05ca2f559e35fb9477`.

Replay returned `COMPLETE` with identical status/counts/summary. Effective game
lanes were 2; all telemetry rows were present; root pruning was true on every
search; the maximum observed search-node count was 512; no cap reason occurred;
and contract failures were empty.

By the exact Arena8 gate (complete eight pairs, mean greater than 0.5, and
child-better pairs greater than child-worse pairs), the accepted classification
is `PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_SURVIVES`. Promotion remains HOLD.
The ignored runtime result is retained for execution evidence only; the durable
strength authority is the tracked Arena8 artifact created with this report.
