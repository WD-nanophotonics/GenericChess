"""F27 product/session/search integration contracts."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from generic_chess import build_standard_shogi_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.cli.play import main
from generic_chess.session import (
    GameSession,
    SessionFinishedError,
    SessionStatus,
    deserialize_game_record,
    serialize_game_record,
)

from test_generic_declaration_semantics import _claim_ruleset, _shogi_boundary_state, _state


def _compiled():
    return compile_ruleset_for_execution(build_standard_shogi_ruleset())


@pytest.mark.parametrize("score, outcome", ((31, "WIN"), (24, "RESTART"), (23, "LOSS")))
def test_product_session_declaration_is_terminal_and_replayable(score, outcome):
    compiled = _compiled()
    session = GameSession(compiled)
    session._state = _shogi_boundary_state(compiled, score)
    before = session.state
    result = session.declare("claim_owner_0")

    assert result.status is SessionStatus.DECLARATION
    assert result.declaration_outcome == outcome
    assert session.state == before
    assert session.history == ()
    assert session.legal_actions() == ()
    assert session.to_record().schema_version == 2
    with pytest.raises(SessionFinishedError):
        session.declare("claim_owner_0")


def test_product_session_rejects_wrong_owner_and_unknown_but_allows_failed_claim():
    compiled = _compiled()
    session = GameSession(compiled)
    with pytest.raises(ValueError, match="belongs to player"):
        session.declare("claim_owner_1")
    with pytest.raises(ValueError, match="unknown declaration"):
        session.declare("missing")
    result = session.declare("claim_owner_0")
    assert result.declaration_outcome == "LOSS"
    assert result.winner == 1
    replayed = GameSession.replay(
        compiled,
        deserialize_game_record(serialize_game_record(session.to_record())),
    )
    assert replayed.result == result


def test_alphabeta_returns_product_shogi_declaration_without_action():
    compiled = _compiled()
    session = GameSession(compiled)
    session._state = _shogi_boundary_state(compiled, 31)
    decision = AlphaBetaPlayer(
        compiled, use_disk_cache=False, use_native_semantic_legality=False
    ).choose_action(session, SearchLimits(max_depth=4, quiescence_max_depth=2))
    assert decision.choice_kind == "DECLARATION"
    assert decision.action is None
    assert decision.declaration.declaration_id == "claim_owner_0"
    assert decision.declaration.outcome == "WIN"
    assert decision.declaration.actor == 0
    assert decision.declaration_root_selected is True


class _ConstantEvaluator:
    def __init__(self, value):
        self.value = value

    def evaluate(self, state):
        return self.value


@pytest.mark.parametrize("value, expected_kind", ((1, "DECLARATION"), (0, "ACTION")))
def test_restart_is_a_floor_and_actions_win_ties(value, expected_kind):
    from generic_chess import Hands, Piece, Position

    compiled = compile_ruleset_for_execution(_claim_ruleset())
    board = [None] * 64
    board[0] = Piece(0, "K", "K")
    for index in range(1, 5):
        board[index] = Piece(0, "P", "P")
    board[63] = Piece(1, "K", "K")
    position = Position(
        tuple(board), hands=(Hands.empty(), Hands.empty()), side_to_move=0,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    session = GameSession(compiled)
    session._state = _state(compiled, position)
    player = AlphaBetaPlayer(
        compiled,
        use_disk_cache=False,
        use_tt=False,
        use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    player._evaluator = _ConstantEvaluator(value)
    decision = player.choose_action(
        session, SearchLimits(max_depth=1, quiescence_max_depth=0)
    )
    assert decision.choice_kind == expected_kind
    if expected_kind == "DECLARATION":
        assert decision.action is None
        assert decision.declaration.outcome == "RESTART"
    else:
        assert decision.action in session.legal_actions()
        assert decision.declaration_root_selected is False


def test_descendant_declaration_win_is_seen_by_parent_search():
    from generic_chess import Hands, Piece, Position

    base = _claim_ruleset()
    child_claim = replace(base.declarations[0], owner=1)
    compiled = compile_ruleset_for_execution(replace(base, declarations=(child_claim,)))
    board = [None] * 64
    board[0] = Piece(1, "K", "K")
    board[1] = Piece(1, "R", "R")
    board[2] = Piece(1, "P", "P")
    board[3] = Piece(1, "P", "P")
    board[63] = Piece(0, "K", "K")
    board[54] = Piece(0, "P", "P")
    position = Position(
        tuple(board), hands=(Hands.empty(), Hands.empty()), side_to_move=0,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    session = GameSession(compiled)
    session._state = _state(compiled, position)
    player = AlphaBetaPlayer(
        compiled, use_disk_cache=False, use_tt=False, use_ordering=False,
        use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    player._evaluator = _ConstantEvaluator(0)
    decision = player.choose_action(
        session, SearchLimits(max_depth=1, quiescence_max_depth=0)
    )
    assert decision.choice_kind == "ACTION"
    assert decision.action in session.legal_actions()
    assert decision.score <= -999_999_999
    assert decision.declaration_win_options > 0


def test_initial_product_shogi_has_only_ordinary_actions_and_cli_commands():
    compiled = _compiled()
    session = GameSession(compiled)
    assert session.available_declarations() == ()
    assert len(session.legal_actions()) == 30

    from io import StringIO
    output = StringIO()
    assert main(["--builtin-ruleset", "standard_shogi"], StringIO("declarations\nquit\n"), output) == 0
    assert "no non-losing declarations" in output.getvalue()


def test_v2_rejects_a_tampered_declaration_marker():
    compiled = _compiled()
    session = GameSession(compiled)
    session._state = _shogi_boundary_state(compiled, 31)
    session.declare("claim_owner_0")
    payload = json.loads(serialize_game_record(session.to_record()))
    payload["declaration"]["weighted_score"] = 30
    record = deserialize_game_record(json.dumps(payload))
    with pytest.raises(ValueError, match="does not match"):
        GameSession.replay(compiled, record)
