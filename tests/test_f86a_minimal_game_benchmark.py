"""Focused F86A admission-foundation tests; no benchmark or Heavy work."""

from dataclasses import replace

import pytest

from generic_chess.benchmark.agent_ladder import AgentLadder
from generic_chess.benchmark.game_quality import classify_game_quality, measure_game_quality
from generic_chess.benchmark.minimal_generator import generate_minimal_game
from generic_chess.core.actions import DropMove


def test_minimal_generator_is_deterministic_and_symmetric():
    first = generate_minimal_game(20260911, board_size=5, ordinary_count=3)
    second = generate_minimal_game(20260911, board_size=5, ordinary_count=3)
    assert first.ruleset_fingerprint == second.ruleset_fingerprint
    assert first.ruleset.initial_position == second.ruleset.initial_position
    assert first.ruleset_fingerprint == first.compiled.ruleset_fingerprint

    for owner in (0, 1):
        pieces = [piece for piece in first.compiled.initial_position.board if piece and piece.owner == owner]
        assert sum(piece.current_type_id == "K" for piece in pieces) == 1
        assert 2 <= len(pieces) - 1 <= 5
    for action in __import__("generic_chess.session.session", fromlist=["GameSession"]).GameSession(
        first.compiled
    ).legal_actions():
        assert not isinstance(action, DropMove)
        assert action.promotion_target_id is None


@pytest.mark.parametrize("board_size", (4, 5, 6))
def test_minimal_generator_supports_required_board_sizes(board_size):
    game = generate_minimal_game(31 + board_size, board_size=board_size, ordinary_count=2)
    assert game.board_size == board_size
    assert game.compiled.initial_entity_count == 6
    assert all(not piece.promoted for piece in game.compiled.initial_position.board if piece)
    assert game.ruleset.promotion_allowed == {}
    assert game.ruleset.promotion_forced == {}
    assert all(not any(mask) for masks in game.ruleset.drop_allowed.values() for mask in masks)


def test_quality_profile_is_raw_and_serializable():
    game = generate_minimal_game(7, board_size=4, ordinary_count=2)
    profile = measure_game_quality(game, trajectory_count=3, max_ply=10, seed=9)
    payload = profile.to_dict()
    assert payload["ruleset_fingerprint"] == game.ruleset_fingerprint
    assert payload["opening_legal_actions"] >= 1
    assert payload["trajectory_count"] == 3
    assert set(payload["classification_reasons"]) <= {
        "QUALIFIED_GENERAL",
        "SIDE_BIASED",
        "TRIVIAL_OR_SHALLOW_SOLVED",
        "FORCED_LINE",
        "SEARCH_EXPLOSIVE",
        "DRAW_DOMINATED",
        "TACTICAL_ONLY",
        "INSUFFICIENT_SKILL_DISCRIMINATION",
        "UNRESOLVED",
    }


def test_quality_pathology_controls_are_diagnostic_only():
    base = measure_game_quality(
        generate_minimal_game(8, board_size=4, ordinary_count=2),
        trajectory_count=2,
        max_ply=6,
    )
    assert classify_game_quality(replace(base, side_bias_magnitude=0.5))[0] == "SIDE_BIASED"
    assert classify_game_quality(replace(base, branching_collapse_fraction=0.9))[0] == "FORCED_LINE"
    assert classify_game_quality(replace(base, p90_game_branching=120))[0] == "SEARCH_EXPLOSIVE"
    assert classify_game_quality(replace(base, shallow_forced_win_rate=0.9))[0] == "TACTICAL_ONLY"


def test_agent_ladder_is_an_interface_not_a_strength_claim():
    ladder = AgentLadder()
    assert ladder.names == ("random_legal", "very_shallow", "low_node", "medium_node")
    assert ladder.require("medium_node").node_budget is None
    assert ladder.skill_discrimination({"random_legal": 0.1}) is None
    assert ladder.skill_discrimination({name: float(i) for i, name in enumerate(ladder.names)}) == 3.0
