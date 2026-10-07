import hashlib
import json
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import pytest
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from scripts.chess_approx_static_inventory import ChessApproxStaticInventory, SCALE
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.native_chess_contact_intervals import _ongoing_features
from scripts.research_state_replay import read_game_state

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT/'docs/research/data'


def record():
    return json.loads((DATA/'chess_approx_static_search_20261006.json').read_text())


def unit(): return ChessApproxStaticInventory({m: F(1) for m in 'PNBRQ'})




def test_full_context_rights_ep_preserved_without_relaxing_strict_adapter():
    r = record(); root = read_game_state(r['opening_root'])
    assert root.position.aux_state == ()
    assert unit().evaluate(root) == 0
    with pytest.raises(ValueError): _ongoing_features(root.position)
    ep = [row for row in r['opening_source'] if row['ep_target'] is not None]
    assert len(ep) == 8
    assert all(all(value == 1 for value in row['effective_rights'].values()) for row in r['opening_source'])
    assert {tuple(row['ep_target']) for row in ep} == {(x, 2) for x in range(8)}
    for stored in r['opening_children'].values():
        state = read_game_state(stored)
        assert unit().evaluate(state) == 0
        assert state.ply_count == 1 and len(state.history) == 2


def test_side_to_move_sign_and_full_stock_quantization_bounds():
    r = record(); small = json.loads((DATA/'chess_adjudicated_exchange_20261006.json').read_text())
    state = read_game_state(next(iter(small['children'].values())))
    eval = unit()
    assert eval.evaluate(state) == -eval.evaluate(replace(state, position=replace(state.position, side_to_move=1-state.position.side_to_move)))
    for law in ('geometric_half', 'linear_mixture'):
        weights = {m: lo for (_, m), (lo, hi) in exact_chess_contact_intervals(law).items()}
        evaluator = ChessApproxStaticInventory(weights)
        assert all(abs(F(evaluator.weights[m], SCALE)-w) <= F(1, 2*SCALE) for m, w in weights.items())
        for row in r['searches']:
            if row['law'] != law: continue
            for key, integer_value in row['child_scores'].items():
                saved = r['opening_children'][key] if row['scope'] == 'initial_full_rights' else small['children'][key]
                exact = sum(weights[p['current_type_id']]*(1 if p['owner'] == 0 else -1)
                            for p in saved['position']['board'] if p and p['current_type_id'] != 'K')
                assert abs(F(integer_value)-SCALE*exact) <= 15


def test_unsupported_hand_origin_missing_king_and_overstock_rejected():
    root = read_game_state(record()['opening_root']); evaluator = unit()
    with pytest.raises(ValueError): evaluator.evaluate(replace(root, position=replace(root.position, hands=(Hands((('P', 1),)), Hands.empty()))))
    board = list(root.position.board); board[0] = Piece(0, 'N', 'R')
    with pytest.raises(ValueError): evaluator.evaluate(replace(root, position=replace(root.position, board=tuple(board))))
    board = list(root.position.board); board[4] = None
    with pytest.raises(ValueError): evaluator.evaluate(replace(root, position=replace(root.position, board=tuple(board))))
    board = list(root.position.board); board[20] = Piece(0, 'P', 'P')
    with pytest.raises(ValueError): evaluator.evaluate(replace(root, position=replace(root.position, board=tuple(board))))


@pytest.mark.parametrize('weights', [{'P': 1}, {m: 1.0 for m in 'PNBRQ'}, {m: True for m in 'PNBRQ'},
                                    {m: F(2) for m in 'PNBRQ'}])
def test_bad_weights_rejected(weights):
    with pytest.raises(ValueError): ChessApproxStaticInventory(weights)
