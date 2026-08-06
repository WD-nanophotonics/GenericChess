"""Player decision result."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.actions import Action


@dataclass(frozen=True, slots=True)
class PlayerDecision:
    """Result of one ``Player.choose_action`` call.

    ``action`` is ``None`` only for terminal positions.  Scores are always in
    the side-to-move perspective of the root position.
    """

    action: Action | None
    score: int
    principal_variation: tuple[Action, ...]
    completed_depth: int
    selective_depth: int
    nodes: int
    qnodes: int
    elapsed_seconds: float
    tt_probes: int
    tt_hits: int
    tt_cutoffs: int
    beta_cutoffs: int
    evaluation_profile_cache_hit: bool
    termination_reason: str
    # Fine-grained diagnostics (0.6.0 search lab).
    q_depth_truncations: int = 0
    q_budget_truncations: int = 0
    q_evasion_truncations: int = 0
    pvs_null_window_searches: int = 0
    pvs_researches: int = 0
    aspiration_fail_low: int = 0
    aspiration_fail_high: int = 0
    aspiration_researches: int = 0
    root_scan_nodes: int = 0
    root_scan_used_fallback: bool = False
    move_picker_generated: int = 0
    move_picker_yielded: int = 0
    move_picker_yielded_by_stage: dict[str, int] = field(default_factory=dict)
    ordering_calls: int = 0
    ordered_moves: int = 0
    ordering_seconds: float = 0.0
    legal_generation_calls: int = 0
    legal_generation_seconds: float = 0.0
    evaluation_calls: int = 0
    evaluation_seconds: float = 0.0
    countermove_hits: int = 0
    mate_pruning_cutoffs: int = 0
