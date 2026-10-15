"""Observed runtime scope failure becomes explicit reference UNKNOWN, not WDL."""
from dataclasses import replace
import pytest
from generic_chess.rules import compile_ruleset_for_execution,build_western_chess_ruleset
from generic_chess.rules.schema import RuleNoProgressDraw
from generic_chess.core.coordinates import Square
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.exact_generic_preference_solver_v3 import solve_root_threshold_v3


@pytest.mark.parametrize('semantic',[False,True])
def test_real_no_progress_scope_has_structured_refusal_before_runtime(monkeypatch,semantic):
    rs=build_western_chess_ruleset() if semantic else krk_ruleset(4)
    rs=replace(rs,no_progress_draw=RuleNoProgressDraw(1,True))
    current=GameSession(compile_ruleset_for_execution(rs));state=current.state;record=current.to_record()
    def forbidden(*args,**kwargs):raise AssertionError('unsupported runtime must not be imported')
    with monkeypatch.context() as patch:
        patch.setattr(SearchPathRuntime,'from_state',forbidden)
        result=solve_root_threshold_v3(current.compiled,state,max_nodes=16,max_depth=4)
    assert result.strong is False and result.root_value is None and not result.optimal_actions and not result.action_values
    assert result.unresolved_reason=='REFERENCE_SOLVE_UNRESOLVED:no_progress_history' and result.stats['states_expanded']==0
    assert current.to_record()==record and current.state==state
    if semantic:
        action=next(a for a in current.legal_actions() if getattr(a,'from_square',None)==Square(6,0) and a.to_square==Square(5,2))
    else:action=current.legal_actions()[0]
    current.submit(action)
    assert current.result.status is SessionStatus.NO_PROGRESS_DRAW and current.result.winner is None
    # A known actual terminal does not license a new unsupported reference label.
    assert solve_root_threshold_v3(current.compiled,current.state,max_nodes=16).strong is False
