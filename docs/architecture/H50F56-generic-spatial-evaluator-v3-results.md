# H50F56 generic spatial evaluator v3 results

## Decision

The F56 capacity gate is negative for both primary rulesets:

```text
SPATIAL_CAPACITY_NOT_SUPPORTED
```

No spatial child is promoted, and the work order's self-improvement and arena
branch is not entered. The v3 representation remains implemented and tested as
an opt-in checkpoint extension, but it is not selected as a stronger evaluator.

## Scope and protocol

The v3 extension adds a 3x3 board occupancy grid with owner/current-type axes
and a nine-cell localized-control residual. Each owner/type occupancy row and
the control vector are represented by eight independent zero-sum coordinates;
anchors are included in the Native type axis. The v2 parent evaluator is
frozen while the new coordinates are fitted. Fitting uses only the development
partition, training-only scaling, four-fold CV/SVD ridge selection, and excludes
the Native mate band `abs(score) > 90,000,000`.

Each ruleset uses a fresh 192-position corpus: 128 development positions and
64 untouched validation positions. Teacher searches use 40k and 80k Native
nodes; policy metrics use only stable, ordinary, non-mate validation positions.
The evaluator was not invoked for corpus selection.

| Ruleset | Corpus ID | Dev/validation position-key SHA256 | Stable teacher rate | Stable ordinary validation |
|---|---|---|---:|---:|
| Western | `4740c748a5efb8f30de26adcacb3d08d529cb91710088fcf1f19f5138cb32c9f` | `c27737345394236817a40681f08c6ee81811d60992f543d9337a526bf0f85c3f` / `12fe3ef8da53996ea649f111bb4ba1523eed23173b79e289457cb19c58d1b19a` | 170/192 = 88.54% | 53/64 |
| Standard Shogi | `deabc9b5dc81c6212845b7c6f2b9625d0a307639eccaf4f65e240ae370500f92` | `d9a62fbad4cee47dc613bad228150af7209a6b9d18bdc52372a51b356bc93d27` / `95f49a4b2fb9b204c92c35365508b50b7614a1071db69011a3a5a996544487e9` | 177/192 = 92.19% | 59/64 |

## Capacity result

| Ruleset | Parent validation MSE | Applied v3 validation MSE | Change | Parent policy agreement | Applied v3 policy agreement |
|---|---:|---:|---:|---:|---:|
| Western | 2,235,747.87 | 3,680,417.64 | +64.65% | 64.15% | 50.94% |
| Standard Shogi | 2,370,423.44 | 3,551,029.97 | +49.80% | 64.41% | 28.81% |

The unbounded fits also failed to generalize (Western validation MSE
4,329,596.37; Shogi 6,064,043.92), so the negative result is not caused only
by Native-safe clipping. The spatial design therefore has no demonstrated
usable value or policy capacity under this fresh, well-posed protocol.

## Compatibility, parity, and runtime

- Python and Native feature vectors matched exactly on the tested canonical
  positions (`max absolute delta = 0.0`), including the localized-control
  zero-sum residual.
- Owner-specific asymmetric witness, zero-mean rows, Native leaf-score parity,
  semantic TT clearing on v3 rebinding, and a generated semantic RuleSet all
  pass. Existing v1/v2 behavior and checkpoint identities remain unchanged.
- Zero-spatial v3 runtime is slower because the opt-in Native path carries the
  extra feature profile: Western 1,414 NPS (v2) vs 747 NPS (v3), and Standard
  Shogi 1,086 NPS (v2) vs 558 NPS (v3), measured over 8 validation positions
  and 40,000 total nodes per side.
- A fitted child is clipped in the eight independent coordinates before the
  ninth coordinate is reconstructed, guaranteeing the derived fixed-point
  coordinate stays within the Native `1,000,000` bound while preserving exact
  zero-sum rows.

The raw corpus and benchmark JSON remain transient under
`.generic_chess_flow/f56-generic-spatial-evaluator-v3/`; this report is the
durable architectural record.
