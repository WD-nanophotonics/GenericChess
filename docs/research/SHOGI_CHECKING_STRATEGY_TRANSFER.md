# Checking-strategy positive transfer and the claim boundary

Independent local follow-through after sending the mate-goal consultation:
Standard Shogi's two compiled declarations require_not_in_check=True. The
core assessor makes a checked actor's claim LOSS, and available_declarations
omits LOSS. Thus if every attacker move in a replayed strategy actually checks
the local defender, no defender nyugyoku WIN/RESTART choice exists at those
nodes. The wider literal-mate wrapper's unknown-claim rule does not weaken
that particular positive checking strategy through an extra declaration.
This is conditional on LOCAL check status, not the source move name or a
foreign move picker saying it is a check. Both-owner existing checked claim
fixtures independently confirm no available declarations, no transitions.

At attacker OR nodes additional legal quiet moves or a claim do not invalidate
a proved legal checking branch: the attacker may choose it. At defender AND
nodes however source evasions must cover all local legal evasions, including
counterchecks, underpromotions, captures/drops and pawn-drop-mate legality.
Both royal safety and full history are required; perpetual-check/repetition,
no-contest/max-ply and compressed source leaves must be replayed rather than
reinterpreted. A checked root on the attacker turn still needs one legal
checking evasion; foreign shortcut failure does not prove none exists.

Under finite, locally legal, all-defense replay ending in attacker checkmate
on every branch, positive tsume transfers to a local win and a mate-distance
upper bound. No shortest-DTM claim follows. The local win includes all extra
attacker options without needing them. Source nonmate never transfers in the
reverse direction: local wins may require a quiet move, declaration, differing
goal/history or a strategy the restricted source omitted. A root where a
defender declaration is legal and the attack is not checking is outside this
simple transfer premise, not a reason to silently remove the claim.

Keep unrestricted Session WDL, literal full-choice checkmate, and foreign tsume
as separately named goals. No external engine/source label or new mate root
was acquired; this closes one concrete positive-transfer objection, not all
operational source conversion obligations. Await any advisor objections while
continuing independently, without duplicate send or compulsory acknowledgement.
