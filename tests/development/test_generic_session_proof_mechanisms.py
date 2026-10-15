"""Actual public-session mechanism controls shared by AND/OR and PN."""
from dataclasses import replace
import pytest
from conftest import T,king_type,make_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.core.movement import RayAtom,LeapAtom
from generic_chess.core.actions import DropMove,PassAction
from generic_chess.rules import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleNoProgressDraw,RuleConsecutiveActionAdjudication
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_proof_rnb_bridge import uci
from scripts.generic_session_win_proof import prove_session_win,SessionStrategyCursor,verify_session_certificate
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_certificate_json import export_session_certificate,decode_session_certificate

SOLVERS=[prove_session_win,prove_session_win_pn]


def layout(rs,pieces):
    board=[None]*16
    for index,piece in pieces:board[index]=piece
    return replace(rs,initial_position=tuple(tuple(board[i:i+4]) for i in range(0,16,4)))


def played(rs,prefix):
    current=GameSession(compile_ruleset_for_execution(rs))
    for move in prefix:
        current.submit(next(a for a in current.legal_actions() if not isinstance(a,(DropMove,PassAction)) and uci(a)==move))
    return current


@pytest.mark.parametrize('solver',SOLVERS)
def test_actual_capture_hand_then_drop_mate_is_preserved(solver):
    rs=replace(krk_ruleset(4),drop_allowed={'R':((True,)*16,)*2},capture_disposition='capture_to_hand')
    rs=layout(rs,[(1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(4,Piece(0,'R','R')),(8,Piece(1,'R','R'))])
    current=played(rs,['a2a3','d1d2']);assert current.state.position.hands[0].count('R')==1
    result=solver(current,max_depth=1,seconds=3.);assert result.status=='PROVEN_WIN'
    replayed,certificate=decode_session_certificate(current.compiled,export_session_certificate(current,result.certificate))
    cursor=SessionStrategyCursor(replayed,certificate,seconds=3.);choice=cursor.choose(replayed)
    assert isinstance(choice.action,DropMove)
    terminal=cursor.commit(replayed,choice)
    assert terminal.status is SessionStatus.CHECKMATE and terminal.winner==0
    assert replayed.state.position.hands[0].count('R')==0 and len(replayed.to_record().actions)==3
    assert current.state.position.hands[0].count('R')==1 and len(current.to_record().actions)==2


@pytest.mark.parametrize('solver',SOLVERS)
def test_real_forced_promotion_mate_retains_base_piece(solver):
    rook=T('R',*(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1))))
    pawn=T('P',LeapAtom((0,1)),is_promotable=True,targets=('R',))
    rs=make_ruleset(4,[king_type(),rook,pawn],lines=['...k','P...','..K.','....'],auto_promotion=True)
    current=GameSession(compile_ruleset_for_execution(rs));result=solver(current,max_depth=1,seconds=3.)
    assert result.status=='PROVEN_WIN'
    replayed,certificate=decode_session_certificate(current.compiled,export_session_certificate(current,result.certificate))
    cursor=SessionStrategyCursor(replayed,certificate,seconds=3.)
    assert cursor.commit(replayed,cursor.choose(replayed)).winner==0
    piece=replayed.state.position.board[12]
    assert piece.base_type_id=='P' and piece.current_type_id=='R' and piece.promoted


@pytest.mark.parametrize('solver',SOLVERS)
def test_real_pass_draw_defense_cannot_be_omitted(solver):
    rs=layout(krk_ruleset(4),[(1,Piece(0,'K','K')),(7,Piece(1,'K','K')),(12,Piece(0,'R','R'))])
    plain=played(rs,['a4a3']);certificate=solver(plain,target=0,max_depth=3,seconds=3.).certificate
    assert certificate is not None
    rs=replace(rs,pass_enabled=True,consecutive_action_adjudications=(RuleConsecutiveActionAdjudication('pass',1,'DRAW'),))
    defended=played(rs,['a4a3']);result=solver(defended,target=0,max_depth=3,seconds=3.)
    assert result.status=='UNKNOWN' and result.certificate is None
    forged=replace(certificate,ruleset_fingerprint=defended.compiled.ruleset_fingerprint,root_record=defended.to_record(),root_state=defended.state)
    assert not verify_session_certificate(defended,forged,seconds=3.)['verified']
    defended.submit(PassAction());assert defended.result.status is SessionStatus.ACTION_CLASS_DRAW and defended.result.winner is None


@pytest.mark.parametrize('solver',SOLVERS)
def test_actual_played_perpetual_history_win_is_not_mislabeled_mate(solver):
    rs=layout(replace(krk_ruleset(4),repetition_policy='continuous_check_loss'),[(0,Piece(0,'K','K')),(15,Piece(1,'K','K')),(2,Piece(0,'R','R'))])
    prefix=['c1d1','d4c4','d1c1','c4d4','c1d1','d4c4','d1c1']
    current=played(rs,prefix);assert len(current.to_record().actions)==7
    result=solver(current,target=1,max_depth=1,seconds=3.);assert result.status=='PROVEN_WIN'
    replayed,certificate=decode_session_certificate(current.compiled,export_session_certificate(current,result.certificate))
    cursor=SessionStrategyCursor(replayed,certificate,seconds=3.);terminal=cursor.commit(replayed,cursor.choose(replayed))
    assert terminal.status is SessionStatus.PERPETUAL_CHECK and terminal.winner==1 and len(replayed.to_record().actions)==8
    assert len(current.to_record().actions)==7 and current.result.status is SessionStatus.ONGOING


@pytest.mark.parametrize('solver',SOLVERS)
def test_actual_no_progress_draw_and_depth_unknown_remain_distinct(solver):
    rs=replace(krk_ruleset(4),max_ply=4,no_progress_draw=RuleNoProgressDraw(1,True))
    current=GameSession(compile_ruleset_for_execution(rs));result=solver(current,max_depth=3,seconds=3.)
    assert result.status=='UNKNOWN' and result.certificate is None
    action=current.legal_actions()[0];current.submit(action)
    assert current.result.status is SessionStatus.NO_PROGRESS_DRAW and current.result.winner is None
    assert solver(current,seconds=3.).status=='ALREADY_TERMINAL'


@pytest.mark.parametrize('solver',SOLVERS)
def test_semantic_action_ids_survive_transport_and_forged_ids_fail_public_execution(solver):
    from generic_chess.rules import build_western_chess_ruleset
    from generic_chess.core.actions import SemanticBoardMove
    rs=build_western_chess_ruleset();board=[None]*64
    for index,piece in [(45,Piece(0,'K','K')),(46,Piece(0,'Q','Q')),(63,Piece(1,'K','K'))]:board[index]=piece
    rs=replace(rs,initial_position=tuple(tuple(board[i:i+8]) for i in range(0,64,8)))
    current=GameSession(compile_ruleset_for_execution(rs));result=solver(current,max_depth=1,seconds=3.)
    assert result.status=='PROVEN_WIN'
    replayed,certificate=decode_session_certificate(current.compiled,export_session_certificate(current,result.certificate))
    choice,leaf=certificate.tree.edges[0]
    assert isinstance(choice.action,SemanticBoardMove) and choice.action.pattern_id and choice.action.geometry_id
    forged=replace(choice,action=replace(choice.action,pattern_id='unregistered_same_coordinates'))
    bad=replace(certificate,tree=replace(certificate.tree,edges=((forged,leaf),)))
    assert not verify_session_certificate(replayed,bad,seconds=3.)['verified']
    cursor=SessionStrategyCursor(replayed,certificate,seconds=3.)
    assert cursor.commit(replayed,cursor.choose(replayed)).winner==0
