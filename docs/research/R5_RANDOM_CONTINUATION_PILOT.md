# Seeded random continuation on the frozen R5 material-control root

**Unknown.** Does Abramson–Korf's uniform-legal-action continuation
produce an easily distinguishable terminal-payoff signal on the existing
frozen R5 DEVELOPMENT root whose exact minimax labels separate DRAW
from LOSS? This probes the new policy assumption without fitting a
material coefficient or opening a human-value holdout.

`scripts/audit_r5_random_continuation.py` verifies the frozen fixture
SHA, rebuilds `generic-f23n-legacy_capture_recapture-2`, and checks
that its five public root actions match the exact certificate. From
each child it samples exactly 100 continuations, uniformly choosing
among the current state's public legal actions until terminal. The
seed is `20260929`. The predeclared budget is at most 5,000 applied
actions or 10 seconds, with an exception if either bound is reached.
It completed 2,479 applied actions in under one second locally.

| Exact minimax root label under `max_ply=6` | Root actions | Seeded terminal observations |
| --- | ---: | --- |
| DRAW | 4 | 100 draws out of 100 for each action |
| LOSS | 1 (the material-changing capture) | 98 draws, 2 losses out of 100 |

Across all 500 seeded continuations, terminal statuses are 482
`max_ply`, 15 repetition draws, one stalemate draw, and two
checkmates. Thus the six-ply cap accounts directly for most observed
draws; this is measured rather than assumed.

For transfer to Chess/Shogi play without this six-ply cap, those 482
`max_ply` outcomes are **censored by this synthetic RuleSet's cap**,
not observed natural draws. That is 96.4% of all sampled lines; the
exact-LOSS capture alone has 96 capped draws, one repetition draw, one
stalemate draw, and two checkmates. The finite R5 contract correctly
calls the capped lines draws, but these data cannot estimate the
uncapped random-continuation outcome or validate a cross-game material
prior. Conditioning only on the 18 uncapped observations would change
the question and leave a very small, selected sample.

The LOSS action's observed mean under payoff coding
`Win=+1, Draw=0, Loss=-1` is `-0.02`; the four DRAW actions' observed
means are zero. The deterministic seeded test reproduces these counts.
This is a **small Monte Carlo observation**, not an exact random-policy
expectation or a confidence claim about game strength. The root is a
synthetic 5×5 capture-to-hand game with an authoritative six-ply cap;
482 of 500 random lines draw at that cap. The observation shows that this
policy can give a near-zero sampled signal even to a move that exact
adversarial play loses. It does not show that a larger sample reverses
the ordering, nor that random-continuation evaluation is generally
bad. It does not identify a static type coefficient, a Chess/Shogi
context distribution, or a cheap full-game calculation. Do not scale
up sampling or tune on this root by default. Xiangqi human values stay
sealed.

**Exact-cost abort.** A subsequent read-only depth-first calculation
attempted exact uniform-action terminal probabilities on this same
frozen root, memoizing full `GameState` values. Its predeclared bounds
were 10,000 expanded states and five seconds. It hit the state-count
bound before the time bound and produced no complete action
expectation. This is a computation abort, not a result about the
probability of loss. The temporary failing calculation was removed
from the checkout; do not simply raise the cap and rerun without a
new compression argument or a decision that the exact number would
change.
