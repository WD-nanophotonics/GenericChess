# F61 Standard Shogi failure-link diagnosis R10

Date: 2026-09-13

## Scope and binding

This is the exact Chat work order `GENERICCHESS-F61-SHOGI-FAILURE-LINK-DIAGNOSIS-R10`
against published sandbox `845e6d4e82887cc9f1ee74ea8e4c5f7b027911af`.  The
diagnostic reconstructed the completed seed-59012 run from the 24 persisted
root checkpoints.  It did not train another model and did not run an Arena.

- Ruleset: `B_CANONICAL_STANDARD_SHOGI`
- Parent checkpoint: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Child checkpoint: `35462d58263581a0f456d863bcd29a78ae82b9d90a82147404bff2346833d1a5`
- Training seed: `59012`
- Reproduction command: `.venv\\Scripts\\python.exe scripts/f61_failure_link_diagnosis.py`
- Durable result: `.generic_chess_flow/f61-gen0-gen1-strength-triage/failure_link_diagnosis.json`

## Compact residual check

The child checkpoint has a nonempty compact nonlinear residual, with
`perspective=successor_root_q`, width 32, and input dimension 2301.  On all
157 usable training-action feature vectors from the 24 roots:

| statistic | value |
|---|---:|
| min | -13792.756031648625 |
| max | 16106.46200709215 |
| mean | -375.70098341346585 |
| standard deviation | 6303.526932207698 |
| `abs(residual) > 1e-9` | 157 / 157 (1.0) |

The residual is therefore attached and materially nonzero/variable; teacher
agreement remains diagnostic only.

## Equal-budget search validation

The four frozen openings were regenerated with Arena opening seed `620700`.
Parent and child each used 2,000 nodes, depth 12, and an 8 MiB transposition
table.  All four selected actions changed:

| opening id | parent action (score) | child action (score) | changed |
|---|---|---|---|
| `986c46f70658ab87e6b521a52d7fb7cb439a577c293dc0de9a7d1219ed12f2ef` | `P (6,2)->(6,3)` (-1280) | `G (3,0)->(2,0)` (1780633) | yes |
| `a870b10dd6f9309a7317f4b5c4afaf2f9026ddd1fbf9e21ea4610c4b10c143dc` | `P (6,2)->(6,3)` (-256) | `P (1,2)->(1,3)` (-96827) | yes |
| `05c4e64ea8f7ad75acab1f6186c4acc3a62df5207efe6c5ea0ed21049e8fc45b` | `P (6,2)->(6,3)` (2560) | `G (3,0)->(3,1)` (1476418) | yes |
| `d7554499dbbe6cfc8f8d3b2780eaa5d4a01b9d55590e94c944b68fde14d78997` | `P (2,6)->(2,5)` (-512) | `R (3,7)->(4,7)` (875449) | yes |

## Interpretation and stop boundary

The residual is nonzero and all four equal-budget search decisions change.
The learning signal therefore reaches search; this failure is consistent with
objective/data/search coupling rather than a disconnected evaluator injection.
This diagnosis does not override the measured first-seed Arena result
(mean child score 0.375, directional failure true), and it does not authorize
another seed, Gen2, Chess, generated rules, a larger Arena, or teacher-only
experiments.  Stop after this diagnosis as ordered.
