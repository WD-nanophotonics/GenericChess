# F61 Standard-Shogi R25 stable-target linear distillation

R25 reused the 24 persisted D0 roots and 157 action rows from parent
`2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`.
Exactly one 10,000-node q10 successor search was added per persisted action;
no roots, root searches, or all-legal spectra were regenerated.

## Stability filter

- stable q10/q20 top-action roots: `22 / 24` (agreement `0.9166667`)
- retained q20 mate-band exclusions: `0` roots / `0` actions
- retained trusted roots/actions: `22 / 145`

The two unstable roots were excluded solely because q10 and q20 selected
different actions. No unavailable root-80k criterion was reconstructed.

## Leave-one-root-out gate

The exact F54 board/hand/native-dynamic owner-perspective vector and no-
intercept ridge (`alpha=1e-3`) were fit on the other 21 trusted roots for each
held-out root.

| Prediction | MSE | Pairwise ranking | Mean root top-action q20 regret |
| --- | ---: | ---: | ---: |
| Base Q | 530,878.5724 | 0.7120419 | 133.1364 |
| Base Q + linear delta | 1,346,705.6694 | 0.6308901 | 309.0909 |

The OOF gate fails all three conditions. Decision:
`STOP_BEFORE_FULL_CANDIDATE_OOF_GATE_FAILED`.

No child checkpoint, external witness, Arena pair, or promotion claim was
created. This rejects the cheap q10/q20 stability-filter rescue under the
existing 24-root corpus.
