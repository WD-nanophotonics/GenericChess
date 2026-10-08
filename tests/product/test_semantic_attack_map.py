"""Bulk attack maps retain scalar Core and independent Native authority."""
import pytest

from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import NativeSemanticPositionMirror
from generic_chess.native.semantic import attacked_squares, is_square_attacked
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import (
    cannon_ruleset, castling_ruleset, en_passant_ruleset, nifu_ruleset,
    uchifuzume_ruleset, weird_rulesets,
)

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator


@pytest.mark.parametrize("definition", [
    cannon_ruleset(), castling_ruleset(), en_passant_ruleset(), nifu_ruleset(),
    uchifuzume_ruleset(), *weird_rulesets(),
    build_western_chess_ruleset(), build_standard_shogi_ruleset(),
], ids=["cannon", "castling", "en-passant", "nifu", "uchifuzume",
        "weird-ray", "zone-drop", "temporary-right", "compound", "postcondition",
        "western", "shogi"])
def test_bulk_map_matches_every_scalar_square_through_actual_play(definition):
    compiled = compile_ruleset_for_execution(definition)
    engine = semantic_engine_for(compiled)
    session = GameSession(compiled)
    native_rules = compile_native_semantic_rules(compiled) if native_available() else None
    for ply in range(4):
        position = session.state.position
        native = NativeSemanticPositionMirror.from_state(
            compiled, native_rules, session.state, history_certified=True
        ) if native_rules is not None else None
        for owner in (0, 1):
            bulk = engine.attacked_squares(position, owner)
            assert bulk == frozenset(i for i in range(len(position.board))
                                    if engine.is_square_attacked(position, i, owner))
            if native is not None:
                assert bulk == attacked_squares(native_rules, native.position, owner)
                assert bulk == frozenset(i for i in range(len(position.board))
                    if is_square_attacked(native_rules, native.position, i, owner))
        if session.state.terminal_status.is_terminal or ply == 3:
            break
        session.submit(sorted(session.legal_actions(), key=repr)[0])


def test_bulk_map_propagates_cooperative_cancellation():
    compiled = compile_ruleset_for_execution(cannon_ruleset())
    session = GameSession(compiled)
    def cancel():
        raise InterruptedError("caller stopped attack traversal")
    with pytest.raises(InterruptedError, match="caller stopped"):
        semantic_engine_for(compiled).attacked_squares(session.state.position, 0, cancel)


@pytest.mark.skipif(not native_available(), reason="Native extension unavailable")
@pytest.mark.parametrize("definition", [cannon_ruleset(), en_passant_ruleset(),
                                      build_western_chess_ruleset(), build_standard_shogi_ruleset()])
def test_semantic_evaluator_backends_match_through_actual_history(definition):
    compiled = compile_ruleset_for_execution(definition)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    core = SemanticAttackEvaluator(compiled, profile, config)
    native = SemanticAttackEvaluator(compiled, profile, config, backend="native")
    session = GameSession(compiled)
    for _ in range(6):
        assert core.evaluate(session.state) == native.evaluate(session.state)
        if session.state.terminal_status.is_terminal:
            break
        session.submit(sorted(session.legal_actions(), key=repr)[0])


def test_static_semantic_evaluator_never_queries_attacks(monkeypatch):
    compiled = compile_ruleset_for_execution(cannon_ruleset())
    config = EvaluationConfig(dynamic_mobility_weight=0, anchor_escape_weight=0)
    profile = build_ruleset_profile(compiled, config)
    evaluator = SemanticAttackEvaluator(compiled, profile, config)
    def forbidden(*args):
        raise AssertionError("static evaluation queried attacks")
    monkeypatch.setattr(evaluator, "_attack_maps", forbidden)
    state = GameSession(compiled).state
    assert evaluator.evaluate(state) == Evaluator(compiled, profile, config).evaluate(state)


@pytest.mark.skipif(not native_available(), reason="Native extension unavailable")
def test_bulk_native_boundary_rejects_wrong_rules_and_owner():
    from generic_chess.native import _module
    compiled = compile_ruleset_for_execution(cannon_ruleset())
    rules = compile_native_semantic_rules(compiled)
    mirror = NativeSemanticPositionMirror.from_state(
        compiled, rules, GameSession(compiled).state, history_certified=True)
    other = compile_native_semantic_rules(compile_ruleset_for_execution(en_passant_ruleset()))
    with pytest.raises(ValueError, match="does not match"):
        attacked_squares(other, mirror.position, 0)
    for owner in (-1, 2, True, 0.0):
        with pytest.raises(ValueError, match="by_owner"):
            attacked_squares(rules, mirror.position, owner)
    for owner in (-1, 2):
        with pytest.raises(ValueError, match="owner"):
            _module().semantic_attacked_squares(rules.capsule, mirror.position, owner)


@pytest.mark.skipif(not native_available(), reason="Native extension unavailable")
def test_semantic_native_evaluator_runs_on_actual_search_views():
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    compiled = compile_ruleset_for_execution(cannon_ruleset())
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    decisions = []
    session = GameSession(compiled)
    for backend in ("core", "native"):
        evaluator = SemanticAttackEvaluator(compiled, profile, config, backend=backend)
        player = AlphaBetaPlayer(compiled, use_disk_cache=False, evaluator_override=evaluator,
            use_tt=False, use_ordering=False, tuning=SearchTuning(use_root_tactical=False))
        decision = player.choose_action(session, SearchLimits(max_depth=2, max_nodes=4096,
            max_time_seconds=5, quiescence_max_depth=0, quiescence_hard_max_depth=0))
        assert decision.completed_depth == 2
        assert decision.action in session.legal_actions()
        decisions.append(decision)
    assert (decisions[0].action, decisions[0].score, decisions[0].nodes,
            decisions[0].principal_variation) == (
            decisions[1].action, decisions[1].score, decisions[1].nodes,
            decisions[1].principal_variation)
