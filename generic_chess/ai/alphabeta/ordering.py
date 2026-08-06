"""Generic move ordering (no chess-specific knowledge).

Two orderers are available:

* :class:`MoveOrderer` - the legacy full-sort orderer (TT, captures,
  promotions, killers, countermove, history) used by default;
* :class:`StagedMovePicker` - a single-pass staged iterator enabled through
  ``SearchTuning.use_staged_move_picker`` (TT, good captures, promotions,
  killer/countermove, history buckets, bad captures).

A checking-action stage is intentionally deferred: classifying a move as
checking requires a per-action legality/attack probe (a full movegen each),
which is too expensive for the generic hot path.
"""

from __future__ import annotations

from ...core.actions import Action, BoardMove
from ...core.coordinates import square_to_index
from ...core.position import GameState
from ..evaluation.evaluator import Evaluator
from .statistics import SearchStatistics
from .tuning import SearchTuning


class MoveOrderer:
    """TT move, captures, promotions, killers, history, canonical tie-break."""

    def __init__(self) -> None:
        self._killers: dict[int, list[Action]] = {}
        self._history: dict[tuple[int, Action], int] = {}
        self._countermoves: dict[Action, Action] = {}

    def clear(self) -> None:
        self._killers.clear()
        self._history.clear()
        self._countermoves.clear()

    def record_killer(self, depth: int, action: Action) -> None:
        killers = self._killers.setdefault(depth, [])
        if action in killers:
            killers.remove(action)
        killers.insert(0, action)
        del killers[2:]

    def record_history(
        self, player: int, action: Action, tuning: SearchTuning
    ) -> None:
        key = (player, action)
        self._history[key] = min(self._history.get(key, 0) + 1, tuning.history_max)

    def record_countermove(self, previous_action: Action, response: Action) -> None:
        """Remember the reply to ``previous_action`` that caused a beta cutoff."""
        self._countermoves[previous_action] = response

    def countermove_for(self, previous_action: Action | None) -> Action | None:
        if previous_action is None:
            return None
        return self._countermoves.get(previous_action)

    def history_value(self, player: int, action: Action) -> int:
        return self._history.get((player, action), 0)

    def order(
        self,
        state: GameState,
        actions: list[Action],
        evaluator: Evaluator,
        depth: int,
        tt_move: Action | None,
        prev_action: Action | None,
        tuning: SearchTuning,
    ) -> list[Action]:
        n = state.position.board_size()
        side = state.position.side_to_move
        killers = self._killers.get(depth, [])
        counter = self.countermove_for(prev_action) if tuning.use_countermove else None

        def priority(action: Action) -> int:
            if tt_move is not None and action == tt_move:
                return -1000
            if isinstance(action, BoardMove):
                occupant = state.position.board[square_to_index(action.to_square, n)]
                if occupant is not None and occupant.owner != side:
                    mover = state.position.board[square_to_index(action.from_square, n)]
                    return -100 - evaluator.capture_order_value(mover, occupant)
                if action.promotion_target_id is not None:
                    return -60
            if counter is not None and action == counter:
                return -40
            if action in killers:
                return -30
            return -min(self.history_value(side, action), 20)

        return sorted(actions, key=lambda a: (priority(a), str(a)))


class StagedMovePicker:
    """Single-pass staged action iterator.

    Actions are classified once into cheap buckets instead of computing an
    expensive per-action feature and sorting everything; stages are then
    yielded lazily so a cutoff never pays for ordering the remaining moves.
    """

    STAGES = ("tt", "good_capture", "promotion", "killer_counter", "quiet", "bad_capture")

    def __init__(
        self,
        state: GameState,
        actions: list[Action],
        evaluator: Evaluator,
        depth: int,
        tt_move: Action | None,
        prev_action: Action | None,
        orderer: MoveOrderer,
        tuning: SearchTuning,
        stats: SearchStatistics,
    ) -> None:
        self._stats = stats
        stats.move_picker_generated += len(actions)
        n = state.position.board_size()
        side = state.position.side_to_move
        killers = orderer._killers.get(depth, [])
        counter = orderer.countermove_for(prev_action) if tuning.use_countermove else None

        tt_stage: list[Action] = []
        good: list[Action] = []
        promotions: list[Action] = []
        killer_counter: list[Action] = []
        buckets: list[list[Action]] = [[] for _ in range(max(1, tuning.quiet_buckets))]
        bad: list[Action] = []

        for action in actions:
            if tt_move is not None and action == tt_move:
                tt_stage.append(action)
                continue
            if isinstance(action, BoardMove):
                occupant = state.position.board[square_to_index(action.to_square, n)]
                if occupant is not None and occupant.owner != side:
                    mover = state.position.board[square_to_index(action.from_square, n)]
                    delta = evaluator.capture_order_value(mover, occupant)
                    (good if delta >= 0 else bad).append(action)
                    continue
                if action.promotion_target_id is not None:
                    promotions.append(action)
                    continue
            if action in killers or (counter is not None and action == counter):
                if counter is not None and action == counter:
                    stats.countermove_hits += 1
                killer_counter.append(action)
                continue
            value = orderer.history_value(side, action)
            bucket = min(
                len(buckets) - 1, value.bit_length() // 3
            ) if value else 0
            buckets[bucket].append(action)

        good.sort(
            key=lambda a: evaluator.capture_order_value(
                state.position.board[square_to_index(a.from_square, n)],
                state.position.board[square_to_index(a.to_square, n)],
            ),
            reverse=True,
        )
        promotions.sort(
            key=lambda a: evaluator.type_value(a.promotion_target_id),
            reverse=True,
        )
        bad.sort(
            key=lambda a: evaluator.capture_order_value(
                state.position.board[square_to_index(a.from_square, n)],
                state.position.board[square_to_index(a.to_square, n)],
            ),
            reverse=True,
        )
        quiet = [a for bucket in reversed(buckets) for a in bucket]
        self._stages = [
            ("tt", tt_stage),
            ("good_capture", good),
            ("promotion", promotions),
            ("killer_counter", killer_counter),
            ("quiet", quiet),
            ("bad_capture", bad),
        ]

    def __iter__(self):
        stats = self._stats
        for name, stage in self._stages:
            for action in stage:
                stats.move_picker_yielded += 1
                stats.move_picker_yielded_by_stage[name] = (
                    stats.move_picker_yielded_by_stage.get(name, 0) + 1
                )
                yield action
