# H50F57 generic tactical-interaction capacity results

## Decision

The F57 offline capacity gate is negative for each primary RuleSet:

```text
A_CANONICAL_WESTERN_CHESS: TACTICAL_INTERACTION_CAPACITY_NOT_SUPPORTED
B_CANONICAL_STANDARD_SHOGI: TACTICAL_INTERACTION_CAPACITY_NOT_SUPPORTED
overall: TACTICAL_INTERACTION_CAPACITY_NOT_SUPPORTED
```

The interaction features are not added to the Native evaluator, and no Native
policy gate, self-improvement child, or arena is run. This preserves the work
order's requirement to establish offline value capacity before paying another
Native evaluator cost.

## Protocol

The tested residual is compact and generic. For every owner/current-type it
counts:

- `attacked_by_type`: the piece's square is semantically attacked by the
  opponent;
- `defended_by_type`: the piece's square is semantically attacked by the same
  owner;
- `hanging_by_type`: attacked by the opponent and not defended by its owner.

The owner axis is explicit and counts are unsigned, allowing asymmetric
RuleSets to learn separate owner coefficients. The extractor requires the
compiled semantic attack engine and fails closed for legacy-only compiled
rules. Its attack meaning is the repository's pseudo-attack contract: current
occupancy and semantic guards apply, friendly-occupied squares are protected,
pinned pieces still attack, and own-anchor safety is not recursively applied.

Each primary RuleSet used a fresh 192-position corpus, split into 128
development and 64 untouched validation positions. The v2 evaluator was
frozen; only the interaction residual was fitted using development-only
scaling, zero-variance removal, four-fold deterministic CV/SVD ridge, and
mate-band exclusion (`abs(80k Native score) > 90,000,000`). Teacher labels used
the stable 40k/80k Native procedure. The evaluator was not used for corpus
selection.

| RuleSet | Corpus ID | Stable teacher rate | Stable ordinary validation |
|---|---|---:|---:|
| Western | `1969d41df48e0181328da4efb8abee7a3eec22dcc4c5a552de973d590e1b69a5` | 159/192 = 82.81% | 51/64 |
| Standard Shogi | `0293bb9e01f9a8a77cdedd9bd24480d497548bc4ca57e2994f32b54178ec57cf` | 177/192 = 92.19% | 57/64 |

## Unseen value capacity

| RuleSet | Parent MSE | Interaction child MSE | Change | Parent correlation | Child correlation |
|---|---:|---:|---:|---:|---:|
| Western | 2,015,841.18 | 2,896,852.90 | -43.70% | 0.457 | 0.400 |
| Standard Shogi | 2,310,660.46 | 7,036,931.79 | -204.54% | 0.427 | 0.054 |

Validation MAE also worsened: Western `1036.39 → 1293.73`, Standard Shogi
`1026.28 → 1604.52`. The interaction residual therefore supplies no
substantial unseen value improvement on either primary RuleSet.

## Compatibility and witness coverage

- The feature vector has `3 × 2 × current_type_count` coordinates, with no
  Chess/Shogi-specific branches, pairwise type matrix, piece-square table, or
  second spatial grid.
- A Western witness keeps material and 3x3 occupancy unchanged while moving a
  pawn within the same coarse cell: the rook attacks the pawn in one position
  and does not in the other. The relation vector changes accordingly.
- Western, Standard Shogi, and a generated semantic RuleSet execute the
  extractor tests; legacy execution fails closed.
- The F56 direct-binding defect was fixed opportunistically: flattened spatial
  profiles now require `2 * type_count * 9`, and a focused direct-binding test
  covers both owner axes. No separate corrective stage was created.

Because the offline gate is negative, F57 deliberately does not implement or
benchmark Native interaction vectors. The architectural implication is that
continuing to append additive handcrafted scalar families is low-value; the
next representation should be compact and nonlinear enough to learn
interactions automatically.

The raw corpus and benchmark JSON remain transient under
`.generic_chess_flow/f57-tactical-interaction-capacity/`; this report is the
durable architectural record.
