"""Actual full-session fallback qualification on existing mechanism fixtures."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import sys,importlib.util,json
sys.path.insert(0,str(Path('tests').resolve()))
from conftest import T,king_type,make_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import DropMove,SemanticBoardMove,PassAction,action_to_dict
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleConsecutiveActionAdjudication
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_proof_rnb_bridge import uci
from scripts.generic_win_proof import _same_state,_ordered
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_player import commit_session_decision
from results.dev_aux.task2136.legal_fallback import LegalFallbackPhasePlayer

def fallback(s,cancel=None):
 before=s.to_record();state=s.state
 p=LegalFallbackPhasePlayer(s.compiled,lambda pos,target:0.,proof_enabled=False,max_depth=2,limits=PhaseLimits(normal_seconds=0.))
 d=p.choose(s,max_nodes=64,seconds=.75,cancel=cancel)
 assert s.to_record()==before and _same_state(s.state,state)
 if cancel is not None:
  assert d.choice is None and d.exit_cause=='cancelled'
  return d,None
 assert d.choice.action==_ordered(s.legal_actions())[0]
 assert d.source=='PRECOMPUTED_LEGAL_FALLBACK'
 after=copy(s);commit_session_decision(after,d,[p])
 replay=GameSession.replay(s.compiled,deserialize_game_record(serialize_game_record(after.to_record())))
 assert _same_state(replay.state,after.state) and replay.result==after.result
 return d,after

def capture_session():
 rs=replace(krk_ruleset(4),drop_allowed={'R':((True,)*16,)*2},capture_disposition='capture_to_hand')
 board=[None]*16
 for i,p in [(1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(4,Piece(0,'R','R')),(8,Piece(1,'R','R'))]:board[i]=p
 rs=replace(rs,initial_position=tuple(tuple(board[i:i+4])for i in range(0,16,4)))
 s=GameSession(compile_ruleset_for_execution(rs))
 for name in ['a2a3','d1d2']:s.submit(next(a for a in s.legal_actions()if not isinstance(a,(DropMove,PassAction))and uci(a)==name))
 return s

def test_capture_history_hand_drop_and_cancel_preserved():
 s=capture_session();assert s.state.position.hands[0].count('R')==1
 d,a=fallback(s);assert isinstance(d.choice.action,DropMove)
 assert a.state.position.hands[0].count('R')==0 and len(a.to_record().actions)==3
 fallback(s,lambda:True)

def test_forced_promotion_preserves_base_and_promotion_target():
 rook=T('R',*(RayAtom(d)for d in((1,0),(-1,0),(0,1),(0,-1))))
 pawn=T('P',LeapAtom((0,1)),is_promotable=True,targets=('R',))
 rs=make_ruleset(4,[king_type(),rook,pawn],lines=['...k','P...','..K.','....'],auto_promotion=True)
 s=GameSession(compile_ruleset_for_execution(rs));d,a=fallback(s)
 assert d.choice.action.promotion_target_id=='R'
 piece=a.state.position.board[12];assert piece.base_type_id=='P' and piece.current_type_id=='R' and piece.promoted
 fallback(s,lambda:True)

def test_semantic_aux_write_preserves_exact_action_identity_and_replay():
 spec=importlib.util.spec_from_file_location('aux_qualification',Path('tests/product/test_runtime_aux_identity.py'))
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 s=GameSession(mod._compiled(initial=0,value=1));d,a=fallback(s)
 assert isinstance(d.choice.action,SemanticBoardMove) and d.choice.action.pattern_id and d.choice.action.geometry_id
 assert a.state.position.aux_state!=s.state.position.aux_state
 fallback(s,lambda:True)

def test_existing_perpetual_history_and_pass_draw_stay_actual_rules():
 rs=replace(krk_ruleset(4),repetition_policy='continuous_check_loss')
 b=[None]*16
 for i,p in[(0,Piece(0,'K','K')),(15,Piece(1,'K','K')),(2,Piece(0,'R','R'))]:b[i]=p
 rs=replace(rs,initial_position=tuple(tuple(b[i:i+4])for i in range(0,16,4)))
 s=GameSession(compile_ruleset_for_execution(rs))
 for name in ['c1d1','d4c4','d1c1','c4d4','c1d1','d4c4','d1c1']:s.submit(next(a for a in s.legal_actions()if uci(a)==name))
 assert len(s.to_record().actions)==7
 d,a=fallback(s);assert len(a.to_record().actions)==8
 fallback(s,lambda:True)
