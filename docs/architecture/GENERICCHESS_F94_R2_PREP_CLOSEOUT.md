# GenericChess F94-R2 result-free PREP closeout

This is the immutable PREP checkpoint for the bounded real Layer-D
calibration. The PREP artifact is:

`docs/architecture/GENERICCHESS_F94_R2_STRENGTH_RESPONSE_PREP.json`

The artifact is result-free and freezes three candidates: Built-in Western
Chess, Built-in Standard Shogi, and the existing F86N-R1 boundary V4-3
candidate. Each candidate freezes three deterministic opening corpus IDs,
three tape seeds, 256/1024/4096 node budgets, max depth 12, TT size 8 MB,
six pairs per tape, checkpoint/evaluator/ruleset identities, bootstrap
configuration, and the current classification rule. The boundary candidate's
existing A/C state is PASS/DEFER, so its eventual RESULT path is a required
short-circuit and will not spend Arena compute.

The PREP artifact was generated from source sandbox SHA
`8782da79ab10d2293f10dd4f785ee38a54fc9bf4` and published in the immutable
sandbox checkpoint `d48b31602af7b5cb5500d949fa807689d6435511`.

No real RESULT, Arena game, training step, or evaluator/search change is
included in this PREP. The 21 focused protocol and F87A contract tests pass.
