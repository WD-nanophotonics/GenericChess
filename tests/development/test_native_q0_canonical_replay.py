"""Observed generated-aux PV bound-as-tie defect at a nonroot node."""
import json
from pathlib import Path
import pytest
from generic_chess import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.core.actions import action_from_dict, SemanticBoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.native import native_available
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits

pytestmark = pytest.mark.skipif(not native_available(), reason='Native unavailable')

def test_exact_root_canonical_replay_does_not_keep_inferior_auxiliary_pv():
    data = json.loads((Path(__file__).parent/'data/native_q0_aux_pv_1091.json').read_text(encoding='utf-8'))
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(data['rules'])))
    session = GameSession(compiled)
    for event in data['state']['history'][1:]:
        session.submit(action_from_dict(json.loads(event['action_signature'])))
    before = session.state
    witnesses = session._search_witnesses
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    engine = SemanticSearchEngine(compiled, provider.native_rules,
        board_values=data['board'], hand_values=data['hand'],
        dynamic_values=(0,0,0), evaluator_scale=1, tt_megabytes=1)
    result = engine.search(session, SearchLimits(max_depth=4, max_nodes=1_000_000,
        max_time_seconds=64, quiescence_max_depth=0), root_window_pruning=True)
    assert result.completed_depth == 4 and result.score == -2514
    state = before
    for action in result.principal_variation:
        assert action in legal_actions(state, compiled)
        state = apply_action(state, action, compiled)
    # Both recorded lines finish at material -2514. However, the old A a2-d4
    # third move permits an independently verified best reply worth -4912,
    # while P e3-c7 keeps the residual minimax value -2514. A leaf-only check
    # therefore cannot detect the observed inferior continuation.
    assert result.principal_variation[2] == SemanticBoardMove(
        pattern_id="legacy_039", geometry_id="g26", actor_type_id="P",
        from_square=Square(4, 2), to_square=Square(2, 6),
    )
    values = [0,0]
    for piece in state.position.board:
        if piece:
            values[piece.owner] += data['board'][piece.current_type_id]
    for owner, hand in enumerate(state.position.hands):
        for tid, count in hand.counts:
            values[owner] += data['hand'][tid]*count
    assert values[before.position.side_to_move]-values[1-before.position.side_to_move] == -2514
    assert len(result.principal_variation) == 4
    assert session.state is before and session._search_witnesses is witnesses


def test_exact_score_refinement_preserves_canonical_pv_within_node_budget():
    from generic_chess.learning.material import LearnableMaterialCheckpoint
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from scripts.research_record import record_value
    directory = Path(__file__).parent / 'data'
    data = json.loads((directory / 'native_q0_aux_pv_1091.json').read_text(encoding='utf-8'))
    follow = json.loads((directory / 'native_q0_score_refinement_1091.json').read_text(encoding='utf-8'))
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(data['rules'])))
    session = GameSession(compiled)
    for event in data['state']['history'][1:]:
        session.submit(action_from_dict(json.loads(event['action_signature'])))
    for action in follow['additional_actions']:
        session.submit(action_from_dict(action))
    before, witnesses = session.state, session._search_witnesses
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    checkpoint = LearnableMaterialCheckpoint.from_profile(
        compiled, build_ruleset_profile(compiled, EvaluationConfig()), dynamic_weights={})
    engine = SemanticSearchEngine(compiled, provider.native_rules,
        board_values=data['board'], hand_values=data['hand'], dynamic_values=(0,0,0),
        evaluator_scale=1, tt_megabytes=1, ordering_checkpoint=checkpoint,
        ordering_min_depth=2)
    result = engine.search(session, SearchLimits(max_depth=4, max_nodes=1_000_000,
        max_time_seconds=64, quiescence_max_depth=0), root_window_pruning=True)
    assert result.completed_depth == 4 and result.score == follow['score']
    assert record_value(result.principal_variation) == follow['expected_pv']
    state = before
    for action in result.principal_variation:
        assert action in legal_actions(state, compiled)
        state = apply_action(state, action, compiled)
    assert session.state is before and session._search_witnesses is witnesses
