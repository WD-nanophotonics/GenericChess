# F111 Semantic Policy-v1 Offline Gate

F111 replaces only the Policy-v0 action representation on the frozen F109
rows. The state vector, hidden width 16, corrected target contract, seeds,
400-step Adam fit, learning rate, and L2 are unchanged. No new search,
self-play, Arena, or Heavy run was used in this offline checkpoint.

The implementation is versioned as `SemanticPolicyV1`; Policy-v0 remains
unchanged. It removes the three scalar type coordinates and adds deterministic
categorical actor/promotion/drop/geometry embeddings plus only the specified
actor-capture, actor-promotion, actor-drop, and actor-geometry interactions.

| Ruleset | Policy-v0 train CE / top1 / pairwise / regret | Policy-v1 train CE / top1 / pairwise / regret | F110 oracle top1 / pairwise | Gate |
| --- | --- | --- | --- | --- |
| Chess | 2.3448 / 0.4286 / 0.6816 / 16667.4 | 2.2873 / 0.5000 / 0.7078 / 2313.1 | 0.5357 / 0.6986 | reject Arena |
| Shogi | 2.5569 / 0.1333 / 0.6937 / 834868.1 | 2.1654 / 0.8000 / 0.7589 / 5820.2 | 0.1333 / 0.7247 | pass offline |

Corrected-target identity matched every persisted F109 row at tolerance
`1e-12`. Both V1 models reload to their serialized SHA exactly:

- Chess: `616e3a9490bd6f73098e347a49ac0c9271682d02e97ab5c5b7f2ddb2fdf77b1e`
- Shogi: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`

Chess improves materially but does not clear the predeclared independent
linear-oracle gate, so no Chess Arena is authorized. Shogi clears the offline
gate; Native V1 parity and timed Arena2 are not claimed by this checkpoint.
Promotion remains HOLD.
