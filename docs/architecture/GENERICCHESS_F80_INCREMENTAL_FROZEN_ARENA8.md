# GenericChess F80: incremental frozen Arena8

Status: `PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_UNRESOLVED`.

F80 consumed the durable Arena4 prefix from
`artifacts/f79_parent_anchored_full_residual/arena4_strength_evidence.json`
(content SHA
`888864459718cbc1d81cd0e4d1f9e3cae5e1eb116b9c3d05ca2f559e35fb9477`) and used
only source openings `[4, 5, 6, 7]` from the frozen corpus
`2923f457e56454520f89c682614b3b10d07da974f03040bfc6c3a831ab41da48`.
The scheduler used a temporary local `[0, 1, 2, 3]` view with an explicit
local-to-source mapping; the durable corpus was not changed.

Configuration was four swapped-owner pairs/eight new games, 512 nodes per move,
depth 12, 8 MiB TT, workers 2, maximum two concurrent games, fresh engines,
and product root-window pruning. The Heavy envelope was small/medium: expected
wall 30 minutes, hard wall 60 minutes, expected CPU 1 hour, hard CPU 2 hours,
eight games, four pairs, two lanes, and one stage.

## Outcome

The stage did not complete four pairs. The execution cap
`per_game_plies` (256 plies) was hit. The first invocation recorded one
completed game; the resumable reload observed three checkpointed games and one
completed pair, but no complete incremental summary. Replay summary equality
was true for the incomplete state; there were no identity, corpus, telemetry,
root-pruning, or evidence-linkage failures. The result was normalized without
scheduling additional games, and no partial games were treated as draws or
strength evidence.

Final identities remained parent
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`, child
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`, and the
F79 Arena4 prefix remained `[0.5, 1.0, 0.5, 0.5]`. No Arena8 aggregate was
computed because the required eight new games/four pairs were not complete.

The ignored runtime record is
`.generic_chess_flow/f80-incremental-frozen-arena8/f80_results.json`; no
`arena8_strength_evidence.json` is emitted for an unresolved stage. The F80
contract tests cover the remaining-opening mapping, two-lane configuration,
durable prefix linkage, and cap-to-unresolved policy.
