# A shared actual-actor population supplies compatible means

The prehashed ACTUAL_ACTOR_POPULATION_PROTOCOL.md runs five abstract finite
contexts using exact rational arithmetic. It changes no game state, sampler,
engine profile or human-reference access. Inputs are declared binary task
flags, not certified Chess/Shogi exchange results. The executable certificate
and hashes are in data/actual_actor_population_20261004.json.

## Fixed inventory: a constructive bridge

Let Q be a declared law over unchanged contexts, and let I_t(c) be their actual
eligible own actors of current type t. Write S_t(c)=sum_{i in I_t(c)} X_i(c),
N_t(c)=|I_t(c)|, and Y(c)=sum_t S_t(c). X is the complete declared binary
task, including its legality and terminal conventions. No piece-removal map,
counterfactual replacement or event-independence assumption is needed.

If N_t(c)=n_t>0 throughout Q, draw c~Q then an actor uniformly from I_t(c).
Its mean is v_t=E_Q S_t/n_t. Consequently E_Q Y=sum_t n_t v_t. This constructs
compatible type means under one inventory and joint law. It does not establish
that the older single-focal replacement means equal these new means, nor does
it require every source-conditioned background to have the same distribution.

For an actual actor at source s, let
q_t(s)=E_Q[number of t actors at s]/n_t. Conditional task means x_t(s) give
v_t=sum_s q_t(s)x_t(s). Both weights and conditional contexts come from Q.
Uniform supported-source weighting is equivalent only with a separate symmetry
or equality argument. Type exchangeability is unnecessary for this counting
identity: the uniform marked actor explicitly averages distinguishable actors.

In the three frozen contexts, both types have v=2/3. Their successful source
has mass 2/3 and unsuccessful source mass 1/3. Uniform averaging over the two
supported sources gives 1/2 instead. The total capability mean is 4/3 under
the actual joint law. This is an exact measure diagnostic, not a new empirical
relative type ranking or a rejection of a separately declared uniform-source
prototype model.

## Changing inventory: sampling order and prediction differ

When counts vary, pooling Q-weighted successes and counts gives
v_t=E_Q S_t/E_Q N_t (when the denominator is positive). It still reconstructs
the unconditional mean: sum_t E_Q N_t*v_t=E_Q Y. This corresponds to weighting
contexts for type t in proportion to N_t(c), then choosing a t actor uniformly.

Drawing c~Q, choosing one of ALL actors uniformly, and conditioning on its type
instead gives v'_t=E_Q[S_t/N_all]/E_Q[N_t/N_all]. These are different estimands
when total inventory varies. The two predeclared regimes give:

| Quantity | A | B |
| --- | ---: | ---: |
| Mean count | 3/2 | 1 |
| Pooled actor mean v | 1/3 | 1/2 |
| Context-then-all-actors mean v' | 3/7 | 2/5 |

E_Q Y=1. The pooled means reconstruct 1; substituting v' reconstructs 73/70.
No sample size or importance weight was fitted after this comparison.

The pooled static predictor h(c)=sum_t N_t(c)v_t is not an automatic
conditional predictor. The two contexts both have Y=1, whereas h=5/6 and 7/6;
their exact squared error is 1/36. The fixed-inventory example also has
squared error 2/9 despite exact mean reconstruction. These are descriptive
errors on the frozen abstract laws; no empirical acceptance threshold follows.

For deployment, E[Y|N=n]=sum_t n_t m_t(n), where
m_t(n)=E[S_t|N=n]/n_t for present types. A static vector needs approximate
stability of these conditional means, or direct predictive validation under a
declared deployment law. Agreement of one unconditional mean cannot establish
this. Nonzero error does not by itself reject an approximation.

## Decision and next operational use

Adopt actual-actor marking as a possible replacement-free *construction*, not
as a repair already applied to the frozen sampler. Defer game-population
selection, computable conditional sampling and material utility. The existing
single-focal prototype remains unchanged and retains its transfer limitation.

A concrete narrow validation target is Y, the count of actors capable of the
declared resistant exchange. A candidate trained from a disjoint reference
law can be frozen and assessed by L=E_deploy[(Y-sum_t N_t v_t)^2]. This is a
capability-count prediction loss; it must never be reported as terminal
decision regret, net custody prediction or human material-value validation.
Do not optimize v against the validation labels. Before measuring it, specify
the reference and deployment laws, inventory variation, complete task coverage,
baseline and an independently chosen acceptance margin. Fixed-count validation
alone tests a constant predictor and cannot establish inventory transfer.

The subsequent ACTUAL_ACTOR_ENUMERATION_RESULTS.md checks whether a complete,
unchanged-inventory Chess/Shogi
reference can mark every actual ordinary actor with valid source accounting
without type substitutions or common screens over counterfactual types. Its
point-mass feasibility pass does not select a population; no coefficient batch follows
merely from this finite identity. Promoted types and hand actors need an explicit
extension, because source identity and available deployment actions differ.
Xiangqi human values remain sealed. Five focused tests pass, including rejection
of malformed/duplicate actors, incomplete zero-mass evidence and unsupported
type normalization. This is not completion of the static-prior objective.
