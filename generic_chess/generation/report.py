"""Generation report and result container."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.coordinates import Square
from ..rules.compiled import CompiledRuleSet
from ..rules.schema import RuleSet
from .filters import FilterResult


@dataclass(frozen=True, slots=True)
class PieceTypeReport:
    type_id: str
    name: str
    movement_atoms: tuple[str, ...]
    is_promotable: bool
    promotion_target_ids: tuple[str, ...]
    promotion_zone: tuple[Square, ...]  # player 0 perspective
    mandatory_promotion: tuple[Square, ...]
    drop_mask: tuple[bool, ...]
    average_mobility: float


@dataclass(frozen=True, slots=True)
class GenerationReport:
    seed: int
    preset: str
    board_size: int
    generation_attempts: int
    opening_legal_move_count: int
    piece_type_reports: tuple[PieceTypeReport, ...]
    filter_results: tuple[FilterResult, ...]


@dataclass(frozen=True, slots=True)
class GeneratedGame:
    ruleset: RuleSet
    compiled_ruleset: CompiledRuleSet
    generation_report: GenerationReport
