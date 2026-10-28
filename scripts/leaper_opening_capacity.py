"""General ordinary-Leap one-ply escape-capacity sufficient condition.

Let S be currently empty/unattacked defender-anchor destinations. For each
opponent actor i and each geometric first destination d, remove from S d and
all squares attacked by i when placed on d. If S remains nonempty for every
such move, a legal empty anchor reply exists after every ACTUAL first action.
Checking all geometric actions is an overapproximation: failing gives UNKNOWN,
not checkmate. Requires unchanged current type, no rays/effects/triggers/hands,
ordinary own-anchor-safe IR and exact fresh-history/clock context. No pruning,
new execution kernel, generic-domain WDL or strength claim is made.
"""
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord

def opening_escape_capacity(state,compiled):
    c=compiled;table=ordinary_leap_geometry(c)
    def unknown(reason,**extra):return {'status':'UNKNOWN','reason':reason,**extra}
    if table is None:return unknown('ordinary movement contract not established')
    pos=state.position
    if state.ply_count!=0 or state.terminal_status.is_terminal or pos!=c.initial_position:return unknown('fresh own ongoing initial position only')
    key=repetition_identity_key(pos,c)
    if state.repetition_counts!=((key,1),) or state.history!=(HistoryRecord(key,-1,'',False),):return unknown('complete initial history/counts mismatch')
    if min(c.max_ply,c.support.max_ply)<2 or min(c.repetition_limit,c.support.repetition_limit)<2:return unknown('one-ply clock/repetition terminal not excluded')
    if pos.aux_state or any(h.counts for h in pos.hands):return unknown('aux/hands outside domain')
    kings=[[],[]]
    for i,p in enumerate(pos.board):
        if p is not None and c.types_by_id[p.current_type_id].is_anchor:kings[p.owner].append(i)
    if any(len(x)!=1 for x in kings):return unknown('one anchor per side required')
    mover=pos.side_to_move;defender=1-mover;king=kings[defender][0];kt=pos.board[king].current_type_id;attacked=set()
    for i,p in enumerate(pos.board):
        if p is not None and p.owner==mover:attacked.update(table.get((mover,p.current_type_id,i),()))
    safe={j for j in table.get((defender,kt,king),()) if pos.board[j] is None and j not in attacked}
    if not safe:return unknown('no initial empty safe anchor destinations')
    witnesses=[]
    for i,p in enumerate(pos.board):
        if p is None or p.owner!=mover:continue
        for dst in sorted(table.get((mover,p.current_type_id,i),())):
            # Including own-occupied/king-unsafe geometric moves is intentionally
            # conservative. Actual legal first moves are a subset; no fake legal
            # action or full-state transition is produced by this analysis.
            # Under the admitted equality of quiet and capture geometry, every
            # candidate landing dst is already in the parent's attacked union;
            # it therefore cannot occupy a member of initially unattacked S.
            assert dst not in safe
            survivors=safe-set(table.get((mover,p.current_type_id,dst),()))
            if not survivors:return unknown('one geometric mover can cover/occupy every reserved escape',source=i,target=dst,actor=p.current_type_id,safe=sorted(safe))
            witnesses.append({'source':i,'target':dst,'defender_empty_escape':min(survivors)})
    if not witnesses:return unknown('no geometric first action;initial consistency unestablished')
    return {'status':'SUFFICIENT_ONE_PLY_REPLY','defender':defender,'initial_safe':sorted(safe),'witnesses':witnesses,'scope':'fresh ordinary all-Leap executable subset;geometric action overapprox;not fullgame/quality/holdout/pruning'}
