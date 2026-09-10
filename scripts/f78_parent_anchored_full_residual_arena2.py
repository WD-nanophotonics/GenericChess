"""F78 parent-anchored full compact-residual fit and Arena2 triage."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import ArenaOpeningCorpus, generate_arena_openings  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f74_parent_retained_output_delta_probe as f74  # noqa: E402
from scripts import f76_parent_retained_pointwise_q_output_delta as f76  # noqa: E402
from scripts import f77_trusted_pointwise_q_arena2_triage as f77  # noqa: E402


WORK_ORDER = "GENERICCHESS-F78-PARENT-ANCHORED-FULL-RESIDUAL-PAIRWISE-ARENA2"
PARENT_SHA = "f4424c7cb31f4487c8342dad6530fa72cd7ab769"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
F62_STAGE_SHA = "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
F62_RECORDS_SHA = "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"
F75_OPENINGS = ROOT / "artifacts" / "f75_parent_retained_arena" / "openings.json"
F77_OPENINGS = ROOT / "artifacts" / "f77_trusted_pointwise_q_arena" / "openings.json"
F62_OUT = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability"
ARTIFACTS = ROOT / "artifacts" / "f78_parent_anchored_full_residual"
CANDIDATE_PATH = ARTIFACTS / "candidate.json"
OPENINGS_PATH = ARTIFACTS / "openings.json"
OUT = ROOT / ".generic_chess_flow" / "f78-parent-anchored-full-residual-arena2"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f78_results.json"
TRUSTED_ROOT_COUNT = 34
OPENING_SEED = 780501
OPENING_COUNT = 8
PAIRS = 2
NODES = 512
MAX_DEPTH = 12
TT_MEGABYTES = 8
ADAM_STEPS = 100
LEARNING_RATE = 0.001
PROXIMAL_COEFFICIENT = 0.001
BACKTRACKING_ALPHAS = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125)


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_gen1(compiled):
    data = json.loads((ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json").read_text(encoding="utf-8"))
    row = next(item for item in data["corrected_candidates"] if item["candidate_id"] == "F60_D0_PAIRWISE_SEED_59012")
    gen1 = f61r2._candidate_checkpoint(f59._parent(LABEL), row)
    if gen1.checkpoint_id != GEN1_ID:
        raise RuntimeError("F78 Gen1 identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1


def _load_trusted_roots():
    fit_roots = f74._load_fit_roots()
    trusted = f74._trusted_fit_roots(fit_roots)
    indices = [root["root_index"] for root in trusted]
    return fit_roots, trusted, indices


def _normalized_hidden(model, features):
    values = np.asarray(features, dtype=np.float64)
    normalized = (values - np.asarray(model.input_mean)) / np.asarray(model.input_scale)
    pre = normalized @ np.asarray(model.hidden_weights, dtype=np.float64).T + np.asarray(model.hidden_bias, dtype=np.float64)
    return normalized, np.tanh(pre)


def _pairwise_data(roots, parent_model):
    data = []
    for root in roots:
        rows = root["metadata"]["action_rows"]
        features = np.asarray([row["features"] for row in rows], dtype=np.float64)
        base = np.asarray([row["base_q"] for row in rows], dtype=np.float64)
        keys = [row["action_key"] for row in rows]
        consensus = root["metadata"]["root_80k"]["action_key"]
        if consensus not in keys:
            raise RuntimeError(f"F78 deep consensus action missing in root-{root['root_index']}")
        target = keys.index(consensus)
        data.append({"root_index": root["root_index"], "features": features, "base": base, "target": target, "keys": keys})
    return data


def _model_prediction(model, features):
    _normalized, hidden = _normalized_hidden(model, features)
    return model.target_scale * (hidden @ np.asarray(model.output_weights) + model.output_bias), hidden


def _pairwise_loss(model, data):
    losses = []
    for root in data:
        prediction, _hidden = _model_prediction(model, root["features"])
        target = root["target"]
        margins = root["base"][target] + prediction[target] - root["base"] - prediction
        margins = np.delete(margins, target)
        losses.append(float(np.mean(np.logaddexp(0.0, -margins))))
    return float(np.mean(losses))


def _adam_fit(parent_model, data):
    hidden_weights = np.asarray(parent_model.hidden_weights, dtype=np.float64).copy()
    hidden_bias = np.asarray(parent_model.hidden_bias, dtype=np.float64).copy()
    output_weights = np.asarray(parent_model.output_weights, dtype=np.float64).copy()
    parent_blocks = (hidden_weights.copy(), hidden_bias.copy(), output_weights.copy())
    moments = [(np.zeros_like(block), np.zeros_like(block)) for block in (hidden_weights, hidden_bias, output_weights)]
    initial_loss = _pairwise_loss(parent_model, data)
    for step in range(1, ADAM_STEPS + 1):
        gradients = [np.zeros_like(hidden_weights), np.zeros_like(hidden_bias), np.zeros_like(output_weights)]
        current = replace(parent_model, hidden_weights=tuple(tuple(row) for row in hidden_weights.tolist()), hidden_bias=tuple(hidden_bias.tolist()), output_weights=tuple(output_weights.tolist()))
        for root in data:
            normalized, hidden = _normalized_hidden(current, root["features"])
            prediction = current.target_scale * (hidden @ output_weights + current.output_bias)
            target = root["target"]
            alternatives = [index for index in range(len(prediction)) if index != target]
            action_weight = 1.0 / len(alternatives)
            root_weight = 1.0 / len(data)
            for alternative in alternatives:
                margin = root["base"][target] + prediction[target] - root["base"][alternative] - prediction[alternative]
                probability = 1.0 / (1.0 + math.exp(float(np.clip(margin, -60.0, 60.0))))
                coefficient = -root_weight * action_weight * probability * current.target_scale
                target_hidden = hidden[target]
                alternative_hidden = hidden[alternative]
                gradients[2] += coefficient * (target_hidden - alternative_hidden)
                gradients[1] += coefficient * output_weights * ((1.0 - target_hidden * target_hidden) - (1.0 - alternative_hidden * alternative_hidden))
                gradients[0] += coefficient * (
                    np.outer(output_weights * (1.0 - target_hidden * target_hidden), normalized[target])
                    - np.outer(output_weights * (1.0 - alternative_hidden * alternative_hidden), normalized[alternative])
                )
        blocks = (hidden_weights, hidden_bias, output_weights)
        for index, (block, parent_block) in enumerate(zip(blocks, parent_blocks)):
            gradients[index] += 2.0 * PROXIMAL_COEFFICIENT * (block - parent_block)
            first, second = moments[index]
            first[:] = 0.9 * first + 0.1 * gradients[index]
            second[:] = 0.999 * second + 0.001 * (gradients[index] * gradients[index])
            first_hat = first / (1.0 - 0.9 ** step)
            second_hat = second / (1.0 - 0.999 ** step)
            block -= LEARNING_RATE * first_hat / (np.sqrt(second_hat) + 1e-8)
    raw_model = replace(
        parent_model,
        hidden_weights=tuple(tuple(row) for row in hidden_weights.tolist()),
        hidden_bias=tuple(hidden_bias.tolist()),
        output_weights=tuple(output_weights.tolist()),
    )
    raw_loss = _pairwise_loss(raw_model, data)
    deltas = (
        hidden_weights - parent_blocks[0], hidden_bias - parent_blocks[1], output_weights - parent_blocks[2]
    )
    proximal = float(PROXIMAL_COEFFICIENT * sum(float(np.sum(delta * delta)) for delta in deltas))
    return raw_model, {
        "steps": ADAM_STEPS,
        "learning_rate": LEARNING_RATE,
        "proximal_coefficient": PROXIMAL_COEFFICIENT,
        "objective_before": initial_loss,
        "raw_pairwise_objective": raw_loss,
        "raw_proximal_term": proximal,
        "raw_total_objective": raw_loss + proximal,
        "hidden_weights_delta_norm": float(np.linalg.norm(deltas[0])),
        "hidden_bias_delta_norm": float(np.linalg.norm(deltas[1])),
        "output_weights_delta_norm": float(np.linalg.norm(deltas[2])),
        "raw_parameter_delta_sha256": stable_sha256({"hidden_weights": deltas[0].tolist(), "hidden_bias": deltas[1].tolist(), "output_weights": deltas[2].tolist()}),
    }


def _static_rows(root, model):
    features = np.asarray([row["features"] for row in root["metadata"]["action_rows"]], dtype=np.float64)
    base = np.asarray([row["base_q"] for row in root["metadata"]["action_rows"]], dtype=np.float64)
    residual, _hidden = _model_prediction(model, features)
    return {"root_index": root["root_index"], "keys": [row["action_key"] for row in root["metadata"]["action_rows"]], "total": base + residual, "residual": residual}


def _top_index(scores, keys):
    return min(range(len(scores)), key=lambda index: (-float(scores[index]), keys[index]))


def _candidate_metrics(fit_roots, trusted_data, parent_model, candidate_model):
    parent_rows = [_static_rows(root, parent_model) for root in fit_roots]
    candidate_rows = [_static_rows(root, candidate_model) for root in fit_roots]
    margins = []
    for row in parent_rows:
        order = sorted(range(len(row["total"])), key=lambda index: (-float(row["total"][index]), row["keys"][index]))
        margins.append(float(row["total"][order[0]] - row["total"][order[1]]))
    threshold = float(np.percentile(np.asarray(margins), 75.0))
    high_indices = [row["root_index"] for row, margin in zip(parent_rows, margins) if margin >= threshold]
    retention = all(
        parent["keys"][_top_index(parent["total"], parent["keys"])] == candidate["keys"][_top_index(candidate["total"], candidate["keys"])]
        for parent, candidate in zip(parent_rows, candidate_rows) if parent["root_index"] in high_indices
    )
    parent_max = max(float(np.max(np.abs(row["residual"]))) for row in parent_rows)
    candidate_max = max(float(np.max(np.abs(row["residual"]))) for row in candidate_rows)
    trusted_parent = _pairwise_loss(parent_model, trusted_data)
    trusted_candidate = _pairwise_loss(candidate_model, trusted_data)
    finite = all(np.isfinite(value) for row in candidate_rows for value in (*row["total"], *row["residual"]))
    return {
        "high_confidence_threshold": threshold,
        "high_confidence_root_count": len(high_indices),
        "high_confidence_root_indices": high_indices,
        "high_confidence_top_retained": retention,
        "parent_max_abs_residual": parent_max,
        "candidate_max_abs_residual": candidate_max,
        "allowed_max_abs_residual": 2.0 * parent_max,
        "trusted_pairwise_objective_parent": trusted_parent,
        "trusted_pairwise_objective_candidate": trusted_candidate,
        "trusted_pairwise_objective_improved": trusted_candidate < trusted_parent,
        "candidate_all_finite": finite,
    }


def _interpolate(parent_model, raw_model, alpha):
    return replace(
        parent_model,
        hidden_weights=tuple(tuple((np.asarray(parent_model.hidden_weights) + alpha * (np.asarray(raw_model.hidden_weights) - np.asarray(parent_model.hidden_weights)))[row].tolist()) for row in range(parent_model.width)),
        hidden_bias=tuple((np.asarray(parent_model.hidden_bias) + alpha * (np.asarray(raw_model.hidden_bias) - np.asarray(parent_model.hidden_bias))).tolist()),
        output_weights=tuple((np.asarray(parent_model.output_weights) + alpha * (np.asarray(raw_model.output_weights) - np.asarray(parent_model.output_weights))).tolist()),
    )


def _select_alpha(fit_roots, trusted_data, parent_model, raw_model):
    attempts = []
    chosen = None
    chosen_metrics = None
    for alpha in BACKTRACKING_ALPHAS:
        model = _interpolate(parent_model, raw_model, alpha)
        metrics = _candidate_metrics(fit_roots, trusted_data, parent_model, model)
        safe = (
            metrics["high_confidence_top_retained"]
            and metrics["candidate_max_abs_residual"] <= metrics["allowed_max_abs_residual"]
            and metrics["trusted_pairwise_objective_improved"]
            and metrics["candidate_all_finite"]
        )
        attempts.append({"alpha": alpha, "safe": safe, **metrics})
        if chosen is None and safe:
            chosen = alpha
            chosen_metrics = metrics
    return chosen, chosen_metrics, attempts


def _make_candidate(gen1, model, identity):
    training_hash = stable_sha256(identity)
    candidate = gen1.child_checkpoint(
        board_weights=gen1.board_weights,
        hand_weights=gen1.hand_weights,
        dynamic_weights=gen1.dynamic_weights,
        compact_nonlinear=model.to_dict(),
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=training_hash,
        training_seed=None,
    )
    return candidate, training_hash


def _representation_guard(compiled, gen1, candidate, parent_model, model):
    failures = []
    if candidate.ruleset_fingerprint != gen1.ruleset_fingerprint:
        failures.append("ruleset binding changed")
    for field in ("input_mean", "input_scale", "target_scale", "output_bias", "width", "hand_type_indices", "perspective"):
        if getattr(parent_model, field) != getattr(model, field):
            failures.append(f"frozen model field changed: {field}")
    if parent_model.hidden_weights == model.hidden_weights and parent_model.hidden_bias == model.hidden_bias and parent_model.output_weights == model.output_weights:
        failures.append("all allowed parameter blocks are unchanged")
    candidate.validate_ruleset(compiled)
    return failures


def _load_or_make_openings(compiled):
    if OPENINGS_PATH.is_file():
        payload = json.loads(OPENINGS_PATH.read_text(encoding="utf-8"))
        corpus = ArenaOpeningCorpus.from_dict(payload["corpus"])
        corpus.validate(compiled)
        if payload.get("corpus_id") != corpus.corpus_id:
            raise RuntimeError("F78 opening corpus SHA mismatch")
        return corpus, payload
    corpus = generate_arena_openings(compiled, count=OPENING_COUNT, seed=OPENING_SEED, min_plies=2, max_plies=6)
    corpus.validate(compiled)
    keys = [opening.final_position_key for opening in corpus.openings]
    f62_keys = {json.loads((F62_OUT / "progress" / "spectrum" / f"root-{index:03d}.json").read_text(encoding="utf-8"))["identity"]["record"]["position_key"] for index in range(96)}
    f75_keys = {opening["final_position_key"] for opening in json.loads(F75_OPENINGS.read_text(encoding="utf-8"))["corpus"]["openings"]}
    f77_keys = {opening["final_position_key"] for opening in json.loads(F77_OPENINGS.read_text(encoding="utf-8"))["corpus"]["openings"]}
    f62_overlap = sorted(set(keys) & f62_keys)
    f75_overlap = sorted(set(keys) & f75_keys)
    f77_overlap = sorted(set(keys) & f77_keys)
    if len(set(keys)) != OPENING_COUNT or f62_overlap or f75_overlap or f77_overlap:
        raise RuntimeError("F78 opening corpus uniqueness or overlap contract failed")
    payload = {
        "schema": "generic-chess-f78-parent-anchored-opening-corpus-v1",
        "corpus": corpus.to_dict(),
        "corpus_id": corpus.corpus_id,
        "f62_overlap_count": len(f62_overlap),
        "f75_overlap_count": len(f75_overlap),
        "f77_overlap_count": len(f77_overlap),
        "unique_final_position_count": len(set(keys)),
    }
    _atomic_json(OPENINGS_PATH, payload)
    return corpus, payload


def _run_arena(compiled, native, gen1, candidate, openings):
    config = ArenaConfig(pairs=PAIRS, nodes_per_move=NODES, parent_nodes_per_move=NODES, child_nodes_per_move=NODES, max_depth=MAX_DEPTH, tt_megabytes=TT_MEGABYTES, opening_seed=OPENING_SEED, opening_count=OPENING_COUNT, min_plies=2, max_plies=6, workers=1)
    caps = ArenaExecutionCaps(per_game_wall_seconds=3600, per_game_nodes=131072, per_game_plies=256, max_stage_games=4, max_concurrent_games=4, stage_wall_seconds=3600)
    first = run_arena_game_resumable(compiled, native, gen1, candidate, config, progress_dir=PROGRESS, openings=openings, capture_search_metrics=True, caps=caps, stage_id="f78-arena2")
    replay = run_arena_game_resumable(compiled, native, gen1, candidate, config, progress_dir=PROGRESS, openings=openings, capture_search_metrics=True, caps=caps, stage_id="f78-arena2")
    summary = f77._summary_payload(first.summary)
    replay_summary = f77._summary_payload(replay.summary)
    telemetry = f77._telemetry(first.summary) if first.summary is not None else {}
    failures = []
    if first.status != "COMPLETE" or first.completed_games != 4 or first.completed_pairs != 2:
        failures.append("stage did not complete four games and two pairs")
    if summary is None:
        failures.append("complete stage has no pair summary")
    if replay.status != first.status or replay.completed_games != first.completed_games or replay.completed_pairs != first.completed_pairs:
        failures.append("progress replay status or counts differ")
    if summary != replay_summary:
        failures.append("progress replay summary differs")
    if telemetry and not telemetry.get("all_root_window_pruning_true", False):
        failures.append("root pruning telemetry was not true for every search")
    if telemetry.get("missing_root_window_pruning_rows", 0):
        failures.append("root pruning telemetry field was missing")
    if first.reason is not None:
        failures.append(f"execution cap or stop reason: {first.reason}")
    return {"config": {"pairs": PAIRS, "total_games": 4, "nodes_per_move": NODES, "parent_nodes_per_move": NODES, "child_nodes_per_move": NODES, "max_depth": MAX_DEPTH, "tt_megabytes": TT_MEGABYTES, "workers": 1, "root_window_pruning": True, "execution_caps": asdict(caps)}, "run": {"status": first.status, "completed_games": first.completed_games, "completed_pairs": first.completed_pairs, "total_games": first.total_games, "reason": first.reason, "effective_game_lanes": first.effective_game_lanes}, "summary": summary, "telemetry": telemetry, "replay_validation": {"status": replay.status, "completed_games": replay.completed_games, "completed_pairs": replay.completed_pairs, "summary_equal": summary == replay_summary}, "contract_failures": failures}


def run() -> dict:
    if not native_available():
        raise RuntimeError("F78 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = _load_gen1(compiled)
    parent_model = CompactNonlinearResidual.from_dict(gen1.compact_nonlinear)
    fit_roots, trusted_roots, trusted_indices = _load_trusted_roots()
    if len(trusted_roots) != TRUSTED_ROOT_COUNT:
        raise RuntimeError(f"F78 trusted root count mismatch: {len(trusted_roots)}")
    trusted_data = _pairwise_data(trusted_roots, parent_model)
    raw_model, fit_summary = _adam_fit(parent_model, trusted_data)
    alpha, selected_metrics, attempts = _select_alpha(fit_roots, trusted_data, parent_model, raw_model)
    safety_failures = []
    if alpha is None:
        safety_failures.append("no registered nonzero backtracking alpha satisfied safety gates")
        alpha = 0.0
        selected_metrics = attempts[-1]
    candidate_model = _interpolate(parent_model, raw_model, alpha)
    raw_delta = {"hidden_weights": (np.asarray(raw_model.hidden_weights) - np.asarray(parent_model.hidden_weights)).tolist(), "hidden_bias": (np.asarray(raw_model.hidden_bias) - np.asarray(parent_model.hidden_bias)).tolist(), "output_weights": (np.asarray(raw_model.output_weights) - np.asarray(parent_model.output_weights)).tolist()}
    raw_delta_sha = stable_sha256(raw_delta)
    identity = {"work_order": WORK_ORDER, "parent_checkpoint_id": gen1.checkpoint_id, "f62_stage_sha256": F62_STAGE_SHA, "f62_records_sha256": F62_RECORDS_SHA, "trusted_root_indices": trusted_indices, "objective": "pairwise_ranking_deep_consensus", "optimizer": "Adam", "steps": ADAM_STEPS, "learning_rate": LEARNING_RATE, "proximal_coefficient": PROXIMAL_COEFFICIENT, "raw_parameter_delta_sha256": raw_delta_sha, "alpha": alpha, "final_compact_model_sha256": stable_sha256(candidate_model.to_dict())}
    candidate, training_hash = _make_candidate(gen1, candidate_model, identity)
    descriptor = {"schema": "generic-chess-f78-parent-anchored-full-residual-candidate-v1", "source_commit": PARENT_SHA, "parent_checkpoint_id": gen1.checkpoint_id, "child_checkpoint_id": candidate.checkpoint_id, "canonical_training_identity": identity, "training_config_hash": training_hash, "final_compact_nonlinear": candidate_model.to_dict(), "candidate_model_sha256": stable_sha256(candidate_model.to_dict())}
    if CANDIDATE_PATH.is_file():
        if json.loads(CANDIDATE_PATH.read_text(encoding="utf-8")) != descriptor:
            raise RuntimeError("F78 candidate descriptor identity mismatch")
    else:
        _atomic_json(CANDIDATE_PATH, descriptor)
    representation_failures = _representation_guard(compiled, gen1, candidate, parent_model, candidate_model)
    parity = f76._native_parity(compiled, native, gen1, candidate, candidate_model, trusted_roots)
    contract_failures = representation_failures + parity["failures"]
    if selected_metrics["candidate_max_abs_residual"] > selected_metrics["allowed_max_abs_residual"]:
        safety_failures.append("selected candidate residual cap exceeded")
    if not selected_metrics["high_confidence_top_retained"]:
        safety_failures.append("selected candidate changed a high-confidence top action")
    if not selected_metrics["trusted_pairwise_objective_improved"]:
        safety_failures.append("selected trusted pairwise objective did not improve")
    if not selected_metrics["candidate_all_finite"]:
        safety_failures.append("selected candidate compact residual is not finite")
    arena = None
    classification = "HARNESS_MISMATCH" if contract_failures else "PARENT_ANCHORED_FULL_RESIDUAL_UNSAFE" if safety_failures else None
    opening_payload = None
    if classification is None:
        openings, opening_payload = _load_or_make_openings(compiled)
        arena = _run_arena(compiled, native, gen1, candidate, openings)
        if arena["contract_failures"]:
            classification = "HARNESS_MISMATCH" if arena["run"]["status"] == "COMPLETE" else "PARENT_ANCHORED_FULL_RESIDUAL_ARENA2_UNRESOLVED"
        elif arena["run"]["status"] != "COMPLETE":
            classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA2_UNRESOLVED"
        elif arena["summary"]["mean_pair_score"] >= 0.5:
            classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA2_SURVIVES"
        else:
            classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA2_REJECTED"
    result = {"schema": "generic-chess-f78-parent-anchored-full-residual-arena2-v1", "work_order": WORK_ORDER, "baseline_sha": PARENT_SHA, "classification": classification, "parent_checkpoint_id": gen1.checkpoint_id, "child_checkpoint_id": candidate.checkpoint_id, "trusted_root_count": len(trusted_roots), "trusted_root_indices": trusted_indices, "fit": {"action_row_count": sum(len(root["features"]) for root in trusted_data), "summary": fit_summary, "raw_delta_sha256": raw_delta_sha, "raw_model_pairwise_objective": fit_summary["raw_pairwise_objective"], "raw_proximal_term": fit_summary["raw_proximal_term"], "raw_total_objective": fit_summary["raw_total_objective"], "block_delta_norms": {"hidden_weights": fit_summary["hidden_weights_delta_norm"], "hidden_bias": fit_summary["hidden_bias_delta_norm"], "output_weights": fit_summary["output_weights_delta_norm"]}}, "backtracking": {"alphas": list(BACKTRACKING_ALPHAS), "chosen_alpha": alpha, "attempts": attempts, "selected_metrics": selected_metrics}, "candidate": {"model_sha256": stable_sha256(candidate_model.to_dict()), "training_config_hash": training_hash, "descriptor_path": str(CANDIDATE_PATH.relative_to(ROOT))}, "native_python_parity": parity, "opening_corpus": None if opening_payload is None else {"path": str(OPENINGS_PATH.relative_to(ROOT)), "corpus_id": opening_payload["corpus_id"], "seed": OPENING_SEED, "opening_count": OPENING_COUNT, "f62_overlap_count": opening_payload["f62_overlap_count"], "f75_overlap_count": opening_payload["f75_overlap_count"], "f77_overlap_count": opening_payload["f77_overlap_count"], "unique_final_position_count": opening_payload["unique_final_position_count"]}, "arena": arena, "safety_failures": safety_failures, "contract_failures": contract_failures + ([] if arena is None else arena["contract_failures"]), "code_provenance": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in ("scripts/f78_parent_anchored_full_residual_arena2.py", "generic_chess/learning/arena.py", "generic_chess/learning/openings.py", "generic_chess/native/semantic_engine.py")}}
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    summary = result["arena"]["summary"] if result["arena"] else {}
    print(json.dumps({"classification": result["classification"], "parent_checkpoint_id": result["parent_checkpoint_id"], "child_checkpoint_id": result["child_checkpoint_id"], "trusted_root_count": result["trusted_root_count"], "chosen_alpha": result["backtracking"]["chosen_alpha"], "raw_total_objective": result["fit"]["raw_total_objective"], "arena_pair_scores": None if not summary else summary["pair_scores"], "arena_mean_pair_score": None if not summary else summary["mean_pair_score"], "contract_failures": result["contract_failures"], "safety_failures": result["safety_failures"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
