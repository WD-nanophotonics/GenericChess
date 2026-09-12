"""Small benchmark-admission primitives for generic rulesets."""

from .agent_ladder import AgentLadder
from .game_quality import (
    GameQualityProfile,
    QualityObservation,
    authoritative_reasons,
    measure_game_quality,
    profile_from_observations,
)
from .minimal_generator import MinimalGeneratedGame, generate_minimal_game, swap_owner_opening
from .tactical_probe import TacticalProbeResult, probe_terminal_only
from .strength_response import (
    ACTION_TRACE_SCHEMA,
    DEFAULT_BUDGETS,
    HORIZON_AWARE_PREP_SCHEMA,
    StrengthResponsePrep,
    StrengthResponseResult,
    measure_strength_response,
    prepare_strength_response,
)

__all__ = [
    "GameQualityProfile",
    "AgentLadder",
    "authoritative_reasons",
    "MinimalGeneratedGame",
    "QualityObservation",
    "TacticalProbeResult",
    "generate_minimal_game",
    "measure_game_quality",
    "probe_terminal_only",
    "profile_from_observations",
    "swap_owner_opening",
    "DEFAULT_BUDGETS",
    "ACTION_TRACE_SCHEMA",
    "HORIZON_AWARE_PREP_SCHEMA",
    "StrengthResponsePrep",
    "StrengthResponseResult",
    "measure_strength_response",
    "prepare_strength_response",
]
