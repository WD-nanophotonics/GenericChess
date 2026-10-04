# Finite projection controls: counts, signs, coverage and prediction

2026-10-05. Pure arithmetic checks, no new game labels, experiments or prices.
`allocation_static_projection.py` accepts a complete finite context law,
physical mode counts and signed total-allocation intervals. It computes
E[A_m]/E[N_m] without per-root division, and conservative inventory score boxes.
Allocation authenticity/common-task semantics remain the caller's responsibility;
this helper does not certify a legal coalition game or independent use.

Five tests qualify variable counts, zero-count roots, the exposed matched
Knight example, negative/unknown component bounds and fail-closed coverage.
In the independent variable-count example, two equally weighted roots have
mode count1/allocation1 and count3/allocation0. Token weighting gives w=1/4,
so mean static score1/2 equals mean allocation1/2. Averaging per-root token
ratios instead gives w=1/2 and mean score1, a different quantity. Deploying
only the count3 root gives static3/4 against actual allocation0: a population
shift destroys even the unconditional first-moment match.

A mode with zero count in some roots retains those roots' mass and zero
allocation; a mode with zero expected count across the entire law has no
justified prototype. Invalid law mass, missing mode coverage, float/Boolean
counts, incoherent intervals and allocation totals outside[-N_m,N_m] fail.
Signed allocations are not clipped. Component intervals are NOT a joint
independent allocation law: a score box[-2,2] can be conservative while a
separate authenticated efficiency identity proves total1. The helper does
not silently narrow it by inventing correlation.

The exposed matched Knight roots reproduce static5/4,3/4, mean1 and squared
error1/16, while constant1 has zero error on that local two-root task. This
tests projection arithmetic; it is not a fresh independent benchmark or a
global rejection of static material vectors.

The coalition helper gained a signed common-background mixed-difference
operator. Three additional tests reconstruct ALL16 binary two-resource
tables, preserve unknown interaction[-1,1], and independently attain local
additive approximation lower bounds1/4 with an intercept and1/3 with a fixed
empty baseline on the pin table. An additional independent permutation control
checks the later physical obstruction table's signed1/6,1/6,-1/3 allocation.
Fifteen tests across the two helpers pass; no empirical audit is rerun by them.
