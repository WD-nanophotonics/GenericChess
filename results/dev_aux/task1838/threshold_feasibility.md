# Begun next step: bounded threshold-search feasibility

Question: can proof visits fall enough to help the fixed cheap phase, rather
than only making the same >1024visit proof faster? No new game/label or solver
implementation is claimed here. Current batch and Session PN remain unchanged.

Concrete representation obstacle derived from current source:

* Current depth-unknown closed leaves carry(pn,dn)=(infinity,infinity).
* An OR parent with one such blocked child and another open child(1,1) has
  pn=1,dn=infinity and can still have an executable winning strategy through
  the open child. Current PN explicitly tracks open flags independently.
* A proposed threshold loop requiring BOTH pn<phi AND dn<delta, with infinite
  root thresholds, stops immediately on that parent, because infinity<infinity
  is false. It must return UNKNOWN, not infer no-win. Copying that loop into
  the current depth-cutoff representation can therefore lose useful work.
* Similarly clamped infinity sums cannot safely be subtracted to derive a
  child threshold: infinity-infinity is undefined. Full sibling sums/explicit
  blocked state must be accounted for; an actual certificate verifier alone
  prevents false WIN but cannot detect every progress/coverage loss.

This is a scalar/loop counterexample, not a claimed board WDL counterexample
or a reproduction of an external algorithm. Next immediate experiment should
first use the already complete16actual maxply4 games, where reaching the TRUE
rule horizon produces real draws and no artificial depth cutoff is needed.
Freeze node/time limits and compare visited work/certificates against the
32existing target labels. A new finite-domain prototype may return UNKNOWN
on exhaustion; it must never turn unresolved into draw/no-win. Only extend
scope to played maxply96/endpoints after the progress/unknown contract is clear.

Keep current learner/opponent/phase budgets unchanged. No new price cohort,
human fitting, source-history merge or oldcap continuation follows this note.
