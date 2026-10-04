# Sound partial goal labels can certify a frozen static comparison

The preceding bridge investigation required a cheap complete-label cost
premise before further experiments. That admission requirement was stronger
than necessary. Keep the exact bounded goal target, but permit sound intervals
for unknown values. A risk comparison can sometimes be proved for every
completion without solving those unknown states. This removes a specific
unnecessary cost gate; it supplies no new material formula or game evidence.

## Derivation

For a label U in [l,h] and fixed prediction p, the squared loss minimum is zero
if p lies in the interval, otherwise the nearer endpoint's squared distance.
Its maximum is the farther endpoint's squared distance. Weighted sums give
valid risk bounds. Intervals may be correlated through the game; allowing
independent completions is a conservative relaxation, never an assumption
that the actual labels are independent.

For a fixed baseline b and declared rho=9/10, use the SAME label in the paired
margin q(U)=rho*(U-b)^2-(U-p)^2:

q(U)=(rho-1)*U^2+2*(p-rho*b)*U+rho*b^2-p^2.

Its exact extrema occur at endpoints and an interior vertex when present.
Since rho<1, the minimum is at an endpoint. Sum the extrema with the frozen
state weights. If the lower baseline risk is positive and the lower margin
is nonnegative, then R_candidate<=rho*R_baseline for ALL admitted label
completions. A negative upper margin certifies failure; remaining cases are
inconclusive. Passing requires every declared comparator, not whichever is
most favourable. This is a finite-measure statement, not a population inference.
With rho=1, the paired difference is affine in U; the implementation handles
that boundary without division by zero.

Sound minimax intervals can be propagated without imputing a frontier score:
max nodes take max of child lower bounds and max of child upper bounds; min
nodes take the corresponding minima. All legal children must be accounted
for, including unexpanded children with full [-1,1]. An incomplete action set
cannot silently be treated as complete. This elementary propagation argument
does not validate any existing engine output as a sound interval. No engine
adapter, complete game solve or real-game certificate was built in this probe.

## Frozen arithmetic control

`PARTIAL_GOAL_RISK_PROTOCOL.md` fixed four inventory feature vectors and a
candidate before computation. Two labels are exact +1/-1 with combined mass
3/4; the remaining two have full unknown [-1,1], mass1/4. Candidate slopes
(1/2,0) and the zero baseline are synthetic declared inputs, not derived prices.
Exact candidate risk is in [3/16,7/16]; baseline risk in [3/4,1]. The paired
10% margin is in [37/80,39/80], strictly positive, so this comparison passes
without reading any value of the unknown quarter. The inventory covariance
is diag(3/4,1/4), full rank, but these labels do NOT uniquely identify an optimal
coefficient vector: full feature rank alone cannot repair partial goal labels.

All-unknown identical-zero predictions are inconclusive: baseline lower risk0
and margin [-1/10,0]. A known +1 label with candidate -1/baseline0 fails with
margin -31/10. Thus neither missing labels nor a zero baseline are manufactured
into successful validation. The generic exact quadratic code is in
`scripts/audit_partial_goal_risk.py`; hashed evidence is in
`data/partial_goal_risk_20261004.json`. Five tests pass, including rational-grid
extrema, every checked unknown-label completion, and malformed inputs.

## Research decision

Replace the blanket all-labels-complete prerequisite with: fixed independent
candidate/baselines, declared goal target/measure/support, sound label intervals,
and a capped comparison capable of an explicit inconclusive outcome. Do not
change any earlier count-use gates, scores or failures retrospectively. This
does not produce a rule-derived prior or admit a sampling/search batch by itself.
The next decision is whether a genuinely independent rule-derived candidate
and justified deployment can exploit this cheaper comparison. No human values,
old global deployment labels or Xiangqi holdout have been inspected.

Also correct the previous theorem's wording: uniform conditional means for
every actor/type/owner are sufficient for E[B|X]=v.X, not necessary. Residual
actor means can cancel in the signed sum. The aggregate identity and goal
calibration, rather than individual invariance, are the premises actually
used in that conditional proof. Existing data supports neither the needed
aggregate deployment identity nor goal calibration; the material decision stands.
