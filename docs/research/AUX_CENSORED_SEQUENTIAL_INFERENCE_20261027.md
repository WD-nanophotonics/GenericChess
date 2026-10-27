# Censored paired evidence and sequential inference â€”2026-10-27

The maintained runner correctly reports finite missing-result completion bounds, not confidence intervals. Optional-stopping-valid inference can preserve UNKNOWN, but requires a specified sampling/filtration/target contract that current output alone does not establish. No existing result is upgraded and no inference module or new experiment follows.

This is a distinct literature fallback after the Pro-requested legacy handoff and runner source questions closed. Its concrete consumer is interpretation of scripts/incremental_learning.py:241â€“277, baseline35c9d091757d2ccb0db7eecb38d6208ea369f254. It does not reopen TD theory, teacher/configuration checks, PRIMARY algorithm work, or frozen studies. Costs/caps remain.

## Primary sources read

[Howard et al., version6,2021](https://arxiv.org/html/1810.08240v6), section2/theorem4: uniform bounds may target averages of conditional means of adapted bounded observations, without independent observations or a common mean. The prediction/variance conditions matter. This does not turn exposed records into estimates of a fixed population mean.

[Waudby-Smith and Ramdas, version7,2022](https://arxiv.org/html/2010.09686v7), sections4/4.3/5 and propositions2â€“3: predictable nonnegative betting products require conditional-mean conditions; a marginal mean alone is insufficient. Their finite-population model randomizes observation order. A fixed panel alone does not establish that model. Publisher access failed once; versioned original arXiv was the successful fallback. Source simulations/packages were not executed.

## Own application and limits

One possible reporting unit is a root family containing both colors and matched profiles. Its WDL contrast d_i lies in[-2,2]. Grouping avoids automatically treating two reused-root colors as independent; it does not itself establish independence. Other units are possible with a correctly specified conditional-mean target.

From actual outcomes/missing slots define lower/upper endpoints l_i,u_i in[-2,2]. If a well-defined completed-policy return exists, l_i<=d_i<=u_i. For the SAME pre-observation filtration F:

    E[l_i | F_(i-1)] <= E[d_i | F_(i-1)] <= E[u_i | F_(i-1)].

Thus an all-time lower confidence bound for the average conditional mean of l_i, plus an upper bound for that of u_i, encloses the average conditional mean of d_i by order and a union bound. Each endpoint stream must be admitted with the claimed adaptedness; retrospectively changing past observations using future outcomes is not covered automatically. Streams may depend on one another. This order argument requires no missing-at-random equality or reconstruction.

A fixed-policy population mean across fresh roots is stronger than the average of conditional means under changing budgets/history. Even without a defined completion policy, the observable streams describe performance envelopes for the bounded procedure. They are not imputed actual rewards. Search returning no action does not define how a game would finish with extra resources; a latent full-game target needs explicit continuation semantics. No bound is a learner label.

A simple separate consequence illustrates the conditional-null requirement. If d_i is well-defined with E[d_i|F_(i-1)]<=0, choose predictable beta_i in[0,1/2]. Once-admitted l_i<=d_i, l_i>=-2 gives nonnegative factors1+beta_i*l_i with conditional expectation<=1. Their product starts at1 and is a nonnegative supermartingale, so its chance of ever crossing1/alpha is at mostalpha. This is a conditional-null test, not a confidence interval for an arbitrary marginal mean, minimax truth, or useful-power guarantee. No bets are fitted to old games or deployed.

## Exact finite controls

A hypothetical independent family returns +2/-2 with probability1/2. Censor negative outcomes. At beta1/4, retaining their valid lower endpoint-2 gives factors3/2 or1/2, expectation1. Dropping those families retains only3/2 factors. Exact enumeration of4096 twelve-family paths at threshold5 (alpha1/5) gives robust crossing57/512 versus3797/4096 when censored negatives are skipped. This is a counterexample to proposed complete-case inference, not a bug observed in the current runner, which retains missing slots. Neither probability is a historical p-value, chess result or performance measurement.

For two perfectly correlated colors on one root, let both return the same random d. Bet0 on the first, then beta1/4 on the second only after a positive first result. Both marginal means are0, but expected capital is5/4. The conditional-mean null fails after observing the first color. One prespecified factor on the whole family instead has expectation1. This demonstrates a possible dependence, not actual measured correlation or automatic validity after clustering.

Controls use Fraction/itertools, no Core/Native/Player/search/training/solver/game/build. [Exact rational outputs](data/aux_censored_sequential_20261027/exact-controls.json) record all counts. No larger sweep is needed: these finite cases already separate the proposed inferences. No test framework/statistical package is added.

## Decision for current evidence

Keep existing completion bounds and counters unchanged. Before a future statistical claim, name the target rule/root law, frozen resource/opponent/model policy, unit, randomization, filtration and any continuation semantics. A fresh seed label or profile-order rotation alone does not prove randomly sampled independent rule families. An anytime theorem grants no budget extension, cap refill or closed-study continuation.

Statistics cannot remove censoring's identification gap. In the special case where fraction q of whole families is entirely unresolved and the rest have observed mean contrast delta, the finite lower completion endpoint is(1-q)*delta-2*q. For positive delta it is positive only if q<delta/(delta+2), before sampling uncertainty. This is an identity for that completion pattern, not a missingness assumption or a forecast.

Outcome: feasible caller-specific inference under explicit premises, but NO_CURRENT_STATISTICAL_UPGRADE of exploratory results. Independent critique should address the envelope/latent-policy distinction and filtration, not launch a general theory or inference framework. No new corpus, game or historical artifact was read/replayed. Token cost UNKNOWN; all prior costs retained.
