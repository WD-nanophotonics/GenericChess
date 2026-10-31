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


## Behavioral quality does not automatically order minimax actions

Here is the precise transfer assumption, rather than a demand to solve every
root first. Write Q(a) for root-player minimax terminal value and mu(a) for
terminal mean under one fixed continuation/opponent law. For any selected a,
if a justified uniform approximation |mu(b)-Q(b)| <= eta holds over the legal
root actions b, then

    max_b Q(b) - Q(a) <= max_b mu(b) - mu(a) + 2*eta.

Indeed, max Q <= max mu + eta and Q(a) >= mu(a)-eta. Similarly, a behavioral
improvement mu(b)-mu(a) larger than the two relevant approximation errors
would imply Q(b)>Q(a). No eta is identified by the present search receipts,
nor does more sampling of the same behavioral law remove a policy mismatch.
Against a fixed arbitrary opponent, an arbitrary continuation mean can lie
on either side of minimax value. Its ordering therefore has no unconditional
minimax interpretation.

This is a conditional interpretation, not an empirical-study admission gate:
a prospectively declared fixed-opponent terminal comparison remains useful
as that behavioral comparison, without knowing eta or all minimax values.
A sampled root-action endpoint and a whole-policy endpoint answer different
questions even under the same opponent.

For finite complete-history play and fixed history policies, let V0 be the
baseline's expected terminal return against fixed opponent sigma. Include
any declared controller/resource information needed to specify that policy.
At a candidate-controlled state h define

    A0(h,a) = E[V0(next history) | h,a] - V0(h).

A telescoping sum along candidate pi1 play against sigma gives

    V(pi1,sigma) - V(pi0,sigma)
       = E(pi1,sigma)[sum over candidate-controlled turns of A0(h,a)].

Terminal V0 is the actual scoring payoff, and the expected increment at an
opponent turn is zero under the same sigma. Thus identical first actions do
not constrain the later sum. The 32 identical root actions settle their own
paired root-action endpoint, not the complete policy comparison. A truncated
trajectory retains an unknown remainder; it cannot be telescoped as though
its last heuristic score or a resource cap were an actual terminal payoff.
This identity is an interpretation only, not an implemented evaluator or a
new requirement to compute every advantage before ordinary matched games.

## The existing learner path does not yet supply the proposed arm samples

At own published 41b171df0d42b01662722c3c3b75dceffe7aa96c,
learning/mainline_search.py blob c9da438405cce54bc5c88d6e8ebe2fd0cb4a365a
documents that seed does not alter lexical ordering. Its q0 receipt is the
matching literal material/terminal leaf from a completed search/PV replay;
it is not an independent terminal rollout mean. Deterministic observations
can mathematically be degenerate stationary samples, but repeatedly reading
that same fixed score does not turn varying-depth search work into terminal
reward observations or create new information by changing a seed.

learning/incremental.py blob e451f7f85426c4cece211a581fef68b6974b0f7d
already provides play_episode with learner=None for evaluation and an explicit
opponent_policy callback. Its EpisodeResult.outcome is optional; horizon,
node, time and non-scoring endings can remain UNKNOWN. This is an existing
whole-episode return route, not an implemented within-root arm sampler.
A future fixed-model, declared-opponent terminal comparison could use the
existing route; this round does not execute it or change its semantics.
No gradient/alias test, new model, rollout wrapper or old closed call is added.

Adaptive sample allocation is distinct from filtering out capped failures.
The former can be covered by a valid recommendation theorem and the random-N
argument. The latter changes the observed reward law if completion depends
on outcome or arm. For a fixed initiated finite panel with well-defined
bounded scoring payoffs Z in [-1,1], completed sum S, missing count u and
total n, the unobserved finite-panel mean lies only in [(S-u)/n,(S+u)/n].
That is a deterministic range, not a population confidence interval.
Non-scoring cases do not acquire fictitious bounded scoring labels.
Missing/censored records, initiated denominator and completion rates must
remain visible rather than being silently removed or assigned zero.

This closes the target-transfer question: no unconditional minimax/whole-policy
claim follows from good-arm theory or the present same-action panel. The
positive route is a declared behavioral terminal comparison using the existing
play path when a concrete new consumer warrants it; it requires no exact-WDL
gate. Another source/fixture/experiment is not launched by this conclusion.


## Direct resource constraints: a positive conditional model, not a free bridge

