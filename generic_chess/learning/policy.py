"""Dedicated Semantic Policy-v0 ordering model.

This module is deliberately independent from the value-learning checkpoints.
The model only produces a score for every legal action.  It has no successor
position evaluation, minimax value, or action filtering semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Sequence

import numpy as np

from ..core.actions import SemanticBoardMove, SemanticDropMove
from ..learning.nonlinear import semantic_state_features
from .serialization import canonical_json, stable_sha256


SEMANTIC_POLICY_ARTIFACT_TYPE = "SemanticPolicyV0"
SEMANTIC_POLICY_VERSION = 0
SEMANTIC_POLICY_HIDDEN_WIDTH = 16
STATE_FEATURE_SCHEMA_ID = "semantic-state-v0"
ACTION_FEATURE_SCHEMA_ID = "semantic-action-v0"
ACTION_FEATURE_WIDTH = 24


def _index_value(index: int, count: int) -> float:
    return 0.0 if count <= 1 else float(index) / float(count - 1)


def _relative_square(square, owner: int, board_size: int) -> tuple[float, float]:
    """Return normalized coordinates in the mover's frame."""
    file_value = square.file
    rank_value = square.rank if owner == 0 else board_size - 1 - square.rank
    denominator = max(board_size - 1, 1)
    return file_value / denominator, rank_value / denominator


def _geometry_path_length(geometry, source: int | None, owner: int) -> int:
    if source is None:
        return 0
    paths = getattr(geometry, "paths", {})
    candidates = []
    for key in (owner, str(owner), "self", "opponent"):
        table = paths.get(key) if hasattr(paths, "get") else None
        if table is not None and source in table:
            candidates.append(len(table[source]))
    return max(candidates, default=0)


def semantic_action_features(compiled, position, action) -> np.ndarray:
    """Encode one semantic action with generic numeric rule metadata.

    Pattern and geometry identities are used only to look up compiled numeric
    metadata.  Their names and raw identifiers never enter the feature vector.
    """
    if not isinstance(action, (SemanticBoardMove, SemanticDropMove)):
        raise TypeError("Semantic Policy-v0 requires a semantic action")
    n = int(compiled.board_size)
    type_ids = tuple(sorted(getattr(compiled.support, "type_metadata", {})))
    type_index = {type_id: index for index, type_id in enumerate(type_ids)}
    pattern = next((p for p in compiled.ir.patterns if p.pattern_id == action.pattern_id), None)
    if pattern is None:
        raise ValueError("action pattern is not in the compiled semantic ruleset")
    geometry = compiled.ir.geometry.get(action.geometry_id)
    if geometry is None:
        raise ValueError("action geometry is not in the compiled semantic ruleset")

    if isinstance(action, SemanticBoardMove):
        source = action.from_square
        source_index = source.rank * n + source.file
        target = action.to_square
        piece = position.board[source_index]
        owner = int(piece.owner) if piece is not None else int(position.side_to_move)
        actor_type = action.actor_type_id
        promotion_target = action.promotion_target_id
        source_present = 1.0 if piece is not None else 0.0
        board_flag, drop_flag = 1.0, 0.0
        target_piece = position.board[target.rank * n + target.file]
        direct_capture = float(target_piece is not None and target_piece.owner != owner)
        src_x, src_y = _relative_square(source, owner, n)
        dst_x, dst_y = _relative_square(target, owner, n)
        dx = dst_x - src_x
        dy = dst_y - src_y
        path_length = _geometry_path_length(geometry, source_index, owner)
    else:
        target = action.to_square
        owner = int(position.side_to_move)
        actor_type = action.base_type_id
        promotion_target = None
        source_present = 0.0
        board_flag, drop_flag = 0.0, 1.0
        direct_capture = 0.0
        src_x = src_y = 0.0
        dst_x, dst_y = _relative_square(target, owner, n)
        dx = dy = 0.0
        path_length = 0

    kind = str(getattr(geometry, "kind", ""))
    kind_leap = float(kind == "leap")
    kind_ray = float(kind == "ray")
    kind_drop = float(kind == "drop")
    cost_match = re.search(r"(\d+)$", str(getattr(pattern, "cost_class", "")))
    cost = float(cost_match.group(1)) if cost_match else 0.0
    stratum_match = re.search(r"(\d+)$", str(getattr(pattern, "stratum", "")))
    stratum = float(stratum_match.group(1)) if stratum_match else 0.0
    max_distance = max(n - 1, 1)
    return np.asarray(
        (
            board_flag,
            drop_flag,
            source_present,
            src_x,
            src_y,
            dst_x,
            dst_y,
            dx,
            dy,
            abs(dx),
            abs(dy),
            abs(dx) + abs(dy),
            max(abs(dx), abs(dy)),
            kind_leap,
            kind_ray,
            kind_drop,
            min(float(path_length) / max_distance, 1.0),
            float(promotion_target is not None),
            direct_capture,
            cost / 10.0,
            stratum / 10.0,
            _index_value(type_index.get(actor_type, 0), len(type_ids)),
            _index_value(type_index.get(promotion_target, 0), len(type_ids))
            if promotion_target is not None else 0.0,
            _index_value(type_index.get(action.base_type_id, 0), len(type_ids))
            if isinstance(action, SemanticDropMove) else 0.0,
        ),
        dtype=np.float64,
    )


