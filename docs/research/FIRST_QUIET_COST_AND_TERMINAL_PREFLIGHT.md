# First-quiet continuation: cost and automatic-terminal preflight

This is a new source/structural analysis after root admission failed, not a
rerun, increased cap or replacement root. No outcome queries or Core events.

For the five-piece K/R versus K/N/B population, suppose an admitted root has
three actions, exactly two captures and one quiet. After one capture, the
enemy has only one ordinary piece plus King: at most21 total legal moves
(8 King plus13 Bishop; Knight has at most8). At most two enemy actors can
capture the sole Rook. After Rook capture, owner0 has only King, at most8
choices and at most one capture of the remaining enemy ordinary piece.
After that capture only Kings remain: at most8 quiet choices. Thus a complete
unmerged first-quiet forest has at most

    3 + 2*21 + 2*2*8 + 2*2*1*8 = 109 public transitions.

Actual terminals can only shorten this bound. It applies ONLY to the stated
two-capture root; if three root captures are possible, the analogous upper
bound162 does not fit128. It is a conditional worst-case cost bound, not an
observed pilot cost or permission to change the failed admission rule. Lists
and membership checks still need their separate5000 cap. Continuing captures
strictly reduce ordinary count, so maximal depth is three captures plus one
quiet action. A pure bound cannot establish independent state/goal semantics.

The smaller stock also creates an automatic-adjudication issue. The pinned
python-chess1.11.2 source Board.outcome checks insufficient material even with
claim_draw=False, before ordinary stalemate. Its material predicate recognizes
K versus K+B or K+N as insufficient. After Rook recapture such a draw may
precede the declared next quiet action. This statement comes from reading
the pinned author implementation, not executing that unadmitted tree.

The local Western rules declare repetition_limit100000,max_ply1000 and
stalemate draw. The shared TerminalStatus/terminal paths have no matching
insufficient-material outcome. The already qualified seven-piece90-transition
census explicitly matched all actual author automatic statuses; this NEW
stock cannot inherit that qualification simply because it is shallower.

Before another trial, choose the target explicitly: SESSION exchange proxy
may keep its own declared terminal contract, but must report the independent
author automatic draw separately and cannot claim full ordinary-Western goal
equivalence. An author-adjudicated task must STOP at its true draw and retain
a distinct terminal category, not continue for a favorable inventory vector.
Mixed terminal/material outcomes cannot use the unweighted set certificate
without an additional declared comparison rule. Merely suppressing author
draws or using claim_draw=False is not a solution. Do not modify production
adjudication for this pilot without a separate rules specification and tests.

One possible prospective population includes a surviving Pawn to avoid the
single-minor stock collapse; that changes stock, action support and cost.
It must be newly frozen and preflighted, not assumed to fit the109 bound.
No promotion, EP/history or physical-origin omissions are allowed. This is
a reserve question, not a task launch or an admitted source-goal adapter.

Source locations inspected: generic_chess/rules/western_chess.py:265,
generic_chess/core/terminal.py:26 and terminal_result paths;
pinned author chess/__init__.py:2041,2073,2110,2117.
