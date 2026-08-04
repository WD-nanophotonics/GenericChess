"""Generator configuration and the generation-level error type."""

from __future__ import annotations

from dataclasses import dataclass


class GenerationError(RuntimeError):
    """Raised when the generator cannot produce a valid game."""


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """Configuration for :func:`generic_chess.generation.generator.generate_game`.

    All randomness lives in the generator and uses a local ``random.Random``
    instance seeded by ``seed``; the same config reproduces the same game.
    """

    seed: int
    board_size: int = 8
    setup_preset: str = "classic_like"
    movement_symmetry: str = "bilateral"
    leap_probability: float = 0.5
    ray_probability: float = 0.5
    allow_hybrid: bool = False
    max_leap_delta: int = 3
    max_ray_component: int = 2
    min_atoms_before_mirroring: int = 1
    max_atoms_before_mirroring: int = 4
    require_promotable_type: bool = True
    require_nonpromotable_type: bool = True
    min_opening_legal_moves: int = 1
    max_opening_legal_moves: int = 256
    max_generation_attempts: int = 1000

    def __post_init__(self) -> None:
        if self.board_size < 4:
            raise GenerationError("generator board_size must be >= 4 (2n pieces per side need 4*n squares)")
        if self.setup_preset not in ("classic_like", "bilateral_random", "free_random"):
            raise GenerationError(f"unknown setup_preset {self.setup_preset!r}")
        if self.movement_symmetry not in ("bilateral", "none"):
            raise GenerationError(f"unknown movement_symmetry {self.movement_symmetry!r}")
        if self.leap_probability < 0 or self.ray_probability < 0:
            raise GenerationError("probabilities must be non-negative")
        if self.leap_probability + self.ray_probability <= 0:
            raise GenerationError("leap_probability + ray_probability must be positive")
        if self.max_leap_delta < 1 or self.max_ray_component < 1:
            raise GenerationError("max deltas must be >= 1")
        if self.min_atoms_before_mirroring < 1:
            raise GenerationError("min_atoms_before_mirroring must be >= 1")
        if self.min_atoms_before_mirroring > self.max_atoms_before_mirroring:
            raise GenerationError("min_atoms_before_mirroring must be <= max_atoms_before_mirroring")
        if self.min_opening_legal_moves > self.max_opening_legal_moves:
            raise GenerationError("min_opening_legal_moves must be <= max_opening_legal_moves")
        if self.max_generation_attempts < 1:
            raise GenerationError("max_generation_attempts must be >= 1")
