# Shogi ordinary board direct masses and qualification

The original metadata adapter rejected its first Pawn quiet pattern because
it expected `empty` instead of IR's `target_empty`. It admitted zero modes;
retain the failed report. A separately frozen predicate-vocabulary correction
qualified110 board patterns over11 current modes in0.125sec. No guard was
removed: no guards, slot/zone conditions or postconditions; quiet move and enemy
capture-to-hand effects; inherited promotion masks; ray path-clear, leap direct
geometry; own_anchor_safe remains the explicit virtual-task omission. Drops
and declarations were excluded, not simplified into board moves. This was
metadata qualification, with zero geometry candidates, event materializations,
public transitions or goal calls.

Under the SAME uniform511920 distinct(s,d,b) worlds:

| Current mode | Exact direct | Proved motionless zero | Unknown distance>=2 |
| --- | ---: | ---: | ---: |
| P |5688|62568|443664|
| L |24840|62568|424512|
| N |8848|114866|388206|
| S |25912|158|485850|
| G/TP/TL/TN/TS (each) |32864|0|479056|
| TB |85872|0|426048|
| TR |119584|0|392336|

Leap counts are displacement products times79. L forward rays give
324*79-756=24840; TB adds288*79 orthogonal-neighbor worlds to63120 diagonal
ray worlds; TR adds256*79 diagonal-neighbor worlds to99360 orthogonal ray
worlds. The additional directions are disjoint from the ray displacement sets.
Alternative promotion descriptions on an absorbing capture are counted once.

Motionless P/L sources comprise9 dead-rank squares with80*79 target/blocker
worlds each, plus72 sources whose only forward adjacent square is the blocker,
with79 remaining target squares. N has18 dead-rank squares and14 single-jump
edge sources trapped by their blocker. S has two far-rank corners blocked at
the only backward-diagonal exit;158 worlds. G and current promoted minor
modes have at least two exits, and TB/TR at least three, so one blocker cannot
make them motionless. These are exact motionless populations, NOT a complete
classification of all unreachable targets. Promotion cannot rescue a source
with no move, but it can rescue longer native B/S/P routes; keep the unknowns.

Dead-rank native sources are deliberately within the declared uniform virtual
law, even where an official prior move would have forced promotion. Do not
silently condition source support on opening reachability for one mode. A
reachable-state law is a different hypothesis, to be independently declared.

For either existing duration law with moments m1,m2, each raw coefficient is
in[direct*m1/511920,(direct*m1+unknown*m2)/511920]. Positive board lower bounds
are now available for these missing modes, but broad upper bounds overlap.
No Shogi maximum normalization, complete material vector, held-mode values or
strategic transfer is established. Origin/current identities remain distinct;
the equal G/promoted-minor direct geometry does not make native P/L/N/S equal.

Fifteen test cases independently census source/blocker coordinates for both
owners and check metadata pins, promoted-mode distinctions and partial bounds.
They do not rerun the completed metadata producers or query game outcomes.
The extra promotion-mask control checks every inherited allowed pair has a
live promoted result, and every forced target is dead in its native mode.
Thus direct capture is not silently removed by an empty mandatory-promotion
choice; correctly marked promoted current modes do not re-promote.
