from dataclasses import replace
from io import StringIO

import pytest

from generic_chess import (
    GameState,
    RuleAutomaticAdjudication,
    TerminalResult,
    TerminalStatus,
    build_standard_shogi_ruleset,
    build_western_chess_ruleset,
    compile_ruleset_for_execution,
    initial_state,
    terminal_result,
)
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import terminal_from_search_runtime
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import compute_fingerprint
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.session import GameSession, SessionFinishedError
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from generic_chess.cli.play import main


NEW_PRODUCT_FINGERPRINT = "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635"
OLD_PRODUCT_FINGERPRINT = "1bf2a46fe8e9e8636dcdde032ad8d9ccdd42d56cba901a8385043103952bd1f4"


def _product_state(compiled, ply, checks):
    position = initial_state(compiled).position
    current_key = str(repetition_identity_key(position, compiled))
    records = []
    keys = []
    for index in range(ply + 1):
        key = current_key if index in (0, ply) else f"audit-history-{index}"
        keys.append(key)
        if index == 0:
            records.append(HistoryRecord(key, -1, "", False))
        else:
            actor = (index - 500) % 2
            records.append(HistoryRecord(key, actor, f"m{index}", bool(checks.get(index, False))))
    counts = tuple((key, keys.count(key)) for index, key in enumerate(keys) if key not in keys[:index])
    state = GameState(
        position=position,
        ply_count=ply,
        repetition_counts=counts,
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
        history=tuple(records),
    )
    return replace(state, terminal_status=terminal_result(state, compiled))


def test_live_product_adopts_rule_roundtrip_and_preserves_ordinary_start():
    ruleset = build_standard_shogi_ruleset()
    assert compute_fingerprint(ruleset) == NEW_PRODUCT_FINGERPRINT
    assert compute_fingerprint(replace(ruleset, automatic_adjudications=())) == OLD_PRODUCT_FINGERPRINT
    restored = deserialize_ruleset(serialize_ruleset(ruleset))
    assert restored.automatic_adjudications == ruleset.automatic_adjudications
    assert compute_fingerprint(restored) == NEW_PRODUCT_FINGERPRINT
    assert ruleset.metadata["nyugyoku_supported"] is True
    assert ruleset.metadata["move_500_no_contest_supported"] is True
    compiled = compile_ruleset_for_execution(ruleset)
    session = GameSession(compiled)
    assert session.result.status.value == "ongoing"
    assert len(session.legal_actions()) == 30
    assert session.available_declarations() == ()


def test_product_threshold_boundary_extension_and_runtime_parity():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    witnesses = (
        (499, {}, TerminalStatus.ONGOING),
        (500, {500: False}, TerminalStatus.NO_CONTEST),
        (500, {500: True}, TerminalStatus.ONGOING),
        (501, {500: True}, TerminalStatus.ONGOING),
        (502, {500: True, 502: True}, TerminalStatus.ONGOING),
        (503, {500: True, 502: True}, TerminalStatus.ONGOING),
        (504, {500: True, 502: True, 504: False}, TerminalStatus.NO_CONTEST),
        (514, {500: True, 502: True, 504: True, 506: True, 508: True, 510: True, 512: True, 514: True}, TerminalStatus.ONGOING),
    )
    for ply, checks, expected in witnesses:
        state = _product_state(compiled, ply, checks)
        assert terminal_result(state, compiled).status is expected
        if ply in (500, 514):
            runtime = SearchPathRuntime.from_state(
                state, compiled, history_witnesses=(state.position,) * len(state.history)
            )
            assert terminal_from_search_runtime(runtime).status is expected
    assert terminal_result(
        _product_state(compiled, 516, {500: True, 502: True, 504: True, 506: True, 508: True, 510: True, 512: True, 514: True, 516: False}),
        compiled,
    ).status is TerminalStatus.NO_CONTEST


def test_product_terminal_session_surface_and_root_search_identity():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    state = _product_state(compiled, 500, {500: False})
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (state.position,) * len(state.history)
    assert session.result.status.value == "no_contest"
    assert session.result.winner is None
    assert "no-contest/restart" in str(session.result)
    assert session.legal_actions() == ()
    assert session.available_declarations() == ()
    with pytest.raises(SessionFinishedError):
        session.submit(None)
    with pytest.raises(SessionFinishedError):
        session.resign()
    with pytest.raises(SessionFinishedError):
        session.declare("claim_owner_0")
    decision = AlphaBetaPlayer(
        compiled, use_disk_cache=False, use_native_semantic_legality=False
    ).choose_action(session, SearchLimits(max_depth=2, quiescence_max_depth=0))
    assert decision.choice_kind == "TERMINAL"
    assert decision.action is None
    assert decision.declaration is None
    assert decision.score == 0


def test_product_declaration_coexistence_and_incomplete_history():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    from test_generic_declaration_semantics import _shogi_boundary_state

    before = GameSession(compiled)
    before._state = _shogi_boundary_state(compiled, 31, ply=499)
    assert before.available_declarations()
    immediate = _product_state(compiled, 500, {500: False})
    finished = GameSession(compiled)
    finished._state = immediate
    assert finished.available_declarations() == ()
    with pytest.raises(SessionFinishedError):
        finished.declare("claim_owner_0")
    truncated = replace(immediate, history=immediate.history[:2])
    with pytest.raises(ValueError, match="requires complete history"):
        terminal_result(truncated, compiled)


def test_game_record_v1_replays_and_rederives_generic_no_contest():
    definition = replace(
        build_western_chess_ruleset(),
        semantic_actions=(),
        automatic_adjudications=(RuleAutomaticAdjudication("opaque_product", 4),),
    )
    compiled = compile_ruleset(definition)
    session = GameSession(compiled)
    for ply in range(1, 5):
        chosen = None
        for action in session.legal_actions():
            candidate = __import__("generic_chess").apply_action(session.state, action, compiled)
            if ply < 4 or not candidate.history[-1].gave_check:
                chosen = action
                break
        assert chosen is not None
        session.submit(chosen)
    assert session.result.status.value == "no_contest"
    record = session.to_record()
    assert record.schema_version == 1
    encoded = serialize_game_record(record)
    assert "no_contest" not in encoded
    replayed = GameSession.replay(compiled, deserialize_game_record(encoded))
    assert replayed.result == session.result


def test_root_tactical_scan_values_no_contest_child_as_zero():
    definition = replace(
        build_western_chess_ruleset(),
        semantic_actions=(),
        automatic_adjudications=(RuleAutomaticAdjudication("opaque_product", 1),),
    )
    compiled = compile_ruleset(definition)
    session = GameSession(compiled)
    assert session.legal_actions()
    # The initial Western position has no checking move; every first action
    # therefore reaches the automatic no-contest child.
    player = AlphaBetaPlayer(
        compiled, use_disk_cache=False, use_native_semantic_legality=False
    )
    player._evaluator = type("ConstantEvaluator", (), {"evaluate": lambda self, state: -100})()
    decision = player.choose_action(
        session, SearchLimits(max_depth=1, quiescence_max_depth=0)
    )
    assert decision.action in session.legal_actions()
    assert decision.score == 0


def test_cli_builtin_standard_shogi_still_renders_initial_product():
    output = StringIO()
    assert main(["--builtin-ruleset", "standard_shogi"], StringIO("quit\n"), output) == 0
    text = output.getvalue()
    assert "legal actions:" in text
    assert "final result: ongoing" in text
