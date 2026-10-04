from dataclasses import dataclass
from fractions import Fraction as F
from itertools import permutations, product

import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.core.terminal import TerminalResult, TerminalStatus as T
from scripts.material_leaf_choice import (
    inventory_features, material_score, material_sensitive_pair, one_ply_choice,
)


def test_current_board_and_held_base_do_not_collapse_to_one_weight():
    position = Position(board=(Piece(0, 'P', 'TP', True), Piece(1, 'P', 'P'),
                               Piece(0, 'K', 'K'), None),
                        hands=(Hands((('P', 1),)), Hands((('P', 2),))))
    features = inventory_features(position, {'K'})
    assert features == {('board', 'TP'): 1, ('board', 'P'): -1, ('hand', 'P'): -1}
    weights = {('board', 'TP'): F(1), ('board', 'P'): F(1, 2), ('hand', 'P'): F(1, 4)}
    assert material_score(position, weights, {'K'}, 5) == F(1, 24)
    with pytest.raises(ValueError, match='missing material mode'):
        material_score(position, {('board', 'TP'): 1, ('board', 'P'): 1}, {'K'}, 5)
    with pytest.raises(ValueError, match='bound exceeded'):
        material_score(position, weights, {'K'}, 4)
    with pytest.raises(ValueError, match='rational'):
        material_score(position, {**weights, ('hand', 'P'): .25}, {'K'}, 5)
    balanced = Position((Piece(0, 'P', 'P'), Piece(1, 'P', 'P'), None, None))
    with pytest.raises(ValueError, match='missing'):
        material_score(balanced, {}, {'K'}, 2)


def test_mixed_sign_pair_reversal_and_dominance_boundary():
    a, b = {('board', 'A'): 2}, {('board', 'B'): 1}
    assert material_sensitive_pair(a, b)
    assert 2*F(1) > F(1, 4) and 2*F(1, 4) < F(1)
    assert not material_sensitive_pair(a, {('board', 'A'): 1})
    # A mixed-sign pair can still be globally dominated by a third child.
    c = {('board', 'A'): 2, ('board', 'B'): 1}
    assert not material_sensitive_pair(c, a) and not material_sensitive_pair(c, b)


@dataclass(frozen=True)
class Child:
    material: F
    terminal: TerminalResult = TerminalResult(T.ONGOING)
    unresolved: bool = False


class Game:
    def terminal(self, child):
        if child.unresolved:
            from types import SimpleNamespace
            return SimpleNamespace(is_terminal=True, status='declaration', winner=None, unresolved=True)
        return child.terminal


def select(children, owner=0, **kwargs):
    return one_ply_choice(children, Game(), lambda s: s.material, owner=owner, complete=True, **kwargs)


def test_both_owners_terminal_dominance_and_canonical_ties():
    children = {'z': Child(F(99, 100)), 'b': Child(F(-99, 100)),
                'win': Child(F(0), TerminalResult(T.CHECKMATE, 0)),
                'loss': Child(F(0), TerminalResult(T.CHECKMATE, 1))}
    for items, owner in product(permutations(children.items()), (0, 1)):
        result = select(dict(items), owner)
        assert result['selected'] == ('win' if owner == 0 else 'loss')
    assert select({'z': Child(F(0)), 'a': Child(F(0))})['selected'] == 'a'
    assert select({'z': Child(F(0)), 'a': Child(F(0))}, 1)['selected'] == 'a'
    assert select({'draw': Child(F(0), TerminalResult(T.STALEMATE)),
                   'bad': Child(F(-1, 10))})['selected'] == 'draw'


def test_incomplete_unresolved_censored_and_invalid_choices_never_fall_back():
    children = {'a': Child(F(0)), 'b': Child(F(0), unresolved=True)}
    result = select(children)
    assert not result['complete'] and result['selected'] is None
    assert not one_ply_choice({'a': Child(F(0))}, Game(), lambda s: s.material, owner=0)['complete']
    for status in (T.NO_CONTEST, T.STALEMATE):
        child = Child(F(0), TerminalResult(status))
        result = select({'x': child}, censored_statuses=(T.STALEMATE,))
        assert not result['complete'] and result['selected'] is None
    with pytest.raises(ValueError, match='strictly inside'):
        select({'bad': Child(F(1))})
    with pytest.raises(ValueError, match='owner0/1'):
        select({'a': Child(F(0))}, True)


def test_public_shogi_capture_demotes_into_a_distinct_held_feature():
    from dataclasses import replace
    from generic_chess.core.actions import action_source_square, action_target_square
    from generic_chess.core.coordinates import Square
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action, initial_state
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from scripts.audit_exchange_custody import synthetic_state
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    position = initial_state(compiled).position
    board = [None] * 81
    board[0] = Piece(0, 'K', 'K'); board[80] = Piece(1, 'K', 'K')
    board[40] = Piece(0, 'R', 'R'); board[49] = Piece(1, 'P', 'TP', True)
    root = synthetic_state(compiled, replace(position, board=tuple(board)))
    action = next(a for a in legal_actions(root, compiled)
                  if action_source_square(a) == Square(4, 4) and action_target_square(a) == Square(4, 5))
    child = apply_action(root, action, compiled)
    weights = {('board', 'R'): 1, ('board', 'TP'): 1, ('hand', 'P'): 1}
    assert material_score(root.position, weights, {'K'}, 2) == 0
    assert material_score(child.position, weights, {'K'}, 2) == F(2, 3)
    assert child.position.hands[0].count('P') == 1
    assert len(child.history) == len(root.history) + 1


@pytest.mark.parametrize('owner', (0, 1))
def test_public_complete_shogi_choice_table_includes_win_and_restart(owner):
    import json
    from dataclasses import replace
    from generic_chess.core.actions import action_to_dict
    from generic_chess.core.declarations import DeclarationAssessment
    from generic_chess.core.terminal import terminal_result
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from scripts.public_goal_intervals import PublicGame
    from test_generic_declaration_semantics import _shogi_boundary_state
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    game = PublicGame(compiled)
    for score in (31, 24):
        root = _shogi_boundary_state(compiled, score, owner=owner)
        root = replace(root, terminal_status=terminal_result(root, compiled))
        children = {}
        claim_id = None
        for action in game.actions(root, lambda: None):
            if isinstance(action, DeclarationAssessment):
                key = f'claim:{action.declaration_id}:{action.actor}:{action.outcome}'
                claim_id = key
            else:
                key = json.dumps(action_to_dict(action), sort_keys=True)
            assert key not in children
            children[key] = game.successor(root, action)
        assert claim_id is not None
        result = one_ply_choice(children, game, lambda _: F(0), owner=owner, complete=True)
        if score == 31:
            assert result['complete'] and result['selected'] == claim_id
        else:
            assert not result['complete'] and result['unresolved_choice'] == claim_id
