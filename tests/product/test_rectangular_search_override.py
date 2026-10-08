"""Search geometry is independent of the default square-only price builder."""
from dataclasses import replace

import pytest

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import reference_minimax
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.pieces import Piece
from generic_chess.native.compiler import NativeUnsupportedRuleError, compile_native_semantic_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import cannon_ruleset
from scripts.unfamiliar_search import validate_pv


class UnitEvaluator:
    """Deliberately shape-independent control, not a material-price claim."""

    def evaluate(self, state):
        score = sum(100 if p.owner == 0 else -100
                    for p in state.position.board
                    if p is not None and p.current_type_id != 'K')
        score += sum((100 if owner == 0 else -100) * sum(n for _, n in hand.counts)
                     for owner, hand in enumerate(state.position.hands))
        return score if state.position.side_to_move == 0 else -score

    def capture_order_value(self, moving, captured):
        return 1000 if captured.current_type_id != 'K' else 0


class UnusedProfileCache:
    def get_or_build(self, *args):
        raise AssertionError('supplied evaluator must not build an unused default profile')


def rectangular_cannon(width, height):
    rows = [[None] * width for _ in range(height)]
    rows[0][0] = Piece(0, 'K', 'K')
    rows[-1][-1] = Piece(1, 'K', 'K')
    rows[1][0] = Piece(0, 'C', 'C')
    rows[1][-1] = Piece(1, 'C', 'C')
    rows[1][width // 2] = Piece(0, 'C', 'C')
    return replace(cannon_ruleset(), board_size=None, board_width=width,
                   board_height=height, initial_position=tuple(map(tuple, rows)),
                   drop_allowed={'C': ((False,) * (width * height),) * 2})


@pytest.mark.parametrize('shape', [(7, 5), (9, 10)])
@pytest.mark.parametrize('native', [False, True])
@pytest.mark.parametrize('ordering,staged', [(False, False), (True, False), (True, True)])
def test_rectangular_public_search_with_supplied_evaluator(shape, native, ordering, staged):
    compiled = compile_ruleset_for_execution(rectangular_cannon(*shape))
    session = GameSession(compiled)
    initial = session.state
    evaluator = UnitEvaluator()
    reference, _ = reference_minimax(initial, 2, evaluator, compiled)
    player = AlphaBetaPlayer(
        compiled, evaluator_override=evaluator, profile_cache=UnusedProfileCache(),
        use_native_semantic_legality=native, use_ordering=ordering,
        tuning=SearchTuning(use_root_tactical=False, use_staged_move_picker=staged))
    assert player.evaluation_profile is None
    assert not player.evaluation_profile_cache_hit
    # The default Native request may use the supported Core fallback. These
    # rectangular carrier fixtures do not establish Native compilation support.
    if not native:
        assert player.native_legality_provider is None
    decision = player.choose_action(session, SearchLimits(
        max_depth=2, max_nodes=4096, max_time_seconds=5,
        quiescence_max_depth=0, quiescence_hard_max_depth=0))
    assert decision.completed_depth == 2
    assert decision.score == reference
    assert decision.native_legality_fallbacks == 0
    assert not decision.evaluation_profile_cache_hit
    validate_pv(session, decision)
    assert session.state == initial


def test_default_evaluator_still_builds_and_reuses_default_profile():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    cache = EvaluationProfileCache(use_disk=False)
    first = AlphaBetaPlayer(compiled, profile_cache=cache)
    second = AlphaBetaPlayer(compiled, profile_cache=cache)
    assert first.evaluation_profile is not None
    assert first.evaluation_profile == second.evaluation_profile
    assert not first.evaluation_profile_cache_hit
    assert second.evaluation_profile_cache_hit


def test_rectangular_native_boundary_reports_unsupported_size():
    compiled = compile_ruleset_for_execution(rectangular_cannon(7, 5))
    with pytest.raises(NativeUnsupportedRuleError, match='semantic board size'):
        compile_native_semantic_rules(compiled)
