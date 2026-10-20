"""Human vs AI match orchestration (Qt-free, injected AI runner)."""

from types import SimpleNamespace

import pytest

from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.clock import SideTimeConfig, TimeControl, TimeControlMode
from generic_chess.core.coordinates import Square
from generic_chess.core.movegen import legal_actions
from generic_chess.ui.controller import UIController
from generic_chess.ui.match import MatchConfig, ParticipantKind
from generic_chess.ui.stores import DictSettingsStore

from conftest import T, king_type, make_ruleset


def _match_config(human_owner: int, mode=TimeControlMode.NONE):
    participants = [ParticipantKind.AI, ParticipantKind.AI]
    participants[human_owner] = ParticipantKind.HUMAN
    return MatchConfig(
        participants=(participants[0], participants[1]),
        time_control=TimeControl(
            mode=mode,
            owner0=SideTimeConfig(60, 10),
            owner1=SideTimeConfig(60, 10),
        ),
        ai_config=ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
    )


def _controller(**kw):
    return UIController(settings=DictSettingsStore(), **kw)


def _stub_runner():
    def runner(session, limits, cancel_token):
        action = legal_actions(session.state, session.compiled)[0]
        return SimpleNamespace(
            action=action,
            score=0,
            principal_variation=(),
            completed_depth=0,
            selective_depth=0,
            nodes=0,
            qnodes=0,
            elapsed_seconds=0.0,
            tt_probes=0,
            tt_hits=0,
            tt_cutoffs=0,
            beta_cutoffs=0,
            evaluation_profile_cache_hit=False,
            termination_reason="stub",
        )

    return runner


def _human_move(ctrl):
    ctrl.square_clicked(Square(1, 0))
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)


def test_human_move_triggers_ai_turn_and_clock_advances():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0, mode=TimeControlMode.FISCHER))
    assert not ctrl.ai_move_needed()  # human to move
    _human_move(ctrl)
    assert ctrl.ai_move_needed()
    now.t += 2.0  # AI (side 1) thinks for 2 seconds
    before = ctrl.clock_state()
    assert before.remaining_for(1) == 58000
    ctrl.make_ai_move(_stub_runner())
    assert ctrl.session.state.ply_count == 2
    assert not ctrl.ai_move_needed()
    after = ctrl.clock_state()
    assert after.active_owner == 0  # human again
    assert after.remaining_for(1) == 68000  # 60000 - 2000 + 10000 increment


def test_ai_plays_first_when_ai_is_side_0():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(1))
    assert ctrl.ai_move_needed()
    ctrl.make_ai_move(_stub_runner())
    assert ctrl.session.state.ply_count == 1
    assert ctrl.session.state.position.side_to_move == 1


def test_controller_ai_limits_preserve_zero_fixed_node_budget():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            participants=(ParticipantKind.AI, ParticipantKind.AI),
            time_control=TimeControl(mode=TimeControlMode.NONE),
            ai_config=ThinkingConfig(strategy="fixed_nodes", max_nodes=0),
        )
    )
    limits = ctrl.ai_limits()
    assert limits.max_nodes == 0
    assert limits.max_time_seconds is None


