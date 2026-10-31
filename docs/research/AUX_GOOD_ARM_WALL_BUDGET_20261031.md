# Good-arm quality under an actual service budget — 2026-10-31

A recommendation can be useful before every action has been sampled, without
certifying a unique best action or solving the full game. This is a conditional
statistical target, not a guarantee for the current alpha-beta/PN service.
The missing bridge is the observation law and actual completed work under the
same whole service, rather than another exact-WDL admission gate.

## Original-source coverage

[Zhao et al. 2023](https://proceedings.mlr.press/v202/zhao23g.html), main
sections 2–5, Appendix B.8/C.4/C.8 and implementation discussion, studies
stationary stochastic arm observations and simple regret. Its bracketed method
can exploit many sufficiently good arms without taking their number as input.
The stated error rates are asymptotic, hide logarithms/constants, and have
minimum-budget conditions; the caption experiments do not establish game-search
speed or quality. PMLR PDF SHA256
6f27abd0f43656e22f406335c82433dc8503f272fd7bcc4654e4fef255b8ba9c
(49 pages). Selected full sections were read, not every proof independently
verified. Pages 5/7 were rendered and visually inspected.

Two printed expressions prevent a literal algorithm/lower-bound port. Page 7
Algorithm 3 uses n max 2^B for a bracket even though its sampler returns all arms
at sizes at least n; this conflicts with its small-bracket description. Page 5
Theorem 3 has a max with 1/2, giving a perpetual error floor inconsistent with
fixed finite Gaussian-arm consistency. Its B.8 proof splits exclusive cases
but repeats that max. Min in each expression is a plausible interpretation,
not an author-confirmed correction. The arXiv v2 PDF contains the same forms
(SHA256 fb95cf90012db03662ec03da1756665e854a18e96567dd6f32586bc2b5e38b22).
For the claimed floor, a direct check is available without solving the paper:
uniformly take k=floor(T/n) independent samples per Gaussian arm and return
the largest empirical mean. For each arm worse by more than epsilon, the
mean difference has variance 2/k, so a Gaussian tail and union bound give
error <= (n-1)*exp(-k*epsilon^2/4), uniformly over all mean vectors. For fixed
n,epsilon this falls below 1/2 as T grows, including the theorem's class.
This contradicts the literal constant floor; it does not validate a repaired
lower bound or discredit every other result. No source implementation,
corrected algorithm or exact lower bound is adopted.

[Katz-Samuels and Jamieson 2020](https://proceedings.mlr.press/v108/katz-samuels20a.html),
definitions 1/2, section 4.1 and supplementary C.1/F, independently separates
self-certifying PAC termination from eventual good recommendations. The latter
need not certify its own output. Its principal upper bound controls an expected
sample stopping time; that expectation is not a fixed-budget confidence
guarantee. Good-arm counts need not be known to its algorithm. Its Algorithm 1
uses capped small brackets; this does not resolve the other paper's print.
Main PDF SHA256 6897f82b7377ba08d65a48d58f11c4698356d3b4463c34f2514d6593c997d32f;
supplement 9b0e653d2dcb5e30385f80df3c3984ead6c501f0928651099fca186380a465bf.
Definitions were visually inspected. Supplement C.1 concerns particular
all-arm-initializing algorithms, not a lower bound on every exploratory method.
No BUCB/BSH implementation or experiment is introduced.

## A conditional random-budget statement

The following is an elementary own derivation, not a numerical application of
either paper's theorem. Fix one complete-history root and one stationary arm
target mu(a). Let J_t be the recommendation after t completed observations on
one infinite coupled run. Define E_t = {max_a mu(a) - mu(J_t) > epsilon}.
Suppose actual, valid bounds P(E_t) <= p_t hold for every deterministic t >= t0.
The service stopped at whole wall allowance B returns J_N, where N=N_B can
depend on all observed values and costs. It must return the corresponding
completed-observation checkpoint, rather than a different unfinished output.

For any deterministic integer M >= max(1,t0),

    {E_N} subset {N < M} union (union over t >= M of E_t)

and therefore

    P(E_N) <= min(1, P(N < M) + sum over t >= M of p_t).

This set inclusion requires neither independence of N and rewards nor that N
be a stopping time in the sample-only filtration. The assumed p_t law and
checkpoint identity remain essential. In particular, substituting E[N] into
a fixed-t theorem is unjustified.

If p_t <= C exp(-c t), with actually justified C,c>0 on this range, the tail is

    C exp(-c M) / (1 - exp(-c)).

To make that tail <= delta2 requires
M >= log(C / (delta2*(1-exp(-c)))) / c, as well as t0.
A separate P(N<M) <= delta1 then gives error <= delta1+delta2.
The prefactor matters at finite c. The asymptotic rate notation in the source
does not supply a calibrated numerical C,c for GenericChess, nor necessarily
a constant-c expression after its hidden logarithms. No current error
probability or service threshold is computed from it.

If instead a source gives an eventual-good event with failure probability
delta0 and a random sample threshold tau with E[tau] <= H, then independently
of any relationship between N and tau,

    P(E_N) <= delta0 + P(N < tau)
            <= delta0 + P(N < M) + H/M.

This deliberately loose Markov conversion distinguishes an expected sample
bound from an actual-budget probability. An expected fast threshold is not
a guarantee that the threshold has been crossed on the current service.

## Project interpretation

Current root scores, proof completion counters and evolving depth estimates
are not the independent stationary terminal observations assumed by the
selected sources. Their count is not T. Within-root good-arm density is also
not the 9/16 PN completion fraction across different roots.

One possible future target is expected actual terminal return after action a
under declared fixed continuation/opponent policies and fresh independent
randomness. That is a legitimate behavioral target, different from minimax
full-history action value. It does not require unique best actions or a
complete WDL oracle. A changing continuation policy or completion-only
filtering needs its own analysis; UNKNOWN is neither reward zero nor DRAW.
No such rollout, policy, training or new sampler is launched here.

Arm sampling and root setup must be physically executable and charged:
legal frontier construction, observation trajectories, verification,
inference, selection and return are part of B. The papers' sample counts do
not make those costs equal, bounded or free. A data-poor sample claim alone
cannot establish a data-poor whole-service gain.

The existing [new policy packet](AUX_NEW_POLICY_ENDPOINTS_20261031.md) contains
32 finite paired identical selected actions. Its exact relative minimax-action
difference zero needs no stochastic concentration argument. It supplies no
independent within-root reward sequence, calibrated p_t, completion-count
tail, or policy-to-minimax approximation. It cannot validate the formulas above.
Identical root actions still do not equate later whole policies.

Current decision: retain good-arm/simple-regret evaluation as an optional
behavioral endpoint where its observation law is real; do not port these
algorithms, add a proof gate, reopen closed panels, or claim a GenericChess
speed/strength result. Actual matched whole-service outcomes remain the
higher-priority Pro quality objective. A future concrete consumer and cheaper
comparison must determine whether this endpoint is useful.
