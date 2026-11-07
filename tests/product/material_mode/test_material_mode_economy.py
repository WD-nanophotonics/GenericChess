"""Material-mode economy and public-session behavior on real movement kernels."""
from dataclasses import replace
import json
import pytest
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.material_mode import (
    ModeRules, ModeSession, Placement, Square, PieceType, LeapAtom, RayAtom,
    BoardMove, DropMove, BuyPiece, BuyAndDrop, BasicTwoPlayer, example_rules,
)
from generic_chess.material_mode.model import ModeResult
from generic_chess.material_mode.rules import price_units, format_score


def economy(penalty=True):
    base=example_rules(width=6,height=6,purchase_penalty=penalty)
    return ModeSession(replace(base,formation=(Placement('K',Square(1,0)),Placement('R',Square(2,0)))))


def earned(penalty=True):
    s=economy(penalty)
    for a in (BoardMove(Square(2,0),Square(2,5)), BoardMove(Square(4,5),Square(4,4)),
              BoardMove(Square(2,5),Square(3,5)), BoardMove(Square(4,4),Square(5,4))):
        s.submit(a)
    return s


def puzzle(s, pieces, *, side=0, balances=None, hands=None, active=None):
    board=[None]*s.rules.shape.area
    for x,y,owner,tid in pieces:board[y*s.rules.width+x]=Piece(owner,tid,tid)
    state=replace(s.state,position=replace(s.state.position,board=tuple(board),side_to_move=side,
                  hands=tuple(Hands(tuple(sorted(h.items()))) for h in hands) if hands is not None else tuple(Hands.empty() for _ in range(s.rules.players))),
                  balances=tuple(balances or [0]*s.rules.players),active=tuple(active or [True]*s.rules.players),
                  repetition_counts=(),result=ModeResult(),eliminations=(),ply_count=0)
    s._states=[state];s._actions=[];s._cursor=0
    return s


@pytest.mark.parametrize('size,rook,bishop,queen',[(8,'8.4','7.8','16.2'),(20,'22.8','22.2','45')])
def test_exact_prices(size,rook,bishop,queen):
    s=ModeSession(example_rules(width=size,height=size))
    assert s.price('N')=='8' and s.price('F')=='1'
    assert (s.price('R'),s.price('B'),s.price('Q'))==(rook,bishop,queen)
    with pytest.raises(ValueError):s.price('K')


def test_rectangle_dedup_caps_and_angles():
    r=example_rules(width=8,height=6)
    assert ModeSession(r).price('R')=='7.2'
    l=(LeapAtom((1,0)),)*2+(LeapAtom((99,0)),)
    rays=(RayAtom((2,1)),)*2
    p=PieceType('X','mixed',l+rays)
    assert format_score(price_units(p,r),r.score_scale)=='2.8'
    capped=PieceType('C','capped',(RayAtom((1,0),2),RayAtom((-1,0),2)))
    assert format_score(price_units(capped,r),r.score_scale)=='2.4'
    overlap=PieceType('D','separate capabilities',(LeapAtom((1,0)),RayAtom((1,0))))
    assert format_score(price_units(overlap,r),r.score_scale)=='5.2'


@pytest.mark.parametrize('multiplier,expected',[('0.625','8.75'),('0','0'),('1.25','17.5')])
def test_exact_custom_multiplier(multiplier,expected):
    assert ModeSession(example_rules(width=8,height=8,ray_multiplier=multiplier)).price('R')==expected


@pytest.mark.parametrize('multiplier',['-0.1','NaN','Infinity','not-a-number'])
def test_bad_multiplier(multiplier):
    with pytest.raises(ValueError):example_rules(ray_multiplier=multiplier)


