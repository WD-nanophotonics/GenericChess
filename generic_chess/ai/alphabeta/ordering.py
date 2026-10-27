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

import time

from ...core.actions import (
    Action,
    action_is_board,
    action_promotion_target_id,
    action_source_square,
    action_target_square,
)
from ...core.coordinates import square_to_index
from ...core.position import GameState
from ..evaluation.evaluator import Evaluator
from .statistics import SearchStatistics
from .tuning import SearchTuning


class MoveOrderer:
    """TT move, captures, promotions, killers, history, canonical tie-break."""

    def __init__(self, compiled=None, stats=None) -> None:
        self._killers: dict[int, list[Action]] = {}
        self._history: dict[tuple[int, Action], int] = {}
        self._countermoves: dict[Action, Action] = {}
        self._geometry_targets = None
        self._geometry_compiled = compiled
        self._geometry_ready = False
        self._geometry_stats = stats
        self._relative_allowed = None
        self._relative_attempts = None
        self._relative_cutoffs = None

    def clear(self) -> None:
        self._killers.clear()
        self._history.clear()
        self._countermoves.clear()
        if self._relative_attempts is not None:
            self._relative_attempts.clear()
            self._relative_cutoffs.clear()

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
        if tuning.use_relative_history and self._relative_allowed:
            self._relative_cutoffs[key] = self._relative_cutoffs.get(key, 0) + 1
            if self._geometry_stats is not None:
                self._geometry_stats.relative_history_cutoffs += 1

    def record_attempt(self, player, action):
        """One entered main-node action, not each PVS re-search or Q visit."""
        if not self._relative_allowed:
            return
        key = player, action
        self._relative_attempts[key] = self._relative_attempts.get(key, 0) + 1
        if self._geometry_stats is not None:
            self._geometry_stats.relative_history_attempts += 1
            self._geometry_stats.relative_history_entries = len(self._relative_attempts)

    def relative_history_value(self, player, action):
        key = player, action
        if self._relative_attempts is None:
            return 0.5
        return (self._relative_cutoffs.get(key, 0) + 1) / (self._relative_attempts.get(key, 0) + 2)

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
        *,
        checkpoint=None,
    ) -> list[Action]:
        n = state.position.board_shape
        side = state.position.side_to_move
        killers = self._killers.get(depth, [])
        counter = self.countermove_for(prev_action) if tuning.use_countermove else None

        def priority(action: Action) -> int:
            if tt_move is not None and action == tt_move:
                return -1000
            if action_is_board(action):
                occupant = state.position.board[square_to_index(action_target_square(action), n)]
                if occupant is not None and occupant.owner != side:
                    mover = state.position.board[square_to_index(action_source_square(action), n)]
                    return -100 - evaluator.capture_order_value(mover, occupant)
                if action_promotion_target_id(action) is not None:
                    return -60
            if counter is not None and action == counter:
                return -40
            if action in killers:
                return -30
            return -min(self.history_value(side, action), 20)

        # TT priority is structural: evaluator capture values have no fixed scale.
        ordered = sorted(actions, key=lambda a: (a != tt_move, priority(a), str(a)))
        if depth <= 0 or not (tuning.use_quiet_geometric_coverage or tuning.use_relative_history):
            return ordered
        if tuning.use_relative_history and self._relative_allowed is None:
            from ...core.search_runtime import _plain_leaper_hash_patterns
            if checkpoint is not None:
                checkpoint()
            self._relative_allowed = (self._geometry_compiled is not None
                and _plain_leaper_hash_patterns(self._geometry_compiled) is not None)
            if self._relative_allowed:
                self._relative_attempts = {}
                self._relative_cutoffs = {}
        slots = [i for i, a in enumerate(ordered)
                 if a != tt_move and a != counter and a not in killers
                 and action_is_board(a) and action_promotion_target_id(a) is None
                 and state.position.board[square_to_index(action_target_square(a), n)] is None]
        if len(slots) < 2:
            return ordered
        if tuning.use_relative_history:
            if not self._relative_allowed:
                return ordered
            quiet = [ordered[i] for i in slots]
            replacement = sorted(quiet, key=lambda a: -self.relative_history_value(side, a))
            if self._geometry_stats is not None:
                self._geometry_stats.relative_history_reorders += replacement != quiet
            for i, action in zip(slots, replacement):
                ordered[i] = action
            return ordered
        # Build inside the main-search abort boundary, never in _Context's
        # constructor (which precedes the root fallback/abort handlers).
        if not self._geometry_ready:
            begin = time.perf_counter()
            try:
                table = (_quiet_geometry_targets(self._geometry_compiled, checkpoint)
                         if self._geometry_compiled is not None else None)
            finally:
                if self._geometry_stats is not None:
                    self._geometry_stats.quiet_geometry_build_seconds += time.perf_counter() - begin
            self._geometry_targets = table  # publish only a complete table
            self._geometry_ready = True
            if self._geometry_stats is not None and table is not None:
                self._geometry_stats.quiet_geometry_target_entries = sum(len(v) for v in table.values())
        if self._geometry_targets is None:
            return ordered
        if checkpoint is not None:
            checkpoint()
        # Enemy source/current type are unchanged by the admitted quiet move.
        # This is geometry, not a set of legal captures or safe destinations.
        covered = set()
        for source, piece in enumerate(state.position.board):
            if checkpoint is not None:
                checkpoint()
            if piece is not None and piece.owner != side:
                covered.update(self._geometry_targets.get(
                    (piece.owner, piece.current_type_id, source), ()))
        quiet = [ordered[i] for i in slots]
        flags = [square_to_index(action_target_square(a), n) in covered for a in quiet]
        replacement = [a for a, flag in zip(quiet, flags) if not flag]
        replacement.extend(a for a, flag in zip(quiet, flags) if flag)
        if self._geometry_stats is not None:
            self._geometry_stats.quiet_geometry_calls += 1
            self._geometry_stats.quiet_geometry_reorders += replacement != quiet
        for i, action in zip(slots, replacement):
            ordered[i] = action
        return ordered


