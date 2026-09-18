# F113 Shogi Policy-v1 Deferred Legality Arena2

## Scope

F113 tested one policy-specific optimization on the frozen Standard-Shogi
Policy-v1 path. Candidate actions are scored and sorted before legality
filtering; the authoritative checked transition is performed only when a
candidate is traversed. The runtime switch is default-off, applies only to
Policy-v1, and does not change candidate generation, logits, evaluator,
features, depth, windows, or ordinary/Policy-v0 ordering.

Frozen identities:

- evaluator checkpoint: `f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`
- Policy-v1: `2357472be320e9df909136a31a5223ec24e79f998467bb0ef3114b7e3433b955`
- reference sandbox: `5ede05ed45894634f7788e979c3ec88194bcdb52`

## Gates

The 100-position legal-subset ordering invariant passed with zero mismatches.
All 24 fixed-node roots passed exact equality for score, best action,
principal variation, node count, and completed depth.

The strict timing gates also passed:

| measure | eager | deferred | deferred/eager |
| --- | ---: | ---: | ---: |
| total wall seconds | 78.184325 | 78.088123 | 0.998770 |
| Policy elapsed seconds | 0.579673 | 0.391153 | 0.674782 |

Deferred Policy-v1 reported zero preorder checked transitions, 107,207
traversal checked attempts, and 14,888 illegal skips. State inferences equal
policy nodes, and action embeddings equal actions scored.

## Fresh Arena2

The two generated opening identities were persisted before interpretation and
were disjoint from the tracked Shogi identity surface. The Arena used two
role-swapped pairs, four valid games, one-second move budgets, depth 12, an
8 MiB TT, one worker, and root-window pruning.

- pair scores: `0.0, 0.25`
- mean pair score: `0.125`
- better/tied/worse pairs: `0/0/2`
- games: `0W/0D/4L` for the candidate

Classification: `SHOGI_POLICY_V1_DEFERRED_LEGALITY_ARENA2_REJECTED`.

## Interpretation

The duplicate checked-transition work is real and materially reduces Policy-v1
time (about 32.5%), but it changes aggregate search wall time by only about
0.12% on the fixed-root comparison and did not produce a strength benefit in
the required fresh Arena2. The frozen Policy-v1/runtime combination is not
retained as a strength candidate. No broader lazy-search framework, retraining,
new target, or larger arena is authorized by this result.
