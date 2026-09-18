"""Semantic Action Encoder-v1 for the F111 frozen-data experiment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from ..core.actions import SemanticBoardMove, SemanticDropMove
from .policy import ACTION_FEATURE_SCHEMA_ID, STATE_FEATURE_SCHEMA_ID, semantic_action_features
from .serialization import stable_sha256


SEMANTIC_POLICY_V1_ARTIFACT_TYPE = "SemanticPolicyV1"
SEMANTIC_POLICY_V1_VERSION = 1
ACTION_V1_SCHEMA_ID = "semantic-action-v1"
ACTION_V1_BASE_WIDTH = 21
ACTION_V1_HIDDEN_WIDTH = 16
GEOMETRY_KIND_IDS = {"leap": 0, "ray": 1, "drop": 2}


def action_v1_categories(compiled, action) -> tuple[int, int, int, int]:
    type_ids = tuple(sorted(getattr(compiled.support, "type_metadata", {})))
    indices = {type_id: index for index, type_id in enumerate(type_ids)}
    geometry = compiled.ir.geometry.get(action.geometry_id)
    geometry_index = GEOMETRY_KIND_IDS[str(getattr(geometry, "kind", "drop"))]
    actor = action.actor_type_id if isinstance(action, SemanticBoardMove) else action.base_type_id
    promotion = action.promotion_target_id if isinstance(action, SemanticBoardMove) else None
    drop = action.base_type_id if isinstance(action, SemanticDropMove) else None
    none = len(type_ids)
    return (indices[actor], indices[promotion] if promotion is not None else none,
            indices[drop] if drop is not None else none, geometry_index)


def action_v1_components(compiled, position, action) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    base = semantic_action_features(compiled, position, action)[:ACTION_V1_BASE_WIDTH]
    return np.asarray(base, dtype=np.float64), action_v1_categories(compiled, action)


def _zeros_like(params):
    return [np.zeros_like(value) for value in params]


@dataclass(frozen=True, slots=True)
class SemanticPolicyV1:
    ruleset_fingerprint: str
    state_schema_id: str
    action_schema_id: str
    state_width: int
    hidden_width: int
    type_count: int
    state_weights: tuple[tuple[float, ...], ...]
    state_bias: tuple[float, ...]
    base_weights: tuple[tuple[float, ...], ...]
    action_bias: tuple[float, ...]
    actor_embedding: tuple[tuple[float, ...], ...]
    promotion_embedding: tuple[tuple[float, ...], ...]
    drop_embedding: tuple[tuple[float, ...], ...]
    actor_geometry_embedding: tuple[tuple[tuple[float, ...], ...], ...]
    actor_capture_embedding: tuple[tuple[float, ...], ...]
    actor_promotion_embedding: tuple[tuple[float, ...], ...]
    actor_drop_embedding: tuple[tuple[float, ...], ...]
    beta_base: tuple[float, ...]
    beta_actor: tuple[float, ...]
    beta_promotion: tuple[float, ...]
    beta_drop: tuple[float, ...]
    beta_actor_geometry: tuple[tuple[float, ...], ...]
    beta_actor_capture: tuple[float, ...]
    beta_actor_promotion: tuple[float, ...]
    beta_actor_drop: tuple[float, ...]
    corpus_config: dict[str, Any]
    training_config: dict[str, Any]
    model_sha256: str = ""

    def _arrays(self):
        return [
            np.asarray(self.state_weights, dtype=np.float64), np.asarray(self.state_bias, dtype=np.float64),
            np.asarray(self.base_weights, dtype=np.float64), np.asarray(self.action_bias, dtype=np.float64),
            np.asarray(self.actor_embedding, dtype=np.float64), np.asarray(self.promotion_embedding, dtype=np.float64),
            np.asarray(self.drop_embedding, dtype=np.float64), np.asarray(self.actor_geometry_embedding, dtype=np.float64),
            np.asarray(self.actor_capture_embedding, dtype=np.float64), np.asarray(self.actor_promotion_embedding, dtype=np.float64),
            np.asarray(self.actor_drop_embedding, dtype=np.float64), np.asarray(self.beta_base, dtype=np.float64),
            np.asarray(self.beta_actor, dtype=np.float64), np.asarray(self.beta_promotion, dtype=np.float64),
            np.asarray(self.beta_drop, dtype=np.float64), np.asarray(self.beta_actor_geometry, dtype=np.float64),
            np.asarray(self.beta_actor_capture, dtype=np.float64), np.asarray(self.beta_actor_promotion, dtype=np.float64),
            np.asarray(self.beta_actor_drop, dtype=np.float64),
        ]

    def hidden(self, state: Sequence[float]) -> np.ndarray:
        weights, bias, *_ = self._arrays()
        return np.tanh(weights @ np.asarray(state, dtype=np.float64) + bias)

    def _action_parts(self, base, categories):
        arrays = self._arrays()
        _, _, base_weights, action_bias, actor, promo, drop, actor_geometry, actor_capture, actor_promotion, actor_drop, beta_base, beta_actor, beta_promo, beta_drop, beta_ag, beta_capture, beta_promotion, beta_drop_context = arrays
        actor_index, promo_index, drop_index, geometry_index = categories
        z = base @ base_weights.T + action_bias
        z = z + actor[actor_index] + promo[promo_index] + drop[drop_index]
        z = z + actor_geometry[actor_index, geometry_index]
        z = z + base[:, 18:19] * actor_capture[actor_index]
        z = z + base[:, 17:18] * actor_promotion[actor_index]
        z = z + base[:, 1:2] * actor_drop[actor_index]
        embedding = np.tanh(z)
        static = base @ beta_base + beta_actor[actor_index] + beta_promo[promo_index] + beta_drop[drop_index]
        static = static + beta_ag[actor_index, geometry_index]
        static = static + base[:, 18] * beta_capture[actor_index] + base[:, 17] * beta_promotion[actor_index] + base[:, 1] * beta_drop_context[actor_index]
        return embedding, static

    def logits(self, state, bases, categories):
        h = self.hidden(state)
        embedding, static = self._action_parts(np.asarray(bases, dtype=np.float64), categories)
        return embedding @ h + static

    def ordered_actions(self, state, bases, categories, native_identities=None):
        scores = self.logits(state, bases, categories)
        identities = tuple(range(len(scores))) if native_identities is None else tuple(native_identities)
        return tuple(sorted(range(len(scores)), key=lambda index: (-float(scores[index]), int(identities[index]))))

    def _payload_without_sha(self):
        arrays = self._arrays()
        names = ("state_weights", "state_bias", "base_weights", "action_bias", "actor_embedding", "promotion_embedding", "drop_embedding", "actor_geometry_embedding", "actor_capture_embedding", "actor_promotion_embedding", "actor_drop_embedding", "beta_base", "beta_actor", "beta_promotion", "beta_drop", "beta_actor_geometry", "beta_actor_capture", "beta_actor_promotion", "beta_actor_drop")
        payload = {"artifact_type": SEMANTIC_POLICY_V1_ARTIFACT_TYPE, "version": SEMANTIC_POLICY_V1_VERSION,
                   "ruleset_fingerprint": self.ruleset_fingerprint, "state_schema_id": self.state_schema_id,
                   "action_schema_id": self.action_schema_id, "state_width": self.state_width,
                   "hidden_width": self.hidden_width, "type_count": self.type_count,
                   "corpus_config": self.corpus_config, "training_config": self.training_config}
        for name, value in zip(names, arrays):
            payload[name] = value.tolist()
        return payload

    @property
    def computed_model_sha256(self):
        return stable_sha256(self._payload_without_sha())

    def to_dict(self):
        payload = self._payload_without_sha()
        payload["model_sha256"] = stable_sha256(payload)
        return payload

    @classmethod
    def from_dict(cls, payload):
        if payload.get("artifact_type") != SEMANTIC_POLICY_V1_ARTIFACT_TYPE or int(payload.get("version", -1)) != SEMANTIC_POLICY_V1_VERSION:
            raise ValueError("not a SemanticPolicyV1 artifact")
        expected = stable_sha256({key: value for key, value in payload.items() if key != "model_sha256"})
        if payload.get("model_sha256") != expected:
            raise ValueError("SemanticPolicyV1 model SHA256 mismatch")
        kwargs = {key: payload[key] for key in ("ruleset_fingerprint", "state_schema_id", "action_schema_id", "state_width", "hidden_width", "type_count", "corpus_config", "training_config")}
        for key in ("state_weights", "base_weights", "actor_embedding", "promotion_embedding", "drop_embedding", "actor_capture_embedding", "actor_promotion_embedding", "actor_drop_embedding"):
            kwargs[key] = tuple(tuple(float(v) for v in row) for row in payload[key])
        for key in ("state_bias", "action_bias", "beta_base", "beta_actor", "beta_promotion", "beta_drop", "beta_actor_capture", "beta_actor_promotion", "beta_actor_drop"):
            kwargs[key] = tuple(float(v) for v in payload[key])
        kwargs["actor_geometry_embedding"] = tuple(tuple(tuple(float(v) for v in row) for row in table) for table in payload["actor_geometry_embedding"])
        kwargs["beta_actor_geometry"] = tuple(tuple(float(v) for v in row) for row in payload["beta_actor_geometry"])
        kwargs["model_sha256"] = payload["model_sha256"]
        return cls(**kwargs)


def fit_semantic_policy_v1(examples, *, ruleset_fingerprint, corpus_config, seed, type_count, steps=400, learning_rate=0.005, regularization=1e-4):
    if steps != 400 or learning_rate != 0.005 or regularization != 1e-4:
        raise ValueError("Semantic Policy-v1 training hyperparameters are frozen")
    if not examples:
        raise ValueError("at least one policy root is required")
    state_width = len(examples[0][0])
    rng = np.random.default_rng(seed)
    params = [
        rng.normal(0, np.sqrt(2.0 / (state_width + 16)), (16, state_width)), np.zeros(16),
        rng.normal(0, 1.0 / np.sqrt(21.0), (16, 21)), np.zeros(16),
        rng.normal(0, 1.0 / np.sqrt(16.0), (type_count, 16)), rng.normal(0, 1.0 / np.sqrt(16.0), (type_count + 1, 16)),
        rng.normal(0, 1.0 / np.sqrt(16.0), (type_count + 1, 16)), rng.normal(0, 1.0 / np.sqrt(16.0), (type_count, 3, 16)),
        rng.normal(0, 1.0 / np.sqrt(16.0), (type_count, 16)), rng.normal(0, 1.0 / np.sqrt(16.0), (type_count, 16)),
        rng.normal(0, 1.0 / np.sqrt(16.0), (type_count, 16)), np.zeros(21), np.zeros(type_count), np.zeros(type_count + 1),
        np.zeros(type_count + 1), np.zeros((type_count, 3)), np.zeros(type_count), np.zeros(type_count), np.zeros(type_count),
    ]
    moments = [(np.zeros_like(param), np.zeros_like(param)) for param in params]
    for step in range(1, steps + 1):
        gradients = _zeros_like(params)
        for state, base, cats, target in examples:
            state = np.asarray(state); base = np.asarray(base); target = np.asarray(target)
            h = np.tanh(params[0] @ state + params[1])
            actor, promo, drop, geometry = cats
            z = base @ params[2].T + params[3] + params[4][actor] + params[5][promo] + params[6][drop] + params[7][actor, geometry]
            z += base[:, 18:19] * params[8][actor] + base[:, 17:18] * params[9][actor] + base[:, 1:2] * params[10][actor]
            embedding = np.tanh(z)
            logits = embedding @ h + base @ params[11] + params[12][actor] + params[13][promo] + params[14][drop] + params[15][actor, geometry] + base[:, 18] * params[16][actor] + base[:, 17] * params[17][actor] + base[:, 1] * params[18][actor]
            probs = np.exp(logits - np.max(logits)); probs /= np.sum(probs)
            dlogits = (probs - target) / len(examples)
            gradients[11] += base.T @ dlogits; gradients[12] += np.bincount(actor, dlogits, minlength=type_count); gradients[13] += np.bincount(promo, dlogits, minlength=type_count + 1); gradients[14] += np.bincount(drop, dlogits, minlength=type_count + 1)
            for index in range(len(dlogits)):
                gradients[15][actor[index], geometry[index]] += dlogits[index]; gradients[16][actor[index]] += dlogits[index] * base[index, 18]; gradients[17][actor[index]] += dlogits[index] * base[index, 17]; gradients[18][actor[index]] += dlogits[index] * base[index, 1]
            d_embedding = dlogits[:, None] * h[None, :]; d_z = d_embedding * (1 - embedding * embedding)
            gradients[2] += d_z.T @ base; gradients[3] += np.sum(d_z, axis=0); gradients[4][actor] += d_z; gradients[5][promo] += d_z; gradients[6][drop] += d_z
            for index in range(len(dlogits)):
                gradients[7][actor[index], geometry[index]] += d_z[index]; gradients[8][actor[index]] += d_z[index] * base[index, 18]; gradients[9][actor[index]] += d_z[index] * base[index, 17]; gradients[10][actor[index]] += d_z[index] * base[index, 1]
            d_h = np.sum(dlogits[:, None] * embedding, axis=0); d_state = d_h * (1 - h * h)
            gradients[0] += np.outer(d_state, state); gradients[1] += d_state
        for index, (param, gradient) in enumerate(zip(params, gradients)):
            gradient += regularization * param
            first, second = moments[index]; first[...] = 0.9 * first + 0.1 * gradient; second[...] = 0.999 * second + 0.001 * gradient * gradient
            param[...] -= learning_rate * (first / (1 - 0.9 ** step)) / (np.sqrt(second / (1 - 0.999 ** step)) + 1e-8)
    return SemanticPolicyV1(
        ruleset_fingerprint=ruleset_fingerprint, state_schema_id=STATE_FEATURE_SCHEMA_ID, action_schema_id=ACTION_V1_SCHEMA_ID,
        state_width=state_width, hidden_width=16, type_count=type_count,
        state_weights=tuple(tuple(float(v) for v in row) for row in params[0]), state_bias=tuple(float(v) for v in params[1]),
        base_weights=tuple(tuple(float(v) for v in row) for row in params[2]), action_bias=tuple(float(v) for v in params[3]),
        actor_embedding=tuple(tuple(float(v) for v in row) for row in params[4]), promotion_embedding=tuple(tuple(float(v) for v in row) for row in params[5]), drop_embedding=tuple(tuple(float(v) for v in row) for row in params[6]), actor_geometry_embedding=tuple(tuple(tuple(float(v) for v in row) for row in table) for table in params[7]), actor_capture_embedding=tuple(tuple(float(v) for v in row) for row in params[8]), actor_promotion_embedding=tuple(tuple(float(v) for v in row) for row in params[9]), actor_drop_embedding=tuple(tuple(float(v) for v in row) for row in params[10]), beta_base=tuple(float(v) for v in params[11]), beta_actor=tuple(float(v) for v in params[12]), beta_promotion=tuple(float(v) for v in params[13]), beta_drop=tuple(float(v) for v in params[14]), beta_actor_geometry=tuple(tuple(float(v) for v in row) for row in params[15]), beta_actor_capture=tuple(float(v) for v in params[16]), beta_actor_promotion=tuple(float(v) for v in params[17]), beta_actor_drop=tuple(float(v) for v in params[18]), corpus_config=dict(corpus_config), training_config={"optimizer": "Adam", "steps": 400, "learning_rate": 0.005, "regularization": 1e-4, "seed": int(seed), "loss": "listwise_cross_entropy"},
    )


__all__ = ["ACTION_V1_SCHEMA_ID", "SemanticPolicyV1", "action_v1_categories", "action_v1_components", "fit_semantic_policy_v1"]
