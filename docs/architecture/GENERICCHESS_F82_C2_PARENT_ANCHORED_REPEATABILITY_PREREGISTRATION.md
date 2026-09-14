# GenericChess F82 C2 parent-anchored repeatability pre-registration

Status: `C2_PROTOCOL_PRE_REGISTERED_AWAITING_COMPUTE_APPROVAL`.

This checkpoint implements the single-candidate continuation of the adopted
C1 champion `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
(model SHA `b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`).
The harness freezes the representation and all board, hand, dynamic, spatial,
and control blocks. Only `hidden_weights`, `hidden_bias`, and
`output_weights` can be updated by full-batch Adam (100 steps, learning rate
`0.001`, proximal coefficient `0.001`, parent anchoring) with the registered
F78 backtracking sequence and first-safe-alpha rule.

The deterministic allocation is recorded in
`artifacts/f82_c2_repeatability/c2_allocation_manifest.json` (allocation SHA
`f0de3d7175da6e5551457d0669e7efd87dc8f0dad446f6b956c1482b8b2a364e`). It
contains 36 fixed training roots and disjoint Arena2/4/8/final opening
corpora (2/4/8/8 pairs). The resource envelope fixes one game lane, 262,144
nodes, 512 plies, 3,600 seconds per game/stage, and 44 total games. Historical
F62/F75/F77/F78/F79/F80/F81 corpora are diagnostic-only and are not admitted
to C2 fitting or selection.

The implementation and contract tests were published at sandbox SHA
`bf79515052153fff4bc803806b6675e3625aeaef`. No Heavy job or Arena game was
started in this pre-registration checkpoint; compute must be requested and
approved against the exact published SHA and allocation digest before
execution.