def test_ai_root_declaration_finishes_match_through_session_and_stops_clock(tmp_path):
    from test_generic_declaration_semantics import _claim_ruleset
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits

    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    assert ctrl.new_game_from_ruleset(_claim_ruleset())
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(60, 10),
                owner1=SideTimeConfig(60, 10),
            ),
            ThinkingConfig(),
        )
    )
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    before_state = ctrl.session.state
    now.t += 2.0
    decision = AlphaBetaPlayer(
        ctrl.compiled, use_disk_cache=False
    ).choose_action(
        snapshot.session,
        SearchLimits(
            max_depth=2,
            max_nodes=10_000,
            max_time_seconds=5,
            quiescence_max_depth=0,
        ),
        cancel_token=token,
    )
    assert decision.choice_kind == "DECLARATION"
    assert decision.action is None
    assert decision.declaration.outcome == "WIN"

    assert ctrl.finish_ai_move(decision, snapshot)

    assert ctrl.session.state == before_state
    # Declarations end the session without synthesizing a board-action ply.
    assert ctrl.session.result.status.value == "declaration"
    assert ctrl.session.result.winner == 0
    assert ctrl.session.result.declaration_id == decision.declaration.declaration_id
    assert not ctrl.ai_move_needed()
    assert not ctrl.ai_thinking
    assert not ctrl.clock_state().running
    record = ctrl.session.to_record()
    assert record.declaration.declaration_id == "opaque_claim"
    assert not ctrl.can_undo  # a root declaration adds no synthetic action
    from generic_chess.session.session import GameSession

    replayed = GameSession.replay(ctrl.compiled, record)
    assert replayed.result == ctrl.session.result

    record_path = tmp_path / "ai-root-declaration.json"
    assert ctrl.save_record(str(record_path))
    restored = _controller()
    assert restored.new_game_from_ruleset(_claim_ruleset())
    assert restored.open_record(str(record_path))
    assert restored.session.result == ctrl.session.result
    assert restored.session.state == before_state


@pytest.mark.parametrize(
    ("outcome", "winner"),
    (("LOSS", 1), ("RESTART", None), ("NO_CONTEST", None)),
)
def test_ai_selected_declaration_preserves_authoritative_outcome(outcome, winner):
    from dataclasses import replace
    from types import SimpleNamespace
    from test_generic_declaration_semantics import _claim_ruleset
    from generic_chess.core.declarations import assess_declaration
    from generic_chess.rules.schema import RuleDeclarationOutcomeBand

    ruleset = _claim_ruleset()
    bands = (
        (RuleDeclarationOutcomeBand(100, "WIN"),)
        if outcome == "LOSS"
        else (RuleDeclarationOutcomeBand(0, outcome),)
    )
    declaration = replace(
        ruleset.declarations[0],
        outcome_bands=bands,
    )
    ctrl = _controller()
    assert ctrl.new_game_from_ruleset(
        replace(ruleset, declarations=(declaration,))
    )
    ctrl.start_match(_match_config(1))
    assessment = assess_declaration(
        ctrl.session.state, ctrl.compiled, "opaque_claim"
    )
    assert assessment.outcome == outcome
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    decision = SimpleNamespace(
        action=None,
        choice_kind="DECLARATION",
        declaration=assessment,
    )

    assert ctrl.finish_ai_move(decision, snapshot)
    assert ctrl.session.result.status.value == "declaration"
    assert ctrl.session.result.winner == winner
    assert ctrl.session.result.declaration_outcome == outcome
    assert not ctrl.ai_move_needed()


def test_ai_rejects_unavailable_root_declaration_without_ending_session():
    from types import SimpleNamespace
    from test_generic_declaration_semantics import _claim_ruleset

    ctrl = _controller()
    assert ctrl.new_game_from_ruleset(_claim_ruleset())
    ctrl.start_match(_match_config(1))
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    decision = SimpleNamespace(
        action=None,
        choice_kind="DECLARATION",
        declaration=SimpleNamespace(declaration_id="not_available"),
    )

    assert not ctrl.finish_ai_move(decision, snapshot)
    assert ctrl.session.result.status.value == "ongoing"
    assert ctrl.session.state.ply_count == 0
    assert ctrl.last_error and "cannot submit declaration" in ctrl.last_error
    assert not ctrl.ai_thinking
    assert ctrl.session.state.position.side_to_move == 0
    assert ctrl.ai_stop_requested
    assert not ctrl.ai_move_needed()


