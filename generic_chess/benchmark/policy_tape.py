"""Deterministic common-random policy tapes for bounded benchmark replay."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PolicyTape:
    """A fixed sequence of independent uniform values for one policy ID."""

    policy_id: str
    seed: int
    uniforms: tuple[float, ...]

    @classmethod
    def from_seed(cls, policy_id: str, seed: int, length: int = 32) -> "PolicyTape":
        if length < 1:
            raise ValueError("policy tape length must be positive")
        rng = random.Random(seed)
        return cls(policy_id, seed, tuple(rng.random() for _ in range(length)))

    def uniform(self, move_index: int) -> float:
        if not 0 <= move_index < len(self.uniforms):
            raise IndexError("policy tape move index is out of range")
        return self.uniforms[move_index]

    def choose_index(self, move_index: int, legal_count: int) -> int:
        if legal_count < 1:
            raise ValueError("legal action count must be positive")
        return min(int(self.uniform(move_index) * legal_count), legal_count - 1)
