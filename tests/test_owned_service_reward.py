from fractions import Fraction as F
from types import SimpleNamespace as NS

import pytest

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from scripts.owned_service_reward import binding_reward, continuation_prediction, public_child_reward


def test_off_target_capture_reward_and_secondary_actor_are_independent(monkeypatch):
    import scripts.owned_service_reward as module
    monkeypatch.setattr(module, '_resolve_square_ref', lambda ref, *args: ref)
    metadata = {t: NS(is_anchor=t == 'K') for t in ('P', 'R', 'K')}
    before = Position((Piece(0, 'P', 'P'), Piece(1, 'P', 'P'), None, None))
    after = Position((None, None, Piece(0, 'P', 'P'), None), side_to_move=1)
    effect = NS(kind='remove', square_ref=1, disposition='remove_from_game')
    pattern = NS(pattern_id='ep', effects=(effect, NS(kind='move')))
    engine = NS(ir=NS(patterns=(pattern,), aux_slots=()), support=NS(type_metadata=metadata))
    common = dict(source=0, target=2, geometry_id='g', promotion_target_id=None)
    runtime = NS(pattern_id='ep', **common)
    binding = NS(pattern=pattern, actor_owner=0, **common)
    tag = {'owner': 0, 'base': 'P', 'board': {0: F(1, 2)}, 'held': 0, 'lost': F(1, 2)}
    action = BoardMove(Square(0, 0), Square(0, 1))
    assert binding_reward(engine, before, runtime, binding, tag) == F(1, 2)
    assert public_child_reward(before, after, action, tag, metadata) == F(1, 2)
    # Terminal status never changes the current earned reward; caller handles
    # continuation eligibility separately. A secondary castling tag is not actor.
    unrelated = Position((Piece(0, 'K', 'K'), Piece(0, 'R', 'R'), None, None))
    castle_tag = {'owner': 0, 'base': 'R', 'board': {1: 1}, 'held': 0, 'lost': 0}
    assert public_child_reward(unrelated, unrelated, action, castle_tag, metadata) == 0
    pattern.effects = (NS(kind='move'), effect)
    with pytest.raises(ValueError, match='pre-move'):
        binding_reward(engine, before, runtime, binding, tag)
    pattern.effects = (effect, effect)
    with pytest.raises(ValueError, match='single-victim'):
        binding_reward(engine, before, runtime, binding, tag)


def test_hand_drop_has_no_immediate_capture_credit():
    metadata = {'P': NS(is_anchor=False)}
    before = Position((None, Piece(1, 'P', 'P'), None, None), hands=(Hands((('P', 1),)), Hands.empty()))
    after = Position((Piece(0, 'P', 'P'), Piece(1, 'P', 'P'), None, None), side_to_move=1)
    tag = {'owner': 0, 'base': 'P', 'board': {}, 'held': 1, 'lost': 0}
    assert public_child_reward(before, after, DropMove('P', Square(0, 0)), tag, metadata) == 0


def test_unknown_modes_and_endpoints_are_not_fabricated_zero_rewards():
    mass = {('board', 'P', 'Q'): F(1, 3), ('board', 'P', 'N'): F(1, 2)}
    assert continuation_prediction(mass, {('board', 'P', 'Q'): F(1, 4)}) == (F(1, 12), F(7, 12))
    assert continuation_prediction({}, {}) == (0, 0)
    assert continuation_prediction({'A': F(1, 2)}, {'A': 0}) == (0, 0)
    for q, g in (({'A': .5}, {}), ({'A': 1, 'B': 1}, {}), ({}, {'A': F(3, 2)})):
        with pytest.raises(ValueError):
            continuation_prediction(q, g)