def test_ai_rejects_invalid_action_without_automatic_retry():
    from types import SimpleNamespace
    from generic_chess.core.actions import BoardMove

    ctrl = _controller()
    assert ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(1))
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    before = ctrl.session.state

    decision = SimpleNamespace(
        action=BoardMove(Square(1, 0), Square(1, 0)),
        choice_kind="ACTION",
    )

    assert not ctrl.finish_ai_move(decision, snapshot)
    assert ctrl.session.state == before
    assert ctrl.session.state.ply_count == 0
    assert ctrl.last_error and "cannot submit action" in ctrl.last_error
    assert ctrl.ai_stop_requested
    assert not ctrl.ai_move_needed()


def test_actionless_terminal_decision_on_ongoing_session_fails_closed():
    from types import SimpleNamespace

    ctrl = _controller()
    assert ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(1))
    snapshot = ctrl.capture_ai_search(CancellationToken())
    assert snapshot is not None
    before = ctrl.session.state

    # Core/GameSession normally adjudicate terminal roots before an AI turn;
    # this result therefore represents a producer/session disagreement.
    decision = SimpleNamespace(action=None, choice_kind="TERMINAL")

    assert not ctrl.finish_ai_move(decision, snapshot)
    assert ctrl.session.result.status.value == "ongoing"
    assert ctrl.session.state == before
    assert ctrl.last_error == "AI returned no committable action"
    assert ctrl.ai_stop_requested
    assert not ctrl.ai_move_needed()


def test_ai_turn_blocks_human_input():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0))
    _human_move(ctrl)
    ctrl.square_clicked(Square(1, 1))
    assert ctrl.interaction.selected_square is None
    assert ctrl.session.state.ply_count == 1


def test_undo_restores_clock_snapshot():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0, mode=TimeControlMode.FISCHER))
    _human_move(ctrl)
    ctrl.make_ai_move(_stub_runner())
    assert ctrl.clock_state().active_owner == 0
    ctrl.undo()
    assert ctrl.session.state.ply_count == 1
    assert ctrl.clock_state().active_owner == 1  # snapshot after the first move


def test_undo_during_ai_search_cancels_worker_and_discards_late_result():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0))
    _human_move(ctrl)
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    assert ctrl.can_undo
    assert ctrl.ai_thinking

    assert ctrl.undo()
    restored = ctrl.session.state
    assert token.is_cancelled()
    assert not ctrl.ai_thinking
    assert not ctrl.ai_move_needed()

    late_decision = _stub_runner()(snapshot.session, snapshot.limits, token)
    assert not ctrl.finish_ai_move(late_decision, snapshot)
    assert ctrl.session.state == restored
    assert ctrl.session.state.ply_count == 0


def test_redo_during_ai_search_cancels_worker_and_discards_late_result():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0))
    _human_move(ctrl)
    ctrl.make_ai_move(_stub_runner())
    assert ctrl.session.state.ply_count == 2
    assert ctrl.undo()
    assert ctrl.session.state.ply_count == 1

    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    assert ctrl.can_redo
    assert ctrl.ai_thinking

    assert ctrl.redo()
    restored = ctrl.session.state
    assert token.is_cancelled()
    assert not ctrl.ai_thinking
    assert not ctrl.ai_move_needed()

    late_decision = _stub_runner()(snapshot.session, snapshot.limits, token)
    assert not ctrl.finish_ai_move(late_decision, snapshot)
    assert ctrl.session.state == restored
    assert ctrl.session.state.ply_count == 2


def test_restart_resets_clock():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0, mode=TimeControlMode.FISCHER))
    _human_move(ctrl)
    ctrl.make_ai_move(_stub_runner())
    ctrl.restart()
    state = ctrl.clock_state()
    assert state.remaining_ms[0] >= 59000  # freshly reset (ms elapsed tolerance)
    assert state.remaining_ms[1] >= 59000
    assert state.active_owner == 0


def test_human_timeout_does_not_end_match():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0, mode=TimeControlMode.FISCHER))
    now.t += 61.0  # human's 60s main + 1s: fischer clock would be expired
    ctrl.clock_tick()
    # Time controls are display/budget only: the game keeps going.
    assert ctrl.session.result.status.value == "ongoing"
    assert ctrl.session.to_record().resigned_by is None