def semantic_state_feature_vector(position, compiled, dynamic_values=()) -> np.ndarray:
    """Build the fixed generic state input used by Semantic Policy-v0."""
    return semantic_state_features(position, compiled, tuple(dynamic_values))


def semantic_policy_hand_type_indices(compiled, native_rules) -> tuple[int, ...]:
    """Map the generic base-hand axis onto the Native current-type table."""
    base_ids = tuple(sorted(
        piece_type.type_id for piece_type in getattr(
            getattr(compiled, "_legacy_compiled", None), "piece_types", ()
        )
    ))
    current_index = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    if not base_ids:
        base_ids = tuple(sorted(getattr(getattr(compiled, "support", None), "type_metadata", {})))
    try:
        return tuple(current_index[type_id] for type_id in base_ids)
    except KeyError as exc:
        raise ValueError("compiled base-hand type is absent from Native type table") from exc


def policy_target_from_q(q_values: Sequence[float], *, epsilon: float = 1e-9) -> np.ndarray:
    """Convert a complete root-player q vector to the mandated soft target."""
    q = np.asarray(tuple(float(value) for value in q_values), dtype=np.float64)
    if q.ndim != 1 or len(q) == 0 or not np.all(np.isfinite(q)):
        raise ValueError("q_values must be a non-empty finite vector")
    median = float(np.median(q))
    quartiles = np.percentile(q, (25.0, 75.0))
    scale = max(float(quartiles[1] - quartiles[0]), float(epsilon))
    logits = (q - median) / scale
    logits -= np.max(logits)
    weights = np.exp(logits)
    return weights / np.sum(weights)


@dataclass(frozen=True, slots=True)
class SemanticPolicyExample:
    state: tuple[float, ...]
    actions: tuple[tuple[float, ...], ...]
    target: tuple[float, ...]
    root_identity: str = ""

    def arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        state = np.asarray(self.state, dtype=np.float64)
        actions = np.asarray(self.actions, dtype=np.float64)
        target = np.asarray(self.target, dtype=np.float64)
        if state.ndim != 1 or actions.ndim != 2 or target.ndim != 1:
            raise ValueError("policy example has incompatible dimensions")
        if actions.shape[1] != ACTION_FEATURE_WIDTH:
            raise ValueError("policy example action width does not match Semantic Policy-v0")
        if len(actions) != len(target) or len(actions) == 0:
            raise ValueError("policy example must contain every legal action")
        if not np.isclose(float(np.sum(target)), 1.0) or np.any(target < 0):
            raise ValueError("policy target must be a probability vector")
        return state, actions, target