def _quiet_geometry_targets(compiled, checkpoint=None):
    """Query-owned bounded geometry table, admitted from executable IR only."""
    from ...core.search_runtime import _plain_leaper_hash_patterns

    # Keep opt-in preprocessing interruptible in practice; unsupported larger
    # boards retain the baseline rather than allocating an unbounded table.
    shape = getattr(compiled, 'board_shape', None)
    if shape is None or shape.area > 64:
        return None
    if checkpoint is not None:
        checkpoint()
    if _plain_leaper_hash_patterns(compiled) is None:
        return None
    targets = {}
    ir = compiled.ir
    for pattern in ir.patterns:
        if checkpoint is not None:
            checkpoint()
        if pattern.target.kind != "target_enemy":
            continue
        for tid in pattern.type_ids:
            for gid in pattern.geometry_ids:
                geometry = ir.geometry[gid]
                if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                    continue
                for owner in (0, 1):
                    for source, path in geometry.paths.get(str(owner), {}).items():
                        if checkpoint is not None:
                            checkpoint()
                        if path:
                            targets.setdefault((owner, tid, source), set()).add(path[0])
    return {key: frozenset(value) for key, value in targets.items()}


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
        n = state.position.board_shape
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
            if action_is_board(action):
                occupant = state.position.board[square_to_index(action_target_square(action), n)]
                if occupant is not None and occupant.owner != side:
                    mover = state.position.board[square_to_index(action_source_square(action), n)]
                    delta = evaluator.capture_order_value(mover, occupant)
                    (good if delta >= 0 else bad).append(action)
                    continue
                if action_promotion_target_id(action) is not None:
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
                state.position.board[square_to_index(action_source_square(a), n)],
                state.position.board[square_to_index(action_target_square(a), n)],
            ),
            reverse=True,
        )
        promotions.sort(
            key=lambda a: evaluator.type_value(action_promotion_target_id(a)),
            reverse=True,
        )
        bad.sort(
            key=lambda a: evaluator.capture_order_value(
                state.position.board[square_to_index(action_source_square(a), n)],
                state.position.board[square_to_index(action_target_square(a), n)],
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
