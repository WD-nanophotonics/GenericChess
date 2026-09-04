"""F59 action-spectrum, distribution, and objective diagnosis.

This is an offline policy-surface audit.  It deliberately keeps the v2 search,
the corrected F58 state encoding, and the observed v4 comparator fixed while it
varies only the state distribution and the supervision objective.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from f50_generic_learnable_evaluator import _ruleset  # noqa: E402
from f54_direct_capacity_and_gradient_geometry_diagnosis import (  # noqa: E402
    _action_key, _parent, _record_dict, _session,
)
from f58_compact_nonlinear_capacity import (  # noqa: E402
    MATE_THRESHOLD, SEEDS, _corpus,
)
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.actions import action_from_dict, action_to_dict  # noqa: E402
from generic_chess.core.identity import position_identity_key  # noqa: E402
from generic_chess.core.transition import apply_action  # noqa: E402
from generic_chess.learning.features import linear_value, material_features  # noqa: E402
from generic_chess.learning.diagnostics import generate_diagnostic_corpus  # noqa: E402
from generic_chess.learning.nonlinear import semantic_state_features  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native.adapter import pack_semantic_search_position  # noqa: E402
from generic_chess.native.semantic import dynamic_features as native_dynamic_features  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402


OUT = ROOT / ".generic_chess_flow" / "f59-action-spectrum-diagnosis"
LABELS = ("A_CANONICAL_WESTERN_CHESS", "B_CANONICAL_STANDARD_SHOGI")
ROOT_COUNT = 36
DEV_COUNT = 24
HOLDOUT_COUNT = 12
SELFPLAY_GAMES = 8
SELFPLAY_MAX_PLIES = 24
PV_NODES = 10_000
SPECTRUM_BUDGETS = (1_000, 10_000, 20_000)
ROOT_BUDGETS = (2_000, 40_000, 80_000)
TRAINING_SEEDS = (59011, 59012, 59013)
MODEL_WIDTH = 32
MODEL_REGULARIZATION = 1e-3
TEMPERATURE = 1_000.0
_ROOT_WORKER_CONTEXT = None


@dataclass(frozen=True)
class SpectrumRow:
    action: dict
    action_key: str
    features: np.ndarray
    base_q: float
    q_1k: float | None = None
    q_10k: float | None = None
    q_20k: float | None = None


def _root_search(compiled, native, checkpoint, record, nodes):
    session = _session(compiled, record)
    result = SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=8).search(
        session, SearchLimits(max_depth=12, max_nodes=nodes, quiescence_max_depth=0)
    )
    payload = None if result.action is None else action_to_dict(result.action)
    return {
        "action": payload,
        "action_key": _action_key(payload),
        "score": int(result.score),
        "completed_depth": int(result.completed_depth),
        "nodes": int(result.nodes),
        "pv": [action_to_dict(a) for a in result.principal_variation],
        "side_to_move": int(session.state.position.side_to_move),
    }


def _parallel_root(compiled, native, checkpoint, records, nodes):
    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda r: _root_search(compiled, native, checkpoint, r, nodes), records))


def _child_features(compiled, native, parent, record, action_payload):
    session = _session(compiled, record)
    root_side = int(session.state.position.side_to_move)
    action = action_from_dict(action_payload)
    if action not in session.legal_actions():
        raise ValueError("spectrum action is not legal at its root")
    session.submit(action)
    packed = pack_semantic_search_position(compiled, native, session)
    dynamic = native_dynamic_features(native, packed)
    features = semantic_state_features(session.state.position, compiled, dynamic)
    type_ids = tuple(sorted(parent.board_weights))
    material = material_features(session.state.position, type_ids, perspective=0)
    static_owner0 = linear_value(material, parent.board_weights, parent.hand_weights,
                                 dynamic, parent.dynamic_weights)
    return features, (float(static_owner0) if root_side == 0 else -float(static_owner0)), root_side


def _child_search(compiled, native, parent, record, action_payload, nodes):
    session = _session(compiled, record)
    root_side = int(session.state.position.side_to_move)
    action = action_from_dict(action_payload)
    session.submit(action)
    result = SemanticSearchEngine(compiled, native, checkpoint=parent, tt_megabytes=8).search(
        session, SearchLimits(max_depth=12, max_nodes=nodes, quiescence_max_depth=0)
    )
    # Native score is from the child side-to-move perspective; negate it back
    # to the player who owned the root action.
    child_value = int(result.score) / parent.semantic_native_scale
    return _root_player_q(child_value, root_side)


def _root_player_q(child_value, root_side):
    """Convert a child-side-to-move value to the owner of the root action."""
    if root_side not in (0, 1):
        raise ValueError("root_side must be 0 or 1")
    return -float(child_value)


def _parallel_children(compiled, native, parent, record, actions, nodes):
    workers = 1 if os.environ.get("F59_ROOT_WORKER") == "1" else min(8, max(1, os.cpu_count() or 1), len(actions) or 1)
    jobs = [(record, action) for action in actions]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda item: _child_search(compiled, native, parent, item[0], item[1], nodes), jobs))


def _record_from_actions(compiled, actions):
    session = _session(compiled, {"action_history": []})
    for action in actions:
        if action not in session.legal_actions():
            return None
        session.submit(action)
        if session.result.status.value != "ongoing":
            return None
    return _record_dict(type("Position", (), {
        "index": 0,
        "action_history": tuple(actions),
        "position_key": position_identity_key(session.state.position, compiled),
        "side_to_move": session.state.position.side_to_move,
        "ply": len(actions),
    })())


def _distributions(label, compiled, native, parent, root_count, smoke=False):
    seed = SEEDS[label]
    openings = generate_arena_openings(compiled, count=max(8, root_count), seed=seed, min_plies=2, max_plies=6)
    corpus = generate_diagnostic_corpus(compiled, openings, count=root_count, seed=seed + 1, min_plies=8, max_plies=40)
    d0 = [_record_dict(position) for position in corpus.positions]
    selfplay_nodes = 50 if smoke else 2_000
    selfplay_plies = 4 if smoke else SELFPLAY_MAX_PLIES
    trajectories = collect_self_play(
        compiled, native, parent,
        SelfPlayConfig(games=min(SELFPLAY_GAMES, max(2, math.ceil(root_count / 12))), nodes_per_move=selfplay_nodes, max_depth=12,
                       seed=SEEDS[label] + 59, epsilon=0.10,
                       tt_megabytes=8, max_plies=selfplay_plies),
    )
    d1 = []
    seen = set()
    for trajectory in trajectories:
        actions = tuple(trajectory.actions)
        for point in trajectory.points:
            if point.ply >= len(actions):
                continue
            record = _record_from_actions(compiled, actions[:point.ply])
            if record is not None and record["position_key"] not in seen:
                seen.add(record["position_key"])
                d1.append(record)
    d1 = d1[:root_count]
    if len(d1) < root_count:
        raise ValueError(f"{label}: v2 self-play supplied only {len(d1)} D1 roots")

    d2 = []
    seen = set()
    for record in d1:
        root = _root_search(compiled, native, parent, record, PV_NODES)
        history = [action_from_dict(item) for item in record["action_history"]]
        for payload_action in root["pv"]:
            history.append(action_from_dict(payload_action))
            candidate = _record_from_actions(compiled, history)
            if candidate is not None and candidate["position_key"] not in seen:
                seen.add(candidate["position_key"])
                d2.append(candidate)
            if len(d2) >= root_count:
                break
        if len(d2) >= root_count:
            break
    if len(d2) < root_count:
        raise ValueError(f"{label}: v2 PV corridor supplied only {len(d2)} D2 roots")
    return {"D0_RANDOM_REACHABLE": d0, "D1_V2_SELFPLAY": d1, "D2_V2_PV_CORRIDOR": d2}, {
        "d0_corpus_id": stable_sha256(corpus.to_dict()),
        "d1_trajectory_count": len(trajectories),
    }


def _model_checkpoint(compiled, model_payload):
    parent = _parent("B_CANONICAL_STANDARD_SHOGI")
    return parent.child_checkpoint(
        board_weights=parent.board_weights, hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights, compact_nonlinear=model_payload,
        games_seen_delta=0, positions_seen_delta=0, training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": "f59-v4-observer"}),
        training_seed=59011,
    )


def _load_v4(compiled):
    source = ROOT / ".generic_chess_flow" / "f58-compact-nonlinear-capacity" / "f58_shogi_baseline_preserved.json"
    if not source.exists():
        raise FileNotFoundError(f"preserved F58 v4 comparator is missing: {source}")
    data = json.loads(source.read_text(encoding="utf-8"))
    result = next(item for item in data["results"] if item["label"] == "B_CANONICAL_STANDARD_SHOGI")
    model = next(item for item in result["compact_models"] if int(item["seed"]) == 58011)
    return _model_checkpoint(compiled, model)


def _init_root_worker(label, smoke):
    global _ROOT_WORKER_CONTEXT
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    observer = _load_v4(compiled) if label == "B_CANONICAL_STANDARD_SHOGI" else parent
    _ROOT_WORKER_CONTEXT = (compiled, native, parent, observer, smoke)
    os.environ["F59_ROOT_WORKER"] = "1"


def _spectrum_root_worker(record):
    compiled, native, parent, observer, smoke = _ROOT_WORKER_CONTEXT
    return _spectrum_for_root(compiled, native, parent, observer, record, smoke=smoke)


def _softmax(values, temperature=TEMPERATURE):
    values = np.asarray(values, dtype=float) / temperature
    shifted = values - np.max(values)
    probabilities = np.exp(shifted)
    return probabilities / np.sum(probabilities)


def _fit_model(features, base_q, targets, groups, objective, seed):
    """Fit the fixed width-32 tanh residual with one of three losses."""
    x = np.asarray(features, dtype=float)
    residual = np.asarray(targets, dtype=float) - np.asarray(base_q, dtype=float)
    mean = np.mean(x, axis=0)
    scale = np.where(np.std(x, axis=0) > 1e-9, np.std(x, axis=0), 1.0)
    xn = (x - mean) / scale
    target_scale = float(np.std(residual)) or 1.0
    yn = residual / target_scale
    rng = np.random.default_rng(seed)
    hidden_weights = rng.normal(0.0, np.sqrt(2.0 / (x.shape[1] + MODEL_WIDTH)), size=(MODEL_WIDTH, x.shape[1]))
    hidden_bias = np.zeros(MODEL_WIDTH)
    output_weights = rng.normal(0.0, 1.0 / np.sqrt(MODEL_WIDTH), size=MODEL_WIDTH)
    output_bias = np.asarray(0.0)
    moments = [(np.zeros_like(p), np.zeros_like(p)) for p in (hidden_weights, hidden_bias, output_weights, output_bias)]
    for step in range(1, 601):
        hidden = np.tanh(xn @ hidden_weights.T + hidden_bias)
        prediction = hidden @ output_weights + output_bias
        grad_prediction = np.zeros(len(x), dtype=float)
        if objective == "POINTWISE_Q":
            grad_prediction = (prediction - yn) / len(x)
        elif objective == "SOFT_POLICY_DISTILLATION":
            for indices in groups:
                teacher = _softmax(targets[indices])
                student = _softmax(base_q[indices] + prediction[indices] * target_scale)
                grad_prediction[indices] = (student - teacher) / TEMPERATURE
            grad_prediction /= max(len(groups), 1)
        elif objective == "PAIRWISE_RANKING":
            pair_count = 0
            for indices in groups:
                for left in range(len(indices)):
                    for right in range(left + 1, len(indices)):
                        i, j = indices[left], indices[right]
                        delta = (targets[i] - targets[j]) / target_scale
                        if abs(delta) < 1e-9:
                            continue
                        sign = 1.0 if delta > 0 else -1.0
                        # Rank total Q (base plus residual), not residual alone.
                        # The division keeps the development-only margin in a
                        # scale comparable to the pointwise objective.
                        total_prediction = base_q + prediction * target_scale
                        margin = sign * (total_prediction[i] - total_prediction[j]) / target_scale
                        derivative = -sign / (1.0 + math.exp(min(60.0, max(-60.0, margin))))
                        grad_prediction[i] += derivative
                        grad_prediction[j] -= derivative
                        pair_count += 1
            grad_prediction /= max(pair_count, 1)
        else:
            raise ValueError(f"unknown objective {objective}")
        grad_output = hidden.T @ grad_prediction + MODEL_REGULARIZATION * output_weights
        grad_hidden = ((grad_prediction[:, None] * output_weights[None, :]) * (1.0 - hidden * hidden)).T @ xn + MODEL_REGULARIZATION * hidden_weights
        grad_hidden_bias = np.sum((grad_prediction[:, None] * output_weights[None, :]) * (1.0 - hidden * hidden), axis=0)
        gradients = (grad_hidden, grad_hidden_bias, grad_output, np.asarray(np.sum(grad_prediction)))
        for index, (param, gradient) in enumerate(zip((hidden_weights, hidden_bias, output_weights, output_bias), gradients)):
            first, second = moments[index]
            first[...] = 0.9 * first + 0.1 * gradient
            second[...] = 0.999 * second + 0.001 * gradient * gradient
            param[...] -= 0.01 * (first / (1.0 - 0.9 ** step)) / (np.sqrt(second / (1.0 - 0.999 ** step)) + 1e-8)

    def predict(values):
        values = np.asarray(values, dtype=float)
        return np.tanh((values - mean) / scale @ hidden_weights.T + hidden_bias) @ output_weights * target_scale + output_bias * target_scale

    return predict


def _metrics(root_rows, predictions):
    regrets = []
    rank_correct = 0
    rank_total = 0
    top1 = 0
    mse = []
    cross_entropy = []
    kl = []
    for root, predicted in zip(root_rows, predictions):
        teacher = np.asarray([row.q_20k for row in root], dtype=float)
        predicted = np.asarray(predicted, dtype=float)
        teacher_best = int(np.argmax(teacher))
        student_best = int(np.argmax(predicted))
        top1 += int(teacher_best == student_best)
        regrets.append(float(np.max(teacher) - teacher[student_best]))
        mse.extend((predicted - teacher).tolist())
        for i in range(len(root)):
            for j in range(i + 1, len(root)):
                teacher_sign = np.sign(teacher[i] - teacher[j])
                if teacher_sign == 0:
                    continue
                rank_total += 1
                rank_correct += int(teacher_sign == np.sign(predicted[i] - predicted[j]))
        teacher_prob = _softmax(teacher)
        student_prob = _softmax(predicted)
        cross_entropy.append(float(-np.sum(teacher_prob * np.log(np.maximum(student_prob, 1e-12)))))
        kl.append(float(np.sum(teacher_prob * np.log(np.maximum(teacher_prob, 1e-12) / np.maximum(student_prob, 1e-12)))))
    return {
        "roots": len(root_rows),
        "top1_agreement": top1 / len(root_rows) if root_rows else 0.0,
        "teacher_regret_mean": float(np.mean(regrets)) if regrets else 0.0,
        "teacher_regret_median": float(np.median(regrets)) if regrets else 0.0,
        "ranking_accuracy": rank_correct / rank_total if rank_total else 0.0,
        "soft_cross_entropy": float(np.mean(cross_entropy)) if cross_entropy else 0.0,
        "soft_kl": float(np.mean(kl)) if kl else 0.0,
        "mse_secondary": float(np.mean(np.asarray(mse) ** 2)) if mse else 0.0,
    }


def _spectrum_for_root(compiled, native, parent, observer, record, smoke=False):
    session = _session(compiled, record)
    legal = sorted(session.legal_actions(), key=lambda a: json.dumps(action_to_dict(a), sort_keys=True))
    root_2k_budget, root_40k_budget, root_80k_budget = (50, 100, 200) if smoke else ROOT_BUDGETS
    cheap_budget, mid_budget, high_budget = (50, 100, 200) if smoke else SPECTRUM_BUDGETS
    root_2k = _root_search(compiled, native, parent, record, root_2k_budget)
    root_40k = _root_search(compiled, native, parent, record, root_40k_budget)
    root_80k = _root_search(compiled, native, parent, record, root_80k_budget)
    observer_2k = _root_search(compiled, native, observer, record, 50 if smoke else 2_000)
    cheap = _parallel_children(compiled, native, parent, record, [action_to_dict(a) for a in legal], cheap_budget)
    order = sorted(range(len(legal)), key=lambda i: (-cheap[i], json.dumps(action_to_dict(legal[i]), sort_keys=True)))
    selected = [action_to_dict(legal[i]) for i in order[:3 if smoke else 6]]
    for payload in (root_2k["action"], observer_2k["action"], root_80k["action"]):
        if payload is not None and _action_key(payload) not in {_action_key(a) for a in selected}:
            selected.append(payload)
    prepared = []
    for payload in selected:
        features, base_q, _side = _child_features(compiled, native, parent, record, payload)
        prepared.append(SpectrumRow(payload, _action_key(payload), features, base_q))
    q10 = _parallel_children(compiled, native, parent, record, [row.action for row in prepared], mid_budget)
    q20 = _parallel_children(compiled, native, parent, record, [row.action for row in prepared], high_budget)
    cheap_by_key = {_action_key(action_to_dict(action)): float(value) for action, value in zip(legal, cheap)}
    rows = [SpectrumRow(row.action, row.action_key, row.features, row.base_q,
                        cheap_by_key.get(row.action_key), a, b)
            for row, a, b in zip(prepared, q10, q20)]
    teacher_q = np.asarray([row.q_20k for row in rows], dtype=float)
    teacher_order = np.argsort(-teacher_q)
    teacher_best = rows[int(teacher_order[0])]
    teacher_second = rows[int(teacher_order[1])] if len(rows) > 1 else teacher_best
    teacher_max = float(teacher_best.q_20k)
    v2_row = next(row for row in rows if row.action_key == root_2k["action_key"])
    v4_row = next(row for row in rows if row.action_key == observer_2k["action_key"])
    return rows, {
        "root_2k": root_2k, "root_40k": root_40k, "root_80k": root_80k,
        "observer_2k": observer_2k, "legal_action_count": len(legal),
        "cheap_top6": [action_to_dict(legal[i]) for i in order[:6]],
        "spectrum_top_10k_action_key": max(rows, key=lambda row: row.q_10k).action_key,
        "spectrum_top_20k_action_key": max(rows, key=lambda row: row.q_20k).action_key,
        "teacher_best_q20": teacher_max,
        "teacher_gap_q20": teacher_max - float(teacher_second.q_20k),
        "v2_action_regret_q20": teacher_max - float(v2_row.q_20k),
        "v4_action_regret_q20": teacher_max - float(v4_row.q_20k),
        "root_2k_score_error_vs_80k": abs(root_2k["score"] - root_80k["score"]),
    }


def _rankdata(values):
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2.0
        start = end
    return ranks


def _correlations(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return {"count": int(len(x)), "pearson": None, "spearman": None}
    return {
        "count": int(len(x)),
        "pearson": float(np.corrcoef(x, y)[0, 1]),
        "spearman": float(np.corrcoef(_rankdata(x), _rankdata(y))[0, 1]),
    }


def _gap_buckets(gaps, regrets):
    gaps = np.asarray(gaps, dtype=float)
    regrets = np.asarray(regrets, dtype=float)
    if not len(gaps):
        return []
    edges = np.quantile(gaps, [0.0, 0.25, 0.5, 0.75, 1.0])
    buckets = []
    for index in range(4):
        if index == 0:
            mask = (gaps >= edges[index]) & (gaps <= edges[index + 1])
        else:
            mask = (gaps > edges[index]) & (gaps <= edges[index + 1])
        buckets.append({
            "quartile": index + 1,
            "gap_low": float(edges[index]), "gap_high": float(edges[index + 1]),
            "count": int(np.sum(mask)),
            "regret_mean": float(np.mean(regrets[mask])) if np.any(mask) else None,
            "regret_median": float(np.median(regrets[mask])) if np.any(mask) else None,
        })
    return buckets


def _run_distribution(label, distribution, records, compiled, native, parent, observer, smoke=False, diagnostic_only=False):
    all_roots = []
    metadata = []
    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_root_worker,
                             initargs=(label, smoke)) as pool:
        computed = list(pool.map(_spectrum_root_worker, records))
    for index, (rows, root_meta) in enumerate(computed):
        all_roots.append(rows)
        metadata.append({"index": index, "position_key": records[index]["position_key"], "root": root_meta})
    stable = [m["root"]["spectrum_top_10k_action_key"] == m["root"]["spectrum_top_20k_action_key"] for m in metadata]
    stable_roots = [i for i, value in enumerate(stable) if value]
    if len(stable_roots) < 2:
        return {"classification": "TEACHER_POLICY_SURFACE_UNSTABLE", "stable_count": len(stable_roots), "roots": len(records)}
    dev = [i for i in stable_roots if i < DEV_COUNT]
    holdout = [i for i in stable_roots if i >= DEV_COUNT]
    if diagnostic_only:
        dev, holdout = [], stable_roots
    elif not dev or not holdout:
        return {
            "classification": "INSUFFICIENT_FROZEN_SPLIT",
            "roots": len(records), "stable_count": len(stable_roots),
            "stable_rate": len(stable_roots) / len(records),
            "stable_indices": stable_roots,
            "development_indices": dev, "holdout_indices": holdout,
        }
    objective_results = {}
    if not diagnostic_only:
        train_rows = [row for i in dev for row in all_roots[i]]
        holdout_rows = [all_roots[i] for i in holdout]
        x = np.vstack([row.features for row in train_rows])
        base = np.asarray([row.base_q for row in train_rows])
        y = np.asarray([row.q_20k for row in train_rows])
        groups = []
        cursor = 0
        for i in dev:
            groups.append(np.arange(cursor, cursor + len(all_roots[i])))
            cursor += len(all_roots[i])
        for objective in ("POINTWISE_Q", "PAIRWISE_RANKING", "SOFT_POLICY_DISTILLATION"):
            runs = []
            for seed in TRAINING_SEEDS:
                model = _fit_model(x, base, y, groups, objective, seed)
                predicted = [row[0].base_q + model(np.vstack([item.features for item in row])) for row in holdout_rows]
                runs.append(_metrics(holdout_rows, predicted))
            objective_results[objective] = {"seeds": list(TRAINING_SEEDS), "runs": runs}
    baseline = {}
    for name in ("v2_parent", "v4_observer"):
        predicted_rows = []
        for i in holdout:
            key = metadata[i]["root"]["root_2k" if name == "v2_parent" else "observer_2k"]["action_key"]
            predicted_rows.append(next(row for row in all_roots[i] if row.action_key == key))
        regrets = [float(max(row.q_20k for row in all_roots[i]) - selected.q_20k) for i, selected in zip(holdout, predicted_rows)]
        baseline[name] = {"roots": len(regrets), "teacher_regret_mean": float(np.mean(regrets)), "teacher_regret_median": float(np.median(regrets))}
    stable_metadata = [metadata[i]["root"] for i in stable_roots]
    score_error = [root["root_2k_score_error_vs_80k"] / parent.semantic_native_scale for root in stable_metadata]
    v2_regret = [root["v2_action_regret_q20"] for root in stable_metadata]
    v4_regret = [root["v4_action_regret_q20"] for root in stable_metadata]
    gaps = [root["teacher_gap_q20"] for root in stable_metadata]
    return {
        "classification": "PENDING_REVIEW", "roots": len(records), "stable_count": len(stable_roots),
        "stable_rate": len(stable_roots) / len(records), "stable_indices": stable_roots,
        "development_indices": dev, "holdout_indices": holdout,
        "teacher_action_spectrum": {
            "candidate_count_mean": float(np.mean([len(rows) for rows in all_roots])),
            "legal_action_count_mean": float(np.mean([m["root"]["legal_action_count"] for m in metadata])),
            "top1_10k_vs_20k": float(np.mean([m["root"]["spectrum_top_10k_action_key"] == m["root"]["spectrum_top_20k_action_key"] for m in metadata])),
            "root_40k_vs_80k_agreement": float(np.mean([m["root"]["root_40k"]["action_key"] == m["root"]["root_80k"]["action_key"] for m in metadata])),
            "v2_2k_agreement_with_80k": float(np.mean([m["root"]["root_2k"]["action_key"] == m["root"]["root_80k"]["action_key"] for m in metadata])),
            "v4_2k_agreement_with_80k": float(np.mean([m["root"]["observer_2k"]["action_key"] == m["root"]["root_80k"]["action_key"] for m in metadata])),
        },
        "baseline_regret": baseline, "objectives": objective_results,
        "policy_error_correlations": {
            "root_2k_score_error_vs_v2_action_regret": _correlations(score_error, v2_regret),
            "root_2k_score_error_vs_v4_action_regret": _correlations(score_error, v4_regret),
            "teacher_gap_vs_v2_action_regret": _correlations(gaps, v2_regret),
            "teacher_gap_vs_v4_action_regret": _correlations(gaps, v4_regret),
            "definitions": {
                "root_2k_score_error": "absolute root score difference between v2 at 2k and v2 at 80k, normalized by semantic_native_scale",
                "action_regret": "teacher max candidate Q20 minus Q20 of the selected v2/v4 2k action",
                "gap": "teacher best-minus-second-best candidate Q20",
            },
        },
        "regret_by_teacher_gap_quartile": {
            "v2_parent": _gap_buckets(gaps, v2_regret),
            "v4_observer": _gap_buckets(gaps, v4_regret),
        },
        "roots_metadata": metadata,
    }


def _run_label(label, root_count=ROOT_COUNT, smoke=False, diagnostic_only=False):
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    observer = _load_v4(compiled) if label == "B_CANONICAL_STANDARD_SHOGI" else parent
    distributions, provenance = _distributions(label, compiled, native, parent, root_count, smoke=smoke)
    results = {}
    for name, records in distributions.items():
        results[name] = _run_distribution(label, name, records[:root_count], compiled, native, parent, observer, smoke=smoke, diagnostic_only=diagnostic_only)
    return {"label": label, "parent_checkpoint_id": parent.checkpoint_id,
            "distributions": results, "provenance": provenance}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ruleset", choices=LABELS, default=None)
    parser.add_argument("--root-count", type=int, default=ROOT_COUNT)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-name", default="f59_results.json")
    parser.add_argument("--diagnostic-only", action="store_true")
    args = parser.parse_args()
    if not 2 <= args.root_count <= ROOT_COUNT:
        raise ValueError("root-count must be in [2, 36]")
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    labels = (args.ruleset,) if args.ruleset else LABELS
    results = [_run_label(label, args.root_count, smoke=args.smoke, diagnostic_only=args.diagnostic_only) for label in labels]
    payload = {"work_order": "GENERICCHESS-F59-THEORY-ROADMAP-AND-DECISION-DIAGNOSIS",
               "parent_checkpoint": "dddd397891203da446da50fc23399d4cf9badae4",
               "root_count": args.root_count, "smoke": args.smoke, "diagnostic_only": args.diagnostic_only, "results": results,
               "wall_seconds": time.perf_counter() - started}
    (OUT / args.output_name).write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"work_order": payload["work_order"], "root_count": args.root_count,
                      "wall_seconds": payload["wall_seconds"],
                      "summaries": [{"label": r["label"], "distributions": {
                          name: {"classification": value.get("classification"), "stable_count": value.get("stable_count"),
                                 "stable_rate": value.get("stable_rate")} for name, value in r["distributions"].items()}
                          } for r in results]}, sort_keys=True))


if __name__ == "__main__":
    main()
