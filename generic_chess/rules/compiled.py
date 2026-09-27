"""The immutable, precomputed form of a RuleSet."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from ..core.coordinates import BoardShape, Square
from ..core.pieces import PieceType
from ..core.position import Position


@dataclass(frozen=True, slots=True)
class CompiledAutomaticAdjudication:
    """Immutable execution form of an automatic ply adjudication."""

    adjudication_id: str
    trigger_ply: int
    outcome: str
    continuation_policy: str


@dataclass(frozen=True, slots=True)
class CompiledConsecutiveActionAdjudication:
    """Execution form of a consecutive action-class terminal policy."""

    action_class: str
    threshold: int
    outcome: str


@dataclass(frozen=True, slots=True)
class CompiledNoProgressDraw:
    """Execution form of a generic automatic no-progress draw rule."""

    threshold_plies: int
    reset_on_capture: bool
    reset_mover_type_ids: tuple[str, ...] = ()
    outcome: str = "DRAW"


@dataclass(frozen=True, slots=True)
class CompiledRepeatedCycleTargetCondition:
    """Compiled actor selector and result for a repeated-cycle condition."""

    actor: int
    outcome: str = "actor_loss"


@dataclass(frozen=True, slots=True)
class CompiledRuleSet:
    """Everything the core kernel needs to reason about one game.

    All movement tables are keyed ``[type_id][player][square_index]`` with
    ``square_index = rank * n + file``.  Movement tables for leap/ray atoms
    are aligned with ``piece_types`` atom order; the entry for an atom of the
    other kind is the empty tuple.

    * ``leap_targets[type][player][sq][atom]``: leap destinations (bounds only).
    * ``ray_paths[type][player][sq][atom]``: ordered empty-board ray path.
    * ``empty_mobility[type][player][sq]``: all empty-board destinations.
    * ``empty_forward_mobility``: the advancing subset of the above.
    * ``drop_allowed[type][player][sq]``: per-square drop mask (bool).
    * ``promotion_allowed[base][player]``: frozenset of ``(from, to)`` pairs.
    * ``promotion_forced[base][player]``: frozenset of destination squares.
    """

    ruleset_fingerprint: str
    board_size: int
    piece_types: tuple[PieceType, ...]
    types_by_id: Mapping[str, PieceType]
    initial_position: Position
    initial_entity_count: int

    leap_targets: Mapping[str, tuple[tuple[tuple[tuple[Square, ...], ...], ...], ...]]
    ray_paths: Mapping[str, tuple[tuple[tuple[tuple[Square, ...], ...], ...], ...]]
    empty_mobility: Mapping[str, tuple[tuple[tuple[Square, ...], ...], ...]]
    empty_forward_mobility: Mapping[str, tuple[tuple[tuple[Square, ...], ...], ...]]
    drop_allowed: Mapping[str, tuple[tuple[bool, ...], ...]]
    promotion_allowed: Mapping[str, tuple[frozenset[tuple[Square, Square]], ...]]
    promotion_forced: Mapping[str, tuple[frozenset[Square], ...]]

    repetition_limit: int
    max_ply: int
    stalemate_result: str
    repetition_policy: str = "draw"
    automatic_adjudications: tuple[CompiledAutomaticAdjudication, ...] = ()
    declarations: tuple[object, ...] = ()
    capture_disposition: str = "capture_to_hand"
    pass_enabled: bool = False
    consecutive_action_adjudications: tuple[CompiledConsecutiveActionAdjudication, ...] = ()
    initial_setup_positions: Mapping[str, Position] = field(default_factory=dict)
    repeated_cycle_target_conditions: tuple[CompiledRepeatedCycleTargetCondition, ...] = ()
    no_progress_draw: CompiledNoProgressDraw | None = None


@dataclass(frozen=True, slots=True)
class CompiledGeometryCarrier:
    """Immutable schema/geometry product; deliberately not executable."""

    ruleset_fingerprint: str
    board_shape: BoardShape
    types_by_id: Mapping[str, PieceType]
    initial_position: Position
    leap_targets: Mapping[str, tuple]
    ray_paths: Mapping[str, tuple]
    empty_mobility: Mapping[str, tuple]
    empty_forward_mobility: Mapping[str, tuple]
    initial_setup_positions: Mapping[str, tuple[tuple[object | None, ...], ...]] = field(
        default_factory=dict
    )
