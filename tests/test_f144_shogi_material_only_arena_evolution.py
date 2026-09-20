from __future__ import annotations

from dataclasses import replace

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset

from scripts.f144_shogi_material_only_arena_evolution import (
    TYPE_IDS,
    GameOutcome,
    MaterialOnlyEvaluator,
    canonicalize_vector,
    gen0_vector,
    mutate_vectors,
)


def _compiled():
    return compile_ruleset_for_execution(build_standard_shogi_ruleset())


def test_f144_vector_is_deterministic_positive_and_gauged():
    values = gen0_vector()
    assert values == gen0_vector()
    assert len(values) == 13
    assert all(value > 0 for value in values)
    assert canonicalize_vector(values) == values
    assert sorted(mutate_vectors(values, 1)) == sorted(mutate_vectors(values, 1))
    assert len(set(mutate_vectors(values, 1))) == 6


def test_f144_material_evaluator_is_pure_and_ordering_is_frozen():
    compiled = _compiled()
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    ordering = {type_id: int(profile.board_value_by_type[type_id]) for type_id in compiled.types_by_id}
    low = MaterialOnlyEvaluator(tuple([1000] * 13), ordering)
    high = MaterialOnlyEvaluator(canonicalize_vector([500, 700, 900, 1100, 1300, 1500, 1700, 1900, 2100, 2300, 2500, 2700, 2900]), ordering)
    from generic_chess.core.transition import initial_state

    state = initial_state(compiled)
    board = list(state.position.board)
    board[next(index for index, piece in enumerate(board) if piece is not None and piece.owner == 1)] = None
    state = replace(state, position=replace(state.position, board=tuple(board)))
    assert low.evaluate(state) != high.evaluate(state)
    for type_id in compiled.types_by_id:
        assert low.type_value(type_id) == high.type_value(type_id) == ordering[type_id]
    moving = next(piece for piece in state.position.board if piece is not None and piece.current_type_id == "P")
    captured = next(piece for piece in state.position.board if piece is not None and piece.current_type_id == "G")
    assert low.capture_order_value(moving, captured) == high.capture_order_value(moving, captured)
    assert set(TYPE_IDS) == set(low._values)


def test_f144_alpha_beta_accepts_override_without_changing_default_contract():
    compiled = _compiled()
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    ordering = {type_id: int(profile.board_value_by_type[type_id]) for type_id in compiled.types_by_id}
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.session.session import GameSession
    from generic_chess.ai.limits import SearchLimits

    player = AlphaBetaPlayer(compiled, use_disk_cache=False, evaluator_override=MaterialOnlyEvaluator(tuple([1000] * 13), ordering))
    decision = player.choose_action(GameSession(compiled), SearchLimits(max_nodes=32, max_depth=1))
    assert decision.action is not None


def test_f144_no_contest_is_non_scoring_not_a_draw():
    outcome = GameOutcome(child_owner=0, winner=None, result="no_contest", plies=500, actions=())
    assert outcome.child_points is None
