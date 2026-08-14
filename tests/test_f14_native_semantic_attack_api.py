from __future__ import annotations

import pytest

from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi
from scripts.audit_f4_runtime_cost import corpus_specs, make_session
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import in_check, is_square_attacked, pack_position


def _native_position(native_rules, state):
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = [
        None
        if piece is None
        else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, int(piece.promoted)]
        for piece in state.position.board
    ]
    hands = []
    for owner in (0, 1):
        counts = [0] * len(ids)
        for type_id, count in state.position.hands[owner].counts:
            counts[ids[type_id]] = count
        hands.append(counts)
    return pack_position(
        native_rules,
        {
            "side": state.position.side_to_move,
            "ply": state.ply_count,
            "root_hash_count": 1,
            "board": board,
            "hands": hands,
            "aux_state": (),
        },
    )


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_f14_standard_shogi_648_attack_queries_and_in_check_match_python():
    semantic = certified_semantic_shogi()
    native_rules = compile_native_semantic_rules(semantic)
    engine = semantic_engine_for(semantic)
    rows = 0
    for spec in corpus_specs():
        if not str(spec["id"]).startswith("semantic_"):
            continue
        state = make_session(spec).state
        position = _native_position(native_rules, state)
        for square in range(semantic.support.board_size ** 2):
            for owner in (0, 1):
                assert is_square_attacked(native_rules, position, square, owner) == engine.is_square_attacked(
                    state.position, square, owner
                ), (spec["id"], square, owner)
                rows += 1
        for side in (0, 1):
            assert in_check(native_rules, position, side) == engine.in_check(state.position, side), (
                spec["id"], side
            )
    assert rows == 648


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_f14_public_api_rejects_invalid_bounds_and_owners():
    semantic = certified_semantic_shogi()
    native_rules = compile_native_semantic_rules(semantic)
    state = make_session(next(spec for spec in corpus_specs() if spec["id"] == "semantic_prefix_0")).state
    position = _native_position(native_rules, state)
    with pytest.raises(ValueError):
        is_square_attacked(native_rules, position, -1, 0)
    with pytest.raises(ValueError):
        is_square_attacked(native_rules, position, 81, 0)
    with pytest.raises(ValueError):
        is_square_attacked(native_rules, position, 0, 2)
    with pytest.raises(ValueError):
        in_check(native_rules, position, -1)
    with pytest.raises(ValueError):
        in_check(native_rules, position, 2)

