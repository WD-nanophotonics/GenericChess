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


def test_timeout_ends_match_as_resignation():
    class FakeNow:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    now = FakeNow()
    ctrl = _controller(clock_now=now)
    ctrl.new_game(seed=42)
    ctrl.start_match(_match_config(0, mode=TimeControlMode.FISCHER))
    now.t += 61.0  # human's 60s main + 1s: fischer -> expired
    ctrl.clock_tick()
    assert ctrl.timeout_owner == 0
    assert ctrl.session.result.status.value == "resignation"
    assert ctrl.session.to_record().resigned_by == 0


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
    player.choose_action(
        GameSession(ctrl.compiled),
        SearchLimits(max_depth=2, quiescence_max_depth=0),
        progress_callback=lambda d, n, q: reports.append((d, n)),
    )
    assert reports and reports[-1][0] == 2
