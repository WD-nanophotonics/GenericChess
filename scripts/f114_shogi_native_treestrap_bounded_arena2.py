"""F114 Native AlphaBeta trace fitting and bounded Shogi Arena2 gate."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import random
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.nonlinear import (
    CompactNonlinearResidual,
    compact_residual_native_value,
    semantic_state_features,
)
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import dynamic_features, evaluate
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession


WORK_ORDER = "GENERICCHESS_F114_SHOGI_NATIVE_TREESTRAP_BOUNDED_ARENA2"
PARENT_CHECKPOINT_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
PARENT_COMPACT_SHA = "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
SEED = 1140101
ARENA_SEED = 1140801
NODES = 512
DEPTH = 12
TRACE_CAP = 4096
MATE_BAND = 90_000_000


def _load_checkpoint(path: Path) -> LearnableMaterialCheckpoint:
    payload = json.loads(path.read_text(encoding="utf-8"))
    checkpoint = LearnableMaterialCheckpoint.from_dict(payload.get("checkpoint", payload))
    if checkpoint.checkpoint_id != PARENT_CHECKPOINT_ID:
        raise RuntimeError("F114_FROZEN_PARENT_CHECKPOINT_MISMATCH")
    if not checkpoint.compact_nonlinear:
        raise RuntimeError("F114_PARENT_COMPACT_MODEL_MISSING")
    compact_sha = hashlib.sha256(
        json.dumps(checkpoint.compact_nonlinear, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if compact_sha != PARENT_COMPACT_SHA:
        raise RuntimeError("F114_PARENT_COMPACT_MODEL_MISMATCH")
    return checkpoint


def _clone(compiled, session: GameSession) -> GameSession:
    clone = GameSession(compiled)
    for action in session.history:
        clone.submit(action.action if hasattr(action, "action") else action)
    return clone


def _engine(compiled, native_rules, checkpoint):
    return SemanticSearchEngine(compiled, native_rules, checkpoint=checkpoint, tt_megabytes=8)


def _search(compiled, native_rules, checkpoint, session, *, trace=False):
    return _engine(compiled, native_rules, checkpoint).search(
        session,
        SearchLimits(max_depth=DEPTH, max_nodes=NODES, quiescence_max_depth=0),
        root_window_pruning=True,
        trace_enabled=trace,
    )


def _action_key(action):
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _self_play(compiled, native_rules, checkpoint):
    rng = random.Random(SEED)
    session = GameSession(compiled)
    roots = []
    moves = []
    flat_rows = []
    while session.result.status.value == "ongoing" and len(moves) < 64:
        root = _clone(compiled, session)
        root_id = position_identity_key(session.state.position, compiled)
        legal = sorted(session.legal_actions(), key=_action_key)
        result = _search(compiled, native_rules, checkpoint, session, trace=True)
        explore = rng.random() < 0.10
        chosen = rng.choice(legal) if explore else result.action
        if chosen is None or chosen not in legal:
            chosen = legal[0] if legal else None
        valid_search = (
            result.action is not None
            and result.termination_reason not in {"terminal_position", "invalid", "cancelled"}
        )
        rows = [dict(row) for row in result.training_trace]
        for row in rows:
            row["source_root_identity"] = root_id
            row["source_move_index"] = len(moves)
            row["source_search_valid"] = valid_search
        flat_rows.extend(rows)
        roots.append((root_id, root, result))
        moves.append({
            "ply": len(moves),
            "root_identity": root_id,
            "side_to_move": int(session.state.position.side_to_move),
            "exploration": explore,
            "chosen_action": None if chosen is None else action_to_dict(chosen),
            "searched_action": None if result.action is None else action_to_dict(result.action),
            "score": int(result.score),
            "nodes": int(result.nodes),
            "completed_depth": int(result.completed_depth),
            "termination_reason": result.termination_reason,
            "trace_raw_count": int(result.training_trace_raw_count),
            "trace_dedup_count": int(result.training_trace_count),
            "trace_rows": rows,
        })
        if chosen is None:
            break
        session.submit(chosen)
    return session, roots, moves, flat_rows


def _features(rows, model: CompactNonlinearResidual):
    values = []
    for row in rows:
        board = np.asarray(row["board_features"], dtype=np.float64)
        hand = np.asarray(row["hand_counts"], dtype=np.float64).reshape(2, -1)
        if model.hand_type_indices:
            hand = hand[:, list(model.hand_type_indices)]
        side = np.asarray((1.0, 0.0) if int(row["side_to_move"]) == 0 else (0.0, 1.0))
        dynamic = np.asarray(row["dynamic_features"], dtype=np.float64)
        aux = np.asarray(row.get("aux_features", ()), dtype=np.float64)
        value = np.concatenate((board, hand.reshape(-1), side, dynamic, aux))
        if len(value) != len(model.input_mean):
            raise RuntimeError(f"F114_FEATURE_SCHEMA_MISMATCH:{len(value)}:{len(model.input_mean)}")
        values.append(value)
    return np.asarray(values, dtype=np.float64)


def _eligible(rows, checkpoint, model):
    eligible = []
    excluded = {"terminal": 0, "mate_band": 0, "invalid_or_incomplete": 0}
    for row in rows:
        if not row.get("source_search_valid", False):
            excluded["invalid_or_incomplete"] += 1
            continue
        if row.get("terminal"):
            excluded["terminal"] += 1
            continue
        if abs(int(row["score_native"])) >= MATE_BAND:
            excluded["mate_band"] += 1
            continue
        eligible.append(row)
    return eligible, excluded


def _target(row, checkpoint, model):
    native_value = int(row["score_native"]) / float(checkpoint.semantic_native_scale)
    return (
        native_value if model.perspective == "owner0" and int(row["side_to_move"]) == 0
        else -native_value if model.perspective == "owner0"
        else -native_value
    )


def _forward(params, model, x):
    mean = np.asarray(model.input_mean); scale = np.asarray(model.input_scale)
    xn = (x - mean) / scale
    hidden = np.tanh(xn @ params[0].T + params[1])
    return hidden @ params[2] + params[3], hidden, xn


def _objective(params, model, x, y, bounds, parent_params):
    pred, _, _ = _forward(params, model, x)
    delta = pred - y
    loss = np.where(bounds == 0, 0.5 * delta * delta,
                    np.where(bounds == 1, 0.5 * np.maximum(0.0, y - pred) ** 2,
                             0.5 * np.maximum(0.0, pred - y) ** 2))
    prox = sum(float(np.sum((a - b) ** 2)) for a, b in zip(params, parent_params))
    return float(np.mean(loss) + 0.001 * prox)


def _fit(parent_model, x, y, bounds):
    params = [
        np.asarray(parent_model.hidden_weights, dtype=np.float64).copy(),
        np.asarray(parent_model.hidden_bias, dtype=np.float64).copy(),
        np.asarray(parent_model.output_weights, dtype=np.float64).copy(),
        np.asarray(parent_model.output_bias, dtype=np.float64),
    ]
    parent_params = [a.copy() for a in params]
    moments = [(np.zeros_like(a), np.zeros_like(a)) for a in params]
    for step in range(1, 101):
        pred, hidden, xn = _forward(params, parent_model, x)
        delta = pred - y
        grad_pred = np.where(bounds == 0, delta,
                             np.where(bounds == 1, np.where(pred < y, delta, 0.0),
                                      np.where(pred > y, delta, 0.0))) / len(x)
        grad_out = hidden.T @ grad_pred + 0.002 * 0.001 * (params[2] - parent_params[2])
        grad_ob = np.asarray(np.sum(grad_pred) + 0.002 * 0.001 * (params[3] - parent_params[3]))
        grad_hidden_pre = (grad_pred[:, None] * params[2][None, :]) * (1.0 - hidden * hidden)
        grad_hw = grad_hidden_pre.T @ xn + 0.002 * 0.001 * (params[0] - parent_params[0])
        grad_hb = np.sum(grad_hidden_pre, axis=0) + 0.002 * 0.001 * (params[1] - parent_params[1])
        for index, gradient in enumerate((grad_hw, grad_hb, grad_out, grad_ob)):
            first, second = moments[index]
            first[...] = 0.9 * first + 0.1 * gradient
            second[...] = 0.999 * second + 0.001 * gradient * gradient
            params[index] -= 0.001 * (first / (1.0 - 0.9 ** step)) / (
                np.sqrt(second / (1.0 - 0.999 ** step)) + 1e-8
            )
    return replace(
        parent_model,
        hidden_weights=tuple(tuple(row) for row in params[0].tolist()),
        hidden_bias=tuple(params[1].tolist()),
        output_weights=tuple(params[2].tolist()),
        output_bias=float(params[3]),
    ), parent_params


def _candidate(parent_model, trained, alpha):
    p = [
        np.asarray(parent_model.hidden_weights) + alpha * (np.asarray(trained.hidden_weights) - np.asarray(parent_model.hidden_weights)),
        np.asarray(parent_model.hidden_bias) + alpha * (np.asarray(trained.hidden_bias) - np.asarray(parent_model.hidden_bias)),
        np.asarray(parent_model.output_weights) + alpha * (np.asarray(trained.output_weights) - np.asarray(parent_model.output_weights)),
        np.asarray(parent_model.output_bias) + alpha * (np.asarray(trained.output_bias) - np.asarray(parent_model.output_bias)),
    ]
    return replace(trained,
        hidden_weights=tuple(tuple(row) for row in p[0].tolist()),
        hidden_bias=tuple(p[1].tolist()), output_weights=tuple(p[2].tolist()),
        output_bias=float(p[3]))


def _arena_payload(arena):
    games = []
    for pair in arena.pairs:
        for game in (pair.game_child_owner0, pair.game_child_owner1):
            games.append({"pair": game.pair, "opening_id": game.opening_id,
                          "child_owner": game.child_owner, "result": game.result,
                          "winner": game.winner, "plies": game.plies})
    return {"pair_scores": list(arena.pair_scores), "mean_pair_score": arena.mean_pair_score,
            "child_better_pairs": arena.child_better_pairs, "tied_pairs": arena.tied_pairs,
            "child_worse_pairs": arena.child_worse_pairs, "game_wins": arena.game_wins,
            "game_draws": arena.game_draws, "game_losses": arena.game_losses,
            "games": games, "valid": arena.pair_count == 2 and len(games) == 4 and
            all(g["result"] != "no_contest" and g["plies"] <= 256 for g in games)}


def _leaf_positions(compiled, roots, final_session, count=100):
    """Build a deterministic parity corpus without another teacher/search run."""
    sessions = [_clone(compiled, session) for _, session, _ in roots]
    cursor = _clone(compiled, final_session)
    while len(sessions) < count and cursor.result.status.value == "ongoing":
        legal = sorted(cursor.legal_actions(), key=_action_key)
        if not legal:
            break
        cursor.submit(legal[0])
        sessions.append(_clone(compiled, cursor))
    return sessions[:count]


def _known_identities():
    pattern = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
    out = set()
    for path in ROOT.joinpath(".generic_chess_flow").rglob("*"):
        if path.is_file() and any(tag in path.name.lower() for tag in ("f62", "f75", "f77", "f78", "f79", "f80", "f81", "f107", "f112", "f113")):
            try:
                out.update(pattern.findall(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--candidate-checkpoint", type=Path, required=True)
    args = ap.parse_args()
    checkpoint = _load_checkpoint(args.checkpoint)
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    native_rules = compile_native_semantic_rules(compiled)
    parent_model = CompactNonlinearResidual.from_dict(checkpoint.compact_nonlinear)

    final_session, roots, moves, trace_rows = _self_play(compiled, native_rules, checkpoint)
    eligible, excluded = _eligible(trace_rows, checkpoint, parent_model)
    if len(eligible) < 1000 or sum(r["bound_class"] == "EXACT" for r in eligible) < 100 or len({r["remaining_depth"] for r in eligible}) < 2:
        report = {"work_order_id": WORK_ORDER, "baseline_checkpoint_id": checkpoint.checkpoint_id,
                  "classification": "TREESTRAP_NATIVE_TRACE_INSUFFICIENT",
                  "trajectory": {"moves": moves, "raw_trace_rows": sum(m["trace_raw_count"] for m in moves),
                                 "dedup_trace_rows": len(trace_rows)}, "excluded": excluded}
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"classification": report["classification"]}))
        return

    x = _features(eligible, parent_model)
    y = np.asarray([_target(row, checkpoint, parent_model) / parent_model.target_scale for row in eligible])
    bounds = np.asarray([{"EXACT": 0, "LOWER": 1, "UPPER": 2}[row["bound_class"]] for row in eligible])
    parent_params = [np.asarray(parent_model.hidden_weights), np.asarray(parent_model.hidden_bias), np.asarray(parent_model.output_weights), np.asarray(parent_model.output_bias)]
    trained, _ = _fit(parent_model, x, y, bounds)
    parent_obj = _objective(parent_params, parent_model, x, y, bounds, parent_params)
    alphas = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125)
    safe_alpha = None; candidate_model = None; alpha_rows = []
    parent_pred = parent_model.predict(x) / parent_model.target_scale
    for alpha in alphas:
        trial = _candidate(parent_model, trained, alpha)
        trial_pred = trial.predict(x) / trial.target_scale
        residual = float(np.max(np.abs(trial_pred - parent_pred)))
        objective = _objective([np.asarray(trial.hidden_weights), np.asarray(trial.hidden_bias), np.asarray(trial.output_weights), np.asarray(trial.output_bias)], parent_model, x, y, bounds, parent_params)
        row = {"alpha": alpha, "objective": objective, "max_parent_residual": residual,
               "finite": bool(np.all(np.isfinite(trial_pred))), "protected_action_unchanged": True}
        protected = [r for r in eligible if r["bound_class"] == "EXACT" and r["source_root_identity"] in {root_id for root_id, _, _ in roots}]
        protected.sort(key=lambda r: (-min(int(r["score_native"]) - int(r["alpha_original"]), int(r["beta_original"]) - int(r["score_native"])), r["position_identity"]))
        protected = protected[:24]
        if len(protected) < 24:
            row["protected_action_unchanged"] = False
        else:
            trial_checkpoint = checkpoint.child_checkpoint(board_weights=checkpoint.board_weights, hand_weights=checkpoint.hand_weights, games_seen_delta=0, positions_seen_delta=0, training_updates_delta=1, training_config_hash="f114-native-treestrap", training_seed=SEED, compact_nonlinear=trial.to_dict())
            root_map = {root_id: session for root_id, session, _ in roots}
            for state_row in protected:
                before = _search(compiled, native_rules, checkpoint, root_map[state_row["source_root_identity"]])
                after = _search(compiled, native_rules, trial_checkpoint, root_map[state_row["source_root_identity"]])
                if before.action != after.action:
                    row["protected_action_unchanged"] = False; break
        row["passes"] = row["finite"] and residual <= 2.0 * max(float(np.max(np.abs(parent_pred - y))), 1e-12) and objective < parent_obj and row["protected_action_unchanged"]
        alpha_rows.append(row)
        if row["passes"]:
            safe_alpha = alpha; candidate_model = trial; break
    if candidate_model is None:
        classification = "TREESTRAP_NO_SAFE_PARENT_ANCHORED_UPDATE"
        report = {"work_order_id": WORK_ORDER, "baseline_checkpoint_id": checkpoint.checkpoint_id,
                  "classification": classification, "trajectory": {"moves": moves, "raw_trace_rows": sum(m["trace_raw_count"] for m in moves), "dedup_trace_rows": len(trace_rows)},
                  "eligible_rows": len(eligible), "excluded": excluded, "fit": {"parent_objective": parent_obj, "alpha_trials": alpha_rows}}
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"classification": classification}))
        return

    candidate = checkpoint.child_checkpoint(board_weights=checkpoint.board_weights, hand_weights=checkpoint.hand_weights, games_seen_delta=0, positions_seen_delta=0, training_updates_delta=1, training_config_hash="f114-native-treestrap", training_seed=SEED, compact_nonlinear=candidate_model.to_dict())
    args.candidate_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    args.candidate_checkpoint.write_text(json.dumps(candidate.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    reloaded = LearnableMaterialCheckpoint.from_dict(json.loads(args.candidate_checkpoint.read_text(encoding="utf-8")))

    roots24 = roots[:24]
    parity_rows = []
    for _, session, _ in roots24:
        off = _search(compiled, native_rules, checkpoint, session)
        on = _search(compiled, native_rules, checkpoint, session, trace=True)
        parity_rows.append({"equal": (off.action, off.score, off.principal_variation, off.nodes, off.completed_depth) == (on.action, on.score, on.principal_variation, on.nodes, on.completed_depth)})
    bound_rows = [{"bound": r["bound_class"], "relation_ok": (r["bound_class"] == "EXACT" and int(r["score_native"]) > int(r["alpha_original"]) and int(r["score_native"]) < int(r["beta_original"])) or (r["bound_class"] == "LOWER" and int(r["score_native"]) >= int(r["beta_original"])) or (r["bound_class"] == "UPPER" and int(r["score_native"]) <= int(r["alpha_original"]))} for r in eligible]

    leaf_rows = []
    for session in _leaf_positions(compiled, roots, final_session, count=100):
        packed = pack_semantic_search_position(compiled, native_rules, session)
        py_features = semantic_state_features(session.state.position, compiled, dynamic_features(native_rules, packed))
        py_value = float(parent_model.predict(py_features.reshape(1, -1))[0])
        full = evaluate(native_rules, packed, board_values=checkpoint.semantic_quantized_board(native_rules.type_ids), hand_values=checkpoint.semantic_quantized_hand(native_rules.type_ids), dynamic_values=checkpoint.semantic_quantized_dynamic(), compact_values=checkpoint.compact_nonlinear, evaluator_scale=checkpoint.semantic_native_scale)
        base = evaluate(native_rules, packed, board_values=checkpoint.semantic_quantized_board(native_rules.type_ids), hand_values=checkpoint.semantic_quantized_hand(native_rules.type_ids), dynamic_values=checkpoint.semantic_quantized_dynamic(), evaluator_scale=checkpoint.semantic_native_scale)
        native_residual = compact_residual_native_value((full - base) / checkpoint.semantic_native_scale, perspective=parent_model.perspective, side_to_move=session.state.position.side_to_move)
        leaf_rows.append(abs(native_residual - py_value))
    leaf_tolerance = 1.0 / float(checkpoint.semantic_native_scale)
    leaf_parity = len(leaf_rows) == 100 and max(leaf_rows, default=float("inf")) <= leaf_tolerance + 1e-9

    openings = generate_arena_openings(compiled, count=2, seed=ARENA_SEED, min_plies=2, max_plies=6)
    opening_ids = [o.final_position_key for o in openings.openings]
    if len(set(opening_ids)) != 2 or set(opening_ids) & _known_identities() or set(opening_ids) & {r["position_identity"] for r in trace_rows}:
        raise RuntimeError("F114_OPENING_DISJOINTNESS_FAILED")
    arena_config = ArenaConfig(pairs=2, nodes_per_move=NODES, max_depth=DEPTH, tt_megabytes=8, opening_seed=ARENA_SEED, opening_count=2, min_plies=2, max_plies=6, workers=1, root_window_pruning=True)
    arena = run_arena(compiled, native_rules, checkpoint, reloaded, arena_config, openings=openings, capture_search_metrics=True, execution_caps=ArenaExecutionCaps(per_game_plies=256, max_concurrent_games=1))
    arena_data = _arena_payload(arena)
    classification = "SHOGI_NATIVE_TREESTRAP_ARENA2_SURVIVES" if arena_data["valid"] and arena.mean_pair_score > 0.5 and arena.child_better_pairs > arena.child_worse_pairs else "SHOGI_NATIVE_TREESTRAP_ARENA2_REJECTED"
    report = {"work_order_id": WORK_ORDER, "baseline_checkpoint_id": checkpoint.checkpoint_id, "candidate_checkpoint_id": reloaded.checkpoint_id, "candidate_compact_sha256": hashlib.sha256(json.dumps(reloaded.compact_nonlinear, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "ruleset_fingerprint": compiled.ruleset_fingerprint, "classification": classification, "trajectory": {"seed": SEED, "moves": moves, "raw_trace_rows": sum(m["trace_raw_count"] for m in moves), "dedup_trace_rows": len(trace_rows), "eligible_rows": len(eligible), "bound_counts": {name: sum(r["bound_class"] == name for r in eligible) for name in ("EXACT", "LOWER", "UPPER")}, "remaining_depths": sorted({int(r["remaining_depth"]) for r in eligible})}, "excluded": excluded, "fit": {"steps": 100, "learning_rate": 0.001, "proximal": 0.001, "parent_objective": parent_obj, "alpha_trials": alpha_rows, "safe_alpha": safe_alpha}, "gates": {"trace_disabled_enabled_parity": len(parity_rows) == 24 and all(r["equal"] for r in parity_rows), "bound_classification": all(r["relation_ok"] for r in bound_rows), "candidate_reload_identity": reloaded.checkpoint_id == candidate.checkpoint_id, "python_native_leaf_parity_100": leaf_parity, "python_native_leaf_count": len(leaf_rows), "python_native_leaf_max_abs_error": max(leaf_rows, default=None), "python_native_leaf_tolerance": leaf_tolerance, "policy_bound": False}, "arena_config": asdict(arena_config), "fresh_openings": openings.to_dict(), "arena": arena_data}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": classification, "candidate_checkpoint_id": candidate.checkpoint_id, "mean_pair_score": arena.mean_pair_score}, sort_keys=True))


if __name__ == "__main__":
    main()
