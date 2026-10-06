"""Defer only the unused terminal check query; keep no-action adjudication."""
import pytest
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import terminal_from_search_runtime, TerminalStatus
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.core.transition import initial_state

@pytest.mark.parametrize('has_legal,checked,expected',[
    (True,False,TerminalStatus.ONGOING),
    (True,True,TerminalStatus.ONGOING),
    (False,True,TerminalStatus.CHECKMATE),
    (False,False,TerminalStatus.STALEMATE),
])
def test_check_query_only_needed_without_legal_action(monkeypatch,has_legal,checked,expected):
    c=compile_ruleset_for_execution(build_western_chess_ruleset())
    runtime=SearchPathRuntime.from_state(initial_state(c),c)
    engine=semantic_engine_for(c);calls=[]
    monkeypatch.setattr(type(engine),'has_legal_action',lambda *args,**kwargs:has_legal)
    def query(*args,**kwargs):
        calls.append(1);return checked
    monkeypatch.setattr(type(engine),'in_check',query)
    result=terminal_from_search_runtime(runtime)
    assert result.status is expected
    assert len(calls)==int(not has_legal)
    if expected is TerminalStatus.CHECKMATE:
        assert result.winner==1-runtime.position.side_to_move

def test_checked_child_history_is_still_recorded():
    import scripts.chess_development as d
    c=compile_ruleset_for_execution(build_western_chess_ruleset())
    root=d.root_from_fen('7k/8/8/8/8/8/8/R6K w - - 0 1',c)
    runtime=SearchPathRuntime.from_state(root,c)
    action=next(a for a in runtime.legal_actions() if d.uci(a)=='a1a8')
    with runtime.pushed(action):
        assert runtime.history[-1].gave_check is True
        assert runtime.terminal_status.status is TerminalStatus.ONGOING
    runtime.assert_balanced()
