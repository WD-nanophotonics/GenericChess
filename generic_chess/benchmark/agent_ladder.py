"""Admission-facing agent ladder interface.

F86A registers names and contracts only.  Search budgets and real-game
calibration are intentionally deferred to F86B.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Agent(Protocol):
    def choose_action(self, session):
        """Return one legal action for the supplied session."""


@dataclass(frozen=True, slots=True)
class AgentSpec:
    name: str
    description: str
    node_budget: int | None = None


DEFAULT_AGENT_LADDER = (
    AgentSpec("random_legal", "uniformly sample a legal action"),
    AgentSpec("very_shallow", "very-shallow tactical probe"),
    AgentSpec("low_node", "low-node search agent", None),
    AgentSpec("medium_node", "medium-node search agent", None),
)


@dataclass(frozen=True, slots=True)
class AgentLadder:
    specs: tuple[AgentSpec, ...] = DEFAULT_AGENT_LADDER

    def __post_init__(self) -> None:
        names = [spec.name for spec in self.specs]
        if len(names) != len(set(names)):
            raise ValueError("agent ladder names must be unique")

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.specs)

    def require(self, name: str) -> AgentSpec:
        for spec in self.specs:
            if spec.name == name:
                return spec
        raise KeyError(f"unknown agent ladder entry {name!r}")

    def skill_discrimination(self, scores: dict[str, float]) -> float | None:
        """Return an order-aware adjacent advantage, or ``None`` if incomplete."""
        if not all(name in scores for name in self.names):
            return None
        advantages = [scores[stronger] - scores[weaker] for weaker, stronger in zip(self.names, self.names[1:])]
        if not all(advantage > 0 for advantage in advantages):
            return 0.0
        return sum(advantages) / len(advantages)

    def evaluate_adjacent_matchups(self, scores: dict[str, float]) -> dict[str, object] | None:
        """Summarize adjacent paired results in configured strength order."""
        if not all(name in scores for name in self.names):
            return None
        labels = [f"{weaker}>{stronger}" for weaker, stronger in zip(self.names, self.names[1:])]
        advantages = [scores[stronger] - scores[weaker] for weaker, stronger in zip(self.names, self.names[1:])]
        return {
            "adjacent_advantages": dict(zip(labels, advantages)),
            "minimum_adjacent_advantage": min(advantages),
            "mean_adjacent_advantage": sum(advantages) / len(advantages),
            "monotonic": all(advantage > 0 for advantage in advantages),
            "skill_discrimination": self.skill_discrimination(scores),
        }
