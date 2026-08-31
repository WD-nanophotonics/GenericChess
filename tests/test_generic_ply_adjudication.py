from dataclasses import replace

import pytest

from generic_chess import (
    GameState,
    RuleAutomaticAdjudication,
    TerminalResult,
    TerminalStatus,
    build_standard_shogi_ruleset,
    build_western_chess_ruleset,
    compile_ruleset,
    initial_state,
    position_key,
    terminal_result,
)
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.core.adjudication import (
    IncompleteAdjudicationHistoryError,
    automatic_adjudication_status,
)
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import _terminal_from_parts
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import compute_fingerprint, ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.session.result import SessionStatus, session_result_from_terminal


def _ruleset(trigger=4, *, max_ply=512, owner=0):
    base = build_western_chess_ruleset()
    return replace(
        base,
        max_ply=max_ply,
        repetition_limit=10_000,
        semantic_actions=(),
        automatic_adjudications=(
            RuleAutomaticAdjudication(f"opaque_threshold_{owner}", trigger),
        ),
    )


def _state(compiled, ply, checks, *, threshold_actor=0, position=None):
    position = position or initial_state(compiled).position
    key = repetition_identity_key(position, compiled)
    history = [HistoryRecord(key, -1, "", False)]
    for move in range(1, ply + 1):
        actor = threshold_actor if (move - compiled.automatic_adjudications[0].trigger_ply) % 2 == 0 else 1 - threshold_actor
        history.append(HistoryRecord(key, actor, f"m{move}", bool(checks.get(move, False))))
    return GameState(
        position=position,
        ply_count=ply,
        repetition_counts=((key, ply + 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
        history=tuple(history),
    )


@pytest.mark.parametrize("threshold_actor", [0, 1])
def test_opaque_owner_symmetric_threshold_and_extension(threshold_actor):
    compiled = compile_ruleset(_ruleset())
    assert terminal_result(_state(compiled, 3, {}, threshold_actor=threshold_actor), compiled).status is TerminalStatus.ONGOING
    assert terminal_result(_state(compiled, 4, {}, threshold_actor=threshold_actor), compiled).status is TerminalStatus.NO_CONTEST
    assert terminal_result(_state(compiled, 4, {4: True}, threshold_actor=threshold_actor), compiled).status is TerminalStatus.ONGOING
    assert terminal_result(_state(compiled, 5, {4: True}, threshold_actor=threshold_actor), compiled).status is TerminalStatus.ONGOING
    assert terminal_result(_state(compiled, 6, {4: True, 6: True}, threshold_actor=threshold_actor), compiled).status is TerminalStatus.ONGOING
    assert terminal_result(_state(compiled, 7, {4: True, 6: True}, threshold_actor=threshold_actor), compiled).status is TerminalStatus.ONGOING
    assert terminal_result(_state(compiled, 8, {4: True, 6: True, 8: False}, threshold_actor=threshold_actor), compiled).status is TerminalStatus.NO_CONTEST


def test_exact_500_boundary_and_long_check_extension_masks_max_ply():
    compiled = compile_ruleset(_ruleset(trigger=500, max_ply=512))
    assert terminal_result(_state(compiled, 499, {}), compiled).status is TerminalStatus.ONGOING
    assert terminal_result(_state(compiled, 500, {500: False}), compiled) == TerminalResult(TerminalStatus.NO_CONTEST)
    assert terminal_result(_state(compiled, 500, {500: True}), compiled).status is TerminalStatus.ONGOING
    assert terminal_result(_state(compiled, 501, {500: True}), compiled).status is TerminalStatus.ONGOING
    checks = {500: True, 502: True, 504: True, 506: True, 508: True, 510: True, 512: True, 514: True}
    assert terminal_result(_state(compiled, 514, checks), compiled).status is TerminalStatus.ONGOING
    assert terminal_result(_state(compiled, 516, {**checks, 516: False}), compiled).status is TerminalStatus.NO_CONTEST


def test_immutable_and_runtime_paths_share_history_semantics():
    compiled = compile_ruleset(_ruleset(trigger=4, max_ply=5))
    state = _state(compiled, 6, {4: True, 6: True})
    runtime = SearchPathRuntime.from_state(
        state, compiled, history_witnesses=(state.position,) * len(state.history)
    )
    assert terminal_result(state, compiled).status is TerminalStatus.ONGOING
    from generic_chess.core.terminal import terminal_from_search_runtime

    assert terminal_from_search_runtime(runtime).status is TerminalStatus.ONGOING
    state2 = _state(compiled, 8, {4: True, 6: True, 8: False})
    runtime2 = SearchPathRuntime.from_state(
        state2, compiled, history_witnesses=(state2.position,) * len(state2.history)
    )
    assert terminal_from_search_runtime(runtime2).status is TerminalStatus.NO_CONTEST


def test_incomplete_history_fails_closed_only_at_or_after_threshold():
    compiled = compile_ruleset(_ruleset(trigger=4))
    position = initial_state(compiled).position
    key = repetition_identity_key(position, compiled)
    below = GameState(position, 3, ((key, 1),), TerminalResult(TerminalStatus.ONGOING), (HistoryRecord(key, -1, "", False),))
    assert terminal_result(below, compiled).status is TerminalStatus.ONGOING
    truncated = replace(below, ply_count=4)
    with pytest.raises(IncompleteAdjudicationHistoryError, match="requires complete history"):
        terminal_result(truncated, compiled)


def test_serialization_fingerprint_and_empty_backcompat_contract():
    base = build_western_chess_ruleset()
    configured = _ruleset(trigger=4)
    assert compute_fingerprint(ruleset_from_dict(ruleset_to_dict(base))) == compute_fingerprint(base)
    assert compute_fingerprint(deserialize_ruleset(serialize_ruleset(configured))) == compute_fingerprint(configured)
    assert compute_fingerprint(configured) != compute_fingerprint(base)
    assert compute_fingerprint(replace(configured, automatic_adjudications=(RuleAutomaticAdjudication("opaque_threshold_0", 5),))) != compute_fingerprint(configured)
    assert compute_fingerprint(replace(configured, automatic_adjudications=(RuleAutomaticAdjudication("opaque_threshold_0", 4, continuation_policy="threshold_actor_continuous_check"),))) == compute_fingerprint(configured)
    assert "automatic_adjudications" not in ruleset_to_dict(base)
    compiled = compile_ruleset(configured)
    assert compiled.automatic_adjudications[0].trigger_ply == 4


def test_repetition_precedes_automatic_and_no_contest_is_session_draw_style():
    ruleset = replace(_ruleset(trigger=4), repetition_limit=2)
    compiled = compile_ruleset(ruleset)
    state = _state(compiled, 4, {4: False})
    result = terminal_result(state, compiled)
    assert result.status is TerminalStatus.REPETITION
    no_contest = TerminalResult(TerminalStatus.NO_CONTEST)
    assert no_contest.winner is None
    assert str(no_contest) == "no-contest/restart"
    session = session_result_from_terminal(no_contest)
    assert session.status is SessionStatus.NO_CONTEST
    assert str(session) == "no-contest/restart"
    assert terminal_score(no_contest, 0, 500) == 0


def test_checkmate_precedes_automatic(monkeypatch):
    compiled = compile_ruleset(_ruleset(trigger=4))
    state = _state(compiled, 4, {4: False})
    import generic_chess.core.terminal as terminal_module

    monkeypatch.setattr(terminal_module, "has_legal_action", lambda position, compiled: False)
    monkeypatch.setattr(terminal_module, "is_in_check", lambda position, side, compiled: True)
    result = _terminal_from_parts(
        state.position, state.ply_count, state.repetition_counts, compiled, state.history
    )
    assert result.status is TerminalStatus.CHECKMATE


def test_semantic_compile_carries_the_same_immutable_primitive_without_live_drift():
    live = build_standard_shogi_ruleset()
    assert live.automatic_adjudications == ()
    assert compute_fingerprint(live) == "1bf2a46fe8e9e8636dcdde032ad8d9ccdd42d56cba901a8385043103952bd1f4"
    audit_definition = replace(
        live,
        repetition_limit=10_000,
        automatic_adjudications=(RuleAutomaticAdjudication("audit_500", 500),),
    )
    semantic = compile_semantic_ruleset(audit_definition)
    assert semantic.ir.automatic_adjudications == semantic.support.automatic_adjudications
    assert semantic.automatic_adjudications[0].trigger_ply == 500
    assert semantic.declarations == compile_semantic_ruleset(live).declarations
    position = initial_state(semantic).position
    key = repetition_identity_key(position, semantic)
    history = tuple(
        [HistoryRecord(key, -1, "", False)]
        + [HistoryRecord(key, (move - 500) % 2, f"m{move}", move == 500 and False) for move in range(1, 501)]
    )
    state = GameState(position, 500, ((key, 501),), TerminalResult(TerminalStatus.ONGOING), history)
    assert terminal_result(state, semantic).status is TerminalStatus.NO_CONTEST


def test_material_independence_and_history_index_sentinel():
    compiled = compile_ruleset(_ruleset(trigger=4))
    pos = initial_state(compiled).position
    sparse_board = tuple(
        piece
        if piece is not None and compiled.types_by_id[piece.base_type_id].is_anchor
        else None
        for piece in pos.board
    )
    sparse = replace(pos, board=sparse_board)
    assert automatic_adjudication_status(
        compiled.automatic_adjudications, 4,
        _state(compiled, 4, {}).history,
    ) == "NO_CONTEST"
    assert terminal_result(_state(compiled, 4, {}, position=pos), compiled).status is TerminalStatus.NO_CONTEST
    assert terminal_result(_state(compiled, 4, {}, position=sparse), compiled).status is TerminalStatus.NO_CONTEST
    history = _state(compiled, 4, {}).history
    assert history[0].actor == -1
    assert history[4].action_signature == "m4"
