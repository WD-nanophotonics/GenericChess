"""Small benchmark-admission primitives for generic rulesets."""

from .agent_ladder import AgentLadder
from .game_quality import (
    GameQualityProfile,
    QualityObservation,
    measure_game_quality,
    profile_from_observations,
)
from .minimal_generator import MinimalGeneratedGame, generate_minimal_game, swap_owner_opening
from .tactical_probe import TacticalProbeResult, probe_terminal_only

__all__ = [
    "GameQualityProfile",
    "AgentLadder",
    "MinimalGeneratedGame",
    "QualityObservation",
    "TacticalProbeResult",
    "generate_minimal_game",
    "measure_game_quality",
    "probe_terminal_only",
    "profile_from_observations",
    "swap_owner_opening",
]
