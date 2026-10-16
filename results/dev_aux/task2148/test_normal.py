from pathlib import Path
from dataclasses import replace
from math import inf
from copy import copy
import sys
sys.path.insert(0,str(Path('tests').resolve()))
sys.path.insert(0,str(Path('tests/development').resolve()))
from test_generic_session_win_proof import session,claim
from test_generic_session_proof_mechanisms import played,layout
from conftest import T,king_type,make_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import DropMove,PassAction
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.rules.schema import RuleConsecutiveActionAdjudication
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_session_phase_player import SessionPhasePlayer,PhaseLimits
from scripts.generic_session_win_proof import execute
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch

def choose(s,depth=1,**kw):
 before=s.to_record();state=s.state
 r=SessionCompleteMaterialSearch(s.compiled,lambda pos,target:0.,max_depth=depth).choose(s,seconds=3.,max_nodes=65536,**kw)
 assert s.to_record()==before and _same_state(s.state,state)
 return r

def test_real_winning_claim_is_selected_without_a_mate_prover():
 s=session(claim(0,'WIN'));r=choose(s)
 assert r.choice.kind=='DECLARATION'and r.choice.declaration_id=='claim'and r.score==inf
 child=copy(s);assert execute(child,r.choice).winner==0
 old=SessionPhasePlayer(s.compiled,lambda pos,target:0.,proof_enabled=False,max_depth=1,limits=PhaseLimits(normal_seconds=1.)).choose(s,max_nodes=65536,seconds=3.)
 assert old.choice is None or old.choice.kind!='DECLARATION'

def test_actual_restart_is_not_reported_as_draw_or_win():
 s=session(claim(0,'RESTART'),k=0,b=15,r=2);r=choose(s)
 assert r.choice.kind=='DECLARATION'and r.score==0.
 child=copy(s);result=execute(child,r.choice)
 assert result.status is SessionStatus.DECLARATION and result.declaration_outcome=='RESTART'and result.winner is None
 assert any(k[2]=='RESTART'for k,count in r.terminal_leaves)

def test_forced_promotion_mate_dominates_finite_material_leaf():
 rook=T('R',*(RayAtom(d)for d in((1,0),(-1,0),(0,1),(0,-1))))
 pawn=T('P',LeapAtom((0,1)),is_promotable=True,targets=('R',))
 rs=make_ruleset(4,[king_type(),rook,pawn],lines=['...k','P...','..K.','....'],auto_promotion=True)
 s=GameSession(compile_ruleset_for_execution(rs));r=choose(s)
 assert r.score==inf and r.choice.action.promotion_target_id=='R'
 child=copy(s);assert execute(child,r.choice).winner==0
 assert child.state.position.board[12].base_type_id=='P'

def test_actual_hand_capture_and_drop_mate_keep_record():
 rs=replace(krk_ruleset(4),drop_allowed={'R':((True,)*16,)*2},capture_disposition='capture_to_hand')
 rs=layout(rs,[(1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(4,Piece(0,'R','R')),(8,Piece(1,'R','R'))])
 s=played(rs,['a2a3','d1d2']);r=choose(s)
 assert isinstance(r.choice.action,DropMove)and r.score==inf
 child=copy(s);assert execute(child,r.choice).winner==0 and len(child.to_record().actions)==3

def test_real_pass_draw_defense_prevents_spurious_losing_mate_choice():
 rs=layout(krk_ruleset(4),[(1,Piece(0,'K','K')),(7,Piece(1,'K','K')),(12,Piece(0,'R','R'))])
 rs=replace(rs,pass_enabled=True,consecutive_action_adjudications=(RuleConsecutiveActionAdjudication('pass',1,'DRAW'),))
 s=played(rs,['a4a3']);r=choose(s,3)
 assert isinstance(r.choice.action,PassAction)and r.score==0.
 child=copy(s);assert execute(child,r.choice).status is SessionStatus.ACTION_CLASS_DRAW

def test_played_perpetual_check_win_uses_actual_history():
 rs=layout(replace(krk_ruleset(4),repetition_policy='continuous_check_loss'),[(0,Piece(0,'K','K')),(15,Piece(1,'K','K')),(2,Piece(0,'R','R'))])
 s=played(rs,['c1d1','d4c4','d1c1','c4d4','c1d1','d4c4','d1c1']);r=choose(s)
 child=copy(s);result=execute(child,r.choice)
 assert r.score==inf and result.status is SessionStatus.PERPETUAL_CHECK and result.winner==1

def test_budget_cancel_and_nonfinite_evaluator_do_not_emit_fake_wdl():
 s=session();before=s.to_record()
 r=choose(s,cancel=lambda:True);assert r.choice is None and r.exit_cause=='cancelled'and r.score is None
 r=SessionCompleteMaterialSearch(s.compiled,lambda pos,target:inf,max_depth=1).choose(s,max_nodes=65536,seconds=3.)
 assert r.choice is None and r.exit_cause=='unsupported_or_unreplayable_session'and r.score is None
 assert s.to_record()==before
