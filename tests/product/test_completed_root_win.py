"""Only a fully completed winning root child survives a later abort."""
from dataclasses import replace
import pytest
from conftest import make_ruleset, king_type, T
from generic_chess.core.movement import RayAtom
from generic_chess.core.position import Hands, HistoryRecord
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import terminal_result
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta import search
from generic_chess.ai.evaluation.config import MATE_SCORE, MATE_THRESHOLD
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.cancellation import CancellationToken
from scripts.full_q_refresh_comparison import (
    compile_legacy_ruleset_for_semantic_execution, SearchMetadataAdapter, GameSession,
)


def prepared():
    rules = make_ruleset(4, [king_type(), T("R", RayAtom((0, 1)),
        RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))],
        lines=["....", "...R", "....", ".k.K"])
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    compiled = SearchMetadataAdapter(ir=compiled.ir,
        _legacy_compiled=compiled._legacy_compiled, support=compiled.support)
    session = GameSession(compiled)
    position = replace(session.state.position, hands=(Hands((("R", 1),)), Hands()))
    key = position_identity_key(position, compiled)
    state = replace(session.state, position=position,
        history=(HistoryRecord(key, -1, "", False),), repetition_counts=((key, 1),))
    session._state = replace(state, terminal_status=terminal_result(state, compiled))
    session._search_history_witnesses = (position,)
    return session


def proves_root_h3(session, action):
    child = apply_action(session.state, action, session.compiled)
    replies = legal_actions(child, session.compiled)
    assert replies
    return all(any(apply_action(after, win, session.compiled).terminal_status.winner == 0
                   for win in legal_actions(after, session.compiled))
               for after in (apply_action(child, a, session.compiled) for a in replies))


@pytest.mark.parametrize("nodes,winning", [(98, False), (99, True), (100000, True)])
def test_completed_child_not_incomplete_iteration_is_retained(nodes, winning):
    session = prepared()
    before = session.state, session.to_record(), session._search_witnesses
    decision = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=False).choose_action(session,
        SearchLimits(max_depth=2, max_nodes=nodes, max_time_seconds=5,
                     quiescence_max_depth=2))
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert decision.runtime_depth_balanced
    if nodes == 99:
        assert decision.completed_depth == 1  # Do not claim the whole D2 finished.
        assert decision.result_source == "completed_root_win"
        assert decision.result_ordinary_qdepth == 2
        assert decision.result_check_hard_qdepth == 8
        assert decision.termination_reason == "node_limit"
        assert not decision.root_scan_used_fallback
    elif nodes == 98:
        assert decision.result_source == "main_iteration"
        assert decision.score < MATE_THRESHOLD
    else:
        assert decision.completed_depth == 2
        assert decision.result_source == "main_iteration"
        assert decision.termination_reason == "completed_depth"
    if winning:
        assert decision.score == MATE_SCORE-3
    assert proves_root_h3(session, decision.action) is winning


def test_cancellation_keeps_completed_proof_and_actual_stop_reason(monkeypatch):
    session = prepared()
    token = CancellationToken()
    original = search._Budget.check
    def cancel_after_completed_child(self, stats, *, force=False):
        if stats.nodes + stats.qnodes >= 99:
            token.cancel()
        return original(self, stats, force=force)
    monkeypatch.setattr(search._Budget, "check", cancel_after_completed_child)
    before = session.state, session.to_record(), session._search_witnesses
    decision = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=False).choose_action(session,
        SearchLimits(max_depth=2, max_nodes=None, max_time_seconds=5,
                     quiescence_max_depth=2), cancel_token=token)
    assert decision.termination_reason == "cancelled"
    assert decision.result_source == "completed_root_win"
    assert decision.completed_depth == 1 and decision.score == MATE_SCORE-3
    assert decision.runtime_depth_balanced and proves_root_h3(session, decision.action)
    assert before == (session.state, session.to_record(), session._search_witnesses)
