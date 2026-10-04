from dataclasses import replace
from fractions import Fraction as F
from random import Random

import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.resource_mode_context import owned_mode_mass, resource_ledger
from scripts.sample_resource_modes import sample_resource_mode
from scripts.resource_mode_structure import ongoing_resource_root


@pytest.fixture(scope='module')
def games():
    return {name: compile_ruleset_for_execution(build()) for name, build in
            (('chess', build_western_chess_ruleset), ('shogi', build_standard_shogi_ruleset))}


def edit(position, square, piece):
    board = list(position.board); board[square] = piece
    return replace(position, board=tuple(board))


def test_chess_promotion_preserves_origin_and_substitution_does_not(games):
    compiled = games['chess']; root = initial_state(compiled).position
    pawn = next(i for i, p in enumerate(root.board) if p and p.owner == 0 and p.base_type_id == 'P')
    promoted = edit(root, pawn, Piece(0, 'P', 'Q', True))
    assert resource_ledger(compiled, promoted, 'chess', full_chess=True)['graveyard'] == {}
    with pytest.raises(ValueError, match='increased'):
        resource_ledger(compiled, edit(root, pawn, Piece(0, 'Q', 'Q')), 'chess')
    captured = edit(promoted, pawn, None)
    assert resource_ledger(compiled, captured, 'chess')['graveyard'] == {(0, 'P'): 1}
    with pytest.raises(ValueError, match='full Chess'):
        resource_ledger(compiled, captured, 'chess', full_chess=True)
    for bad in (Piece(0, 'P', 'Q'), Piece(0, 'R', 'Q', True), Piece(0, 'K', 'Q', True)):
        with pytest.raises(ValueError):
            resource_ledger(compiled, edit(root, pawn, bad), 'chess')


def test_shogi_capture_custody_and_hands_conserve_global_not_owner_counts(games):
    compiled = games['shogi']; root = initial_state(compiled).position
    pawn = next(i for i, p in enumerate(root.board) if p and p.owner == 1 and p.base_type_id == 'P')
    captured = replace(edit(root, pawn, None), hands=(Hands((('P', 1),)), Hands.empty()))
    assert resource_ledger(compiled, captured, 'shogi')['inventory']['P'] == 18
    for hands in ((Hands.empty(), Hands.empty()), (Hands((('P', 2),)), Hands.empty()),
                  (Hands((('TP', 1),)), Hands.empty()), (Hands((('K', 1),)), Hands.empty()),
                  (Hands((('P', 0),)), Hands.empty()), (Hands((('P', 1), ('P', 1))), Hands.empty())):
        with pytest.raises(ValueError):
            resource_ledger(compiled, replace(captured, hands=hands), 'shogi')
    king = next(i for i, p in enumerate(root.board) if p and p.owner == 0 and p.base_type_id == 'K')
    with pytest.raises(ValueError, match='anchors'):
        resource_ledger(compiled, edit(root, king, None), 'shogi')


def test_refined_modes_keep_base_and_fractional_hand_identity(games):
    compiled = games['chess']; root = initial_state(compiled).position
    pawn = next(i for i, p in enumerate(root.board) if p and p.owner == 0 and p.base_type_id == 'P')
    queen = next(i for i, p in enumerate(root.board) if p and p.owner == 0 and p.base_type_id == 'Q')
    promoted = edit(root, pawn, Piece(0, 'P', 'Q', True))
    tag = {'owner': 0, 'base': 'P', 'board': {pawn: 1}, 'held': 0, 'lost': 0}
    assert owned_mode_mass(promoted, tag, compiled.support.type_metadata) == {('board', 'P', 'Q'): 1}
    native = {**tag, 'base': 'Q', 'board': {queen: 1}}
    assert owned_mode_mass(promoted, native, compiled.support.type_metadata) == {('board', 'Q', 'Q'): 1}
    assert owned_mode_mass(promoted, tag, compiled.support.type_metadata, continuation=False) == {}
    compiled = games['shogi']; root = initial_state(compiled).position
    pawn = next(i for i, p in enumerate(root.board) if p and p.owner == 0 and p.base_type_id == 'P')
    mixed = replace(root, hands=(Hands((('P', 1),)), Hands.empty()))
    tag = {'owner': 0, 'base': 'P', 'board': {pawn: F(1, 3)}, 'held': F(2, 3), 'lost': 0}
    assert owned_mode_mass(mixed, tag, compiled.support.type_metadata) == {
        ('board', 'P', 'P'): F(1, 3), ('hand', 'P'): F(2, 3)}
    with pytest.raises(ValueError, match='bool continuation'):
        owned_mode_mass(mixed, tag, compiled.support.type_metadata, continuation=1)


def test_proposal_conservation_and_tag_identity_before_semantic_rejection(games):
    # Construction controls only: no acceptance rate, service or pilot labels.
    for game, modes in (('chess', (('board', 'P', 'P'), ('board', 'P', 'Q'), ('board', 'Q', 'Q'))),
                        ('shogi', (('board', 'P', 'P'), ('board', 'P', 'TP'), ('hand', 'P')))):
        compiled = games[game]
        for mode in modes:
            observed = 0
            for seed in range(32):
                position, tag, reason = sample_resource_mode(compiled, game, mode, Random(seed))
                if reason:
                    assert game == 'shogi' and reason == 'pawn_collision'
                    assert position is None and tag is None
                    continue
                observed += 1
                assert resource_ledger(compiled, position, game, full_chess=True)['graveyard'] == {}
                assert owned_mode_mass(position, tag, compiled.support.type_metadata) == {mode: 1}
                assert sum(p is not None for p in position.board) + sum(h.total() for h in position.hands) == (32 if game == 'chess' else 40)
                pawns = [(i, p) for i, p in enumerate(position.board) if p and p.current_type_id == 'P']
                if game == 'chess':
                    assert all(i//8 not in (0, 7) for i, _ in pawns)
                else:
                    groups = [(p.owner, i % 9) for i, p in pawns]
                    assert len(groups) == len(set(groups))
                    assert all(i//9 != (8 if p.owner == 0 else 0) for i, p in pawns)
            assert observed > 0
    for game, mode in (('chess', ('hand', 'P')), ('chess', ('board', 'R', 'Q')),
                       ('shogi', ('board', 'K', 'K')), ('shogi', ('hand', 'TP'))):
        with pytest.raises(ValueError):
            sample_resource_mode(games[game], game, mode, Random(0))


def test_semantic_chess_pawn_is_not_a_dead_atom_table_mode(games):
    from scripts.audit_resource_mode_feasibility import ongoing_root as old_guard
    compiled = games['chess']; root = initial_state(compiled).position
    assert all(not row for owner in compiled.support.empty_mobility['P'] for row in owner)
    assert old_guard(compiled, root, 'chess', lambda: None)[1] == 'dead_board_mode'
    state, reason = ongoing_resource_root(compiled, root, 'chess', lambda: None)
    assert reason is None and state.position == root and len(state.history) == 1
    board = list(root.board)
    board[0] = Piece(0, 'P', 'P')
    assert ongoing_resource_root(compiled, replace(root, board=tuple(board)), 'chess', lambda: None)[1] == 'pawn_terminal_rank'
    compiled = games['shogi']; root = initial_state(compiled).position
    board = list(root.board); board[8*9] = Piece(0, 'P', 'P')
    assert ongoing_resource_root(compiled, replace(root, board=tuple(board)), 'shogi', lambda: None)[1] == 'dead_board_mode'
