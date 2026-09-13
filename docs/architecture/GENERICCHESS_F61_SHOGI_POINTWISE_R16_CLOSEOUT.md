# F61 Standard-Shogi pointwise-value screen — R16 closeout

## Scope and controlled comparison

R16 changed only the learning objective from calibrated pairwise ranking to
direct `POINTWISE_Q`, using the neutral optimizer seed 59013. It reused the
current Standard-Shogi parent, exactly 24 persisted roots, and 157 q20/base-Q
rows. No post-hoc pairwise scalar alpha was applied. This is a controlled
objective comparison on the same data, not a new data-seed experiment.

- Ruleset: `B_CANONICAL_STANDARD_SHOGI`
- Parent checkpoint: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Objective: `POINTWISE_Q`
- Training seed: `59013`; width 32; regularization `1e-3`; 600 steps
- Roots/actions: `24` / `157`
- Code checkpoint: `4347c3cf1beebdb1f47d820b6c6143ece8e2b14a`
- Compute plan SHA: `5d62b9319ea0bd9691ef24a41c31f33c17b7120ba77a185a794e7a34a7ec76a7`
- Resource envelope SHA: `68b583afbb1100cd3402bd63d8c4c504128131a8ba807860b520e59777d35e23`
- Chat approval request: `GENERICCHESS-20260913-195807-9af8c451`
- Heavy run: `f61-shogi-pointwise-r16-one-pair-e49cc9fad4b6`
- Fresh opening seed: `620706`

## Candidate and residual fit

The pointwise candidate checkpoint is
`78bfa7cad9cc21ecfc95fd166566b25d3c954033b413660a7c398498dd6c571b` with
model SHA256
`c6330b17fc11093cd404e204d3a6f461307971f2458e55d0147c4cc21c0f239c`.
The candidate and calibrated-child fields are identical because no scalar
intervention was applied.

The absolute residual fit was finite and close in scale to its targets:

- target residual RMS: `709.8857134177654`
- learned residual RMS: `703.0291965345359`
- learned/target RMS ratio: `0.9903413792479094`
- learned/target standard-deviation ratio: `0.9908631074058574`
- Pearson correlation: `0.9985805255107525`
- ranking agreement (descriptive only): `301/349 = 0.8624641833810889`
- alpha: none (`POINTWISE_Q` directly fits the absolute residual)

The frozen seed-620700 gate used 2,000 nodes, depth 12, and TT 8 MiB. All
four candidate actions differed from the parent, so the candidate was
behaviorally nontrivial and admissible for actual play. Candidate actions
matched the uncalibrated pointwise child on all four openings.

## Fresh one-pair screen

Exactly one fresh role-swapped pair ran at opening seed `620706`, with 2,000
nodes/move, depth 12, TT 8 MiB, and one worker. Both games ended in checkmate:

| game | pointwise-child owner | winner | plies |
|---|---:|---:|---:|
| owner-0 | 0 | 0 (child) | 152 |
| owner-1 | 1 | 0 (parent) | 60 |

The pair score is `[0.5]`, mean `0.5`, with `0` better, `1` tied, and `0`
worse pairs. Game W/D/L from the child perspective is `1/0/1`; directional
failure is false. Under the screen rule, the score is `>=0.5`, so R16
returns before any confirmation expansion. The result is a screening signal,
not a strength estimate. Descriptively, this does not establish a positive
gain over the fixed seed-59013 calibrated-pairwise four-pair result (mean
`0.5`).

## Verification and disposition

The Heavy completed within the approved envelope. No objective sweep, new
roots, additional pairwise games, alternate alpha, Chess, generated rules,
or Gen2 work was started. This report is ready for Chat/Supervisor review at
the next synchronized sandbox SHA.

