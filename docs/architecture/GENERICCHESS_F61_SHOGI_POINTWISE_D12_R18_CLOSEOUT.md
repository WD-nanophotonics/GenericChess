# F61 Standard-Shogi POINTWISE_Q D1/D2 distribution R18 closeout

Date: 2026-09-14  
Work order: `GENERICCHESS-F61-SHOGI-POINTWISE-D12-DISTRIBUTION-SCREEN-R18`  
Ruleset: `B_CANONICAL_STANDARD_SHOGI`

## Controlled change

The parent, POINTWISE_Q objective, optimizer seed `59013`, width `32`,
regularization `1e-3`, 600 steps, feature representation, q20 target
semantics, evaluator binding, and search implementation were fixed. Only the
training-state distribution changed. The 24 selected roots were exactly 12
`D1_V2_SELFPLAY` roots (seed `620802`) and 12 independently generated
`D2_V2_PV_CORRIDOR` roots (seed `620803`), one root per independent source
trajectory/group where applicable. D2 was built from its own self-play/PV pool,
not from D1. Original D0 roots and Arena opening positions through seed 620707
were excluded.

Fixed parent checkpoint:
`2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`.

## Fit and frozen-opening gate

The resulting child checkpoint is
`e0c36ee8c7355bedfeae996900a0bdcd9c009fbf3a12f2f7f9d782cf9cf1d7ce`, with
model SHA `c0e075e314ddee716cf40db3d0f795eb149a485286fd70b63137efff10d24b24`.
The fit used 24 roots and 164 action rows. Target residual RMS was
`674.7447936704409`; learned residual RMS was `672.5089388739575`, ratio
`0.9966863696949465`. No q10/q20 stability filter or scalar calibration was
introduced.

At the four frozen seed-620700 openings (2,000 nodes, depth 12, TT 8 MiB),
the candidate changed the parent action on all four openings. The candidate
therefore passed the nontriviality gate.

## Fresh Arena screen

One fresh role-swapped Standard-Shogi pair ran at seed `620708`, 2,000
nodes/move, depth 12, TT 8 MiB, one worker:

- pair score: `[0.5]`
- mean: `0.5`
- better/tied/worse: `0/1/0`
- child game W/D/L: `1/0/1`

The pair score is at least `0.5`, so the work-order rule requires reporting
and returning before any confirmation expansion.

## Decision and stop boundary

This is a nontrivial but neutral one-pair screen. It does not establish a
strength improvement, and no further games were started. No D0 mixing, target
filter, objective/seed sweep, scalar calibration, Chess, generated rules, or
Gen2 work was performed.

Compute authority was Chat/Supervisor-approved plan
`f61-shogi-pointwise-d12-r18-screen-20260914-v1` (plan SHA
`8f17398d0bc937994e5b5909d3183ae95de78be7aa4f1dd2f6dde7e102ce7542`),
resource envelope SHA
`009fc4a33483686862ec075c899f1129de1b9ece3c9b98e8575d3c8c280ffac0`, bound
to the implementation sandbox checkpoint before this report.

