"""Real historical false-LOSS counterexample, not a mocked WDL label."""
import pytest
from scripts.exact_generic_preference_solver_v3 import solve_root_threshold_v3
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.rules.schema import RuleSet,RuleDeclaration
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession


def counterexample(outcome=None):
    king=PieceType('K','Anchor',tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if x or y),is_anchor=True)
    rook=PieceType('R','Ray',tuple(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1))))
    board=[None]*16;board[0]=Piece(0,'K','K');board[2]=Piece(1,'K','K');board[9]=Piece(0,'R','R')
    declarations=() if outcome is None else (RuleDeclaration('claim',1,require_not_in_check=False,failure_outcome=outcome),)
    rs=RuleSet(board_size=4,piece_types=(king,rook),initial_position=tuple(tuple(board[i:i+4]) for i in range(0,16,4)),drop_allowed={'R':((False,)*16,)*2},capture_disposition='remove_from_game',max_ply=64,repetition_limit=3,declarations=declarations)
    current=GameSession(compile_ruleset(rs))
    current.submit(next(a for a in current.legal_actions() if a.from_square.file==1 and a.from_square.rank==2 and a.to_square.file==2 and a.to_square.rank==2))
    return current


@pytest.mark.parametrize('outcome',['WIN','RESTART'])
@pytest.mark.parametrize('tt',[False,True])
def test_board_only_reference_refuses_declaration_domain(outcome,tt):
    current=counterexample(outcome)
    before=current.to_record();state=current.state
    result=solve_root_threshold_v3(current.compiled,state,max_nodes=32768,max_depth=8,use_tt=tt)
    assert result.strong is False and result.root_value is None and result.action_values==()
    assert result.unresolved_reason=='REFERENCE_SOLVE_UNRESOLVED:declarations'
    assert result.stats['states_expanded']==0 and current.to_record()==before
    actual=current.declare('claim')
    assert actual.winner==(1 if outcome=='WIN' else None) and current.state==state


def test_ordinary_board_only_reference_still_proves_existing_forced_loss():
    current=counterexample()
    result=solve_root_threshold_v3(current.compiled,current.state,max_nodes=32768,max_depth=8,use_tt=False)
    assert result.strong and result.root_value=='LOSS' and result.unresolved_reason is None
