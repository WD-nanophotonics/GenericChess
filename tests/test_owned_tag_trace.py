from fractions import Fraction as F
from types import SimpleNamespace as NS

import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from scripts.owned_tag_trace import trace_tag, validate_tag


def test_ordered_trace_handles_indistinguishable_tokens_without_equality_search(monkeypatch):
    import scripts.owned_tag_trace as module
    monkeypatch.setattr(module, '_resolve_square_ref', lambda ref, *args: ref)
    monkeypatch.setattr(module, '_resolve_type_id', lambda ref, binding: ref)
    metadata = {t: NS(is_anchor=False) for t in ('P', 'TP')}
    metadata['K'] = NS(is_anchor=True)
    def run(before, after, effects, tag, source=0, target=1, promote=None):
        pattern = NS(pattern_id='trace', effects=tuple(effects))
        engine = NS(support=NS(type_metadata=metadata), ir=NS(patterns=(pattern,), aux_slots=()))
        common = dict(geometry_id='geo', source=source, target=target, promotion_target_id=promote)
        binding = NS(pattern=pattern, actor_owner=before.side_to_move, **common)
        action = NS(pattern_id='trace', **common)
        return trace_tag(engine, before, after, action, binding, tag)
    token = Piece(0, 'P', 'P')
    before = Position((token, None, token, None))
    after = Position((None, token, token, None), side_to_move=1)
    tag = {'owner': 0, 'base': 'P', 'board': {0: 1}, 'held': 0, 'lost': 0}
    move = NS(kind='move', from_ref=0, to_ref=1)
    assert run(before, after, (move,), tag)['board'] == {1: 1}
    # The unmoved equal token at square2 must not steal the tracked identity.
    promoted = Position((None, Piece(0, 'P', 'TP', True), token, None), side_to_move=1)
    assert run(before, promoted, (move,), tag, promote='TP')['board'] == {1: 1}
    held_before = Position((None, None, None, None), hands=(Hands((('P', 2),)), Hands.empty()))
    held_after = Position((None, token, None, None), hands=(Hands((('P', 1),)), Hands.empty()), side_to_move=1)
    held_tag = {'owner': 0, 'base': 'P', 'board': {}, 'held': 1, 'lost': 0}
    remove = NS(kind='remove_from_hand', piece_type_ref='P', count=1)
    place = NS(kind='place', piece_type_ref='P', to_ref=1, count=1)
    result = run(held_before, held_after, (remove, place), held_tag, source=None)
    assert result['board'] == {1: F(1, 2)} and result['held'] == F(1, 2)
    for bad in ((place,), (remove,), (NS(kind='remove_from_hand', piece_type_ref='P', count=2), place)):
        with pytest.raises(ValueError, match='paired hand-drop'):
            run(held_before, held_after, bad, held_tag, source=None)
    with pytest.raises(ValueError, match='paired drop base'):
        run(held_before, held_after, (remove, NS(kind='place', piece_type_ref='TP', to_ref=1, count=1)), held_tag, source=None)
    with pytest.raises(ValueError, match='authoritative'):
        run(before, before, (move,), tag)
    with pytest.raises(ValueError, match='unsupported'):
        run(before, before, (NS(kind='create_hidden_token'),), tag)


def test_enemy_capture_ends_ownership_but_self_hand_conversion_preserves_tag(monkeypatch):
    import scripts.owned_tag_trace as module
    monkeypatch.setattr(module, '_resolve_square_ref', lambda ref, *args: ref)
    metadata = {'P': NS(is_anchor=False)}
    pattern = NS(pattern_id='remove', effects=(NS(kind='remove', square_ref=0, disposition='capture_to_hand'),))
    engine = NS(support=NS(type_metadata=metadata), ir=NS(patterns=(pattern,), aux_slots=()))
    for actor in (0, 1):
        before = Position((Piece(0, 'P', 'P'), None, None, None), side_to_move=actor)
        hands = [Hands.empty(), Hands.empty()]; hands[actor] = Hands((('P', 1),))
        after = Position((None, None, None, None), hands=tuple(hands), side_to_move=1-actor)
        common = dict(source=0, target=1, geometry_id='geo', promotion_target_id=None)
        binding = NS(pattern=pattern, actor_owner=actor, **common)
        action = NS(pattern_id='remove', **common)
        tag = {'owner': 0, 'base': 'P', 'board': {0: 1}, 'held': 0, 'lost': 0}
        result = trace_tag(engine, before, after, action, binding, tag)
        assert result['board'] == {}
        assert result['held'] == (1 if actor == 0 else 0)
        assert result['lost'] == (0 if actor == 0 else 1)
        binding.geometry_id = 'wrong'
        with pytest.raises(ValueError, match='exact caller-verified binding'):
            trace_tag(engine, before, after, action, binding, tag)


def test_bad_tag_mass_location_and_owner_fail_closed():
    metadata = {'P': NS(is_anchor=False), 'K': NS(is_anchor=True)}
    position = Position((Piece(0, 'P', 'P'), None, None, None))
    good = {'owner': 0, 'base': 'P', 'board': {0: 1}, 'held': 0, 'lost': 0}
    validate_tag(position, good, metadata)
    for bad in ({**good, 'owner': True}, {**good, 'base': 'K'},
                {**good, 'board': {1: 1}}, {**good, 'board': {0: .5}, 'lost': F(1, 2)},
                {**good, 'board': {0: F(1, 2)}}, {**good, 'board': {}, 'held': 1}):
        with pytest.raises(ValueError):
            validate_tag(position, bad, metadata)
