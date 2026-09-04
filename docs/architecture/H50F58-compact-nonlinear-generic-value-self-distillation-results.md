# H50F58 compact nonlinear generic value self-distillation

## Decision

F58 has a mixed RuleSet outcome. The compact nonlinear residual is retained as
a Native-capable `learnable-generic-v4` evaluator for
`B_CANONICAL_STANDARD_SHOGI`; it is not promoted for
`A_CANONICAL_WESTERN_CHESS`, where the unseen validation result was negative.
This checkpoint remains an experimental child and is not a champion promotion.

Parent checkpoint for both RuleSets: `49e1076f9b134ca0d6d47ae2decc5f033a18261c`.

## Offline capacity gate

The fixed protocol used 384 development and 128 validation positions per
RuleSet, 40,000/80,000-node Native teachers, ordinary stable positions only,
one fixed development fit/selection split, widths 16/32, regularization
`1e-4/1e-3`, and seeds 58011/58012/58013. Model selection was development-only.

| RuleSet | Parent validation MSE | Child mean validation MSE | Improvement | Gate |
| --- | ---: | ---: | ---: | --- |
| Western chess | 1,429,075.38 | 2,032,942.44 | -38.757% | rejected |
| Standard Shogi | 2,344,965.23 | 2,072,232.65 | +11.631% | supported |

All three Shogi seeds beat the parent. The selected Shogi hyperparameters were
width 32 and regularization 0.001; bounded parent MSE was 0.101315 and child
mean bounded MSE was 0.081879.

## Native implementation

The residual consumes a mechanical semantic state vector: owner/current-type/
square board one-hot values, base-type hand counts, side-to-move, the existing
three dynamic features, and fixed-width compiled auxiliary slots. The Python
model stores its normalization and one-hidden-layer tanh parameters; Native
validates the schema and evaluates the same feature order.

`evaluator_scale` converts the model's human-value residual back to Native
fixed-point score units. The model's `target_scale` is not multiplied into the
model a second time; it is part of the trained prediction. Temporary Native
parameter arrays are heap-owned and released on every evaluate/search parse
success and error path. An engine retains only the Python payload and reparses
it for each search; engine destruction releases that retained payload.

Selected Shogi model:

- seed: 58011
- width: 32
- parameter SHA-256: `dcb8827e7c1b1d7380ab5c41dee248e7f35548744cdc22e4969249e3ecbfaa86`
- child checkpoint: `251ab14de295fa4b0d141f6ea6fa3f334f877133882c7ea7479e5d8e551af573`

## Native verification

The selected model matched Native residual deltas exactly on 8 deterministic
validation positions: maximum absolute fixed-point error 0. A checkpoint
round-trip and changed-checkpoint rebind also passed, with the transposition
table cleared on rebind. The policy smoke changed the selected move on 6 of 8
positions (75%); this is descriptive only, not a policy-capacity gate.

A 2-pair Shogi arena smoke produced four draws (child score 0.5). This small
arena is a transport/lifecycle check, not evidence of playing-strength gain.

## Tests

The F58, F50, F56, and H50B2E focused regression suites pass after rebuilding
the Native extension. The F58 suite includes direct repeated profile parsing,
engine search, checkpoint serialization, TT rebind, and Python/Native feature
and fixed-point contracts.
