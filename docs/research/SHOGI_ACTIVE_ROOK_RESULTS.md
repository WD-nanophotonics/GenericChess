# Active R reply separates path safety from task survival

The new prospectively stocked root's two actual alternating public events pass:
P@e2, Rxe2. Full actions retained (139 explicit entries across two lists, each
<=128);2 public transitions,0 goal queries,0.141sec. Both actual movers are
royally safe after their move, global stock40 conserved, full ply2/history3
preserved with no side reset. Own n=1 physical Pawn is gone; enemy held P16
becomes P17. Own King is checked again. Three saved replay tests pass.

The stock allocation was prospectively changed to keep full public lists small:
missing non-P pieces are in own hand,16 missing P in enemy hand. Those extra
own actions remain listed; they are not cut away. This is an explicitly new
root, not an alternating continuation of a frozen earlier GameState. Earlier
royal source-path qualification restored own turns virtually and had no replies.

## Analytic complete-family implication

In SHOGI_ROYAL_CONTEXT_LAW_PROTOCOL.md's72-frame law, every allowed P drop
at (f,j), r<j<8, leaves an unobstructed R line from (f,8) to that P. R can
capture it immediately. The far enemy King was safe before and remains safe:
the source P, off-file background P and fixed own King do not attack it; removing
the interposing P cannot uncover any own sliding attacker. Pawn-drop-mate is
irrelevant to this ordinary R capture. Being attacked by the own King after
R's capture, when j=r+1, does not make a NONROYAL R move illegal.
This proof applies with the original background hand allocation too; holding
other unused pieces changes alternatives, not this R move's King-safety guard.

Define the active version of the SAME source task to absorb failure when the
designated P loses own custody before removing the designated R. Other own
actors still cannot substitute for the source. Opponent can use the just-given
reply for every admitted first drop, so optimized source-task value is0 in all
72 frames, under both declared deadlines. Empty-drop r7 frames already fail.
This complete-family counterstrategy is analytic; only the named new stocked
root's two events were empirically executed. Own King may later capture R;
that does not undo source-task failure. No claim about whole-game WDL follows.

The passive legal-resampling means3193/26880 and2761/30240 can thus lose ALL
their value under one coherent adversarial reply model. Initial legal filtering
or routewise King safety alone gives no positive dynamic-survival lower bound.
The difference is active-opponent task modeling, not a flaw in the declared
passive-contact arithmetic. It does not justify an arbitrary discount penalty,
new fitted survival factor, or a population error estimate for natural games.

## Next construction decision

Retain cheap passive contact as an explicitly approximate movement/preparation
prior, not literal forced-contact game value. Before full prior admission,
independent deployment benefit must be shown, with source coverage and robust
tie choices. Adding unconditional adversarial play to all contexts is not a
cheap automatic repair: this complete checked stratum becomes all0, while
other supported contexts can behave differently. Do not rerun unchanged sparse
tasks or fit this counterexample away. Investigate an independently declared
deployment domain or a rule-neutral complete constructor and smallest falsifier.
