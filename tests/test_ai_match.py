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
    player.choose_action(
        GameSession(ctrl.compiled),
        SearchLimits(max_depth=2, quiescence_max_depth=0),
        progress_callback=lambda d, n, q: reports.append((d, n)),
    )
    assert reports and reports[-1][0] == 2


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
