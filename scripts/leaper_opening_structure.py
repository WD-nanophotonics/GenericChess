"""Structural one-ply opening liveness witness for a NARROW pure-Leaper subset.

Research-only, not a search pruning or legal-move provider. Requires exact
ordinary Leap IR, K's eight neighboring steps, one K per side, distant kings,
homogeneous checkerboard parity for every nonanchor movement type, and one
empty unattacked king escape cell of EACH color. After a single enemy nonking
move only one target color can be newly attacked, and cannot occupy an initially unattacked escape: ordinary quiet and capture
geometry coincide. A distant enemy K cannot affect
any escape cell. Hence at least one empty legal K reply survives. Clocks/history
and adjudications must also be admitted; no WDL or multi-ply claim follows.
"""
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord

def structural_opening_witness(state,compiled):
    c=compiled;table=ordinary_leap_geometry(c)
    def unknown(reason):return {'status':'UNKNOWN','reason':reason}
    if table is None:return unknown('ordinary movement contract not established')
    pos=state.position;shape=pos.board_shape
    if state.ply_count!=0 or state.terminal_status.is_terminal:return unknown('fresh ongoing initial clock required')
    # Only this initial record domain, not an arbitrary imported history.
    key=repetition_identity_key(pos,c)
    if pos!=c.initial_position or state.repetition_counts!=((key,1),) or state.history!=(HistoryRecord(key,-1,'',False),):return unknown('exact own initial position/history required')
    if c.max_ply<2 or c.support.max_ply<2 or c.repetition_limit<2 or c.support.repetition_limit<2:return unknown('one-ply clock/repetition terminal not excluded')
    if pos.aux_state or any(h.counts for h in pos.hands):return unknown('no aux/hands domain only')
    # Footprint guard excludes IR adjudications; retained support must agree too.
    if any(getattr(c.support,k,()) for k in ('automatic_adjudications','consecutive_action_adjudications','repeated_cycle_target_conditions','declarations')):return unknown('support adjudication outside domain')
    kings=[[],[]];kingsteps={(x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)}
    for t in c.piece_types:
        offsets={tuple(a.offset) for a in t.movement_atoms}
        if t.is_anchor:
            if offsets!=kingsteps:return unknown('anchor must have exactly neighboring K geometry')
        elif len({(x+y)&1 for x,y in offsets})!=1:return unknown('nonanchor movement mixes target parity')
    for i,p in enumerate(pos.board):
        if p is not None and c.types_by_id[p.current_type_id].is_anchor:kings[p.owner].append(i)
    if any(len(k)!=1 for k in kings):return unknown('exactly one anchor each')
    x0,y0=kings[0][0]%shape.width,kings[0][0]//shape.width;x1,y1=kings[1][0]%shape.width,kings[1][0]//shape.width
    if max(abs(x0-x1),abs(y0-y1))<4:return unknown('king separation below four')
    mover=pos.side_to_move;defender=1-mover;k=kings[defender][0];kt=pos.board[k].current_type_id;attacked=set()
    for i,p in enumerate(pos.board):
        if p is not None and p.owner==mover:attacked.update(table.get((mover,p.current_type_id,i),()))
    escapes=[i for i in table.get((defender,kt,k),()) if pos.board[i] is None and i not in attacked];color={v:sorted(i for i in escapes if ((i%shape.width+i//shape.width)&1)==v) for v in (0,1)}
    if any(not color[v] for v in color):return unknown('need one empty unattacked king neighbor of each color')
    return {'status':'SUFFICIENT_ONE_PLY_REPLY','defender':defender,'escape_colors':{str(v):color[v][:1] for v in color},'scope':'conditional fresh ordinary parity-homogeneous Leap subset only;no game WDL/strength or claim about rejected roots'}