def test_cancelled_ai_does_not_submit():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0))
    _human_move(ctrl)
    token = CancellationToken()
    token.cancel()
    ctrl.make_ai_move(_stub_runner(), cancel_token=token)
    assert ctrl.session.state.ply_count == 1
    assert not ctrl.ai_thinking


def test_no_ai_trigger_on_terminal_or_human_side():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0))
    ctrl.resign()
    assert not ctrl.ai_move_needed()

    ctrl2 = _controller()
    ctrl2.new_game(seed=42)
    ctrl2.start_match(_match_config(1))
    ctrl2.make_ai_move(_stub_runner())
    assert not ctrl2.ai_move_needed()  # now human side 1 to move


def test_progress_callback_reports_iterations():
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.session.session import GameSession

    ctrl = _controller()
    ctrl.new_game(seed=42)
    player = AlphaBetaPlayer(ctrl.compiled, use_disk_cache=False)
    reports = []
    decision = player.choose_action(
        GameSession(ctrl.compiled),
        SearchLimits(max_depth=3, quiescence_max_depth=2),
        progress_callback=lambda d, n, q: reports.append((d, n, q)),
    )
    assert reports and reports[-1][0] == 3
    assert reports[-1][1:] == (decision.nodes, decision.qnodes)
    assert all(
        main + q > 0
        for _, main, q in reports
    )
    assert all(
        (left_main + left_q) < (right_main + right_q)
        for (_, left_main, left_q), (_, right_main, right_q) in zip(reports, reports[1:])
    )


def _mate_ruleset():
    from generic_chess.core.movement import RayAtom
    from generic_chess.core.pieces import Piece

    n = 8
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(1, "K", "K", False)
    rows[0][2] = Piece(0, "K", "K", False)
    rows[4][1] = Piece(0, "R", "R", False)
    rows[1][5] = Piece(0, "R", "R", False)
    lines = [
        "".join("." if cell is None else ("k" if cell.owner == 1 else cell.base_type_id) for cell in row)
        for row in reversed(rows)
    ]
    return make_ruleset(8, [king_type(), rook], lines=lines)


def test_terminal_pauses_clock():
    from generic_chess.core.actions import BoardMove

    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    ctrl = _controller(clock_now=FakeNow())
    ctrl.new_game_from_ruleset(_mate_ruleset())
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.FISCHER),
            ThinkingConfig(),
        )
    )
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))  # mate in one
    assert ctrl.session.result.status.value == "checkmate"
    assert not ctrl.clock_state().running  # clock stops at game over


def test_ai_timeout_adjudicates_loss():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game_from_ruleset(_mate_ruleset())
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.AI),
            TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(2, 10),
                owner1=SideTimeConfig(2, 10),
            ),
            ThinkingConfig(strategy="fixed_nodes", preset="quick", max_nodes=500),
        )
    )
    ctrl.square_clicked(Square(2, 0))  # mate-ruleset P0 king
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    assert ctrl.clock_state().active_owner == 1  # AI turn, clock running
    now.t += 3.0  # AI's 2s main time exceeded
    ctrl.clock_tick()
    assert ctrl.session.result.status.value == "resignation"
    assert ctrl.session.to_record().resigned_by == 1
    assert ctrl.timeout_owner == 1
    assert not ctrl.ai_move_needed()


def test_ai_result_returned_after_timeout_is_not_committed_without_ui_tick():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.AI),
            TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(2, 10),
                owner1=SideTimeConfig(2, 10),
            ),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    _human_move(ctrl)
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    decision = _stub_runner()(snapshot.session, snapshot.limits, token)

    now.t += 2.0  # Exactly zero expires; the UI timer has not ticked.
    assert ctrl.session.state.ply_count == 1
    assert ctrl.session.result.status.value == "ongoing"
    assert not token.is_cancelled()
    assert ctrl.clock_state().expired_owner == 1

    assert not ctrl.finish_ai_move(decision, snapshot)

    assert ctrl.session.state.ply_count == 1
    assert ctrl.session.to_record().resigned_by == 1
    assert ctrl.timeout_owner == 1
    assert token.is_cancelled()
    assert not ctrl.ai_move_needed()
    assert not ctrl.ai_thinking
    assert not ctrl.clock_state().running


