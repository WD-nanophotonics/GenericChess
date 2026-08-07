"""Replayable TDLeaf training trajectories."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.actions import Action, action_from_dict, action_to_dict
from .features import MaterialFeatureVector
from .serialization import canonical_json, stable_sha256


@dataclass(frozen=True, slots=True)
class TrainingPoint:
    ply: int
    root_position_key: str
    action: Action | None
    exploration: bool
    pv: tuple[Action, ...]
    leaf_position_key: str
    leaf_feature_board: tuple[int, ...]
    leaf_feature_hand: tuple[int, ...]
    leaf_value: float
    completed_depth: int


@dataclass(frozen=True, slots=True)
class TrainingTrajectory:
    ruleset_fingerprint: str
    generation: int
    game_seed: int
    initial_position_key: str
    actions: tuple[Action, ...]
    search_nodes: int
    search_max_depth: int
    points: tuple[TrainingPoint, ...]
    terminal: str
    winner: int | None
    type_ids: tuple[str, ...]

    @property
    def trajectory_id(self) -> str:
        return stable_sha256(self.to_dict())

    @property
    def terminal_z(self) -> float:
        """Owner-0 perspective terminal target (+1/-1/0)."""
        if self.winner is None:
            return 0.0
        return 1.0 if self.winner == 0 else -1.0

    def to_dict(self) -> dict:
        return {
            "ruleset_fingerprint": self.ruleset_fingerprint,
            "generation": self.generation,
            "game_seed": self.game_seed,
            "initial_position_key": self.initial_position_key,
            "actions": [action_to_dict(a) for a in self.actions],
            "search_nodes": self.search_nodes,
            "search_max_depth": self.search_max_depth,
            "terminal": self.terminal,
            "winner": self.winner,
            "type_ids": list(self.type_ids),
            "points": [
                {
                    "ply": p.ply,
                    "root_position_key": p.root_position_key,
                    "action": action_to_dict(p.action) if p.action else None,
                    "exploration": p.exploration,
                    "pv": [action_to_dict(a) for a in p.pv],
                    "leaf_position_key": p.leaf_position_key,
                    "leaf_feature_board": list(p.leaf_feature_board),
                    "leaf_feature_hand": list(p.leaf_feature_hand),
                    "leaf_value": p.leaf_value,
                    "completed_depth": p.completed_depth,
                }
                for p in self.points
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrainingTrajectory":
        return cls(
            ruleset_fingerprint=data["ruleset_fingerprint"],
            generation=int(data["generation"]),
            game_seed=int(data["game_seed"]),
            initial_position_key=data["initial_position_key"],
            actions=tuple(action_from_dict(a) for a in data["actions"]),
            search_nodes=int(data["search_nodes"]),
            search_max_depth=int(data["search_max_depth"]),
            terminal=str(data["terminal"]),
            winner=data["winner"],
            type_ids=tuple(data["type_ids"]),
            points=tuple(
                TrainingPoint(
                    ply=int(p["ply"]),
                    root_position_key=p["root_position_key"],
                    action=action_from_dict(p["action"]) if p["action"] else None,
                    exploration=bool(p["exploration"]),
                    pv=tuple(action_from_dict(a) for a in p["pv"]),
                    leaf_position_key=p["leaf_position_key"],
                    leaf_feature_board=tuple(int(v) for v in p["leaf_feature_board"]),
                    leaf_feature_hand=tuple(int(v) for v in p["leaf_feature_hand"]),
                    leaf_value=float(p["leaf_value"]),
                    completed_depth=int(p["completed_depth"]),
                )
                for p in data["points"]
            ),
        )

    def leaf_features_at(self, point: TrainingPoint) -> MaterialFeatureVector:
        return MaterialFeatureVector(
            self.type_ids,
            point.leaf_feature_board,
            point.leaf_feature_hand,
        )

    def feature_payload(self, point: TrainingPoint) -> str:
        return canonical_json(
            {
                "board": list(point.leaf_feature_board),
                "hand": list(point.leaf_feature_hand),
            }
        )
