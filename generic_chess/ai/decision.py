"""Player decision result."""

from __future__ import annotations

from dataclasses import dataclass

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
