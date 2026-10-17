from dataclasses import replace
import pytest
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleDeclaration,RuleNoProgressDraw
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_fixtures import krk_ruleset
from results.dev_aux.task2492.adapters import SessionEnv
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2511.generic import ScoringSessionEnv,NonScoringTerminal

def session(outcome=None,draw=False):
 board=[None]*16
 for sq,piece in[(1,Piece(0,'K','K')),(3,Piece(1,'K','K')),(8,Piece(0,'R','R'))]:board[sq]=piece
 declarations=()if outcome is None else(RuleDeclaration('claim',0,require_not_in_check=False,failure_outcome=outcome),)
 rs=replace(krk_ruleset(4),initial_position=tuple(tuple(board[y:y+4])for y in range(0,16,4)),declarations=declarations)
 if draw:rs=replace(rs,no_progress_draw=RuleNoProgressDraw(1,True))
 return GameSession(compile_ruleset(rs))

@pytest.mark.parametrize('outcome',['RESTART','NO_CONTEST'])
def test_actual_non_scoring_declaration_is_never_zero_training_target(outcome):
 s=session(outcome);s.declare('claim');assert s.result.winner is None and s.result.declaration_outcome==outcome
 assert SessionEnv(s,()).terminal()==0 # preserved86 defect reproduced, not silently patched
 env=ScoringSessionEnv(s,());before=env.session.to_record()
 with pytest.raises(NonScoringTerminal)as error:env.terminal()
 assert error.value.result==s.result and env.session.to_record()==before

@pytest.mark.parametrize('outcome,expected',[('WIN',1),('LOSS',-1)])
def test_actual_decisive_declarations_keep_owner_oriented_WL(outcome,expected):
 s=session(outcome);s.declare('claim');assert ScoringSessionEnv(s,()).terminal()==expected

def test_actual_rule_draw_remains_zero_and_ongoing_remains_none():
 s=session(draw=True);env=ScoringSessionEnv(s,());assert env.terminal()is None
 s.submit(s.legal_actions()[0]);assert s.result.status is SessionStatus.NO_PROGRESS_DRAW
 assert ScoringSessionEnv(s,()).terminal()==0

def test_full_owned_loss_choice_and_full_history_pushpop_are_preserved():
 s=session('LOSS');env=ScoringSessionEnv(s,());before=env.session.to_record();choice=next(a for a in env.actions()if a.kind=='DECLARATION');env.push(choice);assert env.terminal()==-1;env.pop();assert env.session.to_record()==before and env.terminal()is None

def test_search_encountering_unscored_terminal_rejects_without_material_label():
 env=ScoringSessionEnv(session('RESTART'),(('board','R'),('hand','R')));before=env.session.to_record();model=Model([1,1]);weights=model.weights[:]
 with pytest.raises(NonScoringTerminal):TrainingSearch(1).search(env,model,nodes=128,seconds=2.,seed=7)
 assert env.session.to_record()==before and model.weights==weights
