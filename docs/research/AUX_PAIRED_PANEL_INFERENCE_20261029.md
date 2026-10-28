# Paired Leaper panels: what uncertainty tools would mean

The new finite panel remains 1W/24D/5L and its frozen gate remains FAILED. This
bounded source-method review adds no CI, bootstrap implementation, experiment,
metric replacement or new approval gate. It asks what a future consumer could
legitimately infer from paired, correlated, differently sized rule panels.

## Original source and implementation scope

[Agarwal et al., statistical precipice, arXiv2108.13264v4](https://arxiv.org/html/2108.13264v4)
defines independent runs within each benchmark task, develops stratified
resampling, and studies robust aggregates. Its few-run empirical coverage is
not a coverage theorem for this Leaper protocol. A task-level resampling option
also exists; using it does not establish that a hand-selected rule family is a
random draw from the intended rule population.

The [official library source at3ccd9f4](https://github.com/google-research/rliable/blob/3ccd9f4dea577a04d3d2b557f259aac08badbd81/rliable/library.py)
resamples runs within fixed tasks by default. A list/tuple of arrays selects
independent-array resampling. Stacking algorithms as an extra array axis also
does not preserve our pairing automatically: its run-index draw has the entire
array shape, so different arm coordinates can choose different source rows.
These are appropriate for their declared targets; they are not a drop-in
implementation of paired-root contrast uncertainty.

The [metrics source](https://github.com/google-research/rliable/blob/3ccd9f4dea577a04d3d2b557f259aac08badbd81/rliable/metrics.py)
uses a25%-trimmed pooled mean for IQM, threshold shortfall for optimality gap,
and an independent-draw rank comparison with half credit for ties. These are
different questions from decisive match wins or minimax action regret.

The exact HTML and source bytes are privately pinned in
[method-sources](data/aux_admitted_extension_20261029/method-sources.json).
No external library was installed or executed. Paper sections2/4.1/4.3/6 and
AppendicesA5/A7 were read for this question; no whole-paper experimental
reproduction is claimed. The web PDF fetch exceeded its response-size limit;
versioned HTML was available and preserved instead.

## A paired-index counterexample using actual finite scores

Family0 has two already-observed root-pair ON scores, normalized per game:
A=[1/4,3/4]. OFF is its exact complement B=[3/4,1/4]. A legitimate same-root
contrast must retain this joint identity.

Selecting a common row gives differences [-1/2,+1/2]. Selecting the two arm
indices independently gives [-1/2,0,0,+1/2]. Two of those four synthetic arm
pairs even violate A+B=1. Under the uniform finite index experiment, the
single-draw variance is1/4 with common indices and1/8 with independent indices.
This exactly demonstrates an understated variance for the latter joint model;
it is **not** an estimated variance or CI for actual controller performance.
The unequal covariance was introduced by the hypothetical resampling procedure.

The broader point is not that independent resampling is universally bad.
For different independently trained algorithm populations it can be the desired
model. Here ON/OFF in the same match are coupled by construction. A paired
contrast would need common root/role blocks. Merely adding another ndarray axis
does not assert that invariant to an implementation.

Nor are30 games30 independent rule families. For a separate illustrative model
with independent family latent outcomes and perfect within-family correlation,
family sizes[4,4,2,4,4,4,4,4] give a variance inflation of
`sum(k_m^2)/sum(k_m)=116/30=58/15` relative to treating games as IID with the
same marginal variance. This is an exact countermodel, not a fitted dependence
estimate for this dataset. Other dependence patterns give different results.

With only one observed scalar per task, resampling within that task repeats the
same scalar. A zero-width result would reflect the resampling input, not proof
of zero uncertainty in future repeats. Similarly, task resampling can be an
explicit sensitivity calculation over the empirical family set without
becoming a confidence statement about all unseen rules.

## A robust statistic can hide the endpoint this project cares about

The actual30 game scores are five0s, twenty-four1/2s and one1. Trimming the
lowest and highest floor(30/4)=7 values removes **all six decisive results**.
The remaining16 are draws, so IQM=1/2. Median is also1/2, whereas the frozen
raw mean is13/30 and the recorded wins/losses are1/5.

That is no contradiction or library defect: it demonstrates a different target.
For a draw-heavy, bounded head-to-head endpoint, robustness to tail outcomes
can discard the very failures being measured. It cannot replace the predeclared
raw score and family-net gate after seeing their negative result. The source
paper's benefits on different score distributions do not authorize that change.

Likewise a threshold1 shortfall is simply17/30 here because every score is
bounded by1. It is not the sum of minimax action losses; unavoidable rule draws
can contribute to that shortfall. In contrast, the main report's ON>=5 WDL-unit
experienced-regret bound follows from the matched complete-game identity, not
from a chosen score threshold. Those units and estimands must remain separate.

Even the independent empirical rank comparison over root-pair scores gives
169/450 after half ties, rather than the head-to-head game-point mean13/30 or
actual decisive-win fraction1/30. That arithmetic uses the same exposed data;
none is a new win-probability measurement on unseen families.

## Three claims that should not share one uncertainty label

| Claim | What the current evidence supplies |
|---|---|
| Score of these exact recorded games | Verified finite points, terminal and missing-slot accounting |
| Expected repeats of a declared controller protocol | Requires a stated repeated-run model and retained pairing/dependence; not estimated here |
| Expected performance on a rule population | Requires a declared rule distribution/coverage argument in addition; not created by resampling |

Seeded layout generation and counterbalanced seat order do not, by themselves,
make the observed roots IID runs of one score distribution. This does not mean
seeded sampling is invalid, or that a finite exploratory comparison needs a
population CI before it can be useful. It means the claim must identify its
actual target and the randomness, if any, over which it is averaging.

The panel also has one selected root in family2 and two in the other families.
Padding an absent second root with0, DRAW or a duplicated result would change
the estimand and invent data. Collapsing to one mean per family avoids padding
but leaves no within-family repeat distribution. If a future learned model is
shared across families, its training-run identity is another shared block;
family evaluations are not extra independent training runs.

The existing wide completion envelopes describe unknown cells in a finite score
range model. They are not sampling confidence intervals. Similarly the Core
terminals/strategy facts and existential regret inequalities are statements
about literal finite games, not estimates of an unknown task distribution.
An interval's name should preserve that distinction.

No new minimum-run count or audit prerequisite is imposed. A small fixed-family
experiment can remain valuable finite development evidence, including a negative
result, without pretending to estimate all-rule strength. Future PRIMARY
production/sampling remains PRIMARY's; AUX can assess a published frozen packet
under its actual declared claim. This source question is closed after these
finite counterexamples; no old packet refill or new bootstrap campaign follows.

[Exact arithmetic evidence](data/aux_admitted_extension_20261029/paired-index-counterexample.json)
and [metric arithmetic](data/aux_admitted_extension_20261029/metric-estimand-counterexample.json)
retain assumptions separately from the actual played outcomes.
