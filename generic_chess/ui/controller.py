"""UI Controller: the only boundary between the UI and GameSession/Core."""

from __future__ import annotations

from typing import Callable
import time

from ..core.actions import Action, BoardMove, DropMove
from ..core.attacks import is_in_check
from ..core.coordinates import Square, square_to_index
from ..core.keys import position_key
from ..core.pieces import Piece, PieceType
from ..core.position import Position
from ..ai.budget import ThinkingConfig, allocate_search_limits
from ..ai.cancellation import CancellationToken
from ..ai.decision import PlayerDecision
from ..ai.alphabeta.snapshot import SearchSnapshot
from ..ai.limits import SearchLimits
from ..clock import ClockState, MatchClock, TimeControl, TimeControlMode
from ..generation.config import GenerationError, GeneratorConfig
from ..generation.generator import generate_game
from ..rules.compiler import compile_ruleset
from ..rules.schema import RuleSet
from ..rules.serialization import deserialize_ruleset, serialize_ruleset
from ..session.record import GameRecord
from ..session.result import SessionResult, SessionStatus
from ..session.serialization import deserialize_game_record, serialize_game_record
from ..session.session import GameSession, SessionFinishedError, SessionRecordError
from . import view_models as vm
from .adapters import movement_summary, reachable_squares
from .interaction_state import BoardInteractionState
from .match import MatchConfig, ParticipantKind
from .settings import (
    KEY_AUTO_PROMOTE_UNIQUE,
    KEY_BOARD_ORIENTATION,
    KEY_ENABLE_PREVIEW,
)
from .stores import (
    SettingsStore,
)


Listener = Callable[[], None]


