"""F27 product/session/search integration contracts."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from generic_chess import build_standard_shogi_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.search import _Budget, _Context, quiescence
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.cli.play import main
from generic_chess.session import (
    GameSession,
    SessionFinishedError,
    SessionStatus,
    deserialize_game_record,
    serialize_game_record,
)

from test_generic_declaration_semantics import (
    _claim_position,
    _claim_ruleset,
    _shogi_boundary_state,
    _state,
)


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
@pytest.mark.parametrize("use_tt", (False, True))
def test_restart_is_a_floor_and_actions_win_ties(value, expected_kind, use_tt):
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
        use_tt=use_tt,
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


def test_repeated_tt_root_preserves_restart_declaration_identity():
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
        compiled, use_disk_cache=False, use_tt=True, use_ordering=False,
        use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    player._evaluator = _ConstantEvaluator(1)
    limits = SearchLimits(max_depth=1, quiescence_max_depth=0)
    first = player.choose_action(session, limits)
    second = player.choose_action(session, limits)
    for decision in (first, second):
        assert decision.choice_kind == "DECLARATION"
        assert decision.action is None
        assert decision.declaration.declaration_id == "opaque_claim"
        assert decision.declaration.outcome == "RESTART"
        assert decision.score == 0
    assert session.state == _state(compiled, position)


def test_qsearch_declaration_outcomes_are_terminal_or_floor_values():
    from generic_chess.ai.alphabeta.tuning import SearchTuning

    compiled = compile_ruleset_for_execution(_claim_ruleset())
    limits = SearchLimits(max_nodes=100, quiescence_max_depth=0)

    def score_for(score_state, evaluator_value):
        stats = SearchStatistics()
        ctx = _Context(
            compiled,
            _ConstantEvaluator(evaluator_value),
            TranspositionTable(),
            stats,
            _Budget(limits, None),
            SearchTuning(),
            False,
            False,
            limits.quiescence_max_depth,
            limits.quiescence_hard_max_depth,
            limits.quiescence_max_nodes,
        )
        return quiescence(
            _state(compiled, _claim_position(compiled, score_state=score_state)),
            -10**12,
            10**12,
            0,
            0,
            ctx,
        )

    assert score_for("win", -1) == 1_000_000_000
    assert score_for("restart", -1) == 0
    assert score_for("loss", -1) == -1


def test_f27r1_results_fixture_has_all_repeats_and_f25_zero_option_parity():
    root = Path(__file__).resolve().parents[1]
    results = json.loads(
        (root / "tests/fixtures/f27r1_standard_shogi_declaration_search_results.json").read_text(
            encoding="utf-8"
        )
    )
    historical = json.loads(
        (root / "tests/fixtures/f25_standard_shogi_search_baseline.json").read_text(
            encoding="utf-8"
        )
    )
    rows = results["rows"]
    assert results["corrective_parent_sha"] == "5b08bf47b8e2b0ab9697feca2aa9e1b84e4fd6c3"
    assert results["integrity"] == {
        "row_count": 30,
        "repeats_per_row": 2,
        "all_roots_unchanged": True,
        "all_repeats_deterministic": True,
        "declaration_affected_rows": 0,
        "zero_option_f25_parity_rows": 30,
        "action_pv_declaration_separation": True,
    }
    assert len(rows) == 30
    assert {row["budget"] for row in rows} == {128, 512, 2048}
    assert {row["position_id"] for row in rows} == {
        item["position_id"] for item in historical["manifest"]["positions"]
    }
    expected = {
        (item["position_id"], item["budget"]): item["repeats"][0]
        for item in historical["fixed_node"]
    }
    for row in rows:
        assert row["repeats"] == [1, 2]
        assert row["declaration_win_options"] == 0
        assert row["declaration_restart_options"] == 0
        assert row["declaration_root_selected"] is False
        baseline = expected[(row["position_id"], row["budget"])]
        assert row["action"] == baseline["action"]
        assert row["visible_alias"] == baseline["visible_action"]
        assert row["score"] == baseline["score"]
        assert row["pv_head"].endswith(":" + baseline["pv_visible"][0])
        assert row["completed_depth"] == baseline["completed_depth"]


@pytest.mark.parametrize("use_pvs", (False, True))
def test_descendant_declaration_win_is_seen_by_parent_search(use_pvs):
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
        tuning=SearchTuning(use_root_tactical=False, use_pvs=use_pvs),
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
