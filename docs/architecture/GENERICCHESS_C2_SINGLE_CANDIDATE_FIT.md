# C2 Single Candidate Fit

The preregistered F82 parent-anchored full-residual fit was run exactly once
against the published F85 teacher evidence.  No alternate seed, sweep, retry,
or teacher regeneration was used.

- parent checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- parent model SHA: `b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`
- teacher evidence SHA (Chat-registered): `c0a5e69f5d3345bbf4ab699d67b14b0fcbad745003ca17ac5beec3a1f4fbb4c2`
- frozen allocation SHA: `f0de3d7175da6e5551457d0669e7efd87dc8f0dad446f6b956c1482b8b2a364e`
- candidate checkpoint: `86f026ef85d60e600bc1bd6bc7b7285f11e5ce7e6528911b2ea361a489dc5983`
- candidate model SHA: `b2308bea76ba55a533b95036f9b0ca37265c15d772ce5fbd14f7b6b098677e95`
- training-config hash: `ffebc2b03e4095b244bfe857bf4e849248c2ae4636721df25120b581e6f5747c`
- chosen first safe alpha: `0.5`

The fit used full-batch Adam for 100 steps at learning rate `0.001` with
proximal coefficient `0.001`, training only
`hidden_weights`, `hidden_bias`, and `output_weights`.  Parent representation,
normalization, scale, output bias, linear/dynamic/spatial/control fields were
retained.  The registered safety/backtracking result is preserved in
`artifacts/f82_c2_repeatability/c2_candidate_result.json`.

Arena2 is not executed in this checkpoint.  Its exact two-opening-pair,
role-swapped plan is prepared separately for compute approval.