@dataclass(frozen=True, slots=True)
class SemanticPolicyV0:
    """Frozen one-hidden-layer listwise policy model."""

    ruleset_fingerprint: str
    state_schema_id: str
    action_schema_id: str
    state_width: int
    action_width: int
    hidden_width: int
    state_weights: tuple[tuple[float, ...], ...]
    state_bias: tuple[float, ...]
    action_embedding: tuple[tuple[float, ...], ...]
    action_bias: tuple[float, ...]
    corpus_config: dict[str, Any]
    training_config: dict[str, Any]
    hand_type_indices: tuple[int, ...] = ()
    model_sha256: str = ""

    def __post_init__(self) -> None:
        if self.hidden_width != SEMANTIC_POLICY_HIDDEN_WIDTH:
            raise ValueError("Semantic Policy-v0 hidden width must be exactly 16")
        if self.action_width != ACTION_FEATURE_WIDTH:
            raise ValueError("unexpected Semantic Policy-v0 action width")
        if len(self.state_weights) != self.hidden_width or len(self.state_bias) != self.hidden_width:
            raise ValueError("invalid state projection dimensions")
        if any(len(row) != self.state_width for row in self.state_weights):
            raise ValueError("invalid state projection width")
        if len(self.action_embedding) != self.hidden_width:
            raise ValueError("invalid action embedding dimensions")
        if any(len(row) != self.action_width for row in self.action_embedding):
            raise ValueError("invalid action embedding width")
        if len(self.action_bias) != self.action_width:
            raise ValueError("invalid action bias width")

    def _arrays(self):
        return (
            np.asarray(self.state_weights, dtype=np.float64),
            np.asarray(self.state_bias, dtype=np.float64),
            np.asarray(self.action_embedding, dtype=np.float64),
            np.asarray(self.action_bias, dtype=np.float64),
        )

    def hidden(self, state: Sequence[float]) -> np.ndarray:
        x = np.asarray(state, dtype=np.float64)
        if x.shape != (self.state_width,):
            raise ValueError("state vector width does not match policy")
        weights, bias, _, _ = self._arrays()
        return np.tanh(weights @ x + bias)

    def logits(self, state: Sequence[float], actions: Sequence[Sequence[float]]) -> np.ndarray:
        phi = np.asarray(actions, dtype=np.float64)
        if phi.ndim != 2 or phi.shape[1] != self.action_width:
            raise ValueError("action matrix width does not match policy")
        _, _, embedding, action_bias = self._arrays()
        h = self.hidden(state)
        return phi @ (embedding.T @ h + action_bias)

    def ordered_actions(self, state, actions, native_identities: Sequence[int] | None = None):
        scores = self.logits(state, actions)
        identities = tuple(range(len(scores))) if native_identities is None else tuple(native_identities)
        if len(identities) != len(scores):
            raise ValueError("native identity count must match action count")
        order = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), int(identities[index])))
        return tuple(order)

    def _payload_without_sha(self) -> dict[str, Any]:
        return {
            "artifact_type": SEMANTIC_POLICY_ARTIFACT_TYPE,
            "version": SEMANTIC_POLICY_VERSION,
            "ruleset_fingerprint": self.ruleset_fingerprint,
            "state_schema_id": self.state_schema_id,
            "action_schema_id": self.action_schema_id,
            "state_width": self.state_width,
            "action_width": self.action_width,
            "hidden_width": self.hidden_width,
            "state_weights": [list(row) for row in self.state_weights],
            "state_bias": list(self.state_bias),
            "action_embedding": [list(row) for row in self.action_embedding],
            "action_bias": list(self.action_bias),
            "hand_type_indices": list(self.hand_type_indices),
            "corpus_config": self.corpus_config,
            "training_config": self.training_config,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload_without_sha()
        payload["model_sha256"] = stable_sha256(payload)
        return payload

    @property
    def computed_model_sha256(self) -> str:
        return stable_sha256(self._payload_without_sha())

    def native_payload(self) -> dict[str, Any]:
        """Return the compact numeric payload consumed by Native."""
        payload = self.to_dict()
        payload["state_weights"] = [list(row) for row in self.state_weights]
        payload["action_embedding"] = [list(row) for row in self.action_embedding]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SemanticPolicyV0":
        if payload.get("artifact_type") != SEMANTIC_POLICY_ARTIFACT_TYPE:
            raise ValueError("not a SemanticPolicyV0 artifact")
        if int(payload.get("version", -1)) != SEMANTIC_POLICY_VERSION:
            raise ValueError("unsupported SemanticPolicyV0 version")
        expected = stable_sha256({key: value for key, value in payload.items() if key != "model_sha256"})
        if payload.get("model_sha256") != expected:
            raise ValueError("SemanticPolicyV0 model SHA256 mismatch")
        return cls(
            ruleset_fingerprint=str(payload["ruleset_fingerprint"]),
            state_schema_id=str(payload["state_schema_id"]),
            action_schema_id=str(payload["action_schema_id"]),
            state_width=int(payload["state_width"]), action_width=int(payload["action_width"]),
            hidden_width=int(payload["hidden_width"]),
            state_weights=tuple(tuple(float(v) for v in row) for row in payload["state_weights"]),
            state_bias=tuple(float(v) for v in payload["state_bias"]),
            action_embedding=tuple(tuple(float(v) for v in row) for row in payload["action_embedding"]),
            action_bias=tuple(float(v) for v in payload["action_bias"]),
            corpus_config=dict(payload.get("corpus_config", {})),
            training_config=dict(payload.get("training_config", {})),
            hand_type_indices=tuple(int(v) for v in payload.get("hand_type_indices", ())),
            model_sha256=str(payload["model_sha256"]),
        )


def fit_semantic_policy_v0(
    examples: Sequence[SemanticPolicyExample],
    *,
    ruleset_fingerprint: str,
    corpus_config: dict[str, Any],
    seed: int,
    steps: int = 400,
    learning_rate: float = 0.005,
    regularization: float = 1e-4,
    hand_type_indices: Sequence[int] = (),
) -> SemanticPolicyV0:
    """Fit the mandated full-root listwise cross-entropy model with Adam."""
    if steps != 400:
        raise ValueError("Semantic Policy-v0 requires exactly 400 Adam steps")
    if learning_rate != 0.005 or regularization != 1e-4:
        raise ValueError("Semantic Policy-v0 training hyperparameters are frozen")
    if not examples:
        raise ValueError("at least one policy root is required")
    arrays = [example.arrays() for example in examples]
    state_width = int(arrays[0][0].shape[0])
    if any(state.shape != (state_width,) for state, _, _ in arrays):
        raise ValueError("all policy roots must use one state schema width")
    rng = np.random.default_rng(seed)
    scale = math.sqrt(2.0 / (state_width + SEMANTIC_POLICY_HIDDEN_WIDTH))
    state_weights = rng.normal(0.0, scale, size=(SEMANTIC_POLICY_HIDDEN_WIDTH, state_width))
    state_bias = np.zeros(SEMANTIC_POLICY_HIDDEN_WIDTH, dtype=np.float64)
    action_embedding = rng.normal(0.0, 1.0 / math.sqrt(ACTION_FEATURE_WIDTH), size=(SEMANTIC_POLICY_HIDDEN_WIDTH, ACTION_FEATURE_WIDTH))
    action_bias = np.zeros(ACTION_FEATURE_WIDTH, dtype=np.float64)
    params = [state_weights, state_bias, action_embedding, action_bias]
    moments = [(np.zeros_like(param), np.zeros_like(param)) for param in params]

    for step in range(1, steps + 1):
        gradients = [np.zeros_like(param) for param in params]
        for state, phi, target in arrays:
            h = np.tanh(state_weights @ state + state_bias)
            action_vector = action_embedding.T @ h + action_bias
            logits = phi @ action_vector
            logits -= np.max(logits)
            probabilities = np.exp(logits)
            probabilities /= np.sum(probabilities)
            dlogits = (probabilities - target) / len(arrays)
            d_action_vector = phi.T @ dlogits
            gradients[2] += np.outer(h, d_action_vector)
            gradients[3] += d_action_vector
            d_hidden = action_embedding @ d_action_vector
            d_state = d_hidden * (1.0 - h * h)
            gradients[0] += np.outer(d_state, state)
            gradients[1] += d_state
        for index, (param, gradient) in enumerate(zip(params, gradients)):
            gradient += regularization * param
            first, second = moments[index]
            first[...] = 0.9 * first + 0.1 * gradient
            second[...] = 0.999 * second + 0.001 * gradient * gradient
            first_hat = first / (1.0 - 0.9 ** step)
            second_hat = second / (1.0 - 0.999 ** step)
            param[...] -= learning_rate * first_hat / (np.sqrt(second_hat) + 1e-8)

    return SemanticPolicyV0(
        ruleset_fingerprint=ruleset_fingerprint,
        state_schema_id=STATE_FEATURE_SCHEMA_ID,
        action_schema_id=ACTION_FEATURE_SCHEMA_ID,
        state_width=state_width,
        action_width=ACTION_FEATURE_WIDTH,
        hidden_width=SEMANTIC_POLICY_HIDDEN_WIDTH,
        state_weights=tuple(tuple(float(v) for v in row) for row in state_weights),
        state_bias=tuple(float(v) for v in state_bias),
        action_embedding=tuple(tuple(float(v) for v in row) for row in action_embedding),
        action_bias=tuple(float(v) for v in action_bias),
        corpus_config=dict(corpus_config),
        training_config={
            "optimizer": "Adam", "steps": steps, "learning_rate": learning_rate,
            "regularization": regularization, "seed": int(seed),
            "loss": "listwise_cross_entropy",
        },
        hand_type_indices=tuple(int(value) for value in hand_type_indices),
    )


__all__ = [
    "ACTION_FEATURE_SCHEMA_ID", "ACTION_FEATURE_WIDTH", "SEMANTIC_POLICY_ARTIFACT_TYPE",
    "SEMANTIC_POLICY_HIDDEN_WIDTH", "SEMANTIC_POLICY_VERSION", "STATE_FEATURE_SCHEMA_ID",
    "SemanticPolicyExample", "SemanticPolicyV0", "fit_semantic_policy_v0",
    "policy_target_from_q", "semantic_action_features", "semantic_state_feature_vector",
    "semantic_policy_hand_type_indices",
]
