"""Opt-in rectangle profiles use semantic metadata, not square inspection handles."""
from dataclasses import replace
import pytest
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import reference_minimax
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from tests.product.test_rectangular_search_override import rectangular_cannon, UnusedProfileCache
from tests.product.test_semantic_zone_guards import zone_rule
from scripts.unfamiliar_search import validate_pv

CONFIG = EvaluationConfig(dynamic_mobility_weight=2, anchor_escape_weight=0,
                          promotion_potential_weight=0)


def test_semantic_candidate_does_not_need_legacy_inspection_handle():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    expected = build_semantic_opportunity_profile(compiled, CONFIG)
    assert build_semantic_opportunity_profile(replace(compiled, _legacy_compiled=None), CONFIG) == expected


@pytest.mark.parametrize('shape', [(7, 5), (9, 10)])
def test_rectangle_drop_metadata_uses_area_and_keeps_default_boundary(shape):
    width, height = shape
    definition = rectangular_cannon(width, height)
    mask = tuple(i in (1, width + 1) for i in range(width * height))
    compiled = compile_ruleset_for_execution(replace(definition, drop_allowed={'C': (mask, mask)}))
    profile, scope = build_semantic_opportunity_profile(replace(compiled, _legacy_compiled=None), CONFIG)
    assert profile.piece_profiles['C'].drop_freedom_ratio == pytest.approx(2 / (width * height))
    assert profile.piece_profiles['C'].normalized_board_value == 1000
    assert profile.board_value_by_type['K'] == 0
    assert not scope['complete_legal_mobility']
    assert 'drop diagnostics' in scope['ignored']
    with pytest.raises(ValueError, match='supply an evaluator for rectangular search'):
        build_ruleset_profile(compiled, CONFIG)


@pytest.mark.parametrize('definition', [rectangular_cannon(7, 5), rectangular_cannon(9, 10),
                                       zone_rule('target', True, 'inside')])
@pytest.mark.parametrize('qdepth', [0, 2])
def test_actual_rectangle_candidate_search_restores_and_replays(definition, qdepth):
    compiled = compile_ruleset_for_execution(definition)
    profile, _ = build_semantic_opportunity_profile(compiled, CONFIG)
    evaluator = SemanticAttackEvaluator(compiled, profile, CONFIG, backend='core')
    session = GameSession(compiled)
    before = session.state
    reference, _ = reference_minimax(before, 2, evaluator, compiled) if not qdepth else (None, None)
    signatures = []
    for _ in range(2):
        player = AlphaBetaPlayer(compiled, evaluator_override=evaluator,
            profile_cache=UnusedProfileCache(), use_native_semantic_legality=False,
            tuning=SearchTuning(use_root_tactical=False))
        decision = player.choose_action(session, SearchLimits(max_depth=2, max_nodes=8192,
            max_time_seconds=5, quiescence_max_depth=qdepth,
            quiescence_hard_max_depth=8 if qdepth else 0))
        assert decision.completed_depth == 2
        if not qdepth:
            assert decision.score == reference
        validate_pv(session, decision)
        assert session.state == before
        signatures.append((decision.action, decision.score, decision.nodes, decision.qnodes))
    assert signatures[0] == signatures[1]