def test_capture_buy_wait_drop_and_roundtrip():
    s=earned()
    assert s.snapshot().balances==('6','0')
    assert s.state.position.hands[0].total()==0
    s.submit(BuyPiece('F'))
    assert s.snapshot().balances==('5','0') and s.state.position.hands[0].count('F')==1
    assert s.state.current_player==1
    before=s.state
    with pytest.raises(IllegalActionError):s.submit(DropMove('F',Square(0,5)))
    assert s.state is before
    s.submit(BoardMove(Square(5,4),Square(5,3)))
    before_drop=s.state
    s.submit(DropMove('F',Square(0,5)))  # dead forward-leap landing is permitted
    end=s.state
    assert end.position.hands[0].count('F')==0
    assert s.undo() and s.state==before_drop
    assert s.redo() and s.state==end
    loaded=ModeSession.from_record(json.dumps(s.to_record()))
    assert loaded.state==end and loaded.snapshot()==s.snapshot()
    assert s.undo()
    s.submit(DropMove('F',Square(0,4)))
    assert not s.redo()
    assert ModeSession.from_record(s.to_record()).state==s.state


def test_immediate_buy_drop_is_one_atomic_turn_and_can_check():
    s=earned(False);before=s.state.ply_count
    s.submit(BuyAndDrop('F',Square(5,3)))
    assert s.state.ply_count==before+1 and s.state.current_player==1
    assert s.snapshot().balances[0]=='5' and s.state.position.hands[0].total()==0
    assert s.snapshot().in_check[1]
    assert ModeSession.from_record(s.to_record()).state==s.state


def test_illegal_purchase_atomic_and_no_promotion_or_anchor_drop():
    s=earned();before=s.state
    for action in (BuyPiece('N'),BuyPiece('K'),BuyPiece('missing'),BuyAndDrop('F',Square(0,2)),
                   BoardMove(Square(3,5),Square(3,4),'Q'),DropMove('K',Square(0,2))):
        with pytest.raises(IllegalActionError):s.submit(action)
        assert s.state is before


def test_check_forbids_purchase_but_allows_blocking_drop_or_buy_drop():
    s=ModeSession(example_rules(width=6,height=6,purchase_penalty=False))
    puzzle(s,[(0,0,0,'K'),(5,5,1,'K'),(0,4,1,'R')],balances=[100,0],hands=[{'F':1},{}])
    assert s.snapshot().in_check[0]
    assert BuyPiece('F') not in s.legal_actions()
    assert DropMove('F',Square(0,2)) in s.legal_actions()
    assert BuyAndDrop('F',Square(0,2)) in s.legal_actions()
    assert BuyAndDrop('F',Square(1,2)) not in s.legal_actions()
    assert DropMove('F',Square(0,4)) not in s.legal_actions()


def test_drop_mate_is_allowed():
    s=ModeSession(example_rules(width=4,height=4))
    puzzle(s,[(2,1,0,'K'),(0,3,1,'K')],hands=[{'Q':1},{}])
    # Verify a real mate drop without introducing a Shogi drop-mate restriction.
    winning=[]
    for a in s.legal_actions():
        if isinstance(a,DropMove) and s._engine.after_legal(s.state,a).result.winner==0:winning.append(a)
    assert winning
    s.submit(winning[0]);assert s.result.winner==0 and s.result.reason=='checkmate'


def test_purchase_changes_repetition_identity_and_money_is_exact():
    s=earned();before=s.state;key=s._engine.identity(before)
    s.submit(BuyPiece('F'))
    assert s.state.position.board==before.position.board
    assert s._engine.identity(s.state)!=key
    assert sum(s._engine.material_value(s.state,p) for p in (0,1))==s._engine.material_ceiling
    assert s.rules.score_scale==10


def test_limits_repetition_and_undo_restore_draw():
    s=ModeSession(replace(example_rules(width=6,height=6),formation=(Placement('K',Square(0,0)),),repetition_limit=2))
    for a,b in [((0,0),(0,1)),((5,5),(5,4)),((0,1),(0,0)),((5,4),(5,5))]:s.submit(BoardMove(Square(*a),Square(*b)))
    assert s.result.reason=='repetition' and s.result.drawn_players==(0,1)
    assert s.undo() and not s.result.terminal
    assert s.redo() and s.result.reason=='repetition'
    limited=ModeSession(replace(example_rules(),max_ply=1))
    limited.submit(limited.legal_actions()[0]);assert limited.result.reason=='ply_limit'


