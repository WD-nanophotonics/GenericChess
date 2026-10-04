# Public-information task arithmetic qualification

2026-10-04. public_task_intervals.py and five independent finite-world tests
qualify only the controlled proposal's arithmetic, not actual game inference.
No task tree, material vector, game sample, source probe or optimization fit.

Two equally likely hidden worlds permit public action A to succeed only when
the tag is on board, B only when it is held. A public policy's best expectation
is1/2; optimizing separately in each unobservable world falsely returns1.
The opponent's public minimum is also1/2 here, whereas clairvoyant per-world
min gives0. Integrate each public action's joint-world payoff before backup.

Capture-completed and source-alive events can be negatively correlated. Worlds
(completed,dead) and(not-completed,alive), each mass1/2, have joint payoff0
but product of marginals1/4. A completed-mass subdistribution, not a single
global completion scalar times alive tag mass, is needed after ambiguous drops.
This directly applies to physical q/n tagging; it cannot be replaced by an
uncorrelated survival rate. Full multi-tag/event tracing remains to implement.

Unknown world payoffs are explicit[0,1] with their original weights; missing
world keys or probability mass fail closed. At incomplete max nodes upper
stays1; at incomplete min nodes lower stays0. Exhaustive independent corner
completion tests verify these bounds. Known value1/max or0/min can prove a
VALUE by range dominance even with unexplored choices. This does not certify
a full canonical material-selector tie; those operators keep their full-table
requirement. The helper returns no selected action and authenticates no game.

Adding optional unchanged own actions leaves max value nondecreasing, while
adding opponent choices leaves min nonincreasing. Uniform average can instead
fall1->1/2 after adding a zero-payoff own action. Neither statement extends
to changed opponent legality or modified original continuations/checks.

Next actual qualification: a held resource's drop-then-capture task, with full
adversarial replies and physical custody. Positive conditional means from the
spent Shogi quiet-reply controls do not establish this control value. Use a
predeclared certificate strategy/counterstrategy rather than another all-type
random-service batch.
