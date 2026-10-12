"""Observed generated-aux PV bound-as-tie defect at a nonroot node."""
import json
from pathlib import Path
import pytest
from generic_chess import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.core.actions import action_from_dict
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
    # In the old exact-root replay the same reported -2514 accompanied a
    # legal line whose local residual value/leaf was -4912. Both independent
    # Core and TT-free Native branch queries established this distinction.
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
