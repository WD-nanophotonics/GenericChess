"""F122: reverse benchmark for known evaluator system identification.

This is deliberately a benchmark-only module.  It does not modify or import
the production evaluator, learning arena, teacher, or promotion paths.  The
oracle is a frozen linear functional over a ruleset-specific handcrafted
basis; the learner is a plain linear Adam fit on the same basis.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import random
import statistics
import time
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from generic_chess.core.actions import (
    Action,
    action_drop_base_type_id,
    action_is_board,
    action_is_drop,
    action_source_square,
    action_target_square,
)
from generic_chess.core.attacks import anchor_square, is_in_check, is_square_attacked, pseudo_attacks
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.position import GameState, Position
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.core.semantic_executor import semantic_engine_for


RULESETS = ("western_chess", "standard_shogi")
COUNTS = {"train": 3000, "dev": 750, "holdout": 750}
SEARCH_NODES = 2000
SEARCH_DEPTH = 12


def _json_sha(value: object) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _sq_index(file: int, rank: int, n: int) -> int:
    return rank * n + file


def _owner_sign(piece_owner: int, side: int) -> int:
    return 1 if piece_owner == side else -1


def _sort_actions(actions: Iterable[Action]) -> list[Action]:
    return sorted(actions, key=lambda action: str(action))


def _state_for_side(state: GameState, side: int) -> GameState:
    """Make a legal-action counting view with a selected side to move."""
    return dataclasses.replace(
        state,
        position=dataclasses.replace(state.position, side_to_move=side),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )


def _anchor_square_generic(position: Position, owner: int) -> tuple[int, int] | None:
    n = position.board_size()
    for idx, piece in enumerate(position.board):
        if piece is not None and piece.owner == owner and piece.current_type_id == "K":
            return (idx % n, idx // n)
    return None


def _zone_squares(anchor: tuple[int, int] | None, n: int) -> set[tuple[int, int]]:
    if anchor is None:
        return set()
    file, rank = anchor
    return {
        (file + df, rank + dr)
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if 0 <= file + df < n and 0 <= rank + dr < n
    }


def _pawn_structure(position: Position, owner: int) -> tuple[int, int, int]:
    n = position.board_size()
    pawns: list[tuple[int, int]] = []
    for idx, piece in enumerate(position.board):
        if piece is None or piece.owner != owner or piece.current_type_id != "P":
            continue
        pawns.append((idx % n, idx // n))
    by_file: dict[int, list[int]] = {}
    for file, rank in pawns:
        by_file.setdefault(file, []).append(rank)
    doubled = sum(max(0, len(ranks) - 1) for ranks in by_file.values())
    isolated = sum(
        1
        for file in by_file
        if file - 1 not in by_file and file + 1 not in by_file
    )
    enemy_files: dict[int, list[int]] = {}
    for idx, piece in enumerate(position.board):
        if piece is None or piece.owner == owner or piece.current_type_id != "P":
            continue
        enemy_files.setdefault(idx % n, []).append(idx // n)
    direction = 1 if owner == 0 else -1
    passed = 0
    for file, rank in pawns:
        blocked = False
        for enemy_file in (file - 1, file, file + 1):
            for enemy_rank in enemy_files.get(enemy_file, ()):
                if (enemy_rank - rank) * direction > 0:
                    blocked = True
        if not blocked:
            passed += 1
    return doubled, isolated, passed


def _king_escape_count(state: GameState, compiled, owner: int, actions: list[Action]) -> int:
    anchor = _anchor_square_generic(state.position, owner)
    if anchor is None:
        return 0
    return sum(
        1
        for action in actions
        if action_is_board(action) and action_source_square(action) is not None
        and (action_source_square(action).file, action_source_square(action).rank) == anchor
    )


class FrozenBasis:
    """Fixed feature order and frozen oracle vector for one ruleset family."""

    def __init__(self, family: str, compiled) -> None:
        self.family = family
        self.compiled = compiled
        self.n = compiled.board_size
        if family == "western_chess":
            self.material_types = ("P", "N", "B", "R", "Q")
            self.board_types = self.material_types
            self.hand_types: tuple[str, ...] = ()
            self.base_values = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900}
            self.family_types = self.material_types
        else:
            self.material_types = ("P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR")
            self.board_types = self.material_types
            self.hand_types = ("P", "L", "N", "S", "G", "B", "R")
            self.base_values = {"P": 100, "L": 300, "N": 320, "S": 450, "G": 550, "B": 800, "R": 1000}
            self.family_types = self.material_types
        self.names: list[str] = []
        self.weights: list[float] = []
        self._vector_cache: dict[str, np.ndarray] = {}
        self._add_names_and_weights()
        self.oracle_weight_sha256 = _json_sha({"names": self.names, "weights": self.weights})

    def _add(self, name: str, weight: float) -> None:
        self.names.append(name)
        self.weights.append(float(weight))

    def _square_bonus(self, type_id: str, file: int, rank: int) -> float:
        center = (self.n - 1) / 2.0
        centrality = (self.n - abs(file - center) - abs(rank - center)) / max(1.0, self.n)
        type_factor = 1.0 + (sum(ord(c) for c in type_id) % 7) / 20.0
        forward = (rank if type_id not in ("P", "L", "N", "S") else rank) / max(1, self.n - 1)
        return round(0.35 * centrality * type_factor + 0.05 * forward, 8)

    def _add_names_and_weights(self) -> None:
        for type_id in self.material_types:
            self._add(f"material_diff:{type_id}", self.base_values.get(type_id, self.base_values.get(type_id[1:], 100)))
        for type_id in self.board_types:
            for rank in range(self.n):
                for file in range(self.n):
                    self._add(f"occupancy_diff:{type_id}:{file}:{rank}", self._square_bonus(type_id, file, rank))
        if self.family == "western_chess":
            for name, weight in (
                ("mobility_diff", 5.0),
                ("king_escape_diff", 12.0),
                ("king_zone_pressure_diff", 8.0),
                ("current_check_diff", 20.0),
                ("doubled_pawns_diff", -6.0),
                ("isolated_pawns_diff", -5.0),
                ("passed_pawns_diff", 10.0),
            ):
                self._add(name, weight)
        else:
            for type_id in self.hand_types:
                self._add(f"hand_diff:{type_id}", round(self.base_values[type_id] * 1.05, 8))
            for name, weight in (
                ("mobility_diff", 5.0),
                ("king_escape_diff", 12.0),
                ("king_zone_pressure_diff", 8.0),
                ("current_check_diff", 20.0),
                ("promotion_potential_diff", 15.0),
            ):
                self._add(name, weight)
            for type_id in self.hand_types:
                self._add(f"legal_drop_count_diff:{type_id}", 2.0)
            self._add("mean_legal_drop_mobility_diff", 2.0)

    def _side_actions(self, state: GameState) -> tuple[list[Action], list[Action]]:
        current = _sort_actions(legal_actions(state, self.compiled))
        other_state = _state_for_side(state, 1 - state.position.side_to_move)
        other = _sort_actions(legal_actions(other_state, self.compiled))
        return current, other

    def _attack_count(self, position: Position, owner: int) -> int:
        engine = semantic_engine_for(self.compiled)
        anchor = _anchor_square_generic(position, owner)
        zone = _zone_squares(anchor, self.n)
        if engine is not None:
            return sum(
                1
                for file, rank in zone
                if engine.is_square_attacked(position, _sq_index(file, rank, self.n), 1 - owner)
            )
        attacks = pseudo_attacks(position, 1 - owner, self.compiled)
        return sum(1 for file, rank in zone if (file, rank) in {(sq.file, sq.rank) for sq in attacks})

    def _promotion_potential(self, position: Position, owner: int, actions: list[Action]) -> int:
        if self.family != "standard_shogi":
            return 0
        zones = set((file, rank) for rank in ((6, 7, 8) if owner == 0 else (0, 1, 2)) for file in range(self.n))
        n = self.n
        legal_targets = {
            (action_source_square(action).file, action_source_square(action).rank): set()
            for action in actions if action_is_board(action) and action_source_square(action) is not None
        }
        for action in actions:
            if not action_is_board(action) or action_source_square(action) is None:
                continue
            source = action_source_square(action)
            target = action_target_square(action)
            legal_targets.setdefault((source.file, source.rank), set()).add((target.file, target.rank))
        result = 0
        for idx, piece in enumerate(position.board):
            if piece is None or piece.owner != owner or piece.base_type_id not in ("P", "L", "N", "S", "B", "R") or piece.promoted:
                continue
            source = (idx % n, idx // n)
            if source in zones or legal_targets.get(source, set()) & zones:
                result += 1
        return result

    def vector(self, state: GameState) -> np.ndarray:
        position = state.position
        cache_key = str(position_identity_key(position, self.compiled))
        cached = self._vector_cache.get(cache_key)
        if cached is not None:
            return cached
        side = position.side_to_move
        other = 1 - side
        current_actions, other_actions = self._side_actions(state)
        values: list[float] = []
        for type_id in self.material_types:
            own = sum(1 for piece in position.board if piece is not None and piece.owner == side and piece.current_type_id == type_id)
            opp = sum(1 for piece in position.board if piece is not None and piece.owner == other and piece.current_type_id == type_id)
            values.append(float(own - opp))
        for type_id in self.board_types:
            for rank in range(self.n):
                for file in range(self.n):
                    piece = position.board[_sq_index(file, rank, self.n)]
                    values.append(float(0 if piece is None or piece.current_type_id != type_id else _owner_sign(piece.owner, side)))
        values.extend([
            float(len(current_actions) - len(other_actions)),
            float(_king_escape_count(state, self.compiled, side, current_actions) - _king_escape_count(_state_for_side(state, other), self.compiled, other, other_actions)),
            float(self._attack_count(position, side) - self._attack_count(position, other)),
            float(int(self._in_check(position, side)) - int(self._in_check(position, other))),
        ])
        if self.family == "western_chess":
            own_struct = _pawn_structure(position, side)
            other_struct = _pawn_structure(position, other)
            values.extend(float(a - b) for a, b in zip(own_struct, other_struct))
        else:
            for type_id in self.hand_types:
                values.append(float(position.hands[side].count(type_id) - position.hands[other].count(type_id)))
            values.append(float(self._promotion_potential(position, side, current_actions) - self._promotion_potential(position, other, other_actions)))
            own_drop = {tid: 0 for tid in self.hand_types}
            other_drop = {tid: 0 for tid in self.hand_types}
            for action in current_actions:
                tid = action_drop_base_type_id(action) if action_is_drop(action) else None
                if tid in own_drop:
                    own_drop[tid] += 1
            for action in other_actions:
                tid = action_drop_base_type_id(action) if action_is_drop(action) else None
                if tid in other_drop:
                    other_drop[tid] += 1
            values.extend(float(own_drop[tid] - other_drop[tid]) for tid in self.hand_types)
            own_held = [own_drop[tid] for tid in self.hand_types if position.hands[side].count(tid) > 0]
            other_held = [other_drop[tid] for tid in self.hand_types if position.hands[other].count(tid) > 0]
            own_mean = statistics.fmean(own_held) if own_held else 0.0
            other_mean = statistics.fmean(other_held) if other_held else 0.0
            values.append(float(own_mean - other_mean))
        if len(values) != len(self.names):
            raise AssertionError((self.family, len(values), len(self.names)))
        vector = np.asarray(values, dtype=np.float64)
        self._vector_cache[cache_key] = vector
        return vector

    def _in_check(self, position: Position, owner: int) -> bool:
        engine = semantic_engine_for(self.compiled)
        if engine is not None:
            return bool(engine.in_check(position, owner))
        return bool(is_in_check(position, owner, self.compiled))

    def oracle(self, features: np.ndarray) -> float:
        return float(features @ np.asarray(self.weights, dtype=np.float64))


def _collect_corpus(family: str, compiled, basis: FrozenBasis, seed: int, forbidden: set[str]) -> list[dict]:
    needed = sum(COUNTS.values())
    seen = set(forbidden)
    rows: list[dict] = []
    trajectory_lengths = (8, 24, 64, 128, 192, 256)
    trajectory = 0
    while len(rows) < needed:
        rng = random.Random(seed + trajectory * 7919)
        state = initial_state(compiled)
        length = trajectory_lengths[trajectory % len(trajectory_lengths)]
        for ply in range(length):
            actions = _sort_actions(legal_actions(state, compiled))
            if not actions:
                break
            action = actions[rng.randrange(len(actions))]
            state = apply_action(state, action, compiled)
            key = str(position_identity_key(state.position, compiled))
            if key in seen or state.terminal_status.status is not TerminalStatus.ONGOING:
                continue
            seen.add(key)
            features = basis.vector(state)
            rows.append({
                "identity": key,
                "trajectory": trajectory,
                "ply": state.ply_count,
                "side_to_move": state.position.side_to_move,
                "features": features.tolist(),
                "oracle": basis.oracle(features),
            })
            if len(rows) >= needed:
                break
        trajectory += 1
        if trajectory > 2000:
            raise RuntimeError(f"corpus generation exceeded trajectory bound for {family}")
    return rows


def _collect_fresh_roots(family: str, compiled, basis: FrozenBasis, seed: int, forbidden: set[str], count: int) -> list[GameState]:
    result: list[GameState] = []
    seen = set(forbidden)
    trajectory = 0
    while len(result) < count:
        rng = random.Random(seed + trajectory * 3571)
        state = initial_state(compiled)
        length = 16 + (trajectory % 13) * 7
        for _ in range(length):
            actions = _sort_actions(legal_actions(state, compiled))
            if not actions:
                break
            state = apply_action(state, actions[rng.randrange(len(actions))], compiled)
            key = str(position_identity_key(state.position, compiled))
            if key in seen or state.terminal_status.status is not TerminalStatus.ONGOING:
                continue
            seen.add(key)
            result.append(state)
            if len(result) >= count:
                break
        trajectory += 1
        if trajectory > 500:
            raise RuntimeError(f"fresh root generation exceeded bound for {family}")
    return result


def _fit(rows: list[dict], basis: FrozenBasis, init_seed: int) -> dict:
    x = np.asarray([row["features"] for row in rows], dtype=np.float64)
    y = np.asarray([row["oracle"] for row in rows], dtype=np.float64)
    train_x, train_y = x[:COUNTS["train"]], y[:COUNTS["train"]]
    dev_x, dev_y = x[COUNTS["train"]:COUNTS["train"] + COUNTS["dev"]], y[COUNTS["train"]:COUNTS["train"] + COUNTS["dev"]]
    hold_x, hold_y = x[-COUNTS["holdout"]:], y[-COUNTS["holdout"]:]
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    active = scale > 1e-12
    scale_safe = np.where(active, scale, 1.0)
    z_train = (train_x - mean) / scale_safe
    z_dev = (dev_x - mean) / scale_safe
    z_hold = (hold_x - mean) / scale_safe
    target_mean = float(train_y.mean())
    target_std = float(train_y.std()) or 1.0
    n_train_y = (train_y - target_mean) / target_std
    d = int(active.sum()) + 1
    rng = np.random.default_rng(init_seed)
    params = rng.normal(0.0, 0.01, size=d)
    adam_m = np.zeros_like(params)
    adam_v = np.zeros_like(params)
    x_aug = np.column_stack([z_train[:, active], np.ones(len(z_train))])
    # Full-batch Adam: fixed 2000 steps, fixed lr and L2 exactly as ordered.
    for step in range(1, 2001):
        pred = x_aug @ params
        grad = (x_aug.T @ (pred - n_train_y)) / len(x_aug)
        grad[:-1] += 1e-6 * params[:-1]
        adam_m = 0.9 * adam_m + 0.1 * grad
        adam_v = 0.999 * adam_v + 0.001 * (grad * grad)
        mhat = adam_m / (1.0 - 0.9 ** step)
        vhat = adam_v / (1.0 - 0.999 ** step)
        params -= 0.01 * mhat / (np.sqrt(vhat) + 1e-8)
    # Closed form is diagnostic only; no model-selection use.
    gram = x_aug.T @ x_aug
    gram[:-1, :-1] += 1e-8 * np.eye(gram.shape[0] - 1)
    closed = np.linalg.solve(gram, x_aug.T @ n_train_y)
    def predict(z, model):
        return target_mean + target_std * (np.column_stack([z[:, active], np.ones(len(z))]) @ model)
    return {
        "train_features": train_x,
        "dev_features": dev_x,
        "holdout_features": hold_x,
        "train_oracle": train_y,
        "dev_oracle": dev_y,
        "holdout_oracle": hold_y,
        "mean": mean,
        "scale": scale_safe,
        "active": active,
        "target_mean": target_mean,
        "target_std": target_std,
        "adam_model": params,
        "closed_model": closed,
        "adam_predict": lambda z: predict(z, params),
        "closed_predict": lambda z: predict(z, closed),
        "constant_feature_names": [name for name, keep in zip(basis.names, active) if not keep],
        "normalization": {"train_feature_mean": mean.tolist(), "train_feature_scale": scale_safe.tolist(), "target_mean": target_mean, "target_std": target_std},
    }


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    result = np.empty(len(values), dtype=np.float64)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        result[order[i:j]] = (i + j - 1) / 2.0 + 1.0
        i = j
    return result


def _scalar_metrics(y: np.ndarray, pred: np.ndarray, train_std: float) -> dict:
    err = pred - y
    rmse = float(np.sqrt(np.mean(err * err)))
    centered_y = y - y.mean()
    centered_p = pred - pred.mean()
    denom = float(np.sqrt(np.sum(centered_y ** 2) * np.sum(centered_p ** 2)))
    pearson = float(np.sum(centered_y * centered_p) / denom) if denom else 0.0
    r2 = float(1.0 - np.sum(err * err) / np.sum(centered_y ** 2)) if np.sum(centered_y ** 2) else 0.0
    return {
        "rmse_oracle_units": rmse,
        "normalized_rmse": rmse / train_std,
        "r2": r2,
        "pearson": pearson,
        "spearman": float(np.corrcoef(_rankdata(y), _rankdata(pred))[0, 1]),
        "sign_agreement_nonzero": float(np.mean(np.sign(y[y != 0]) == np.sign(pred[y != 0]))) if np.any(y != 0) else 1.0,
        "max_abs_error": float(np.max(np.abs(err))),
    }


class BenchmarkNegamax:
    """Shared benchmark search, run fresh per root and evaluator."""

    def __init__(self, compiled, basis: FrozenBasis, evaluate: Callable[[GameState], float]) -> None:
        self.compiled = compiled
        self.basis = basis
        self.evaluate = evaluate
        self.nodes = 0
        self.tt: dict[tuple[str, int], float] = {}
        self.pv: tuple[Action, ...] = ()
        self.completed_depth = 0

    def _terminal(self, state: GameState) -> float | None:
        status = state.terminal_status
        if status.status is TerminalStatus.ONGOING:
            return None
        if status.winner is None:
            return 0.0
        return 1_000_000.0 if status.winner == state.position.side_to_move else -1_000_000.0

    def _negamax(self, state: GameState, depth: int, alpha: float, beta: float) -> tuple[float, tuple[Action, ...]]:
        if self.nodes >= SEARCH_NODES:
            return self.evaluate(state), ()
        terminal = self._terminal(state)
        if terminal is not None:
            return terminal, ()
        key = (str(position_identity_key(state.position, self.compiled)), depth)
        if key in self.tt:
            return self.tt[key], ()
        if depth == 0:
            self.nodes += 1
            value = self.evaluate(state)
            self.tt[key] = value
            return value, ()
        actions = _sort_actions(legal_actions(state, self.compiled))
        if not actions:
            self.nodes += 1
            return self.evaluate(state), ()
        best = -float("inf")
        best_pv: tuple[Action, ...] = ()
        for action in actions:
            if self.nodes >= SEARCH_NODES:
                break
            child = apply_action(state, action, self.compiled)
            child_value, child_pv = self._negamax(child, depth - 1, -beta, -alpha)
            value = -child_value
            if value > best or (value == best and (not best_pv or str(action) < str(best_pv[0]))):
                best = value
                best_pv = (action,) + child_pv
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        if best == -float("inf"):
            best = self.evaluate(state)
        self.tt[key] = best
        return best, best_pv

    def search(self, state: GameState) -> dict:
        best_value = self.evaluate(state)
        best_pv: tuple[Action, ...] = ()
        for depth in range(1, SEARCH_DEPTH + 1):
            before = self.nodes
            value, pv = self._negamax(state, depth, -float("inf"), float("inf"))
            if self.nodes >= SEARCH_NODES and before < self.nodes and not pv:
                break
            if pv:
                best_value, best_pv = value, pv
                self.completed_depth = depth
            if self.nodes >= SEARCH_NODES:
                break
        self.pv = best_pv
        return {"action": str(best_pv[0]) if best_pv else None, "score": float(best_value), "pv_head": str(best_pv[0]) if best_pv else None, "depth": self.completed_depth, "nodes": self.nodes}


def _evaluate_model(state: GameState, basis: FrozenBasis, fit: dict, which: str) -> float:
    z = (basis.vector(state) - fit["mean"]) / fit["scale"]
    model = fit[f"{which}_model"]
    active = fit["active"]
    return float(fit["target_mean"] + fit["target_std"] * (np.r_[z[active], 1.0] @ model))


def _action_ranking(roots: list[GameState], basis: FrozenBasis, fit: dict, which: str) -> dict:
    top_agree = 0
    pair_agree = 0
    pair_total = 0
    regrets: list[float] = []
    top2_gaps: list[float] = []
    for state in roots:
        actions = _sort_actions(legal_actions(state, basis.compiled))
        oracle_scores = []
        learned_scores = []
        for action in actions:
            child = apply_action(state, action, basis.compiled)
            child_features = basis.vector(child)
            oracle_scores.append(-basis.oracle(child_features))
            learned_scores.append(-_evaluate_model(child, basis, fit, which))
        oracle_order = sorted(range(len(actions)), key=lambda idx: (-oracle_scores[idx], str(actions[idx])))
        learned_order = sorted(range(len(actions)), key=lambda idx: (-learned_scores[idx], str(actions[idx])))
        if oracle_order and learned_order and oracle_order[0] == learned_order[0]:
            top_agree += 1
        for i in range(len(actions)):
            for j in range(i + 1, len(actions)):
                pair_total += 1
                if (oracle_order.index(i) < oracle_order.index(j)) == (learned_order.index(i) < learned_order.index(j)):
                    pair_agree += 1
        if oracle_order:
            regrets.append(float(oracle_scores[oracle_order[0]] - oracle_scores[learned_order[0]]))
            top2_gaps.append(float(oracle_scores[oracle_order[0]] - oracle_scores[oracle_order[1]]) if len(oracle_order) > 1 else 0.0)
    scale = float(np.std([row["oracle"] for row in []])) if False else 1.0
    # Caller inserts the scalar holdout standard explicitly.
    return {
        "roots": len(roots),
        "top1_agreement": top_agree / len(roots),
        "pairwise_ordering_agreement": pair_agree / pair_total if pair_total else 1.0,
        "regrets": regrets,
        "oracle_top2_gaps": top2_gaps,
    }


def _search_probe(roots: list[GameState], basis: FrozenBasis, fit: dict, which: str) -> dict:
    records = []
    for state in roots:
        oracle_result = BenchmarkNegamax(basis.compiled, basis, lambda s: basis.oracle(basis.vector(s))).search(state)
        if which == "random":
            rng = np.random.default_rng(1220991 + len(records))
            random_weights = rng.normal(0.0, 1.0, len(basis.names))
            evaluator = lambda s, rw=random_weights: float(basis.vector(s) @ rw)
        elif which == "oracle":
            evaluator = lambda s: basis.oracle(basis.vector(s))
        else:
            evaluator = lambda s: _evaluate_model(s, basis, fit, "adam")
        learned_result = BenchmarkNegamax(basis.compiled, basis, evaluator).search(state)
        records.append({"oracle": oracle_result, "candidate": learned_result})
    same_action = sum(r["oracle"]["action"] == r["candidate"]["action"] for r in records)
    same_pv = sum(r["oracle"]["pv_head"] == r["candidate"]["pv_head"] for r in records)
    depths = [r["candidate"]["depth"] for r in records]
    nodes = [r["candidate"]["nodes"] for r in records]
    gaps = [abs(r["oracle"]["score"] - r["candidate"]["score"]) for r in records if r["oracle"]["action"] != r["candidate"]["action"]]
    return {
        "roots": len(records),
        "top_action_agreement": same_action / len(records),
        "pv_head_agreement": same_pv / len(records),
        "mean_oracle_score_gap_if_different": float(np.mean(gaps)) if gaps else 0.0,
        "depth_parity": {"same": sum(r["oracle"]["depth"] == r["candidate"]["depth"] for r in records) / len(records), "oracle_mean": float(np.mean([r["oracle"]["depth"] for r in records])), "candidate_mean": float(np.mean(depths))},
        "node_parity": {"same": sum(r["oracle"]["nodes"] == r["candidate"]["nodes"] for r in records) / len(records), "oracle_mean": float(np.mean([r["oracle"]["nodes"] for r in records])), "candidate_mean": float(np.mean(nodes))},
    }


def _summarize_model(rows: list[dict], fit: dict, which: str) -> dict:
    x = fit["holdout_features"]
    y = fit["holdout_oracle"]
    return _scalar_metrics(y, fit[f"{which}_predict"]((x - fit["mean"]) / fit["scale"]), fit["target_std"])


def run() -> dict:
    all_results = {"schema": "F122_REVERSE_BENCHMARK_V1", "rulesets": {}, "classification": {}}
    for family, corpus_seed, init_seed, root_seed in (
        ("western_chess", 1220101, 1220111, 1220121),
        ("standard_shogi", 1220201, 1220211, 1220221),
    ):
        ruleset = build_western_chess_ruleset() if family == "western_chess" else build_standard_shogi_ruleset()
        compiled = compile_semantic_ruleset(ruleset)
        basis = FrozenBasis(family, compiled)
        rows = _collect_corpus(family, compiled, basis, corpus_seed, set())
        fit = _fit(rows, basis, init_seed)
        roots = _collect_fresh_roots(family, compiled, basis, root_seed, {row["identity"] for row in rows}, 256)
        scalar = {model: _summarize_model(rows, fit, model) for model in ("adam", "closed")}
        random_scalar = _scalar_metrics(fit["holdout_oracle"], np.full(len(fit["holdout_oracle"]), float(np.mean(fit["train_oracle"]))), fit["target_std"])
        ranking = _action_ranking(roots, basis, fit, "adam")
        holdout_std = float(np.std(fit["holdout_oracle"]))
        ranking_summary = {
            "top1_agreement": ranking["top1_agreement"],
            "pairwise_ordering_agreement": ranking["pairwise_ordering_agreement"],
            "mean_regret_normalized": float(np.mean(ranking["regrets"]) / holdout_std),
            "median_regret_normalized": float(np.median(ranking["regrets"]) / holdout_std),
            "p95_regret_normalized": float(np.percentile(ranking["regrets"], 95) / holdout_std),
            "mean_oracle_top2_gap_normalized": float(np.mean(ranking["oracle_top2_gaps"]) / holdout_std),
            "regret_raw": ranking["regrets"],
            "oracle_top2_gaps_raw": ranking["oracle_top2_gaps"],
        }
        search = {"random": _search_probe(roots[:64], basis, fit, "random"), "oracle": _search_probe(roots[:64], basis, fit, "oracle"), "adam": _search_probe(roots[:64], basis, fit, "adam")}
        adam_scalar_pass = scalar["adam"]["normalized_rmse"] <= 0.05 and scalar["adam"]["r2"] >= 0.99 and scalar["adam"]["pearson"] >= 0.995
        closed_scalar_pass = scalar["closed"]["normalized_rmse"] <= 0.05 and scalar["closed"]["r2"] >= 0.99 and scalar["closed"]["pearson"] >= 0.995
        adam_action_pass = ranking_summary["top1_agreement"] >= 0.90 and ranking_summary["pairwise_ordering_agreement"] >= 0.95 and ranking_summary["mean_regret_normalized"] <= 0.05
        all_results["rulesets"][family] = {
            "basis": {"feature_count": len(basis.names), "feature_names": basis.names, "oracle_weights": basis.weights, "oracle_weight_sha256": basis.oracle_weight_sha256},
            "corpus": {"counts": COUNTS, "rows": len(rows), "corpus_seed": corpus_seed, "trajectory_lengths": [8, 24, 64, 128, 192, 256], "identity_sha256": _json_sha([row["identity"] for row in rows])},
            "fit": {"init_seed": init_seed, "optimizer": {"name": "full_batch_adam", "steps": 2000, "lr": 0.01, "l2": 1e-6}, "constant_feature_names": fit["constant_feature_names"], "scalar_metrics": scalar, "random_baseline_scalar": random_scalar, "adam_scalar_gate_pass": adam_scalar_pass, "closed_form_scalar_gate_pass": closed_scalar_pass},
            "action_ranking": {"root_seed": root_seed, "roots": 256, "model": "adam", "gates_pass": adam_action_pass, **ranking_summary},
            "search_recovery": {"budget_nodes": SEARCH_NODES, "max_depth": SEARCH_DEPTH, "same_engine": True, "results": search},
            "gates": {"adam_scalar": adam_scalar_pass, "adam_action": adam_action_pass, "closed_form_scalar": closed_scalar_pass},
        }
        if not closed_scalar_pass:
            all_results["classification"][family] = "REVERSE_BENCHMARK_CORPUS_OR_BASIS_UNDERDETERMINED"
        elif not adam_scalar_pass or not adam_action_pass:
            all_results["classification"][family] = "REVERSE_BENCHMARK_LEARNING_PIPELINE_FAILURE_SUPPORTED"
        else:
            all_results["classification"][family] = "KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES"
    chess = all_results["classification"]["western_chess"]
    shogi = all_results["classification"]["standard_shogi"]
    if chess == "KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES" and shogi != chess:
        all_results["classification"]["overall"] = "SHOGI_PIPELINE_SPECIFIC_FAILURE_SUPPORTED"
    elif shogi == "KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES" and chess != shogi:
        all_results["classification"]["overall"] = "CHESS_PIPELINE_SPECIFIC_FAILURE_SUPPORTED"
    elif chess == shogi == "KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES":
        all_results["classification"]["overall"] = chess
    else:
        all_results["classification"]["overall"] = "REVERSE_BENCHMARK_DIAGNOSTIC_REQUIRED"
    return all_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    result = run()
    result["runtime_seconds"] = time.time() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
