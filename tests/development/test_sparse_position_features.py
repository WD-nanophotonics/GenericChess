"""Semantic research representation; live compact model layout stays separate."""
from dataclasses import replace

import numpy as np
import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.learning.nonlinear import semantic_state_features
from generic_chess.rules.compiler import compile_semantic_ruleset, compile_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import cannon_ruleset, en_passant_ruleset, weird_rulesets
from scripts.position_features import SparsePositionEncoder


def dense_reference(position, compiled, dynamic):
    """Independent channel construction, without using encoder offsets/indices."""
    types = tuple(sorted(compiled.support.type_metadata))
    area = len(position.board)
    current = [float(p is not None and p.owner == owner and p.current_type_id == tid)
               for owner in (0, 1) for tid in types for p in position.board]
    hand = [float(position.hands[owner].count(tid)) for owner in (0, 1) for tid in types]
    side = [float(position.side_to_move == owner) for owner in (0, 1)]
    aux, stored = [], dict(position.aux_state)
    for slot in compiled.ir.aux_slots:
        for owner in ((-1,) if slot.scope == "global" else (0, 1)):
            value = stored.get((slot.slot_id, owner), slot.initial)
            if slot.value_kind == "bool":
                aux.append(float(value or 0))
            elif value is None:
                aux.extend((0., 0., 0.))
            else:
                aux.extend((1., value[0] / position.board_shape.width,
                            value[1] / position.board_shape.height))
    base = [float(p is not None and p.owner == owner and p.base_type_id == tid)
            for owner in (0, 1) for tid in types for p in position.board]
    promoted = [float(p is not None and p.owner == owner and p.promoted)
                for owner in (0, 1) for p in position.board]
    assert len(current) == len(base) == 2 * len(types) * area
    return np.asarray(current + hand + side + list(dynamic) + aux + base + promoted)


@pytest.mark.parametrize("ruleset", [build_western_chess_ruleset(), *weird_rulesets()])
def test_real_semantic_states_match_dense_oracle_and_old_square_prefix(ruleset):
    compiled = compile_semantic_ruleset(ruleset)
    session = GameSession(compiled)
    encoder = SparsePositionEncoder(compiled)
    before = session.state
    for _ in range(4):
        position = session.state.position
        dynamic = (-2.5, 0., 1.75)
        indices, values = encoder.encode(position, dynamic)
        assert len(set(indices)) == len(indices)
        assert np.all(values != 0)
        result = encoder.dense(position, dynamic)
        assert np.array_equal(result, dense_reference(position, compiled, dynamic))
        assert np.array_equal(result[:encoder.base_offset],
                              semantic_state_features(position, compiled, dynamic))
        if session.state.terminal_status.is_terminal or not session.legal_actions():
            break
        session.submit(session.legal_actions()[0])
    assert before.position == GameSession(compiled).state.position


def test_base_and_promotion_channels_separate_old_encoder_aliases():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    position = GameSession(compiled).state.position
    board = list(position.board)
    square = next(i for i, piece in enumerate(board) if piece is None)
    board[square] = Piece(0, "P", "Q", True)
    first = replace(position, board=tuple(board), hands=(Hands((("P", 2),)), Hands.empty()))
    board[square] = Piece(0, "Q", "Q", True)
    second = replace(first, board=tuple(board))
    board[square] = replace(board[square], promoted=False)
    third = replace(second, board=tuple(board))
    encoder = SparsePositionEncoder(compiled)
    assert np.array_equal(semantic_state_features(first, compiled, (0, 0, 0)),
                          semantic_state_features(second, compiled, (0, 0, 0)))
    assert not np.array_equal(encoder.dense(first), encoder.dense(second))
    assert not np.array_equal(encoder.dense(second), encoder.dense(third))
    assert np.array_equal(encoder.dense(first), dense_reference(first, compiled, (0, 0, 0)))


def test_aux_logical_default_and_explicit_none_on_rectangle():
    ruleset = en_passant_ruleset()
    width, height = 7, 5
    board = [[None] * width for _ in range(height)]
    board[0][0], board[-1][-1] = Piece(0, "K", "K"), Piece(1, "K", "K")
    ruleset = replace(ruleset, board_size=None, board_width=width, board_height=height,
        initial_position=tuple(map(tuple, board)),
        drop_allowed={tid: ((False,) * (width * height),) * 2
                      for tid in ruleset.drop_allowed},
        semantic_actions=tuple(replace(action, aux_state=tuple(
            replace(slot, initial=(2, 1)) if slot.name == "ep_token" else slot
            for slot in action.aux_state)) for action in ruleset.semantic_actions))
    compiled = compile_semantic_ruleset(ruleset)
    position = GameSession(compiled).state.position
    encoder = SparsePositionEncoder(compiled)
    slot = next(slot for slot in compiled.ir.aux_slots if slot.value_kind == "square_or_none")
    missing = replace(position, aux_state=())
    explicit = replace(position, aux_state=(((slot.slot_id, -1), (2, 1)),))
    cleared = replace(position, aux_state=(((slot.slot_id, -1), None),))
    assert np.array_equal(encoder.dense(missing), encoder.dense(explicit))
    assert not np.array_equal(encoder.dense(missing), encoder.dense(cleared))
    assert np.array_equal(encoder.dense(missing), dense_reference(missing, compiled, (0, 0, 0)))
    offset = next(offset for offset, key, _, _ in encoder.aux_slots if key == (slot.slot_id, -1))
    assert np.allclose(encoder.dense(missing)[offset:offset+3], (1, 2/7, 1/5))
    with pytest.raises(ValueError, match="rectangular"):
        semantic_state_features(missing, compiled, (0, 0, 0))


def test_legacy_wrong_rule_and_wrong_dynamic_contract_are_not_silent():
    with pytest.raises(TypeError, match="semantic"):
        SparsePositionEncoder(compile_ruleset(replace(cannon_ruleset(), semantic_actions=())))
    compiled = compile_semantic_ruleset(cannon_ruleset())
    encoder = SparsePositionEncoder(compiled)
    position = GameSession(compiled).state.position
    with pytest.raises(ValueError, match="layout"):
        encoder.encode(replace(position, ruleset_fingerprint="different"))
    with pytest.raises(ValueError, match="three"):
        encoder.encode(position, (0, 0))
