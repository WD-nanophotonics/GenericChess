"""Mutable search statistics (hot-path counters)."""

from __future__ import annotations

from dataclasses import dataclass


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
