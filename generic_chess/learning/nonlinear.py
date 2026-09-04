"""Compact generic nonlinear value residuals for offline experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def semantic_state_features(position, compiled, dynamic_values) -> np.ndarray:
    """Encode semantic state mechanically; no game-name or type branches."""
    metadata = getattr(getattr(compiled, "support", None), "type_metadata", {})
    current_type_ids = tuple(sorted(metadata))
    type_index = {type_id: index for index, type_id in enumerate(current_type_ids)}
    legacy = getattr(compiled, "_legacy_compiled", None)
    base_type_ids = tuple(sorted(
        piece_type.type_id for piece_type in getattr(legacy, "piece_types", ())
    )) or current_type_ids
    base_index = {type_id: index for index, type_id in enumerate(base_type_ids)}
    board_size = position.board_size()
    values = np.zeros(2 * len(current_type_ids) * len(position.board), dtype=np.float64)
    for square, piece in enumerate(position.board):
        if piece is None or piece.current_type_id not in type_index:
            continue
        offset = (piece.owner * len(current_type_ids) + type_index[piece.current_type_id]) * len(position.board)
        values[offset + square] = 1.0
    hand_values = np.zeros(2 * len(base_type_ids), dtype=np.float64)
    for owner in (0, 1):
        for type_id, count in position.hands[owner].counts:
            if type_id in base_index:
                hand_values[owner * len(base_type_ids) + base_index[type_id]] = float(count)
    side = np.asarray((1.0, 0.0) if position.side_to_move == 0 else (0.0, 1.0))
    dynamic = np.asarray(tuple(float(value) for value in dynamic_values), dtype=np.float64)
    # Use the compiled slot schema so bool and square_or_none values retain a
    # fixed width even when a square slot is currently None.
    aux = []
    aux_state = dict(position.aux_state)
    ir = getattr(compiled, "ir", None)
    for slot in getattr(ir, "aux_slots", ()):
        owner_tags = (-1,) if slot.scope == "global" else (0, 1)
        for owner_tag in owner_tags:
            value = aux_state.get((slot.slot_id, owner_tag))
            if slot.value_kind == "bool":
                aux.append(float(value or 0))
            elif isinstance(value, tuple) and len(value) == 2:
                aux.extend((1.0, float(value[0]) / max(board_size, 1), float(value[1]) / max(board_size, 1)))
            else:
                aux.extend((0.0, 0.0, 0.0))
    return np.concatenate((values, hand_values, side, dynamic, np.asarray(aux, dtype=np.float64)))


def bounded_value_domain(values: np.ndarray, value_scale: float) -> np.ndarray:
    """Map owner-0 values to the established bounded learning domain."""
    if value_scale <= 0:
        raise ValueError("value_scale must be positive")
    return np.tanh(np.asarray(values, dtype=np.float64) / float(value_scale))


@dataclass(frozen=True)
class CompactNonlinearResidual:
    input_mean: tuple[float, ...]
    input_scale: tuple[float, ...]
    target_scale: float
    hidden_weights: tuple[tuple[float, ...], ...]
    hidden_bias: tuple[float, ...]
    output_weights: tuple[float, ...]
    output_bias: float
    width: int
    regularization: float
    seed: int
    # Indices into the Native current-type table for the base-type hand axis.
    # Populated when a trained model is bound to a checkpoint.
    hand_type_indices: tuple[int, ...] = ()

    def predict(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float64)
        normalized = (x - np.asarray(self.input_mean)) / np.asarray(self.input_scale)
        hidden = np.tanh(normalized @ np.asarray(self.hidden_weights).T + np.asarray(self.hidden_bias))
        output = hidden @ np.asarray(self.output_weights) + self.output_bias
        return output * self.target_scale

    def to_dict(self) -> dict:
        payload = {
            "input_mean": list(self.input_mean), "input_scale": list(self.input_scale),
            "target_scale": self.target_scale,
            "hidden_weights": [list(row) for row in self.hidden_weights],
            "hidden_bias": list(self.hidden_bias), "output_weights": list(self.output_weights),
            "output_bias": self.output_bias, "width": self.width,
            "regularization": self.regularization, "seed": self.seed,
        }
        if self.hand_type_indices:
            payload["hand_type_indices"] = list(self.hand_type_indices)
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "CompactNonlinearResidual":
        return cls(
            input_mean=tuple(payload["input_mean"]), input_scale=tuple(payload["input_scale"]),
            target_scale=float(payload["target_scale"]),
            hidden_weights=tuple(tuple(row) for row in payload["hidden_weights"]),
            hidden_bias=tuple(payload["hidden_bias"]), output_weights=tuple(payload["output_weights"]),
            output_bias=float(payload["output_bias"]), width=int(payload["width"]),
            regularization=float(payload["regularization"]), seed=int(payload["seed"]),
            hand_type_indices=tuple(int(v) for v in payload.get("hand_type_indices", ())),
        )


def fit_compact_residual(
    features: np.ndarray,
    targets: np.ndarray,
    *,
    width: int,
    regularization: float,
    seed: int,
    epochs: int = 600,
    learning_rate: float = 0.01,
) -> CompactNonlinearResidual:
    """Fit one deterministic full-batch tanh residual with Adam."""
    x = np.asarray(features, dtype=np.float64)
    y = np.asarray(targets, dtype=np.float64)
    if x.ndim != 2 or y.ndim != 1 or len(x) != len(y):
        raise ValueError("features and targets must be a compatible matrix/vector")
    if width not in (16, 32):
        raise ValueError("compact nonlinear width must be 16 or 32")
    mean = np.mean(x, axis=0)
    scale = np.std(x, axis=0)
    scale = np.where(scale > 1e-9, scale, 1.0)
    xn = (x - mean) / scale
    target_scale = float(np.std(y)) or 1.0
    yn = y / target_scale
    rng = np.random.default_rng(seed)
    hidden_weights = rng.normal(0.0, np.sqrt(2.0 / (x.shape[1] + width)), size=(width, x.shape[1]))
    hidden_bias = np.zeros(width, dtype=np.float64)
    output_weights = rng.normal(0.0, 1.0 / np.sqrt(width), size=width)
    output_bias = np.asarray(0.0)
    params = [hidden_weights, hidden_bias, output_weights, output_bias]
    moments = [(np.zeros_like(param), np.zeros_like(param)) for param in params]
    for step in range(1, epochs + 1):
        pre = xn @ hidden_weights.T + hidden_bias
        hidden = np.tanh(pre)
        prediction = hidden @ output_weights + output_bias
        error = prediction - yn
        grad_output = (hidden.T @ error) / len(x) + regularization * output_weights
        grad_bias = np.mean(error)
        grad_hidden = ((error[:, None] * output_weights[None, :]) * (1.0 - hidden * hidden)).T @ xn / len(x)
        grad_hidden += regularization * hidden_weights
        grad_hidden_bias = np.mean((error[:, None] * output_weights[None, :]) * (1.0 - hidden * hidden), axis=0)
        gradients = [grad_hidden, grad_hidden_bias, grad_output, np.asarray(grad_bias)]
        for index, (param, gradient) in enumerate(zip(params, gradients)):
            first, second = moments[index]
            first[...] = 0.9 * first + 0.1 * gradient
            second[...] = 0.999 * second + 0.001 * gradient * gradient
            corrected_first = first / (1.0 - 0.9 ** step)
            corrected_second = second / (1.0 - 0.999 ** step)
            param[...] -= learning_rate * corrected_first / (np.sqrt(corrected_second) + 1e-8)
    return CompactNonlinearResidual(
        input_mean=tuple(mean.tolist()), input_scale=tuple(scale.tolist()),
        target_scale=target_scale, hidden_weights=tuple(tuple(row) for row in hidden_weights.tolist()),
        hidden_bias=tuple(hidden_bias.tolist()), output_weights=tuple(output_weights.tolist()),
        output_bias=float(output_bias), width=width, regularization=regularization, seed=seed,
    )
