# GenericChess F82-R1: F81 sealed-corpus contract corrective

Status: `C1_CHAMPION_ADOPTED_REPEATABILITY_PROTOCOL_FROZEN`.

This is a zero-compute durable-contract correction. The F82 semantic protocol,
C1 champion identity, sealed corpus contents, optimizer family, mechanism
family, and strength funnel are unchanged. No training, teacher search,
self-play, Arena, Heavy job, opening generation, candidate fitting, model
mutation, or production change was performed.

The F82 contract test now executablely reads
`artifacts/f81_final_confirmation/openings.json` and verifies that the sealed
history entry has the exact path, content SHA, corpus ID
`67b9dafc51a618645c3328228c30a8744cc8f988395a7d54d382b65276dc935c`, and a
reuse policy that permits final-evaluation history only while prohibiting C2
training and candidate selection.

The sole correction closes the F81 sealed-corpus validation gap. C1 remains
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`, and the
success classification remains
`C1_CHAMPION_ADOPTED_REPEATABILITY_PROTOCOL_FROZEN`.
