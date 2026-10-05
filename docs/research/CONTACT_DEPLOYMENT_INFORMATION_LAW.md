# Contact preparation: information and deployment conventions

2026-10-05. New construction hypothesis after the optimized held B/R result;
no coefficient fit or new goal labels. The question is what quantity a held
prototype measures when placement is optimized, randomized or prior to demand.
These conventions are separate hypotheses, not interchangeable interpretations.

## The fixed-world legality problem

The existing task discloses the stationary target d and own blocker b before
planning. E[max_strategy gamma^tau] is legitimate for THAT public task. It
measures preparation capability with favorable placement choice, not a covert
hidden-target policy. Its near-equal held B/R values are now compiled-qualified.

If only b is observed and d may occupy any other square, no board square is a
drop destination legal in EVERY possible world: each q!=b is occupied by d in
one possible world. Blindly replacing E[max] with max[E] over those same drop
actions therefore does not define a legal policy. Revealing the legal drop set
reveals occupancy information; an attempted occupied drop needs a separately
specified failure/sensing/cost model. Sampling d AFTER placement changes the
world-generation task. None of these changes follows from withholding a label.

LaValle's [information-state game formulation](https://lavalle.pl/planning/node586.html)
explicitly makes policies functions of information states and assumes the
inferred action set agrees across their decision vertices. The failed common
drop intersection above is our application to this synthetic task, not a
claim from the textbook about Shogi. No perfect-information goal is changed.

## A declared randomized deployment alternative

HYPOTHESIS, not measured deployment frequency: keep the same uniform distinct
(s,d,b) law; a held source has an empty nominal marker s. After public d/b
disclosure, take ONE uniformly random qualified empty drop q, then choose a
shortest compatible board continuation. Pay the drop cost once. No optimization
over q; continuation does know q/d/b. This law is independently motivated as
an occupancy-balanced placement prototype, not human play or a rule-unique prior.

For native B/R, every square is mask-enabled and no intrinsic state guard is
excluded. There are79 available q, INCLUDING s. Integrating the irrelevant
marker s leaves d/b uniform on81*80 pairs. Each ordered distinct(q,d,b) then
has mass1/(81*80*79), precisely the same law as board(s,d,b). Hence

    w_random_hand,m(gamma)=gamma*w_board,m(gamma),  m=B,R.

This is equality of population means, not worldwise equality at q=s and not
an optimized controlled policy. It retains every failed/unreachable target.
The new B censored interval simply multiplies both endpoints by gamma; the
R mean becomes its same polynomial times gamma. Thus R>B survives this task
without fitted hand premiums, while hand<board for each positive component.
That direction is a falsifiable modeling consequence, not a desired chess price.
It may be a poor real-game prior because favorable strategic drops are ignored.

## Restricted masks cannot reuse the identity silently

For N squares and allowed mask M of size m>=3, after public distinct d/b:

    P_A(q,d,b)=1/[N*(N-1)*(m-k)], q in M minus{d,b},
    k=1[d in M]+1[b in M].

Compare a different source-first reference P_B: sample q uniformly from M,
then d/b uniformly distinct outside q. Its mass is1/[m*(N-1)*(N-2)].
The likelihood ratio is m*(N-2)/[N*(m-k)]. The reference CHANGES the demand
marginal when m<N; zero-mask/favorable-world filtering is not a repair.
If m<=2 some worlds have no drop; preserve their no-action mass or define an
explicit failure reward. Never renormalize them out. Even m>=3 does not remove
Pawn nifu/postconditions, dynamic safety or full-inventory restrictions.

For N/2<=m<N, exact total variation of these JOINT triple laws is

    TV(P_A,P_B)=2*(m-1)*(N-m)/[N*(N-1)*(N-2)].

Proof: only k=2 has positive P_A-P_B after marginalizing q; there are m*(m-1)
ordered d/b pairs in that class. Sum their mass excess. At m=N the laws coincide.
For any fixed compatible contact function0<=f<=gamma, the board-mean difference
is <=gamma*TV; charging the drop gives <=gamma^2*TV. This bounds ONLY changing
these mask sampling laws, not dropping safety/state guards or changing type.
For N81,m72 the TV is1278/511920; m63 gives2232/511920. These sizes correspond
to familiar compiled dead-square masks, but the identity is pure measure math,
not qualified Pawn/Lance/Knight held values or an intrinsic1/n rule.

Independent small finite-world controls verify full mass, unrestricted marginal
identity, restricted-mask bias and exact TV. No all-mode geometry batch, engine
transition or holdout is run. Next freeze a use question BEFORE observing it,
and retain uncertainty/assumption sensitivity; do not pick a convention from
desired R/B ordering or baseline outcomes. General-game masks/effects and mode
coverage remain qualifications to solve, not reasons to halt construction.