def test_timeout_can_resign_shared_session_during_search_and_cancel_without_mutation():
    """The live UI timeout may cancel a worker while it reads the same session."""
    import threading

    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits

    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    class BlockingEvaluator:
        def __init__(self):
            self.entered = threading.Event()
            self.release = threading.Event()

        def evaluate(self, state):
            self.entered.set()
            if not self.release.wait(5):
                raise TimeoutError("test barrier expired")
            return 0

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0, mode=TimeControlMode.FISCHER))
    _human_move(ctrl)

    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    before = (
        snapshot.session.state,
        snapshot.session.history,
        snapshot.session._search_witnesses,
    )
    evaluator = BlockingEvaluator()
    player = AlphaBetaPlayer(
        ctrl.compiled,
        evaluator_override=evaluator,
        use_disk_cache=False,
        use_native_semantic_legality=False,
    )
    results = {}

    def search():
        try:
            results["decision"] = player.choose_action(
                snapshot.session,
                SearchLimits(
                    max_depth=3,
                    max_nodes=10_000,
                    max_time_seconds=10,
                    quiescence_max_depth=0,
                ),
                cancel_token=token,
            )
        except BaseException as exc:
            results["error"] = exc

    worker = threading.Thread(target=search, daemon=True)
    worker.start()
    try:
        assert evaluator.entered.wait(3), "search did not reach the barrier"
        now.t += 60.0
        ctrl.clock_tick()
        assert snapshot.session.result.status.value == "resignation"
        assert token.is_cancelled()
        assert snapshot.session.state == before[0]
        assert snapshot.session.history == before[1]
        assert snapshot.session._search_witnesses == before[2]
    finally:
        evaluator.release.set()
        worker.join(3)

    assert not worker.is_alive(), "cancelled search failed to return"
    assert "error" not in results
    decision = results["decision"]
    assert decision.termination_reason == "cancelled"
    assert not ctrl.finish_ai_move(decision, snapshot)
    assert snapshot.session.state == before[0]
    assert snapshot.session.history == before[1]
    assert snapshot.session._search_witnesses == before[2]
    assert snapshot.session.result.status.value == "resignation"


def test_ai_declaration_returned_after_timeout_is_not_committed_without_ui_tick():
    from test_generic_declaration_semantics import _claim_ruleset
    from generic_chess.core.declarations import assess_declaration

    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    assert ctrl.new_game_from_ruleset(_claim_ruleset())
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(2, 10),
                owner1=SideTimeConfig(2, 10),
            ),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    declaration = assess_declaration(
        snapshot.session.state, snapshot.session.compiled, "opaque_claim"
    )
    assert declaration.outcome == "WIN"
    decision = SimpleNamespace(
        action=None,
        choice_kind="DECLARATION",
        declaration=declaration,
    )

    now.t += 2.0  # Exactly zero expires; the UI timer has not ticked.
    assert ctrl.session.result.status.value == "ongoing"
    assert ctrl.clock_state().expired_owner == 0

    assert not ctrl.finish_ai_move(decision, snapshot)

    assert ctrl.session.state.ply_count == 0
    assert ctrl.session.to_record().resigned_by == 0
    assert ctrl.timeout_owner == 0
    assert token.is_cancelled()
    assert not ctrl.ai_move_needed()
    assert not ctrl.ai_thinking
    assert not ctrl.clock_state().running


