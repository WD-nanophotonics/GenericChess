from dataclasses import replace
from types import SimpleNamespace as NS
import pytest
from generic_chess.core.terminal import TerminalResult,TerminalStatus as T,terminal_result
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.core.declarations import available_declarations
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.public_goal_intervals import PublicGame,observe
from scripts.mate_only_public_game import MateOnlyPublicGame,mate_goal_terminal
from test_generic_declaration_semantics import _shogi_boundary_state

@pytest.mark.parametrize('owner',(0,1))
def test_real_nyugyoku_win_is_not_a_mate_label(owner):
    c=compile_ruleset_for_execution(build_standard_shogi_ruleset())
    for score in (31,24):
        state=_shogi_boundary_state(c,score,owner=owner)
        state=replace(state,terminal_status=terminal_result(state,c))
        claim=available_declarations(state,c)[0]
        before=state;full=PublicGame(c);mate=MateOnlyPublicGame(c)
        assert claim.outcome==('WIN' if score==31 else 'RESTART')
        full_leaf=full.successor(state,claim);mate_leaf=mate.successor(state,claim)
        assert full_leaf==mate_leaf and mate.terminal(mate_leaf).unresolved
        result=observe(mate_leaf,mate,depth=0)
        assert result['interval']==(-1,1) and result['transitions']==result['public_materializations']==0
        if score==31:assert observe(full_leaf,full,depth=0)['interval']==((1,1) if owner==0 else (-1,-1))
        assert state==before
    bad=replace(state,terminal_status=TerminalResult(T.CHECKMATE,owner))
    with pytest.raises(ValueError,match='stale'):mate.terminal(bad)

def test_all_nonmate_terminals_stay_terminal_and_unknown():
    for status in T:
        result=TerminalResult(status,0 if status in (T.CHECKMATE,T.RULE_LOSS,T.PERPETUAL_CHECK) else None)
        projected=mate_goal_terminal(result)
        if status in (T.CHECKMATE,T.ONGOING):assert projected is result
        else:assert projected.is_terminal and projected.unresolved and projected.winner==result.winner and projected.status==status
    claim=NS(is_terminal=True,status='declaration',winner=0,unresolved=False)
    assert mate_goal_terminal(claim).unresolved

@pytest.mark.parametrize('owner',(0,1))
def test_local_checking_defender_cannot_escape_through_a_claim(owner):
    c=compile_ruleset_for_execution(build_standard_shogi_ruleset())
    assert all(d.require_not_in_check for d in c.declarations)
    state=_shogi_boundary_state(c,31,owner=owner,condition='checked')
    assert semantic_engine_for(c).in_check(state.position,owner)
    assert available_declarations(state,c)==()
