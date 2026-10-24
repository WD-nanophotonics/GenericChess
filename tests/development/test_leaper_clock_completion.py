"""Full short-clock completion agrees with literal Core two-ply terminals."""
from dataclasses import replace
import pytest
from scripts.leaper_clock_completion import ClockCompletion
from scripts import leaper_design as L
from generic_chess.ai.alphabeta import search as S
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from test_leaper_last_clock_shield import context,q

def terminal_reference(sess,remaining,ply=0):
    if sess.state.terminal_status.is_terminal:return S.terminal_score(sess.state.terminal_status,sess.state.position.side_to_move,ply)
    assert remaining>0,'all literal leaves must be actual terminals, no static placeholder'
    vals=[]
    for action in sess.legal_actions():
        child=L.GameSession.replay(sess.compiled,sess.to_record());child.submit(action)
        vals.append(-terminal_reference(child,remaining-1,ply+1))
    assert vals;return max(vals)

def test_two_ply_completion_agrees_with_literal_Core_terminals():
    sess,ctx=context(replace(L.definition(5,7),max_ply=2));expected=terminal_reference(sess,2)
    with ClockCompletion()as policy:
        assert q(ctx)==expected and policy.counts['root_remaining_2']==1 and policy.counts['terminal']>0
    ctx.runtime.assert_balanced()

def test_not_enough_qhard_room_retains_original_policy():
    _,ctx=context(replace(L.definition(5,7),max_ply=2),hard=1)
    with ClockCompletion()as policy:assert q(ctx)==4242 and not policy.counts
    ctx.runtime.assert_balanced()

def test_completion_qbudget_abort_restores_state_and_function():
    _,ctx=context(replace(L.definition(5,7),max_ply=2),qcap=1);original=S._quiescence_runtime
    with pytest.raises(S.SearchAborted,match='qsearch_budget'):
        with ClockCompletion():q(ctx)
    assert S._quiescence_runtime is original and not hasattr(S,'_complete_rules_clock');ctx.runtime.assert_balanced()
