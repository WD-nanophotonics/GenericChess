# H=2 depletion bound with custody and drops

2026-10-04. A construction/precision boundary derived from the actual standard
capture/drop effects, not a new sampled coefficient or general long-horizon
claim. It refines dot's warning that custody can invalidate depletion bounds.

Let E be the physical enemy ordinary tokens initially on board OR in enemy
hand; M=|E|. Count rewards over the tagged owner's first action, enemy reply,
and tagged owner's second action. Stop at an authoritative endpoint. Standard
Chess/Shogi actions each remove at most one enemy ordinary token; a Shogi drop
and capture are separate actions, never a compound capture-and-drop.

Every token eligible for removal on the first own action belongs to E. Every
token eligible on the second own action also belongs to E:

* The enemy reply can move an existing board token, or drop an E token from
  its original hand. Promotion changes type, not physical identity.
* A token newly taken from our side by the enemy reply enters enemy HAND. It
  cannot also be dropped in that same reply, hence is not on the board when
  the second own action removes its victim. In Chess it instead leaves play.
* A token removed on the first own action leaves play or joins our hand. The
  enemy cannot remove it from our hand in its reply and cannot return it to
  its own board before the second own action. It cannot be rewarded twice.

Therefore actual tagged H2 service is between0 and min(2,M), even in Shogi.
The bound concerns these three action plies; it does not assume custody never
changes. Absorbing tag loss and early endpoints only reduce service.
Anchor captures are terminal goals, not ordinary removal service.

There is a stronger first-branch bound. Let C_a be the number of ordinary
enemy tokens removed by the FIRST OWN ACTION, including removal by a different
friendly actor. Then future tagged reward is at most min(1,M-C_a). When M=1
and another friendly piece takes that victim, future tagged service is exactly0
even though its first reward is0 and its tag survives. For a held tag, combine
with the already qualified drop/anonymous-label factor: a non-drop branch is0;
a same-base drop branch is bounded by min(1,M-C_a)/n. No refreshed victim may
be introduced, and no original branch probability is changed.

This can eliminate entire future subtrees from deterministic direct-service
intervals without paying for a child/reply probe. It is conditional on the
single-removal, separate-drop physical scope and actual M/C_a, not metadata
claiming a generic game obeys it. Existing binding/child reward controls qualify
the standard scope; unsupported compound effects remain unknown.

Why not H>=3? With M=0 an enemy King can capture another friendly ordinary
piece into its hand on reply1; on reply2 it can drop that newly acquired token;
our tagged piece can remove it on own action3. Thus no initial-enemy-pool bound
follows at longer horizons. Return of previously rewarded physical tokens also
requires more plies. We neither admit H3 nor run a new long-horizon experiment.

For finite-law design, one initial enemy ordinary token can supply at most one
actual H2 removal, so a regenerated g+Pg value above1 is a replenishment model,
not physical lifetime evidence. Two initial enemy tokens avoid that particular
forced ceiling but do not prove closure or strategic usefulness. Preserve both
the removal numerator and complete-choice denominator; a larger tag mobility
can dilute a uniform-side capture probability. This is the next concrete cheap
branch-pruning premise, not a replacement price or a new prior admission.