def test_ai_result_returned_at_byoyomi_expiry_is_not_committed_without_ui_tick():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.AI),
            TimeControl(
                mode=TimeControlMode.BYOYOMI,
                owner0=SideTimeConfig(2, 1),
                owner1=SideTimeConfig(2, 1),
            ),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    _human_move(ctrl)
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    decision = _stub_runner()(snapshot.session, snapshot.limits, token)

    now.t += 2.0  # Main time is zero, but the AI still has one overtime second.
    assert ctrl.clock_state().remaining_for(1) == 0
    assert ctrl.clock_state().overtime_for(1) == 1000
    assert ctrl.clock_state().expired_owner is None
    assert ctrl.session.result.status.value == "ongoing"

    now.t += 1.0  # Exactly zero overtime is the inclusive expiration boundary.
    assert ctrl.clock_state().expired_owner == 1
    assert not ctrl.finish_ai_move(decision, snapshot)

    assert ctrl.session.state.ply_count == 1
    assert ctrl.session.to_record().resigned_by == 1
    assert ctrl.timeout_owner == 1
    assert token.is_cancelled()
    assert not ctrl.ai_move_needed()
    assert not ctrl.ai_thinking
    assert not ctrl.clock_state().running


def test_ai_thinking_clock_ticks():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.AI),
            TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(60, 10),
                owner1=SideTimeConfig(60, 10),
            ),
            ThinkingConfig(strategy="fixed_nodes", preset="quick", max_nodes=500),
        )
    )
    _human_move(ctrl)
    assert ctrl.begin_ai_move()
    assert ctrl.clock_state().running  # clock visibly ticks during AI thinking
    assert ctrl.clock_state().active_owner == 1
    before = ctrl.clock_state().remaining_for(1)
    now.t += 1.0
    assert ctrl.clock_state().remaining_for(1) < before


def test_drop_can_save_trapped_king_so_not_terminal():
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.terminal import terminal_result
    from generic_chess.rules.compiler import compile_ruleset

    compiled = compile_ruleset(_mate_ruleset())
    lines = [
        "........",
        "........",
        "........",
        "R.......",  # rank 4: checking rook at (0,4)
        "........",
        "........",
        ".....R..",  # rank 1
        "k.K.....",  # rank 0: trapped black king at (0,0)
    ]
    from conftest import make_state

    state = make_state(compiled, lines, side_to_move=1, hands=([], [("R", 1)]))
    # Even though the king has no square, the hand drop can block the check,
    # so the position is correctly NOT terminal.
    assert legal_actions(state, compiled)
    assert not terminal_result(state, compiled).is_terminal


def test_resign_pauses_clock():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    ctrl = _controller(clock_now=FakeNow())
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.FISCHER),
            ThinkingConfig(),
        )
    )
    ctrl.resign()
    assert not ctrl.clock_state().running


def test_expired_human_can_continue_playing():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.HUMAN),
            TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(2, 10),
                owner1=SideTimeConfig(2, 10),
            ),
            ThinkingConfig(),
        )
    )
    now.t += 3.0
    # Expired clock must not stop the human from playing.
    ctrl.square_clicked(Square(1, 0))
    assert ctrl.interaction.selected_square == Square(1, 0)
    assert ctrl.session.result.status.value == "ongoing"
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    assert ctrl.session.state.ply_count == 1


def test_stale_ai_decision_discarded_after_restart():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    token = CancellationToken()
    assert ctrl.begin_ai_move(token)
    ctrl.restart()  # session replaced while the AI is "thinking"
    decision = _stub_runner()(ctrl.session, ctrl.ai_limits(), token)
    committed = ctrl.finish_ai_move(decision)
    assert not committed
    assert ctrl.session.state.ply_count == 0
    assert not ctrl.ai_thinking


