"""Focused F86A admission-foundation tests; no benchmark or Heavy work."""

import pytest

from generic_chess.benchmark.agent_ladder import AgentLadder
from generic_chess.benchmark.game_quality import (
    QualityObservation,
    classify_game_quality,
    measure_game_quality,
    profile_from_observations,
)
from generic_chess.benchmark.minimal_generator import generate_minimal_game
from generic_chess.benchmark.tactical_probe import minimax_node_value, probe_terminal_only
from generic_chess.core.actions import DropMove
from generic_chess.session.session import GameSession


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
    for action in GameSession(first.compiled).legal_actions():
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
    assert payload["paired_game_count"] == 3
    assert payload["played_game_count"] == 6
    assert payload["first_player_score"] is not None
    assert payload["second_player_score"] is not None
    assert payload["swapped_opening_legal_count_equal"] is True
    assert payload["tactical_probe_position_count"] == 1
    assert payload["tactical_probe_nodes"] <= 256
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


def test_terminal_probe_minimax_known_tree_and_cutoff_contract():
    assert minimax_node_value((1.0, 0.0), maximizing=True) == 1.0
    assert minimax_node_value((1.0, 0.0), maximizing=False) == 0.0
    assert minimax_node_value((None, 0.0), maximizing=True) is None
    assert minimax_node_value((None, 1.0), maximizing=False) is None
    game = generate_minimal_game(13, board_size=4, ordinary_count=2)
    result = probe_terminal_only(GameSession(game.compiled), depth=4, node_budget=32)
    assert result.nodes <= 32
    assert result.solved is False or result.value is not None


def test_quality_pathology_controls_are_diagnostic_only():
    neutral = profile_from_observations(
        [QualityObservation((5, 4, 3), 3, "ongoing", 0.5, 0.5)]
    )
    biased = profile_from_observations(
        [QualityObservation((5, 4), 2, "ongoing", 1.0, 0.0)]
    )
    forced = profile_from_observations([QualityObservation((1,) * 20, 20, "ongoing")])
    explosive = profile_from_observations([QualityObservation((200, 180), 2, "ongoing")])
    shallow = profile_from_observations(
        [QualityObservation((3, 2), 2, "checkmate", forced_win=True, solved=True)]
    )
    draw_heavy = profile_from_observations(
        [QualityObservation((2, 2), 2, "repetition") for _ in range(4)]
    )
    assert neutral.classification == "UNRESOLVED"
    assert "SIDE_BIASED" in classify_game_quality(biased, thresholds={})[1]
    assert "FORCED_LINE" in classify_game_quality(forced, thresholds={})[1]
    assert "SEARCH_EXPLOSIVE" in classify_game_quality(explosive, thresholds={})[1]
    assert "TACTICAL_ONLY" in classify_game_quality(shallow, thresholds={})[1]
    assert "DRAW_DOMINATED" in classify_game_quality(draw_heavy, thresholds={})[1]
    assert classify_game_quality(biased)[0] == "UNRESOLVED"
    assert classify_game_quality(biased, thresholds={"side_bias": 0.1})[0] == "SIDE_BIASED"
    assert classify_game_quality(explosive, thresholds={"side_bias": 0.1})[0] == "UNRESOLVED"


def test_agent_ladder_is_an_interface_not_a_strength_claim():
    ladder = AgentLadder()
    assert ladder.names == ("random_legal", "very_shallow", "low_node", "medium_node")
    assert ladder.require("medium_node").node_budget is None
    assert ladder.evaluate_ordered_scores({"random_legal": 0.1}) is None
    paired = {
        (weaker, stronger): score
        for (weaker, stronger), score in zip(
            zip(ladder.names, ladder.names[1:]), (0.7, 0.5, 0.2)
        )
    }
    assert ladder.skill_discrimination(paired) == 0.0
    report = ladder.evaluate_adjacent_matchups(paired)
    assert report["monotonic"] is False
    assert report["stronger_scores"]["random_legal>very_shallow"] == 0.7
    assert report["minimum_adjacent_advantage"] == pytest.approx(-0.3)
    incomplete = {("random_legal", "very_shallow"): 0.7}
    assert ladder.skill_discrimination(incomplete) is None
