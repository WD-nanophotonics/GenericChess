# Prospective single-source Pawn auxiliary qualification

Question: can the full Western Pawn grammar retain its initial double step
without making en passant reachable in the declared passive contact task?
This is a changed task variant, not a correction to frozen old Pawn coefficients.

Before observations: compile the unchanged Western builder. Inspect all Pawn
patterns and auxiliary lifetimes. Two owner-reflected virtual paths use own K a1,
enemy K h8, own P d2, passive enemy N e8, with all rights zero and EP None.
Prescribed path d2-d4-d5-d6-d7xe8=Q. Reset only side-to-move to the source owner
between actual position-level applications. Preserve aux state and origin.
Enumerate the full legal action set before each application, including King
actions, and retain all patterns; select exactly the prescribed source action.
Check intermediate EP=d3 after the double step and None after the next action;
no available source EP action at any prefix. Reflect ranks/owners for owner1.
No alternating history, official goal label, coefficient population or utility
claim. Kings guard these paths; omitted full stock and active opponent remain
explicit. At most128 materializations,5000 enumerated actions,128 choices per
position,15sec cooperative cumulative computation. Never rerun producer.

Analytic scope: initial EP None; source is the only mover, starts native P or a
Pawn-origin promoted ordinary mode; same owner restored after each action.
While native P it strictly advances one/two ranks. A double occurs only at
relative rank1 and leaves EP at relative rank2, behind its rank3 landing.
The next EP geometry requires relative rank4. Every next transition expires
the old token before effects; no return to rank1 is possible. Promotion removes
the P actor binding. Thus EP can be omitted in this task only, while the double
step itself cannot be silently removed. A foreign nonempty initial token, an
opponent action or another source invalidates this reduction premise.
