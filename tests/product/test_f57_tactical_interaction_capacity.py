import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.learning.features import (
    TACTICAL_INTERACTION_FEATURE_NAMES,
    SPATIAL_CELL_COUNT,
    spatial_cell,
    tactical_interaction_features,
)
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


pytestmark = pytest.mark.skipif(not native_available(), reason="native extension unavailable")


def _western():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(compiled)
    return compiled, native


def _position(compiled, entries):
    board = [None] * (compiled.board_size * compiled.board_size)
    for file, rank, piece in entries:
        board[rank * compiled.board_size + file] = piece
    return Position(
        board=tuple(board),
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        aux_state=(),
    )


def test_f57_tactical_features_use_semantic_attack_contract_and_owner_axis():
    compiled, _native = _western()
    type_ids = tuple(sorted(compiled.support.type_metadata))
    position = _position(compiled, (
        (7, 0, Piece(0, "K", "K")),
        (7, 7, Piece(1, "K", "K")),
        (0, 0, Piece(0, "R", "R")),
        (0, 1, Piece(1, "P", "P")),
    ))
    features = tactical_interaction_features(position, compiled, type_ids)
    assert set(TACTICAL_INTERACTION_FEATURE_NAMES) == {
        key.split(":", 1)[0] for key in features
    }
    assert features["attacked_by_type:1:P"] == 1
    assert features["hanging_by_type:1:P"] == 1
    assert features["defended_by_type:1:P"] == 0
    assert all(value >= 0 for value in features.values())


def test_f57_relation_witness_preserves_material_and_coarse_occupancy():
    compiled, _native = _western()
    type_ids = tuple(sorted(compiled.support.type_metadata))
    common = (
        (7, 0, Piece(0, "K", "K")),
        (7, 7, Piece(1, "K", "K")),
        (0, 0, Piece(0, "R", "R")),
    )
    attacked = _position(compiled, common + ((0, 1, Piece(1, "P", "P")),))
    quiet = _position(compiled, common + ((1, 1, Piece(1, "P", "P")),))
    first = tactical_interaction_features(attacked, compiled, type_ids)
    second = tactical_interaction_features(quiet, compiled, type_ids)
    assert sum(piece is not None for piece in attacked.board) == sum(
        piece is not None for piece in quiet.board
    )
    attacked_index = 1 * compiled.board_size + 0
    quiet_index = 1 * compiled.board_size + 1
    assert spatial_cell(attacked_index, compiled.board_size) == spatial_cell(
        quiet_index, compiled.board_size
    )
    assert first["attacked_by_type:1:P"] == 1
    assert second["attacked_by_type:1:P"] == 0
    assert first != second


def test_f57_generated_semantic_rules_fail_closed_only_without_semantic_engine():
    import sys
    sys.path.insert(0, "tests")
    from phase19c1_native_semantic_fixtures import semantic_corpus

    compiled = dict(semantic_corpus())["weird_0"]
    type_ids = tuple(sorted(compiled.support.type_metadata))
    position = GameSession(compiled).state.position
    features = tactical_interaction_features(position, compiled, type_ids)
    assert len(features) == 3 * 2 * len(type_ids)
    with pytest.raises(TypeError, match="compiled semantic rules"):
        tactical_interaction_features(
            compiled._legacy_compiled.initial_position,
            compiled._legacy_compiled,
            type_ids,
        )


def test_f57_direct_spatial_binding_accepts_both_owner_axes():
    compiled, native = _western()
    type_count = len(native.type_ids)
    board = (0,) * type_count
    hand = (0,) * type_count
    spatial = (0,) * (2 * type_count * SPATIAL_CELL_COUNT)
    control = (0,) * SPATIAL_CELL_COUNT
    engine = SemanticSearchEngine(
        compiled,
        native,
        board_values=board,
        hand_values=hand,
        dynamic_values=(0, 0, 0),
        spatial_occupancy_values=spatial,
        localized_control_values=control,
        evaluator_scale=1,
        tt_megabytes=0,
    )
    assert len(engine.native_evaluator_values["spatial_occupancy"]) == 2 * type_count * 9
    engine.bind_evaluator(
        board, hand, (0, 0, 0), spatial, control, evaluator_scale=1
    )
