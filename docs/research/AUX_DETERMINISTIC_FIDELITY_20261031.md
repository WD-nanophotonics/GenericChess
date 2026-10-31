# Deterministic fidelity is an alternative, not an automatic search guarantee

The absence of iid terminal-reward observations does not exclude every useful
allocation method. A nonstochastic convergence model is a real alternative.
Its target and physical cost still have to match the actual consumer.

Original [Jamieson and Talwalkar 2016](https://proceedings.mlr.press/v51/jamieson16.html):
sections 2–5 and all three supplementary proof pages read. Main PDF SHA256
97a2ce24804114bc64702c6948c960696593523f925d257048b332e5afca5128;
supplement 6786910429693ad9ed7d62163bae8639631bda2b28262a86e7aaf2f869409706.
PDF theory page 4 visually checked. No experiments or implementation replicated.

The model fixes each arm's loss sequence independently of the allocator's
choices, permits nonmonotonicity, and assumes the sequence converges. Its
Successive Halving allocator need not know a convergence-rate envelope.
The sufficient budget and anytime approximation result nevertheless depend
on the latent envelope. Thus an unknown envelope is not a prerequisite for
running an exploratory comparison, but its existence is not a supplied
numerical quality certificate at a chosen service budget. The paper separately
counts training iterations and expensive loss observations; the latter can
change wall-time rankings. These are hyperparameter experiments, not Leaper
strength or runtime results. No algorithm or numerical doubling constant
is adopted here.

## What the mathematical assumption says

For a convergent loss sequence ell_i(t) with limit nu_i, the smallest
non-increasing envelope is

    gamma_i(t) = sup over s>=t of |ell_i(s)-nu_i|.

It tends to zero, even if the actual iterates oscillate. If observed iterates
for two arms are separated by more than their relevant envelope errors,
their limiting order follows. Merely seeing several stable iterates supplies
no bound on the unobserved tail.

For the general class of all convergent sequences, any finite observed
prefix can have different convergent continuations with different best arms.
An allocator seeing only that prefix cannot certify which continuation is
actual. This is an indistinguishability observation about that broad sequence
class, not a constructed legal Leaper counterexample or a new domain-wide
impossibility theorem. Finite rules or additional structure may give useful
bounds. No exact-WDL certificate is required before an ordinary bounded
empirical comparison.

Convergence of parameters is also not automatically convergence of terminal
policy quality. A finite-tree minimax value built from continuous leaf values
is continuous, but the chosen argmax can change at ties. A parameter sequence
approaching such a boundary can keep changing the selected policy. A limiting
strict decision gap would instead yield eventual local action stability in
that fixed-tree model. Neither condition has been measured for the current
learner. This is a target distinction, not a rerun of old gradient/tie panels.

## Mapping to the actual public learner

Own source pin 41b171df0d42b01662722c3c3b75dceffe7aa96c:
generic_chess/learning/mainline_search.py, blob
c9da438405cce54bc5c88d6e8ebe2fd0cb4a365a.

The adapter starts a new AlphaBetaPlayer per query, retains TT/ordering inside
the query, and sets max_depth to the declared depth (default 2). More nodes
or wall time at a fixed depth can therefore approach the completed finite-depth
material/terminal criterion, rather than full-game minimax value. A convergent
trace with the wrong limit target is not repaired by identifying its best arm.

Where a declared finite scoring horizon and complete search eventually provide
full-game values, a different convergent fidelity trace can be defined in
principle. This does not establish a cheap convergence rate, a valid score for
every interrupted query, or applicability across unsupported/non-scoring rules.
The current adapter explicitly returns unusable/UNKNOWN receipts for incomplete
results and failed PV admission; those are not loss observations.

Independent-arm fidelity also needs its source context fixed: the complete
history, model, search policy and resource convention. PVS alternatives share
alpha, TT and ordering work; their observed numeric returns are not automatically
independent oblivious arm sequences. This is not a request to build another
chooser or isolate TT in a new framework.

Cold queries do not make all such ideas invalid, but repeated work must be paid.
The 2016 experiments themselves do not warm-start the outer doubling runs.
One cannot call a new cold query's full cost merely the incremental difference
from the preceding allowance. Nor may nominal depth be substituted for time
when branching and Q/terminal work differ.

The learner adapter's progress callback records completed depth/nodes/time.
Its explicit full Session PV replay occurs after the search returns; it does
not independently rerun that replay at every progress callback. Search itself
still does full-PV/TT work as needed. Therefore the source's saving from fewer
expensive validation observations cannot be announced as a new saving here.
No new observer, timing run, PV reader or product change follows.

Current decision: nonstochastic fidelity remains a legitimate conceptual
alternative to the stochastic mean models in
[AUX_GOOD_ARM_WALL_BUDGET_20261031](AUX_GOOD_ARM_WALL_BUDGET_20261031.md).
Neither is a drop-in guarantee for the existing learner. A future concrete
allocation trial should declare whether it targets finite-depth estimates,
behavioral terminal returns or minimax action value, and pay actual service.
The current Pro quality direction and all closed panels/caps remain intact.
