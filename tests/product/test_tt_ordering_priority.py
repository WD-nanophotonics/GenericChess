"""TT priority must not depend on the supplied evaluator's price scale."""

from types import SimpleNamespace

import pytest

from ai_fixtures import build_4x4_rooks
from conftest import make_state
from generic_chess.ai.alphabeta.ordering import MoveOrderer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import action_target_square
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.movegen import legal_actions


def _fixture():
    compiled = build_4x4_rooks()
    state = make_state(compiled, ["...k", "r...", "R...", "K..."])
    actions = legal_actions(state, compiled)
    captures = [
        action
        for action in actions
        if state.position.board[
            square_to_index(action_target_square(action), state.position.board_shape)
        ] is not None
    ]
    quiet = next(a for a in actions if a not in captures)
    assert captures
    return compiled, state, actions, quiet


@pytest.mark.parametrize("capture_value", [10000, 10**12, -10**12])
def test_tt_action_precedes_arbitrary_capture_scale_without_reordering_others(capture_value):
    _, state, actions, tt_move = _fixture()
    evaluator = SimpleNamespace(capture_order_value=lambda *_: capture_value)
    orderer = MoveOrderer()
    baseline = orderer.order(state, actions, evaluator, 1, None, None, SearchTuning())
    ordered = orderer.order(state, actions, evaluator, 1, tt_move, None, SearchTuning())
    assert ordered == [tt_move] + [a for a in baseline if a != tt_move]
    assert len(ordered) == len(actions)


def test_default_rule_prices_cannot_outrank_tt_action():
    compiled, state, actions, tt_move = _fixture()
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    ordered = MoveOrderer().order(
        state, actions, evaluator, 1, tt_move, None, SearchTuning()
    )
    assert ordered[0] == tt_move


def test_absent_tt_action_is_not_inserted_or_used_to_change_legal_order():
    _, state, actions, tt_move = _fixture()
    actions = [action for action in actions if action != tt_move]
    evaluator = SimpleNamespace(capture_order_value=lambda *_: 10**12)
    orderer = MoveOrderer()
    baseline = orderer.order(state, actions, evaluator, 1, None, None, SearchTuning())
    assert orderer.order(
        state, actions, evaluator, 1, tt_move, None, SearchTuning()
    ) == baseline