def test_restart_clock_active_owner_matches_initial_side():
    class FakeNow:
        def __init__(self) -> None:
            self.t = 0.0

        def __call__(self) -> float:
            return self.t

    ctrl = _controller(clock_now=FakeNow())
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.HUMAN),
            TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(60, 10),
                owner1=SideTimeConfig(60, 10),
            ),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    _human_move(ctrl)
    assert ctrl.session.state.position.side_to_move == 1
    ctrl.restart()
    state = ctrl.clock_state()
    assert state.active_owner == 0  # initial side, not the stale side-to-move
    assert ctrl.session.state.position.side_to_move == 0
    assert len(ctrl._clock_snapshots) == 1


def test_worker_snapshot_freezes_limits_and_commits():
    class FakeNow:
        def __init__(self) -> None:
            self.t = 0.0

        def __call__(self) -> float:
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(60, 10),
                owner1=SideTimeConfig(60, 10),
            ),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    frozen = snapshot.limits
    now.t += 30.0  # remaining clock time drops
    assert ctrl.ai_limits() != frozen  # live limits moved...
    assert snapshot.limits == frozen  # ...but the snapshot is frozen
    ctrl.finish_ai_move(None, snapshot)  # cleanup
    assert not ctrl.ai_thinking


def test_finish_ai_move_rejects_stale_snapshot():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    ctrl.restart()  # generation/session change invalidates the snapshot
    decision = _stub_runner()(ctrl.session, ctrl.ai_limits(), token)
    assert not ctrl.finish_ai_move(decision, snapshot)
    assert ctrl.session.state.ply_count == 0


def test_same_position_history_mutation_invalidates_inflight_ai_result():
    """Generation guards the path context that the position key omits."""
    from generic_chess.core.actions import action_is_board, action_source_square, action_target_square
    from generic_chess.core.identity import (
        position_identity_key,
        search_state_identity,
    )

    ctrl = _controller()
    assert ctrl.new_game_from_builtin("western_chess")
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    decision = _stub_runner()(snapshot.session, snapshot.limits, token)
    root_key = snapshot.root_key
    root_search_identity = search_state_identity(ctrl.session.state, ctrl.compiled)
    live_session = ctrl.session

    cycle = (
        (Square(1, 0), Square(2, 2)),  # b1-c3
        (Square(1, 7), Square(2, 5)),  # b8-c6
        (Square(2, 2), Square(1, 0)),  # c3-b1
        (Square(2, 5), Square(1, 7)),  # c6-b8
    )
    for source, target in cycle:
        action = next(
            candidate
            for candidate in ctrl.session.legal_actions()
            if action_is_board(candidate)
            and action_source_square(candidate) == source
            and action_target_square(candidate) == target
        )
        assert ctrl.submit_action(action)

    # Position identity alone cannot tell this four-ply path from the root;
    # the controller's generation must reject the old worker decision.
    assert ctrl.session is live_session is snapshot.session
    assert len(ctrl.session.history) == 4
    assert str(
        position_identity_key(ctrl.session.state.position, ctrl.compiled)
    ) == root_key
    assert decision.action in ctrl.session.legal_actions()
    assert search_state_identity(ctrl.session.state, ctrl.compiled) != root_search_identity
    assert snapshot.generation != ctrl._ai_generation
    assert not token.is_cancelled()
    assert not ctrl.finish_ai_move(decision, snapshot)
    assert ctrl.session.state.ply_count == 4
    assert len(ctrl.session.history) == 4


def test_resign_cancels_inflight_ai_search_and_discards_its_result():
    ctrl = _controller()
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0))
    _human_move(ctrl)
    assert ctrl.ai_move_needed()

    token = CancellationToken()
    snapshot = ctrl.capture_ai_search(token)
    assert snapshot is not None
    # Model a worker result that arrives after the user's resignation.
    decision = _stub_runner()(snapshot.session, snapshot.limits, token)

    assert ctrl.resign()
    assert token.is_cancelled()
    assert not ctrl.ai_thinking
    assert ctrl.session.result.status.value == "resignation"
    assert not ctrl.finish_ai_move(decision, snapshot)
    assert ctrl.session.state.ply_count == 1
