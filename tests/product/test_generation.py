"""Generator: determinism, presets, filters, config validation."""

import pytest

from generic_chess.core.coordinates import Square
from generic_chess.generation.config import GenerationError, GeneratorConfig
from generic_chess.generation.generator import generate_game


def test_same_seed_produces_identical_game():
    g1 = generate_game(GeneratorConfig(seed=7))
    g2 = generate_game(GeneratorConfig(seed=7))
    assert g1.compiled_ruleset.ruleset_fingerprint == g2.compiled_ruleset.ruleset_fingerprint
    assert g1.ruleset == g2.ruleset
    assert g1.generation_report == g2.generation_report


def test_different_seeds_produce_different_games():
    g1 = generate_game(GeneratorConfig(seed=1))
    g2 = generate_game(GeneratorConfig(seed=2))
    assert g1.compiled_ruleset.ruleset_fingerprint != g2.compiled_ruleset.ruleset_fingerprint


def test_classic_like_8x8_layout():
    game = generate_game(GeneratorConfig(seed=42, setup_preset="classic_like"))
    compiled = game.compiled_ruleset
    assert compiled.board_size == 8
    assert compiled.initial_entity_count == 4 * 8
    pos = compiled.initial_position
    # P0 anchor at rank 0 near the center (file 3 or 4 on 8x8).
    p0_anchor = [
        Square(f, 0)
        for f in range(8)
        if pos.board[f] is not None
        and pos.board[f].owner == 0
        and compiled.types_by_id[pos.board[f].current_type_id].is_anchor
    ]
    assert p0_anchor == [Square(3, 0)]
    # Player 1 is the strict 180-degree rotation of player 0.
    for f in range(8):
        p0 = pos.board[f]  # rank 0, file f
        p1 = pos.board[7 * 8 + (7 - f)]  # rank 7, rotated file
        if p0 is not None:
            assert p1 is not None
            assert p1.owner == 1
            assert p1.base_type_id == p0.base_type_id
        else:
            assert p1 is None


def test_all_presets_generate_valid_games():
    for preset in ("classic_like", "bilateral_random", "free_random"):
        game = generate_game(GeneratorConfig(seed=11, setup_preset=preset))
        assert all(f.passed for f in game.generation_report.filter_results)
        assert 1 <= game.generation_report.opening_legal_move_count <= 256
        assert game.compiled_ruleset.initial_entity_count == 4 * 8


def test_board_size_3_rejected_for_generator():
    with pytest.raises(GenerationError):
        generate_game(GeneratorConfig(seed=5, board_size=3))


def test_board_size_4_works():
    game = generate_game(GeneratorConfig(seed=5, board_size=4))
    assert game.compiled_ruleset.board_size == 4
    assert game.compiled_ruleset.initial_entity_count == 16  # 2n per side


def test_generation_report_contents():
    game = generate_game(GeneratorConfig(seed=3))
    report = game.generation_report
    assert report.seed == 3
    assert report.preset == "classic_like"
    assert report.board_size == 8
    assert report.generation_attempts >= 1
    assert report.opening_legal_move_count >= 1
    ids = [r.type_id for r in report.piece_type_reports]
    assert "P" in ids
    assert "K" not in ids  # anchors are not reported as ordinary types
    # The front pawn must be promotable in classic_like.
    pawn_report = next(r for r in report.piece_type_reports if r.type_id == "P")
    assert pawn_report.is_promotable


def test_config_dict_accepted():
    game = generate_game({"seed": 9})
    assert game.compiled_ruleset.ruleset_fingerprint


def test_invalid_config_raises():
    with pytest.raises(GenerationError):
        GeneratorConfig(seed=1, board_size=2)
    with pytest.raises(GenerationError):
        GeneratorConfig(seed=1, setup_preset="nope")


def test_require_nonpromotable_type_filter():
    # A config that requires a non-promotable type is satisfiable; the filter
    # must report it passed.
    game = generate_game(GeneratorConfig(seed=21, require_nonpromotable_type=True))
    filters = {f.name: f for f in game.generation_report.filter_results}
    assert filters["promotion_target_present"].passed
