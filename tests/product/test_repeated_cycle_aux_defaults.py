"""Repeated-cycle search keeps sparse/default auxiliary identity semantics."""
from dataclasses import replace
import pytest
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_is_board, action_source_square, action_target_square
from generic_chess.core.adjudication import IncompleteAdjudicationHistoryError
from generic_chess.core.coordinates import Square
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import terminal_from_search_runtime, _repeated_cycle_target_history_projection
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleRepeatedCycleTargetCondition
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import weird_rulesets

class Constant:
    def evaluate(self, state): return 77
    def type_value(self, type_id): return 0 if type_id == 'K' else 1000
    def capture_order_value(self, moving, captured):
        return 10 * self.type_value(captured.current_type_id) - self.type_value(moving.current_type_id)

def fixture():
    rules = replace(weird_rulesets()[2], repeated_cycle_target_conditions=(RuleRepeatedCycleTargetCondition(actor=0),), max_ply=64, repetition_limit=4)
    compiled = replace(compile_semantic_ruleset(rules), _legacy_compiled=None)
    return compiled, GameSession(compiled)

def advance(session):
    actions = []
    for source, target in (((0, 0), (1, 0)), ((7, 7), (6, 7)), ((1, 0), (0, 0)), ((6, 7), (7, 7))):
        action = next(a for a in session.legal_actions() if action_is_board(a) and action_source_square(a) == Square(*source) and action_target_square(a) == Square(*target))
        session.submit(action)
        actions.append(action)
    return actions

def snapshot(rt):
    return (rt.position, rt.ply_count, rt.terminal_status, rt.runtime_hash, rt._snapshot, tuple(rt.history), rt._history_context, dict(rt.repetition_counts), rt.depth)

@pytest.mark.parametrize('supplied', (False, True))
@pytest.mark.parametrize('forced_hash', (None, 7))
def test_explicit_default_cycle_matches_core_and_restores(supplied, forced_hash):
    compiled, session = fixture()
    initial = session.state
    rt = SearchPathRuntime(initial, compiled, history_witnesses=session._search_witnesses if supplied else None, hash_override=forced_hash)
    before = snapshot(rt)
    reference = GameSession(compiled)
    actions = advance(reference)
    for action in actions:
        session.submit(action)
        rt.push(action)
        assert rt.position == session.state.position
        assert rt.terminal_status == session.state.terminal_status
        assert rt.ply_count == session.state.ply_count
    assert rt.position.aux_state and not rt.history[-1].identity.position.aux_state
    counts, history = _repeated_cycle_target_history_projection(rt)
    assert counts == session.state.repetition_counts
    assert history == session.state.history
    for _ in actions:
        rt.pop()
    assert snapshot(rt) == before
    rt.assert_balanced()

@pytest.mark.parametrize('supplied', (False, True))
@pytest.mark.parametrize('forced_hash', (None, 7))
def test_imported_explicit_default_cycle_searches_without_legacy_metadata(supplied, forced_hash):
    compiled, session = fixture()
    advance(session)
    state = session.state
    assert state.position.aux_state and not state.terminal_status.is_terminal
    rt = SearchPathRuntime(state, compiled, history_witnesses=session._search_witnesses if supplied else None, hash_override=forced_hash)
    assert terminal_from_search_runtime(rt) == state.terminal_status
    value = AlphaBetaPlayer(compiled, evaluator_override=Constant(), use_disk_cache=False, use_native_semantic_legality=False).choose_action(session, SearchLimits(max_depth=1, max_nodes=512, max_time_seconds=2, quiescence_max_depth=0, quiescence_hard_max_depth=0))
    assert value.completed_depth == 1 and value.action in session.legal_actions()
    assert session.state is state

@pytest.mark.parametrize('change', ('aux', 'board', 'hands'))
def test_history_projection_still_rejects_actual_current_position_change(change):
    compiled, session = fixture()
    advance(session)
    rt = SearchPathRuntime(session.state, compiled, history_witnesses=session._search_witnesses)
    position = rt.position
    if change == 'aux':
        position = replace(position, aux_state=(((0, -1), 1),))
    elif change == 'board':
        board = list(position.board)
        board[1] = Piece(0, 'R', 'R')
        position = replace(position, board=tuple(board))
    else:
        position = replace(position, hands=(Hands((('R', 1),)), position.hands[1]))
    rt.position = position
    with pytest.raises(IncompleteAdjudicationHistoryError):
        _repeated_cycle_target_history_projection(rt)
