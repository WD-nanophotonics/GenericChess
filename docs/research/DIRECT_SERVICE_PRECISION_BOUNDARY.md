# Direct-service precision before any new samples

2026-10-04. Analytic feasibility, no new proposals/transitions or coefficient
estimates. H2 direct observation Y is in[0,2]. Multiple paths from ONE root do
not become independent draws of a proposed context population; distinguish
conditional path precision, independent context precision and population bias.

## Distribution-free sufficient bound

Our derivation: normalize Z=Y/2 in[0,1]. Under any exponential tilt, Var(Z)<=1/4
since E[Z^2]<=E[Z], hence variance<=mu(1-mu)<=1/4. The centred log moment-
generating function has value/first derivative0 at0 and second derivative at
most1/4, so log E exp(t(Z-EZ))<=t^2/8. For n independent observations multiply
the mgfs, use exponential Markov and optimize t=4epsilon, obtaining each tail
<=exp(-2n epsilon^2). Union across both tails and K modes gives simultaneous
raw-service halfwidth epsilon_raw=sqrt(2 log(2K/alpha)/n).
This is the bounded-variable concentration route associated with
[Hoeffding's original paper](https://www.cs.rpi.edu/academics/courses/spring06/random/hoefding.pdf);
the algebra/application above is our derivation, not a new empirical result.

Illustration only, NOT a frozen acceptance threshold: K=25 current components
(Chess5 board, Shogi13 board+7 hand), alpha=.05. With n=1,6,25 independent
contexts/component, raw halfwidths are3.717,1.517,0.743 respectively, intersected
with[0,2]. Sufficient n for raw precision0.5 is56/component; for0.1 it is1382.
These are sufficient worst-case counts, NOT necessary sample lower bounds or
an impossibility theorem. Variance-aware, structural or deterministic evidence
can be sharper if independently justified. No sample/compute budget increased.

Even optimistic uniform allocation of the existing128 proposals/game would
offer at most25 contexts for each Chess type or6 for each of20 Shogi components,
before structural rejection, complete-choice/transition/time costs. Thus tiny
direct pilots cannot honestly assert these simultaneous high-precision means
from a generic bounded-variable bound. The original six point-reference
diagnostic is an exact finite-law question, not an n-per-population claim.

Independent observations and a fixed target law are prerequisites. Do not
retain only cheap-to-complete paths/positive modes or silently censor hard
states and call the resulting mean the original law. Timer/choice failures
leave incompleteness. Reusing exposed contexts to choose a new law/policy or
counting successive seeds until positivity appears is not an uncertainty fix.

## Next decision

Direct expectation removes refreshed-mode bias but not context bias, action
competition or finite-cost precision. Before sampling, derive a decision-
changing precision target and evaluate rare-service/structural bounds without
exposed-goal fitting. Alternatively choose an independently motivated analytic
constructor/use question with smaller information requirements. A finite
representative law can be a declared approximation, but must face reserved
independent usefulness evidence; it is not a calibrated population mean.
This observation limits the next CLAIM, not permission to continue research.
