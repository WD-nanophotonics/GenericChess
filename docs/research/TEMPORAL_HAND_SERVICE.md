# Capture time and remaining service

2026-10-08. Rule-only construction evidence, exposed development. This keeps a
cheap temporal approximation with explicit assumptions; no material table,
human fit, player-strength claim or default change follows.

## Observable and approximation

Use the two previously frozen five-entity Shogi contexts, differing only in
own King(0,0) versus(0,1). The unique target starts as enemy G or promoted P;
actual capture resets its base G/P into the recipient hand. Ordinary legal
actions are uniform. If the current actor holds that unique tag and can drop
it, choose uniformly among its legal drops instead. Either owner follows this
policy. Every sampled Core/Native legal set, full child and terminal agrees.

T is first transfer to owner0, including later captures and nontransfer paths.
U at a fixed final node is the number of distinct legal endpoints of that tag
when owner0 has it on board and is to move; terminal/hand/enemy custody is0.
This is an opportunity at the final node, not accumulated reward or game utility.
Further recapture/promotion remains part of the actual continuation.

The old exact H3 measures three actual transitions after forced initial capture.
A constant approximation predicts P(T<=H-3)*H3. A time-aware alternative uses
sum_t P(T=t)*K(H-t), with K5/7/9 independently sampled after forced initial
capture and K3 kept at the old exact value. Transfer on the penultimate ply
cannot deploy the newly acquired hand piece by this final node, so contributes0.
Both models approximate delayed-capture contexts by the initial postcapture
context. Unlike sum P(T=t)*E[U|T=t], this is not an identity or same-sample fit.

## Prospective batches and decision

Pilot512 episodes/cell led to a separate2048/cell six-step batch, followed
by a separately declared2048/cell ten-step batch. All four cells share fixed
policies and paired G/P random quantiles. Practical impact screens were0.1G and
0.025P with a diagnostic normal interval excluding0, declared before the later
batch. They are development decisions, not universal accuracy tolerances.

The six-step batch triggers neither practical screen. Its paired
G-P opportunity differences are0.81494/0.74365. One P residual interval excludes0
but its magnitude0.01902 is below the declared0.025 screen. Ten steps exposes
larger P underestimation in both contexts; unchanged horizon expansion would
therefore be less informative than testing the specific remaining-time omission.

| Context/target | Actual ten-step U | Constant H3 prediction | Time-aware prediction |
|---|---:|---:|---:|
|0/G|1.315430|1.321160|1.299207|
|0/P|0.314941|0.265095|0.325788|
|1/G|1.130371|1.157749|1.120265|
|1/P|0.270508|0.226564|0.267110|

Seed audit found1048 shared seeds per context between the original kernel and
outer ten-step sample. Its means remain observations, but its independent-source
standard errors were unqualified and are superseded. Six/ten-step samples also
overlap seeds: they are separate batches, not independent horizon replication.
Original sources, results and posthoc strata remain isolated with this warning.
The strata's combined-error interpretation inherits the overlap qualification.

The corrected kernel uses2048 paths/cell with proved-disjoint intervals
202610090000..202610092047 and202610190000..202610192047, keeping H3/5/7/9 on
each path. G/P common seeds within a context intentionally preserve pairing.
The same estimator, policies, N and300sec resource checkpoint were declared
before correction execution; this is not result-driven precision extension.
P's service grows with remaining time; G changes less. Combined outer/kernel
first-order delta standard errors now give P residual intervals
[-0.01591,0.03760] and[-0.02691,0.02011]. These approximate development
intervals are not bounded finite-sample coverage or proof of model accuracy.
Final promoted-P opportunity contributions0.07715/0.06055 localize a possible
mechanism but are postdeclared strata, not a causal attribution of the bias.

Retain the qualified time-aware approximation rather than reject the whole
service construction or sweep unchanged horizons. Next useful work must address
one actual omitted service/context mechanism, not select a discount or horizon
against human prices. Current material construction remains OPEN.

The six-step, ten-step and original kernel batches take about
128.27,202.13 and224.37 seconds respectively, including full cross-executor
checks and record writing. Raw counters distinguish actual transitions from
declared maxima. Initial loop/else pilot failure and its partial record remain.

Compact diagnostics: [temporal data](data/temporal_hand_service_20261008.json).
Exact producers, plans, partials and restore dependencies:
[isolated archive](../archive/temporal_hand_service_20261008/README.md).
