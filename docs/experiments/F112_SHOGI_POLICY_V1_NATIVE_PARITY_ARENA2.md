# F112 Shogi Policy-v1 Native Parity and Arena2

F112 bound the frozen offline-qualified Shogi SemanticPolicyV1 to the Native
ordering path without retraining or changing the leaf evaluator.

Published implementation checkpoints:

- Native V1 binding: `685b3bb96b5ca9d27059e8de17a7a5afedada829`
- Frozen-identity parser correction: `80d16c28de4680343aebd6a16503cdd263e54594`

Frozen identities were preserved exactly:

- evaluator: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- Policy-v1: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`

The Native depth-2 probe and all 24 existing F109 performance roots returned
legal actions. There were zero telemetry failures for
`policy_state_inferences == policy_nodes` and
`policy_action_embeddings == policy_actions_scored`. Across the 24 roots,
Native processed 48,000 search nodes, 506 policy nodes, and 13,384 scored
actions in 0.5738362 seconds of policy time.

The fresh two-opening, role-swapped Shogi Arena2 completed validly with pair
scores `0.5, 0.5`, mean `0.5`, and classification
`SHOGI_POLICY_V1_ACTION_ENCODER_ARENA2_REJECTED`. The offline improvement did
not survive equal-wallclock strength testing. No Chess Arena was run because
Chess failed the F111 offline gate. Promotion remains HOLD.
