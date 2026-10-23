from dataclasses import replace
from scripts import leaper_design as L
from scripts.leaper_e0_panel import rule
from scripts.leaper_single_entity_scope import definition,admit_rule,admit_position,position
from scripts.leaper_parity_scope import orthogonally_independent
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.pieces import PieceType
from generic_chess.core.position import Hands
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalStatus

def test_per_current_type_not_union():
    r=definition();assert admit_rule(r)[0]
    assert not orthogonally_independent(set(L.offsets(1))|set(L.offsets(2)))
    c=L.compile_rule(r)
    for spec in [(0,15,0,0,1,'A'),(0,15,0,0,1,'P'),(0,15,0,1,None,'A')]:assert admit_position(position(c,spec),r)[0]

def test_mixed_future_type_is_a_real_mating_counterexample():
    r=definition();p=replace(r.piece_types[2],movement_atoms=tuple(LeapAtom(z) for z in L.offsets(5)))
    r=replace(r,piece_types=(*r.piece_types[:2],p));assert admit_rule(r)==(False,'adjacent_attack_targets_P')
    b=[None]*16
    for i,owner,t in ((6,0,'K'),(9,0,'A'),(0,1,'K')):b[i]=L.Piece(owner,t,t)
    r=replace(r,initial_position=tuple(tuple(b[4*j:4*j+4]) for j in range(4)));c=L.compile_rule(r);ss=L.GameSession(c)
    winners=[]
    for action,ch in L.legal_successors(ss.state,c):
        if ch.terminal_status.winner==0:winners.append((action,ch))
    assert any(a.promotion_target_id=='P' for a,ch in winners)

def test_entity_cap_is_required_even_for_single_parity_type():
    r=definition();c=L.compile_rule(r);b=[None]*16
    for i,owner,t in ((6,0,'K'),(4,0,'A'),(5,0,'A'),(0,1,'K')):b[i]=L.Piece(owner,t,t)
    pos=replace(c.initial_position,board=tuple(b),side_to_move=1)
    assert admit_position(pos,r)==(False,'more_than_one_physical_ordinary')
    e=semantic_engine_for(c);key=repetition_identity_key(pos,c)
    t=e.terminal_result(pos,0,((key,1),),(HistoryRecord(key,-1,'',False),))
    assert t.status is TerminalStatus.CHECKMATE and t.winner==0

def test_unsupported_semantic_goals_and_rays_fail_closed():
    r=definition()
    assert not admit_rule(replace(r,repetition_policy='continuous_check_loss'))[0]
    assert not admit_rule(replace(r,stalemate_result='loss'))[0]
    a=replace(r.piece_types[1],movement_atoms=(RayAtom((1,0)),))
    assert admit_rule(replace(r,piece_types=(r.piece_types[0],a,r.piece_types[2])))==(False,'non_fixed_Leap_A')
    no_clock=replace(r,max_ply=0);assert not admit_rule(no_clock)[0]
