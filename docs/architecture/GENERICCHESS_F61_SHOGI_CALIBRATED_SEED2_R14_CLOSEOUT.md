# F61 Standard-Shogi calibrated optimizer-seed confirmation — R14 closeout

## Scope and fixed candidate

R14 executed the Chat-ordered confirmation for the fixed seed-59013 calibrated
child. The existing 24 persisted Standard-Shogi roots and 157 q20/base-Q rows
were reused; no model refit, alpha change, root regeneration, objective,
evaluator, or search-budget change was introduced. This remains an optimizer-
seed replication on the same data roots, not an independent data-seed study.

- Ruleset: `B_CANONICAL_STANDARD_SHOGI`
- Parent checkpoint: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Fixed calibrated child: `7c25f0d6475f00735a0ad14fe6bc24f5b46936c674b39e7dc455770c55338c12`
- Training seed: `59013`; roots: `24`; actions: `157`
- Fixed scalar: `alpha = 0.04417702070586609`
- Code/report base checkpoint: `92d69e6608de62d1e3965e293ae5231842f4a35c`
- Compute plan SHA: `431d90c21ee056becce9280fc2f3f58949af8ed1bd5614eb459a02314f842e03`
- Resource envelope SHA: `6232bb35857956873bd28727cda6508094b450026c6de16fa084b6b79f9a6e8c`
- Chat approval request: `GENERICCHESS-20260913-172904-cdfd2bb3`
- Heavy run: `f61-shogi-seed2-r14-confirm-ffaccf8a6a95`
- Fresh opening seed: `620704`

The fixed four-opening gate remained active, and the reconstructed child
identity matched the R13 checkpoint exactly. Arena settings were 2,000
nodes/move, depth 12, TT 8 MiB, and one worker.

## New three-pair block

All six games completed by checkmate:

| pair | child owner 0 | child owner 1 | pair score |
|---:|---|---|---:|
| 0 | child win, 89 plies | child win, 128 plies | 1.0 |
| 1 | parent win, 170 plies | child win, 123 plies | 0.0 |
| 2 | parent win, 117 plies | child win, 113 plies | 0.5 |

The fresh block is therefore:

- pair scores: `[1.0, 0.0, 0.5]`
- mean pair score: `0.5`
- better/tied/worse pairs: `1/1/1`
- game W/D/L (child perspective): `3/0/3`
- directional failure: false

## Seed-59013 four-pair aggregate

R13's separate fresh pair at seed 620703 was `[0.5]` (one child win and one
parent win). Appending it to this R14 block, and not pooling with the
seed-59012 candidate, gives:

- pair scores: `[0.5, 1.0, 0.0, 0.5]`
- mean pair score: `0.5`
- better/tied/worse pairs: `1/2/1`
- game W/D/L (child perspective): `4/0/4`

The preregistered rule requires combined mean `> 0.5` and better pairs greater
than worse pairs for provisional success, or mean `< 0.5` and worse greater
than better for failure. This result is exactly tied at `0.5` with equal
better/worse counts, so optimizer-seed replication is **inconclusive**. It is
not evidence of directional failure, and it does not authorize another Arena
or model change.

## Verification and disposition

The six-game Heavy completed within the approved resource envelope. R14 stops
here as instructed; no seed 59011, new data roots, alternate alpha, Chess,
generated rules, Gen2, or larger Arena was started. The report is published
at the synchronized sandbox SHA and is ready for Chat/Supervisor review.

