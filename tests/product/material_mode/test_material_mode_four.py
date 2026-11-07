"""Four-seat turns, neutral resources, frozen anchors and delayed mate."""
from dataclasses import replace
import pytest
from generic_chess.material_mode import ModeSession,example_rules,PieceType,LeapAtom,Square,BoardMove,BuyPiece,DropMove
from test_material_mode_economy import puzzle


def test_four_square_and_initial_overlap_and_safety():
    with pytest.raises(ValueError):example_rules(players=4,width=8,height=6)
    base=example_rules(players=4)
    from generic_chess.material_mode import Placement
    with pytest.raises(ValueError):ModeSession(replace(base,formation=(Placement('K',Square(0,0)),Placement('F',Square(0,7)))))
    with pytest.raises(ValueError):ModeSession(replace(base,formation=(Placement('K',Square(3,0)),Placement('R',Square(4,0)))))


def test_rotational_equivalence_with_forward_leap_and_purchases():
    from generic_chess.material_mode import BuyAndDrop,action_to_dict
    s=ModeSession(example_rules(players=4,purchase_penalty=False));e=s._engine
    base=replace(s.state,balances=(100,)*4)
    actions=e.legal_actions(base)
    for seat in (1,2,3):
        other=replace(base,position=replace(base.position,side_to_move=seat))
        expected=set()
        for a in actions:
            raw=action_to_dict(a)
            for key in ('from','to'):
                if key not in raw:continue
                x,y=raw[key]
                for _ in range(seat):x,y=y,7-x
                raw[key]=[x,y]
            import json
            expected.add(json.dumps(raw,sort_keys=True))
        import json
        assert expected=={json.dumps(action_to_dict(a),sort_keys=True) for a in e.legal_actions(other)}


def test_mate_elimination_keeps_board_and_neutral_capture_yields_score():
    s=ModeSession(example_rules(players=4,width=6,height=6))
    puzzle(s,[(0,0,0,'K'),(3,4,0,'N'),(2,1,1,'K'),(0,2,1,'R'),(1,0,1,'R'),(3,2,1,'R'),(5,5,2,'K'),(5,0,3,'K')],
           side=3,balances=[37,0,0,0],hands=[{'R':2},{},{},{}])
    assert s._engine.in_check(s.state,0)
    # It is not player0's turn yet, so player0 remains active.
    assert s.state.active[0]
    s.submit(BoardMove(Square(5,0),Square(5,1)))
    view=s.snapshot()
    assert s.state.active==(False,True,True,True) and s.state.current_player==1
    assert s.state.balances[0]==0 and s.state.position.hands[0].total()==0
    assert view.board[0].status=='frozen_anchor' and view.board[4*6+3].status=='neutral'
    assert not s._engine.in_check(s.state,2)  # dead knight no longer attacks5,5
    assert BoardMove(Square(0,2),Square(0,0)) not in s.legal_actions()
    s.submit(BoardMove(Square(3,2),Square(3,4)))
    assert s.snapshot().balances[1]=='8' and s.state.current_player==2
    assert s.undo() and s.snapshot().board[27].status=='neutral'
    assert s.undo() and s.state.active[0]
    assert s.redo() and not s.state.active[0]


def test_intervening_player_can_rescue_a_future_mated_player():
    s=ModeSession(example_rules(players=4,width=6,height=6));e=s._engine
    puzzle(s,[(3,4,0,'K'),(5,3,0,'R'),(0,0,1,'K'),(4,2,1,'N'),(5,5,2,'K'),(1,5,2,'F'),(0,5,3,'K')],side=1)
    victim=replace(s.state,position=replace(s.state.position,side_to_move=2))
    assert e.in_check(victim,2) and not e.legal_actions(victim)
    s.submit(BoardMove(Square(4,2),Square(5,4)))
    assert s.state.current_player==2 and s.state.active[2] and not e.in_check(s.state,2)


def test_four_stalemate_eliminates_but_available_buy_prevents_it():
    s=ModeSession(example_rules(players=4,width=6,height=6))
    pieces=[(0,0,0,'K'),(2,1,1,'K'),(1,2,1,'B'),(5,5,2,'K'),(5,0,3,'K')]
    puzzle(s,pieces)
    assert not s._engine.in_check(s.state,0) and not s.legal_actions()
    ended=s._engine.settle(s.state)
    assert not ended.active[0] and ended.eliminations[-1].reason=='stalemate'
    puzzle(s,pieces,balances=[10,0,0,0])
    assert BuyPiece('F') in s.legal_actions()
    assert s._engine.settle(s.state).active[0]


def test_frozen_anchor_blocks_rays_but_can_be_leapt_over():
    base=example_rules(players=4,width=6,height=6)
    g=PieceType('G','long leap',(LeapAtom((0,3)),))
    s=ModeSession(replace(base,piece_types=base.piece_types+(g,)))
    puzzle(s,[(2,2,0,'K'),(4,3,0,'N'),(0,5,1,'K'),(2,0,1,'R'),(0,2,1,'G'),(5,5,2,'K'),(5,0,3,'K')],side=1,active=[False,True,True,True])
    moves=s.legal_actions()
    assert BoardMove(Square(2,0),Square(2,1)) in moves
    assert BoardMove(Square(2,0),Square(2,2)) not in moves
    assert BoardMove(Square(2,0),Square(2,3)) not in moves
    assert BoardMove(Square(0,2),Square(3,2)) in moves
    assert not s.snapshot().in_check[2]


def test_consecutive_stalemates_skip_turns_and_last_survivor_wins():
    base=example_rules(players=4,width=6,height=6)
    immobile=PieceType('I','immobile royal',(),is_anchor=True)
    s=ModeSession(replace(base,piece_types=base.piece_types+(immobile,)))
    puzzle(s,[(0,0,0,'I'),(0,5,1,'I'),(5,5,2,'K'),(5,0,3,'K')])
    state=s._engine.settle(s.state)
    assert state.active==(False,False,True,True) and state.current_player==2
    s=ModeSession(example_rules(players=4))
    s.resign();s.resign();s.resign()
    assert s.result.winner==3 and s.state.active==(False,False,False,True)
    assert ModeSession.from_record(s.to_record()).state==s.state
    assert s.undo() and not s.result.terminal
    assert s.redo() and s.result.winner==3


def test_unplayable_symmetric_start_is_rejected_instead_of_arbitrary_winner():
    from generic_chess.material_mode import ModeRules,Placement
    immobile=PieceType('I','immobile royal',(),is_anchor=True)
    with pytest.raises(ValueError,match='legal opening action'):
        ModeSession(ModeRules(8,8,4,(immobile,),(Placement('I',Square(3,0)),)))
