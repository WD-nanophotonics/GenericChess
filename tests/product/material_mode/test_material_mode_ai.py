"""Basic two-player AI, complete legal sessions and cooperative stopping."""
from dataclasses import replace
import pytest
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from generic_chess.material_mode import ModeSession,example_rules,BasicTwoPlayer,BoardMove,DropMove,Square,BuyPiece
from test_material_mode_economy import earned,puzzle


def test_ai_plays_real_two_player_match_and_replays():
    s=ModeSession(example_rules(max_ply=20));ai=BasicTwoPlayer(seed=42)
    for _ in range(12):
        if s.result.terminal:break
        before=s.state
        d=ai.choose_action(s,SearchLimits(max_depth=2,max_nodes=150,max_time_seconds=.15))
        assert d.action in s.legal_actions() and s.state is before
        s.submit(d.action)
    assert s.state.ply_count>0 and ModeSession.from_record(s.to_record()).state==s.state


def test_material_counts_wallet_hand_board_and_wins_dominate():
    s=earned();e=s._engine
    assert e.material_value(s.state,0)-e.material_value(s.state,1)==120
    before=e.material_value(s.state,0)
    s.submit(BuyPiece('F'))
    assert e.material_value(s.state,0)==before
    s=ModeSession(example_rules(width=4,height=4))
    puzzle(s,[(2,1,0,'K'),(0,3,1,'K')],hands=[{'Q':1},{}])
    d=BasicTwoPlayer().choose_action(s,SearchLimits(max_depth=1,max_nodes=1000,max_time_seconds=2))
    assert isinstance(d.action,DropMove)
    assert s._engine.after_legal(s.state,d.action).result.winner==0
    assert d.score_units==s._engine.material_ceiling+1


@pytest.mark.parametrize('limits',[SearchLimits(max_nodes=0),SearchLimits(max_time_seconds=0),SearchLimits(max_depth=0),SearchLimits(max_nodes=1)])
def test_budget_returns_legal_fallback(limits):
    s=ModeSession(example_rules());d=BasicTwoPlayer().choose_action(s,limits)
    assert d.action in s.legal_actions() and not d.cancelled


def test_explicit_cancellation_has_no_action_and_search_is_readonly(monkeypatch):
    s=ModeSession(example_rules());before=s.state;t=CancellationToken();t.cancel()
    assert BasicTwoPlayer().choose_action(s,cancel_token=t).action is None
    t=CancellationToken();original=s._engine.after_legal
    def cancel_after(state,action):
        result=original(state,action);t.cancel();return result
    monkeypatch.setattr(s._engine,'after_legal',cancel_after)
    d=BasicTwoPlayer().choose_action(s,cancel_token=t)
    assert d.cancelled and d.action is None and s.state is before


def test_ai_rejects_four_players_and_returns_none_after_finish():
    with pytest.raises(NotImplementedError):BasicTwoPlayer().choose_action(ModeSession(example_rules(players=4)))
    s=ModeSession(example_rules());s.resign()
    assert BasicTwoPlayer().choose_action(s).action is None


def test_ai_uses_purchase_when_it_is_the_legal_turn_and_takes_material():
    s=ModeSession(example_rules(width=6,height=6))
    puzzle(s,[(0,0,0,'K'),(2,1,1,'K'),(1,2,1,'B')],balances=[10,0])
    assert s.legal_actions()==(BuyPiece('F'),)
    d=BasicTwoPlayer().choose_action(s,SearchLimits(max_depth=1,max_nodes=100,max_time_seconds=1))
    assert d.action==BuyPiece('F')
    s.submit(d.action);assert s.state.position.hands[0].count('F')==1
    s=ModeSession(example_rules(width=6,height=6))
    puzzle(s,[(0,0,0,'K'),(2,0,0,'R'),(5,5,1,'K'),(2,3,1,'F')])
    d=BasicTwoPlayer().choose_action(s,SearchLimits(max_depth=1,max_nodes=100,max_time_seconds=1))
    assert d.action==BoardMove(Square(2,0),Square(2,3))