class UIController:
    """Owns the live GameSession and all transient interaction state.

    The controller is deliberately Qt-free so its logic is testable headless.
    Every game mutation goes through GameSession public semantics.
    """

    def __init__(
        self,
        settings: SettingsStore | None = None,
        *,
        clock_now: Callable[[], float] | None = None,
    ) -> None:
        self._settings = settings
        self._clock_now = clock_now or time.monotonic
        self._compiled = None
        self._ruleset: RuleSet | None = None
        self._session: GameSession | None = None
        self._display_session: GameSession | None = None
        self._actions: list[Action] = []
        self._redo: list[Action] = []
        self._resigned_by: int | None = None
        self._seed: int | None = None
        self._ruleset_path: str | None = None
        self._record_path: str | None = None
        self._interaction = BoardInteractionState()
        self._type_browse_id: str | None = None
        self._listeners: list[Listener] = []
        self._last_error: str | None = None
        self._match: MatchConfig | None = None
        self._clock: MatchClock | None = None
        self._clock_snapshots: list[ClockState] = []
        self._ai_thinking = False
        self._ai_cancel: CancellationToken | None = None
        self._ai_stop_requested = False
        self._timeout_owner: int | None = None
        self._ai_generation = 0
        self._ai_search_generation = 0
        self._ai_session: GameSession | None = None
        self._ai_root_key: str | None = None
        self._ai_fingerprint: str | None = None

    # ------------------------------------------------------------------ match

    def start_match(self, config: MatchConfig) -> None:
        """Begin a Human vs AI (or any participant) match with a match clock."""
        if self._session is None:
            self._last_error = "load a ruleset before starting a match"
            return
        self._match = config
        self._ai_thinking = False
        self._ai_cancel = None
        self._timeout_owner = None
        self._clock = MatchClock(
            config.time_control,
            active_owner=self._session.state.position.side_to_move,
            now=self._clock_now,
        )
        self._clock_snapshots = [self._clock.state()]
        self._interaction.clear_selection()
        self._type_browse_id = None
        self._last_error = None
        self._notify()

    def _clear_match(self) -> None:
        self._match = None
        self._clock = None
        self._clock_snapshots = []
        self._ai_thinking = False
        self._ai_cancel = None
        self._ai_stop_requested = False
        self._timeout_owner = None

    @property
    def match_active(self) -> bool:
        return self._match is not None

    @property
    def match_config(self) -> MatchConfig | None:
        return self._match

    @property
    def ai_thinking(self) -> bool:
        return self._ai_thinking

    @property
    def ai_stop_requested(self) -> bool:
        return self._ai_stop_requested

    def clock_state(self) -> ClockState | None:
        if self._clock is None:
            return None
        return self._clock.state()

    def clock_tick(self) -> None:
        """Called by the UI timer; detects timeouts without rebuilding everything."""
        self._check_timeout()

    def _check_timeout(self) -> bool:
        """AI forfeits on time; humans are never adjudicated on time."""
        if self._clock is None or self._match is None or self._session is None:
            return False
        state = self._clock.state()
        expired = state.expired_owner
        if expired is None:
            return False
        if self._match.participants[expired] is not ParticipantKind.AI:
            return False  # humans never forfeit on time
        if self._session.result.status.value != "ongoing":
            return False
        if expired != self._session.state.position.side_to_move:
            return False
        try:
            self._session.resign()
        except ValueError:
            return False
        self._bump_ai_generation()
        self._resigned_by = self._session.to_record().resigned_by
        self._timeout_owner = expired
        if self._ai_cancel is not None:
            self._ai_cancel.cancel()
        self._ai_thinking = False
        self._clock.pause()
        self._interaction.clear_selection()
        self._notify()
        return True

    @property
    def timeout_owner(self) -> int | None:
        return self._timeout_owner

    def ai_move_needed(self) -> bool:
        if (
            self._match is None
            or self._session is None
            or self._ai_thinking
            or self._ai_stop_requested
        ):
            return False
        if self._display_session is not None:
            return False
        if self._session.result.status.value != "ongoing":
            return False
        side = self._session.state.position.side_to_move
        return self._match.participants[side] is ParticipantKind.AI

    def make_ai_move(self, runner, cancel_token: CancellationToken | None = None) -> PlayerDecision | None:
        """Run one AI move via the injected runner (View calls this in a worker)."""
        if not self.begin_ai_move(cancel_token):
            return None
        decision = runner(self._session, self.ai_limits(), self._ai_cancel)
        self.finish_ai_move(decision)
        return decision

    def cancel_ai(self) -> None:
        self._ai_stop_requested = True
        if self._ai_cancel is not None:
            self._ai_cancel.cancel()
        self._ai_thinking = False
        self._notify()

    def clear_stop_request(self) -> None:
        self._ai_stop_requested = False
        self._notify()

    def begin_ai_move(self, cancel_token: CancellationToken | None = None) -> bool:
        """Start an AI turn on the calling thread (View calls this on the GUI thread)."""
        if not self.ai_move_needed():
            return False
        self._ai_stop_requested = False
        self._ai_thinking = True
        self._ai_cancel = cancel_token
        self._ai_generation += 1
        self._ai_search_generation = self._ai_generation
        self._ai_session = self._session
        self._ai_fingerprint = self._compiled.ruleset_fingerprint
        self._ai_root_key = position_key(
            self._session.state.position, self._compiled
        )
        self._notify()
        return True

    def capture_ai_search(
        self, cancel_token: CancellationToken | None = None
    ) -> SearchSnapshot | None:
        """Freeze the search input on the GUI thread before spawning a worker."""
        if not self.begin_ai_move(cancel_token):
            return None
        return SearchSnapshot(
            session=self._session,
            limits=self.ai_limits(),
            ruleset_fingerprint=self._ai_fingerprint,
            root_key=self._ai_root_key,
            generation=self._ai_search_generation,
        )

    def ai_limits(self) -> SearchLimits:
        """Build the per-move search limits for the current AI turn (pure)."""
        side = self._session.state.position.side_to_move
        move_number = self._session.state.ply_count + 1
        clock_state = self._clock.state() if self._clock is not None else None
        time_control = (
            self._match.time_control
            if self._clock is not None
            else TimeControl(mode=TimeControlMode.NONE)
        )
        return allocate_search_limits(
            clock_state, time_control, side, move_number, self._match.ai_config
        )

    def finish_ai_move(
        self,
        decision: PlayerDecision | None,
        snapshot: SearchSnapshot | None = None,
    ) -> bool:
        """Commit the worker's decision on the GUI thread; skips cancelled/stale runs."""
        cancelled = self._ai_cancel is not None and self._ai_cancel.is_cancelled()
        snapshot_stale = snapshot is not None and (
            snapshot.generation != self._ai_generation
            or snapshot.root_key != self._ai_root_key
            or snapshot.ruleset_fingerprint != self._ai_fingerprint
        )
        session_same = (
            self._session is not None and self._ai_session is self._session
        )
        fingerprint_same = (
            self._compiled is not None
            and self._ai_fingerprint == self._compiled.ruleset_fingerprint
        )
        root_same = (
            session_same
            and fingerprint_same
            and self._ai_root_key
            == position_key(self._session.state.position, self._compiled)
        )
        stale = (
            self._ai_search_generation != self._ai_generation
            or not root_same
            or snapshot_stale
        )
        committed = False
        if (
            not cancelled
            and not stale
            and decision is not None
            and decision.action is not None
        ):
            committed = self.submit_action(decision.action)
            if committed:
                self._ai_stop_requested = False
        self._ai_thinking = False
        self._ai_cancel = None
        self._notify()
        return committed

    def _bump_ai_generation(self) -> None:
        self._ai_generation += 1

    # ------------------------------------------------------------------ setup

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        """Idempotently remove a listener; absent callbacks are ignored."""
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()

    def new_game(
        self,
        *,
        seed: int = 42,
        board_size: int = 8,
        preset: str = "classic_like",
        hybrid: bool = False,
    ) -> bool:
        try:
            game = generate_game(
                GeneratorConfig(
                    seed=seed,
                    board_size=board_size,
                    setup_preset=preset,
                    allow_hybrid=hybrid,
                )
            )
        except (GenerationError, ValueError) as exc:
            self._last_error = f"cannot generate game: {exc}"
            return False
        self._set_ruleset(game.ruleset, compiled=game.compiled_ruleset, seed=seed, path=None)
        return True

    def new_game_from_ruleset(self, ruleset: RuleSet, path: str | None = None) -> bool:
        try:
            compiled = compile_ruleset(ruleset)
        except ValueError as exc:
            self._last_error = f"invalid ruleset: {exc}"
            return False
        self._set_ruleset(ruleset, compiled=compiled, seed=None, path=path)
        return True

    def open_ruleset(self, path: str) -> bool:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            self._last_error = f"cannot read ruleset file: {exc}"
            return False
        try:
            ruleset = deserialize_ruleset(text)
        except ValueError as exc:
            self._last_error = f"invalid ruleset ({path}): {exc}"
            return False
        if not self.new_game_from_ruleset(ruleset, path=path):
            return False
        self._ruleset_path = path
        self._last_error = None
        return True

    def export_ruleset(self, path: str) -> bool:
        if self._ruleset is None:
            self._last_error = "no ruleset loaded"
            return False
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(serialize_ruleset(self._ruleset) + "\n")
        except OSError as exc:
            self._last_error = f"cannot write ruleset file: {exc}"
            return False
        return True

    def save_record(self, path: str) -> bool:
        if self._session is None:
            self._last_error = "no game in progress"
            return False
        try:
            text = serialize_game_record(self._session.to_record())
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
        except OSError as exc:
            self._last_error = f"cannot write record file: {exc}"
            return False
        self._record_path = path
        self._last_error = None
        self._notify()
        return True

    def open_record(self, path: str) -> bool:
        if self._compiled is None:
            self._last_error = "load a RuleSet before opening a record"
            return False
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            record = deserialize_game_record(text)
            session = GameSession.replay(self._compiled, record)
        except (OSError, SessionRecordError, ValueError) as exc:
            self._last_error = f"cannot open record ({path}): {exc}"
            return False
        self._bump_ai_generation()
        self._session = session
        self._display_session = None
        self._actions = list(record.actions)
        self._redo = []
        self._resigned_by = record.resigned_by
        self._record_path = path
        self._clear_match()
        self._interaction = BoardInteractionState(
            orientation_owner=self._interaction.orientation_owner
        )
        self._last_error = None
        self._notify()
        return True

    def _set_ruleset(
        self,
        ruleset: RuleSet,
        compiled,
        seed: int | None,
        path: str | None,
    ) -> None:
        self._bump_ai_generation()
        self._ruleset = ruleset
        self._compiled = compiled
        self._seed = seed
        self._ruleset_path = path
        self._record_path = None
        self._actions = []
        self._redo = []
        self._resigned_by = None
        self._clear_match()
        self._interaction = BoardInteractionState(
            orientation_owner=self._interaction.orientation_owner
        )
        self._type_browse_id = None
        self._display_session = None
        self._rebuild()
        self._last_error = None
        self._notify()

    def _rebuild(self) -> None:
        if self._compiled is None:
            self._session = None
            return
        record = GameRecord(
            schema_version=1,
            ruleset_fingerprint=self._compiled.ruleset_fingerprint,
            actions=tuple(self._actions),
            resigned_by=self._resigned_by,
        )
        self._session = GameSession.replay(self._compiled, record)
        self._display_session = None

    # ------------------------------------------------------------------ queries

    @property
    def session(self) -> GameSession | None:
        return self._session

    @property
    def compiled(self):
        return self._compiled

    @property
    def ruleset(self) -> RuleSet | None:
        return self._ruleset

    @property
    def interaction(self) -> BoardInteractionState:
        return self._interaction

    @property
    def can_undo(self) -> bool:
        return bool(self._actions) and self._resigned_by is None

    @property
    def can_redo(self) -> bool:
        return bool(self._redo) and self._resigned_by is None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def displayed_position(self) -> Position | None:
        source = self._display_session if self._display_session is not None else self._session
        return source.state.position if source is not None else None

    def displayed_history(self) -> tuple:
        source = self._display_session if self._display_session is not None else self._session
        return source.history if source is not None else ()

    # ------------------------------------------------------------------ actions

    def submit_action(self, action: Action) -> bool:
        if self._check_timeout():
            return False
        if self._session is None or self._display_session is not None:
            self._last_error = "cannot move while viewing history preview"
            return False
        mover = self._session.state.position.side_to_move
        try:
            self._session.submit(action)
        except (ValueError, SessionFinishedError) as exc:
            self._last_error = f"cannot submit action: {exc}"
            return False
        self._bump_ai_generation()
        self._actions.append(action)
        self._redo = []
        if self._match is not None and self._clock is not None:
            self._clock.complete_turn(mover)
            self._clock_snapshots.append(self._clock.state())
            if self._session.result.status is not SessionStatus.ONGOING:
                self._clock.pause()
        self._interaction.clear_selection()
        self._last_error = None
        self._notify()
        return True

    def resign(self) -> bool:
        if self._session is None or self._display_session is not None:
            return False
        try:
            self._session.resign()
        except SessionFinishedError as exc:
            self._last_error = str(exc)
            return False
        self._bump_ai_generation()
        self._resigned_by = self._session.to_record().resigned_by
        if self._match is not None and self._clock is not None:
            self._clock.pause()
        self._interaction.clear_selection()
        self._last_error = None
        self._notify()
        return True

    def restart(self) -> None:
        self._actions = []
        self._redo = []
        self._resigned_by = None
        self._ai_thinking = False
        self._ai_cancel = None
        self._timeout_owner = None
        self._bump_ai_generation()
        self._interaction = BoardInteractionState(
            orientation_owner=self._interaction.orientation_owner
        )
        self._type_browse_id = None
        self._rebuild()
        # Rebuild first so the clock starts on the initial position's side.
        if self._match is not None and self._session is not None:
            self._clock = MatchClock(
                self._match.time_control,
                active_owner=self._session.state.position.side_to_move,
                now=self._clock_now,
            )
            self._clock_snapshots = [self._clock.state()]
        self._notify()

    def undo(self) -> bool:
        if not self._actions or self._resigned_by is not None:
            return False
        self._redo.append(self._actions.pop())
        self._bump_ai_generation()
        if self._match is not None and self._clock is not None and self._clock_snapshots:
            self._clock_snapshots.pop()
            if self._clock_snapshots:
                self._clock.restore(self._clock_snapshots[-1])
        self._ai_thinking = False
        self._ai_cancel = None
        self._interaction = BoardInteractionState(
            orientation_owner=self._interaction.orientation_owner
        )
        self._type_browse_id = None
        self._rebuild()
        self._notify()
        return True

    def redo(self) -> bool:
        if not self._redo or self._resigned_by is not None:
            return False
        self._actions.append(self._redo.pop())
        self._bump_ai_generation()
        if self._match is not None and self._clock is not None:
            mover = (len(self._actions) - 1) % 2
            self._clock.complete_turn(mover)
            self._clock_snapshots.append(self._clock.state())
        self._interaction = BoardInteractionState(
            orientation_owner=self._interaction.orientation_owner
        )
        self._rebuild()
        self._notify()
        return True

    # ------------------------------------------------------------------ interaction

    def square_clicked(self, square: Square) -> None:
        if self._check_timeout():
            return
        if self._ai_thinking:
            return
        self._type_browse_id = None
        pos = self.displayed_position()
        if pos is None:
            return
        if self._match is not None and self._match.participants[pos.side_to_move] is ParticipantKind.AI:
            self._last_error = "AI is to move"
            return
        if self._interaction.pending_promotion_actions:
            return  # a promotion dialog is already open
        if self._display_session is not None:
            self._last_error = "viewing history preview: press Return to Current Position"
            self._notify()
            return
        if self._session.result.status is not SessionStatus.ONGOING:
            return

        piece = pos.board[square_to_index(square, pos.board_size())]
        side = pos.side_to_move

        if self._interaction.selected_hand_piece_type_id is not None:
            drop = next(
                (a for a in self._interaction.legal_actions if _is_drop_to(a, square)), None
            )
            if drop is not None:
                self.submit_action(drop)
            elif piece is not None and piece.owner == side:
                self._select_square(square)
            return

        if self._interaction.selected_square is not None:
            targets = [
                a
                for a in self._interaction.legal_actions
                if _action_to(a) == square
            ]
            if targets:
                self._resolve_target_actions(targets)
                return

        if piece is not None and piece.owner == side:
            self._select_square(square)
        elif piece is not None:
            self._preview_piece(square)

    def _select_square(self, square: Square) -> None:
        self._interaction.clear_selection()
        self._interaction.selected_square = square
        self._interaction.legal_actions = tuple(
            a
            for a in self._session.legal_actions()
            if isinstance(a, BoardMove) and a.from_square == square
        )
        self._notify()

    def _preview_piece(self, square: Square) -> None:
        enabled = bool(self._settings and self._settings.get(KEY_ENABLE_PREVIEW, True))
        if not enabled:
            return
        pos = self.displayed_position()
        self._interaction.clear_selection()
        self._interaction.preview_piece_square = square
        self._interaction.preview_squares = reachable_squares(pos, square, self._compiled)
        self._notify()

    def _resolve_target_actions(self, targets: list[Action]) -> None:
        if len(targets) == 1:
            self.submit_action(targets[0])
            return
        promotions = [a for a in targets if isinstance(a, BoardMove) and a.promotion_target_id]
        plain = [a for a in targets if isinstance(a, BoardMove) and not a.promotion_target_id]
        if (
            self._settings
            and self._settings.get(KEY_AUTO_PROMOTE_UNIQUE, True)
            and not plain
            and len({a.promotion_target_id for a in promotions}) == 1
        ):
            self.submit_action(promotions[0])
            return
        self._interaction.pending_promotion_actions = tuple(targets)
        self._notify()

    def choose_promotion(self, action: Action) -> None:
        self._interaction.pending_promotion_actions = ()
        self.submit_action(action)

    def cancel_promotion(self) -> None:
        self._interaction.pending_promotion_actions = ()
        self._notify()

    def hand_piece_clicked(self, type_id: str) -> None:
        if self._check_timeout():
            return
        if self._ai_thinking:
            return
        self._type_browse_id = None
        if self._session is None or self._display_session is not None:
            return
        if self._session.result.status is not SessionStatus.ONGOING:
            return
        side = self._session.state.position.side_to_move
        if self._match is not None and self._match.participants[side] is ParticipantKind.AI:
            return
        if self._session.state.position.hands[side].count(type_id) <= 0:
            return
        self._interaction.clear_selection()
        self._interaction.selected_hand_piece_type_id = type_id
        self._interaction.legal_actions = tuple(
            a
            for a in self._session.legal_actions()
            if isinstance(a, DropMove) and a.base_type_id == type_id
        )
        self._notify()

    def cancel(self) -> None:
        self._type_browse_id = None
        self._interaction.clear_selection()
        self._interaction.hovered_square = None
        self._notify()

    def flip_board(self) -> None:
        self._interaction.orientation_owner = 1 - self._interaction.orientation_owner
        if self._settings is not None:
            self._settings.set(KEY_BOARD_ORIENTATION, self._interaction.orientation_owner)
        self._notify()

    def set_orientation(self, owner: int) -> None:
        if owner not in (0, 1):
            raise ValueError(f"orientation owner must be 0 or 1, got {owner!r}")
        self._interaction.orientation_owner = owner
        if self._settings is not None:
            self._settings.set(KEY_BOARD_ORIENTATION, owner)
        self._notify()

    def set_hover(self, square: Square | None) -> None:
        self._interaction.hovered_square = square

    def display_ply(self, ply: int) -> bool:
        self._type_browse_id = None
        if self._session is None or not (0 <= ply <= len(self._actions)):
            return False
        record = GameRecord(
            schema_version=1,
            ruleset_fingerprint=self._compiled.ruleset_fingerprint,
            actions=tuple(self._actions[:ply]),
            resigned_by=None,
        )
        try:
            self._display_session = GameSession.replay(self._compiled, record)
        except SessionRecordError as exc:
            self._last_error = f"cannot rebuild history position: {exc}"
            return False
        self._interaction.displayed_ply = ply
        self._interaction.clear_selection()
        self._notify()
        return True

    def return_to_current(self) -> None:
        self._type_browse_id = None
        self._display_session = None
        self._interaction.displayed_ply = None
        self._interaction.clear_selection()
        self._notify()

    # ------------------------------------------------------------------ view models

    def board_view_model(self) -> vm.BoardViewModel | None:
        pos = self.displayed_position()
        if pos is None or self._compiled is None:
            return None
        n = pos.board_size()
        side = pos.side_to_move
        check_side = side if is_in_check(pos, side, self._compiled) else None
        interaction = self._interaction

        move_targets: set[Square] = set()
        capture_targets: set[Square] = set()
        for a in interaction.legal_actions:
            target = _action_to(a)
            if target is None:
                continue
            occupant = pos.board[square_to_index(target, n)]
            if isinstance(a, BoardMove) and occupant is not None and occupant.owner != side:
                capture_targets.add(target)
            else:
                move_targets.add(target)

        preview_set = set(interaction.preview_squares)
        history = self.displayed_history()
        last_from: Square | None = None
        last_to: Square | None = None
        if history:
            last = history[-1].action
            if isinstance(last, BoardMove):
                last_from, last_to = last.from_square, last.to_square
            elif isinstance(last, DropMove):
                last_to = last.to_square

        squares = []
        for idx in range(n * n):
            square = Square(idx % n, idx // n)
            piece = pos.board[idx]
            squares.append(
                vm.SquareViewModel(
                    square=square,
                    piece=piece,
                    is_last_move_from=last_from == square,
                    is_last_move_to=last_to == square,
                    is_selected=interaction.selected_square == square,
                    is_legal_move=square in move_targets,
                    is_legal_capture=square in capture_targets,
                    is_preview=square in preview_set,
                    is_hovered=interaction.hovered_square == square,
                    is_check_anchor=check_side is not None
                    and piece is not None
                    and piece.owner == check_side
                    and self._compiled.types_by_id[piece.current_type_id].is_anchor,
                )
            )
        return vm.BoardViewModel(
            board_size=n,
            squares=tuple(squares),
            side_to_move=side,
            check_side=check_side,
        )

    def game_info(self) -> vm.GameViewModel | None:
        if self._session is None or self._compiled is None:
            return None
        state = self._session.state
        hands = tuple(
            tuple(vm.HandEntry(tid, count) for tid, count in state.position.hands[p].counts)
            for p in (0, 1)
        )
        fp = self._compiled.ruleset_fingerprint
        return vm.GameViewModel(
            side_to_move=state.position.side_to_move,
            ply_count=state.ply_count,
            result=self._session.result,
            hands=hands,
            fingerprint=fp,
            fingerprint_short=fp[:8],
            seed=self._seed,
            ruleset_path=self._ruleset_path,
            record_path=self._record_path,
            board_size=self._compiled.board_size,
            piece_type_count=len(self._compiled.piece_types),
        )

    def history_entries(self) -> tuple[vm.HistoryEntry, ...]:
        return tuple(
            vm.HistoryEntry(
                ply=i + 1,
                player=i % 2,
                action=action,
                label=_action_label(action),
            )
            for i, action in enumerate(self._actions)
        )

    def piece_info(self) -> vm.PieceInfo | None:
        if self._compiled is None:
            return None
        pos = self.displayed_position()
        interaction = self._interaction
        square = interaction.selected_square
        piece: Piece | None = None
        owner: int | None = None
        base = None
        promoted = False
        preview = False
        type_id = None
        if square is not None and pos is not None:
            piece = pos.board[square_to_index(square, pos.board_size())]
        elif interaction.preview_piece_square is not None and pos is not None:
            square = interaction.preview_piece_square
            piece = pos.board[square_to_index(square, pos.board_size())]
            preview = True
        elif interaction.selected_hand_piece_type_id is not None:
            type_id = interaction.selected_hand_piece_type_id

        if piece is not None:
            owner = piece.owner
            base = piece.base_type_id
            promoted = piece.promoted
            type_id = piece.current_type_id

        if type_id is None:
            if self._type_browse_id is not None:
                return self.piece_type_info(self._type_browse_id)
            return None
        pt: PieceType = self._compiled.types_by_id[type_id]

        legal_count = capture_count = promotion_count = None
        if (
            not preview
            and self._session is not None
            and interaction.selected_square == square
            and piece is not None
            and piece.owner == self._session.state.position.side_to_move
        ):
            legal_count = len(interaction.legal_actions)
            capture_count = sum(
                1
                for a in interaction.legal_actions
                if isinstance(a, BoardMove)
                and pos.board[square_to_index(a.to_square, pos.board_size())] is not None
            )
            promotion_count = sum(
                1
                for a in interaction.legal_actions
                if isinstance(a, BoardMove) and a.promotion_target_id is not None
            )
        preview_count = len(interaction.preview_squares) if preview else None
        is_actionable = (
            piece is not None
            and self._session is not None
            and self._display_session is None
            and self._session.result.status is SessionStatus.ONGOING
            and piece.owner == self._session.state.position.side_to_move
        )

        return vm.PieceInfo(
            type_id=type_id,
            name=pt.name,
            owner=owner,
            square=square,
            base_type_id=base,
            promoted=promoted,
            movement_lines=movement_summary(pt),
            legal_action_count=legal_count,
            capture_count=capture_count,
            promotion_count=promotion_count,
            preview_count=preview_count,
            is_actionable=is_actionable,
            is_preview=preview,
        )

    def browse_type(self, type_id: str) -> bool:
        """Enter type-only browsing mode (used by the Rules panel)."""
        if self._compiled is None or type_id not in self._compiled.types_by_id:
            return False
        self._type_browse_id = type_id
        self._notify()
        return True

    def clear_browse(self) -> None:
        if self._type_browse_id is not None:
            self._type_browse_id = None
            self._notify()

    def piece_type_info(self, type_id: str) -> vm.PieceInfo | None:
        """Rule-only info for a piece type (used by the Rules panel)."""
        if self._compiled is None or type_id not in self._compiled.types_by_id:
            return None
        pt = self._compiled.types_by_id[type_id]
        return vm.PieceInfo(
            type_id=type_id,
            name=pt.name,
            owner=None,
            square=None,
            base_type_id=None,
            promoted=False,
            movement_lines=movement_summary(pt),
            legal_action_count=None,
            capture_count=None,
            promotion_count=None,
            preview_count=None,
            is_actionable=False,
            is_preview=False,
        )

    def rules_info(self) -> vm.RulesInfo | None:
        if self._ruleset is None or self._compiled is None:
            return None
        relations = []
        for pt in self._compiled.piece_types:
            if pt.is_promotable:
                relations.append(f"{pt.type_id} -> {', '.join(pt.promotion_target_ids)}")
        n = self._compiled.board_size
        drop_parts = []
        for pt in self._compiled.piece_types:
            if pt.is_anchor:
                continue
            allowed = sum(1 for b in self._compiled.drop_allowed[pt.type_id][0] if b)
            drop_parts.append(f"{pt.type_id}: {allowed}/{n * n}")
        terminal = (
            f"stalemate={self._compiled.stalemate_result}, "
            f"repetition_limit={self._compiled.repetition_limit}, "
            f"max_ply={self._compiled.max_ply}"
        )
        types = tuple(
            (pt.type_id, pt.name, movement_summary(pt))
            for pt in self._compiled.piece_types
        )
        return vm.RulesInfo(
            board_size=n,
            seed=self._seed,
            fingerprint=self._compiled.ruleset_fingerprint,
            piece_type_count=len(self._compiled.piece_types),
            promotion_relations=tuple(relations),
            drop_summary="; ".join(drop_parts),
            terminal_summary=terminal,
            initial_entity_count=self._compiled.initial_entity_count,
            piece_types=types,
        )


def _action_to(action: Action) -> Square | None:
    if isinstance(action, BoardMove):
        return action.to_square
    if isinstance(action, DropMove):
        return action.to_square
    return None


def _is_drop_to(action: Action, square: Square) -> bool:
    return isinstance(action, DropMove) and action.to_square == square


def _action_label(action: Action) -> str:
    if isinstance(action, DropMove):
        return f"drop {action.base_type_id}@{action.to_square}"
    base = f"{action.from_square}-{action.to_square}"
    if action.promotion_target_id is not None:
        return f"{base}={action.promotion_target_id}"
    return base
