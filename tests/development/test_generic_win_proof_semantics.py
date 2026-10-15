"""Proofs exercise public rule semantics, not a hand-coded chess oracle."""
from dataclasses import replace
import pytest
from conftest import T,king_type,make_ruleset
from generic_chess import build_western_chess_ruleset,build_standard_shogi_ruleset
from generic_chess.core.actions import DropMove,BoardMove,PassAction,action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands,GameState,HistoryRecord
from generic_chess.core.terminal import TerminalStatus,terminal_result,TerminalResult
from generic_chess.core.transition import initial_state,apply_action
from generic_chess.rules.schema import RuleNoProgressDraw,RuleAutomaticAdjudication,RuleConsecutiveActionAdjudication
from generic_chess.rules.compiler import compile_ruleset,compile_ruleset_for_execution
from scripts.generic_win_proof import prove_win,verify_certificate,StrategyCursor,PROVEN_WIN,UNKNOWN
from scripts.generic_proof_fixtures import krk_ruleset,krk_state,compile_krk


def bind(c,pos):
    key=repetition_identity_key(pos,c)
    s=GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),))
    return replace(s,terminal_status=terminal_result(s,c))


def require(c,s,kind):
    r=prove_win(c,s,target=0,max_nodes=4096,seconds=2.,max_depth=3)
    assert r.status==PROVEN_WIN,r
    a=r.certificate.tree.edges[0][0]
    assert kind(a),a
    assert verify_certificate(c,s,r.certificate,seconds=2.)['verified']
    cur=StrategyCursor(c,r.certificate,seconds=2.)
    while cur.node.edges:cur.advance(cur.state,cur.node.edges[0][0])
    assert cur.state.terminal_status.winner==0
    return r,a


def test_rook_drop_mate_preserves_hand_semantics():
    rs=krk_ruleset(4);rs=replace(rs,drop_allowed={'R': ((True,)*16,)*2},capture_disposition='capture_to_hand')
    c=compile_ruleset(rs);s=krk_state(c,1,3,8,0)
    board=list(s.position.board);board[8]=None
    s=bind(c,replace(s.position,board=tuple(board),hands=(Hands((('R',1),)),Hands.empty())))
    r,a=require(c,s,lambda a:isinstance(a,DropMove))
    child=apply_action(s,a,c)
    assert child.position.hands[0].count('R')==0 and r.certificate.tree.rank==1


def test_forced_promotion_is_part_of_actual_winning_action():
    rook=T('R',*(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1))))
    pawn=T('P',LeapAtom((0,1)),is_promotable=True,targets=('R',))
    rs=make_ruleset(4,[king_type(),rook,pawn],lines=['...k','P...','..K.','....'],auto_promotion=True)
    c=compile_ruleset(rs);s=initial_state(c)
    r,a=require(c,s,lambda a:isinstance(a,BoardMove) and a.promotion_target_id=='R')
    child=apply_action(s,a,c)
    assert child.position.board[12].promoted
    assert child.position.board[12].base_type_id=='P' and child.position.board[12].current_type_id=='R'


def test_pass_is_defense_not_discarded_as_nonchecking_move():
    # One legal nonchecking pass immediately draws. Omitting it would falsely
    # certify the old no-pass forced mate against the sole board defense.
    rs=replace(krk_ruleset(4),consecutive_action_adjudications=(
        RuleConsecutiveActionAdjudication('pass',1,'DRAW'),))
    old=compile_krk();base=krk_state(old,1,7,8,1)
    cert=prove_win(old,base,target=0,max_nodes=4096,seconds=2.,max_depth=3).certificate
    assert cert is not None
    c=compile_ruleset(replace(rs,pass_enabled=True));s=krk_state(c,1,7,8,1)
    from generic_chess.core.search_runtime import SearchPathRuntime
    assert PassAction() in SearchPathRuntime.from_state(s,c).legal_actions()
    r=prove_win(c,s,target=0,max_nodes=4096,seconds=2.,max_depth=3)
    assert r.status==UNKNOWN and r.reason=='no_forced_win_in_exhausted_tree'
    forged=replace(cert,root=s,ruleset_fingerprint=c.ruleset_fingerprint)
    assert not verify_certificate(c,s,forged,seconds=2.)['verified']


def test_actual_stalemate_loss_goal_is_not_falsely_called_checkmate():
    # No legal move and not checked; the rule specifies side-to-move loss.
    c=compile_ruleset(replace(krk_ruleset(4),stalemate_result='loss'))
    s=krk_state(c,1,3,4,1)
    assert s.terminal_status.status==TerminalStatus.STALEMATE
    assert s.terminal_status.winner==0
    r=prove_win(c,s,target=0)
    assert r.status=='ALREADY_TERMINAL' and r.terminal_kind=='stalemate'


def test_no_progress_and_declarations_fail_closed():
    c=compile_ruleset(replace(krk_ruleset(4),no_progress_draw=RuleNoProgressDraw(10,True)))
    assert prove_win(c,initial_state(c)).reason=='unsupported_no_progress_history'
    c=compile_ruleset_for_execution(build_standard_shogi_ruleset())
    assert prove_win(c,initial_state(c)).reason=='unsupported_declarations'


