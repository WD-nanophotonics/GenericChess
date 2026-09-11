"""Serializable summaries for static ordinary-piece mate-capacity censuses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MateCapacityProfile:
    sample_id: str
    cell: str
    ruleset_fingerprint: str
    board_size: int
    ordinary_type_multiset: tuple[str, ...]
    anchor_square_count: int
    anchor_square_checkable_fraction: float
    mean_anchor_zone_coverage_fraction: float
    max_anchor_zone_coverage_fraction: float
    geometric_full_net_anchor_fraction: float
    minimum_geometric_attackers_distribution: dict[str, int]
    engine_validated_mate_exists: bool
    engine_validated_mate_anchor_fraction: float
    minimum_validated_ordinary_attackers_distribution: dict[str, int]
    checked_position_count: int
    candidate_position_count: int
    truncation: bool
    canonical_mate_examples: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
