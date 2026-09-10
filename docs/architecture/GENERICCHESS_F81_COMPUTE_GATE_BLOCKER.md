# GenericChess F81: compute-gated before final confirmation

Status: `COMPUTE_APPROVAL_REQUIRED`.

The F81 fresh-corpus final-strength harness is implemented and published at
sandbox checkpoint
`74619e8a62a1446767ba7ea692fde615a9ce3360`. Its contract tests pass, and no
F81 Arena game has been launched.

## Frozen inputs

The required fixed identities are parent
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`, child
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`, and
candidate model
`b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`.

The evaluator-neutral Standard-Shogi corpus was generated with seed `810501`,
contains eight openings, and is persisted at
`artifacts/f81_final_confirmation/openings.json`. Its corpus ID is
`67b9dafc51a618645c3328228c30a8744cc8f988395a7d54d382b65276dc935c`. Final
position overlap counts are zero against F62's 96 roots and the F75, F77, and
F78 corpora.

The harness preflight also verifies the F80 v2 artifact content SHA
`438ddec64d1225488900f3a823fa0fd8a52a9dd60942b39d1f9f32dcb3b0ead0`, its
F80-R1 report SHA
`e992fb9f7804d48878b3eb71a309d95f3979f8b55a775ecded9e6bff6ffcfd4b`, and the
F79 Arena4 artifact content SHA
`888864459718cbc1d81cd0e4d1f9e3cae5e1eb116b9c3d05ca2f559e35fb9477`.

## Cheapest-sufficient compute decision

The work order's nominal 30-minute wall estimate is not credible from the
immediately preceding measured execution. F80-R1 ran eight games on two lanes
from `07:40:15` (manifest creation) to `08:16:04` (durable result), or 35
minutes 49 seconds. F81 requires 16 games, even though it raises concurrency
to four; the prior long-tail search behavior makes a sub-30-minute declaration
unsafe. No additional experiment is needed to establish this bound.

The formal versioned plan is
`.generic_chess_flow/compute-plans/f81-final-confirmation-v1.json` with plan
SHA `6bc143a80c134535fc20dbfcfc194befcc9e18024106e4b5a0bcbbe4c3deb8f2`.
Its exact resource envelope is
`.generic_chess_flow/f81-final-confirmation-envelope-v1.json` with digest
`c8bf85892aa047a77a798276cc74385d540a2389e31b6357ae0cc5e0ff762b63`.
The envelope declares 45 expected wall minutes (range 35–55), 60 hard wall
minutes, 2.5 expected CPU hours, 4 hard CPU hours, eight pairs, 16 games, four
concurrent lanes, one stage, 262144 nodes and 512 plies per game. Policy
therefore classifies it as large because expected wall exceeds 30 minutes.

Execution is blocked until Chat scientific approval and registered-Supervisor
approval are both bound to this exact plan SHA, envelope digest, and sandbox
SHA. The only permitted next execution is the published F81 harness with its
fixed fresh corpus and declared caps; no prior progress namespace may be
reused.
