"""Small benchmark-admission primitives for generic rulesets."""

from .game_quality import GameQualityProfile, measure_game_quality
from .minimal_generator import MinimalGeneratedGame, generate_minimal_game

__all__ = [
    "GameQualityProfile",
    "MinimalGeneratedGame",
    "generate_minimal_game",
    "measure_game_quality",
]