The unresolved throughput term motivated a separate original-source check:
[Li and Cheung 2024](https://proceedings.mlr.press/v238/li24c.html), sections
2–4/6 and Appendix B.1–B.4. PDF SHA256
eadbedf953ffdeb4a889c96b66d1650f423aaa14e6f4bdc9400f7316c0d7e7f5,
30 pages; model/algorithm pages 3/4 visually checked, not full-proof validation.

The resource-constrained model explicitly allows correlation between reward
and consumption. It assumes stationary independent arm draws, a unique best
mean, and a known per-pull consumption bound normalized to one for every
resource. SH-RR reserves one unit before a pull, rations resources across
elimination phases and carries observations forward. The stochastic-resource
bound uses a larger effective cost than simply the mean cost. Its proof
separates insufficient completed pulls from a wrong reward ranking, handling
the former with cost concentration. Thus cost/reward correlation alone need
not invalidate a resource-aware method; the completion-tail issue is analyzed
inside that method rather than abolished. This is not the many-good-arm,
possibly-tied objective from Zhao. Their guarantees cannot simply be spliced.

A hard-budget reservation has a direct physical meaning. If each completed
observation costs at most c_max in wall units, starting one with remaining
wall >= c_max can protect that observation's allowance. A mean, nominal
deadline or observed maximum is not c_max. If a nonpreemptive observation has
positive probability of costing more than the remaining wall, insisting on
its completion cannot give a certain hard wall guarantee. Interrupting it
instead creates an incomplete observation; no terminal reward is supplied by
that interruption. Neither point asks for a new wrapper or cancellation worker.

The paper-linked software was inspected ONLY as text at repository
lzt68/BAI-Resource-Constraint-AISTATS2024-Camera-Ready,
commit c89f434e3eae4b0b808e586ed57c8ddbee92d403.
In NumericRecord/RealWorld/Source/env.py, timing surrounds fit plus predict;
split, clone, scoring and agent work lie outside that recorded consumption.
The environment checks remaining consumption after a response. It does not
enforce a one-second worst-case fit/predict bound before starting one.
This limits a literal inclusive-hard-wall interpretation of that module.
It does not establish an observed overrun, reproduce any experiment, or show
which exact module produced every published result. No external code ran.
Saved env SHA256 15c5457bef3eb97f560eef5ef12cd0134f99b36c1c7c76d8b29b5e24a1e939bc;
agent 2d0ce22ffc4224a14f88d58e4353903a2c800322e35a35c15d2a28cb09aad82b.

The useful project implication is positive but conditional: a resource-aware
statistical model can handle unequal random costs without knowing their means
as algorithm inputs. It still needs a real observation law, the required
physical bounds and charged overhead. Existing cooperative search deadlines
and UNKNOWN returns do not by themselves instantiate all those assumptions.
No measured GenericChess speed/strength or SH-RR port follows.


## The generic union prefactor is not a universal anytime penalty

The earlier random-N set inclusion is valid, but its geometric prefactor is
not a lower bound or a reason to reject anytime methods. A direct maximal
inequality can be sharper when an actual stochastic process supports it.
The following own derivation keeps the variance proxy explicit rather than
copying a source proof's reward-difference constant.

For balanced paired observations of two fixed arms a,b with gap
Delta=mu(a)-mu(b)>0, set

    X_j = (R_bj-mu(b)) - (R_aj-mu(a)).

Assume E[exp(lambda X_j) | past] <= exp(v*lambda^2/2) for every real lambda,
with a fixed justified v>0. This assumption includes centering and the
relevant conditional law, not merely bounded marginal scores.
M_n=exp(lambda*sum(X_j)-v*lambda^2*n/2) is then a nonnegative supermartingale
starting at one. With lambda=Delta/v, a wrong empirical ranking at any n>=m
implies M_n >= exp(m*Delta^2/(2v)). The nonnegative maximal inequality gives

    P(exists n>=m: empirical_b(n) >= empirical_a(n))
       <= exp(-m*Delta^2/(2v)).

For independent unit-sub-Gaussian arm observations, v=2 suffices.
Without within-pair independence, conditional Cauchy-Schwarz gives v=4
from the same per-arm unit proxies. A common-seed pairing therefore needs
its joint/conditional assumption stated; independence is not invented.
The gap is an analysis parameter here, not required prior knowledge for
forming empirical rankings. Plugging an observed gap into this expression
would need a separate valid argument.

If the service returns that ranking at a completed-pair count N, its error
is at most P(N<m)+exp(-m*Delta^2/(2v)), without the geometric factor.
With a fixed best comparator and all K arms sampled in balanced complete
rounds, a union over only epsilon-bad arms gives the corresponding
sum of exp(-m*Delta_k^2/(2v_k)). Ties at the best mean do not create value
regret. This all-arm construction is NOT a data-poor method, BSH proof,
policy proposal or current search guarantee.

A separate elementary check confirms the resource paper's useful cost-tail
mechanism. For iid D in [0,1] with mean d, its f(d) is e^2*d when d>=e^-2
and 2/log(1/d) otherwise. In the first case f(d)>=1, so
P(average D>f(d))=0. In the second, put r=log(1/d)>2 and p=2/r.
The Bernoulli Chernoff exponent obeys

    KL(p,d) = p*log(1/d) - binary_entropy(p)
              - (1-p)*log(1-d)
            >= 2-log(2) > 1/3.

Thus P(average D>f(d)) <= exp(-N/3) follows directly. This validates that
particular bounded-cost tail statement under its assumptions, not every
rounding, constant or theorem in the source or its physical-time experiments.
No stochastic simulation or extra scalar fixture is used.

Decision consequence: neither outcome-dependent stopping nor cost/reward
correlation is an automatic impossibility. A suitable conditional process
can address both. Current evolving search scores, censored trajectories and
uncalibrated resource bounds still cannot be substituted for that process.