def test_readonly_snapshot_and_rule_record():
    s=ModeSession(example_rules(players=4));view=s.snapshot();copy=view.to_dict()
    copy['balances'][0]='999';copy['board'][0]={'status':'changed'}
    assert s.snapshot()==view
    with pytest.raises(Exception):view.balances=('999',)*4
    assert ModeRules.from_dict(s.rules.to_dict())==s.rules
    bad=s.to_record();bad['actions']=[{'kind':'buy','type_id':'Q'}]
    with pytest.raises(IllegalActionError):ModeSession.from_record(bad)


def test_legacy_ordinary_rules_import_and_initial_moves_match():
    from generic_chess.rules.schema import RuleSet
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.session.session import GameSession
    s=economy();r=s.rules;board=s.state.position.board
    legacy=RuleSet(board_size=6,piece_types=r.piece_types,
       initial_position=tuple(tuple(board[y*6:y*6+6]) for y in range(6)),
       drop_allowed={p.type_id:((False,)*36,)*2 for p in r.piece_types if not p.is_anchor},capture_disposition='remove_from_game')
    original=GameSession(compile_ruleset(legacy))
    assert set(s.legal_actions())==set(original.legal_actions())
    imported=ModeSession(ModeRules.from_ruleset(legacy))
    assert imported.state.position.board==s.state.position.board
    assert imported.rules.width==6


def test_mutable_catalog_input_cannot_mutate_compiled_rules():
    base=example_rules()
    vector=[0,1];atoms=[LeapAtom(vector)]
    piece=PieceType('X','mutable caller input',atoms)
    rules=replace(base,piece_types=base.piece_types+(piece,))
    before=rules.to_dict()
    vector[0]=99;atoms.append(RayAtom((1,0)))
    assert rules.to_dict()==before
    assert ModeSession(rules).price('X')=='1'


@pytest.mark.parametrize('coordinate',[True,1.0])
def test_invalid_numeric_action_cannot_break_record_roundtrip(coordinate):
    s=economy();before=s.state
    with pytest.raises(IllegalActionError):
        s.submit(BoardMove(Square(coordinate,0),Square(1,1)))
    assert s.state is before
    assert ModeSession.from_record(s.to_record()).state==before


def test_four_example_uses_requested_square_size():
    assert example_rules(players=4,width=10).shape.width==10
    assert example_rules(players=4,width=10).shape.height==10


def test_fractional_capture_purchase_and_undo_are_exact():
    base=example_rules(width=8,height=8)
    s=ModeSession(replace(base,formation=(Placement('K',Square(1,0)),Placement('R',Square(2,0)))))
    for src,dst in [((2,0),(2,7)),((6,7),(6,6)),((2,7),(5,7)),((6,6),(7,6))]:
        s.submit(BoardMove(Square(*src),Square(*dst)))
    assert s.snapshot().balances[0]=='8.4'
    s.submit(BuyPiece('N'))
    assert s.snapshot().balances[0]=='0.4' and s.state.position.hands[0].count('N')==1
    assert ModeSession.from_record(s.to_record()).state==s.state
    assert s.undo() and s.snapshot().balances[0]=='8.4'


def test_four_seat_mixed_action_record_replays():
    import random
    s=ModeSession(example_rules(players=4));rng=random.Random(71)
    for _ in range(96):
        if s.result.terminal:break
        s.submit(rng.choice(s.legal_actions()))
        assert all(v>=0 for v in s.state.balances)
    assert s.state.ply_count>8
    assert ModeSession.from_record(s.to_record()).state==s.state


def test_two_player_finish_preserves_public_wallet_and_hand():
    s=earned();s.submit(BuyPiece('F'));s.submit(BoardMove(Square(5,4),Square(5,3)))
    before=s.snapshot();s.resign()
    assert s.result.winner==1 and s.result.reason=='resignation'
    assert s.snapshot().balances==before.balances and s.snapshot().hands==before.hands
    assert ModeSession.from_record(s.to_record()).state==s.state


def test_zero_price_still_consumes_a_purchase_turn():
    s=ModeSession(example_rules(ray_multiplier='0'))
    s.submit(BuyPiece('R'))
    assert s.state.ply_count==1 and s.state.current_player==1
    assert s.state.position.hands[0].count('R')==1 and s.snapshot().balances==('0','0')
    assert all(not isinstance(a,BuyAndDrop) for a in s.legal_actions())
