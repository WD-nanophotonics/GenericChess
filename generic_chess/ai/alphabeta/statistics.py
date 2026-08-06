"""Mutable search statistics (hot-path counters)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SearchStatistics:
    nodes: int = 0
    qnodes: int = 0
    tt_probes: int = 0
    tt_hits: int = 0
    tt_cutoffs: int = 0
    beta_cutoffs: int = 0
    completed_depth: int = 0
    selective_depth: int = 0
    termination_reason: str = ""
    # Quiescence truncation reasons.
    q_depth_truncations: int = 0
    q_budget_truncations: int = 0
    q_evasion_truncations: int = 0
    # PVS.
    pvs_null_window_searches: int = 0
    pvs_researches: int = 0
    # Aspiration windows.
    aspiration_fail_low: int = 0
    aspiration_fail_high: int = 0
    aspiration_researches: int = 0
    # Root tactical scan.
    root_scan_nodes: int = 0
    root_scan_seconds: float = 0.0
    root_scan_used_fallback: bool = False
    # Staged move picker.
    move_picker_generated: int = 0
    move_picker_yielded: int = 0
    move_picker_yielded_by_stage: dict[str, int] = field(default_factory=dict)
    # Ordering / movegen / evaluation timing.
    ordering_calls: int = 0
    ordered_moves: int = 0
    ordering_seconds: float = 0.0
    legal_generation_calls: int = 0
    legal_generation_seconds: float = 0.0
    evaluation_calls: int = 0
    evaluation_seconds: float = 0.0
    # Countermove heuristic.
    countermove_hits: int = 0
    # Mate-distance pruning.
    mate_pruning_cutoffs: int = 0
