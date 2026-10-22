"""A real rule-clock terminal takes precedence over the measurement horizon."""

import pytest

from generic_chess.benchmark.game_quality import measure_game_quality
from generic_chess.benchmark.minimal_generator import MinimalGeneratedGame
from generic_chess.benchmark.qualification import (
    semantic_search_games,
    semantic_tape_games,
    semantic_termination_control_games,
)
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import RuleSet


def _clock_game(rule_limit):
    board = [[None] * 4 for _ in range(4)]
    board[0][0] = Piece(0, "K", "K")
    board[3][3] = Piece(1, "K", "K")
    rules = RuleSet(
        board_size=4,
        piece_types=(PieceType(
            type_id="K", name="Anchor", is_anchor=True,
            movement_atoms=tuple(LeapAtom(offset) for offset in
                                 ((1, 0), (0, 1), (1, 1), (-1, 1))),
        ),),
        initial_position=tuple(map(tuple, board)),
        repetition_limit=4,
        max_ply=rule_limit,
    )
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    return MinimalGeneratedGame(0, 4, 0, rules, compiled)


@pytest.mark.parametrize("caller", ("tape", "search", "termination"))
@pytest.mark.parametrize("rule_limit,caller_limit,expected", (
    (1, 1, "max_ply"),  # exact collision
    (1, 2, "max_ply"),  # terminal strictly before caller horizon
    (2, 1, "CENSORED"),  # actual game still ongoing
))
def test_rule_clock_terminal_is_not_caller_censorship(
    caller, rule_limit, caller_limit, expected,
):
    game = _clock_game(rule_limit)
    if caller == "tape":
        result = semantic_tape_games(
            game.compiled, policy_id="canonical_common_tape_random",
            pair_count=1, max_ply=caller_limit, seed=9,
        )
    elif caller == "search":
        result = semantic_search_games(
            game.compiled, pair_count=1, max_ply=caller_limit,
            node_cap=64, search_depth=1,
        )
    else:
        policy = "deterministic_complete_root_material_search"
        result = semantic_termination_control_games(
            game.compiled, policy_ids=(policy,), pair_count=1,
            max_ply=caller_limit, root_node_cap_per_ply=64,
        )["policies"][policy]
    assert result["terminal_counts"] == {expected: 2}
    for row in result["records"]:
        assert row["plies"] == 1
        assert row["terminal_status"] == expected
        assert row["completion"] == ("CENSORED" if expected == "CENSORED" else "TERMINAL")
        assert row["winner"] is None
        if "terminal_utility" in row:
            assert row["terminal_utility"] == (None if expected == "CENSORED" else 0.0)
        if "first_player_score" in row:
            assert row["first_player_score"] == (None if expected == "CENSORED" else 0.5)
    raw = []
    quality = measure_game_quality(
        game, trajectory_count=1, max_ply=caller_limit, seed=9, raw_games=raw,
    )
    assert quality.terminal_distribution == {expected: 2}
    assert quality.rule_draw_fraction == (0.0 if expected == "CENSORED" else 1.0)
    assert all(row["terminal_status"] == expected for row in raw)


def test_incomplete_root_remains_search_budget_censored():
    game = _clock_game(1)
    policy = "deterministic_complete_root_material_search"
    result = semantic_termination_control_games(
        game.compiled, policy_ids=(policy,), pair_count=1, max_ply=1,
        root_node_cap_per_ply=0,
    )["policies"][policy]
    assert result["terminal_counts"] == {"SEARCH_BUDGET_CENSORED": 2}
    assert all(row["plies"] == 0 and row["terminal_utility"] is None
               for row in result["records"])