def test_incomplete_adjudication_history_unknown_and_not_silently_reset():
    c=compile_ruleset(replace(krk_ruleset(4),automatic_adjudications=(RuleAutomaticAdjudication('opaque_threshold_0',4),)))
    s=replace(initial_state(c),ply_count=4)
    r=prove_win(c,s)
    assert r.status==UNKNOWN and r.reason=='incomplete_adjudication_history'


def test_semantic_chess_mate_proof_has_lossless_semantic_actions():
    from scripts.chess_development import root_from_fen
    c=compile_ruleset_for_execution(build_western_chess_ruleset())
    s=root_from_fen('7k/8/5KQ1/8/8/8/8/8 w - - 0 1',c)
    r,a=require(c,s,lambda a:action_to_dict(a)['kind']=='semantic_board')
    assert r.certificate.tree.rank==1


def test_root_terminal_maxply_and_repetition_are_rule_results_not_proof_cutoffs():
    c=compile_krk();s=krk_state(c,1,3,8,0)
    maxed=replace(s,ply_count=64)
    maxed=replace(maxed,terminal_status=terminal_result(maxed,c))
    r=prove_win(c,maxed)
    assert r.status=='ALREADY_TERMINAL' and r.terminal_kind=='max_ply' and r.winner is None
    key=s.repetition_counts[0][0]
    repeated=replace(s,repetition_counts=((key,3),),history=())
    repeated=replace(repeated,terminal_status=terminal_result(repeated,c))
    r=prove_win(c,repeated)
    assert r.status=='ALREADY_TERMINAL' and r.terminal_kind=='repetition'


def test_draw_terminal_cannot_be_vacuous_all_defense_win():
    from scripts.generic_win_proof import WinCertificate,ProofNode
    c=compile_ruleset(replace(krk_ruleset(4),max_ply=1))
    s=krk_state(c,0,15,10,0)
    from generic_chess.core.movegen import legal_actions
    child=next(apply_action(s,a,c) for a in legal_actions(s,c)
               if apply_action(s,a,c).terminal_status.status==TerminalStatus.MAX_PLY)
    assert child.position.side_to_move==1 and child.terminal_status.winner is None
    for node in (ProofNode(0,terminal_kind='max_ply'),ProofNode(1)):
        forged=WinCertificate(c.ruleset_fingerprint,child,0,node)
        assert not verify_certificate(c,child,forged)['verified']


def test_actual_mate_at_ply_limit_precedes_draw_limit():
    c=compile_ruleset(replace(krk_ruleset(4),max_ply=1));s=krk_state(c,1,3,8,0)
    r,a=require(c,s,lambda a:True)
    assert apply_action(s,a,c).terminal_status.status==TerminalStatus.CHECKMATE


@pytest.mark.parametrize('algorithm',['ANDOR','PN'])
def test_played_perpetual_check_win_keeps_history_and_is_not_mate(algorithm):
    from scripts.generic_win_proof_pn import prove_win_pn
    from scripts.generic_proof_rnb_bridge import uci
    from generic_chess.core.movegen import legal_actions
    solver=prove_win if algorithm=='ANDOR' else prove_win_pn
    c=compile_ruleset(replace(krk_ruleset(4),repetition_policy='continuous_check_loss'))
    state=krk_state(c,0,15,2,0)
    prefix=['c1d1','d4c4','d1c1','c4d4','c1d1','d4c4','d1c1']
    for move in prefix:
        state=apply_action(state,next(a for a in legal_actions(state,c) if uci(a)==move),c)
    assert not state.terminal_status.is_terminal and state.position.side_to_move==1
    r=solver(c,state,target=1,max_nodes=4096,seconds=2.,max_depth=1)
    assert r.status==PROVEN_WIN,r
    assert r.certificate.tree.rank==1
    assert verify_certificate(c,state,r.certificate,seconds=2.)['verified']
    cur=StrategyCursor(c,r.certificate,seconds=2.);a=cur.choose(state);child=cur.advance(state,a)
    assert child.terminal_status.status==TerminalStatus.PERPETUAL_CHECK and child.terminal_status.winner==1
    fresh=bind(c,state.position)
    assert not verify_certificate(c,fresh,r.certificate)['verified']
    assert solver(c,fresh,target=1,max_nodes=4096,seconds=2.,max_depth=1).status==UNKNOWN


def test_certificate_binds_aux_rights_and_lossless_action_identity():
    from scripts.chess_development import root_from_fen
    c=compile_ruleset_for_execution(build_western_chess_ruleset())
    state=root_from_fen('7k/8/5KQ1/8/8/8/8/8 w - - 0 1',c)
    r=prove_win(c,state,max_nodes=4096,seconds=2.,max_depth=1)
    assert r.status==PROVEN_WIN and state.position.aux_state
    aux=list(state.position.aux_state)
    i=next(i for i,(_,v) in enumerate(aux) if type(v) is int and v in (0,1))
    key,value=aux[i];aux[i]=(key,1-value)
    changed=bind(c,replace(state.position,aux_state=tuple(aux)))
    assert verify_certificate(c,changed,r.certificate)['reason']=='root_binding_mismatch'
    a,child=r.certificate.tree.edges[0]
    forged_action=replace(a,pattern_id='unregistered_pattern_with_same_coordinates')
    forged=replace(r.certificate,tree=replace(r.certificate.tree,edges=((forged_action,child),)))
    assert not verify_certificate(c,state,forged)['verified']
