"""F86: distill parent-native search actions into its compact residual model."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.learning.arena import (
    ArenaConfig,
    ArenaExecutionCaps,
    ArenaExecutionError,
    ArenaOpeningCorpus,
    run_arena_game_resumable,
)
from generic_chess.learning.features import linear_value, material_features
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.nonlinear import CompactNonlinearResidual, semantic_state_features
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.serialization import stable_sha256
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.semantic import dynamic_features as native_dynamic_features
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from scripts import f59_action_spectrum_diagnosis as f59
from scripts.f84_native_selfplay_tdleaf import _load_parent
from scripts.f78_parent_anchored_full_residual_arena2 import _adam_fit, _model_prediction, _pairwise_loss
from tools.generic_chess_flow import repo_relative_path


WORK_ORDER = "F86_NATIVE_SEARCH_DISTILLATION_NONLINEAR_SINGLE_UPDATE"
OUT = ROOT / "artifacts/f86_native_search_distillation"
DESCRIPTOR = OUT / "successor_candidate_descriptor.json"
ARTIFACT = OUT / "successor_candidate_result.json"
SEED = 860401


def _rows(compiled, native, parent, trajectories):
    type_ids = tuple(sorted(parent.board_weights))
    rows = []
    for point in trajectories[0].points:
        prefix = tuple(trajectories[0].actions[: point.ply])
        root = GameSession(compiled)
        for action in prefix:
            root.submit(action)
        legal = list(root.legal_actions())
        target_key = f59._action_key(action_to_dict(point.action))
        action_rows = []
        for action in legal:
            child = GameSession(compiled)
            for prior in prefix:
                child.submit(prior)
            child.submit(action)
            packed = pack_semantic_search_position(compiled, native, child)
            dynamic = native_dynamic_features(native, packed)
            features = semantic_state_features(child.state.position, compiled, dynamic)
            material = material_features(child.state.position, type_ids, perspective=0)
            base_owner0 = linear_value(material, parent.board_weights, parent.hand_weights, dynamic, parent.dynamic_weights)
            base_q = float(base_owner0 if root.state.position.side_to_move == 0 else -base_owner0)
            action_rows.append({"action_key": f59._action_key(action_to_dict(action)), "features": features.tolist(), "base_q": base_q})
        keys = [row["action_key"] for row in action_rows]
        if target_key not in keys:
            raise RuntimeError("native search-selected target is not legal at reconstructed root")
        rows.append({"root_index": len(rows), "features": np.asarray([r["features"] for r in action_rows], dtype=np.float64), "base": np.asarray([r["base_q"] for r in action_rows], dtype=np.float64), "target": keys.index(target_key), "keys": keys, "target_action_key": target_key, "root_position_key": point.root_position_key})
    if not rows:
        raise RuntimeError("F86 requires at least one training root")
    return rows


def build() -> dict:
    allocation, compiled, native, parent = _load_parent()
    if DESCRIPTOR.is_file() and ARTIFACT.is_file():
        return json.loads(ARTIFACT.read_text(encoding="utf-8"))
    config = SelfPlayConfig(games=1, nodes_per_move=512, max_depth=12, seed=SEED, epsilon=0.0, tt_megabytes=8, max_plies=64)
    trajectories = collect_self_play(compiled, native, parent, config)
    trajectory = trajectories[0]
    if not trajectory.points or (trajectory.truncated and trajectory.bootstrap_value is None):
        raise RuntimeError("F86 trajectory gate failed")
    data = _rows(compiled, native, parent, trajectories)
    parent_model = CompactNonlinearResidual.from_dict(parent.compact_nonlinear)
    objective_before = _pairwise_loss(parent_model, data)
    raw_model, fit = _adam_fit(parent_model, data)
    objective_after = _pairwise_loss(raw_model, data)
    parent_residual = np.concatenate([_model_prediction(parent_model, row["features"])[0] for row in data])
    candidate_residual = np.concatenate([_model_prediction(raw_model, row["features"])[0] for row in data])
    if not (objective_after < objective_before and np.isfinite(objective_after) and np.all(np.isfinite(candidate_residual))):
        raise RuntimeError("F86 pairwise objective did not improve")
    if float(np.max(np.abs(candidate_residual))) > 2.0 * float(np.max(np.abs(parent_residual))) + 1e-9:
        raise RuntimeError("F86 residual 2x safety cap failed")
    if parent_model.hidden_weights == raw_model.hidden_weights and parent_model.hidden_bias == raw_model.hidden_bias and parent_model.output_weights == raw_model.output_weights:
        raise RuntimeError("F86 nonlinear parameters did not change")
    identity = {"work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id, "parent_model_sha256": stable_sha256(parent.compact_nonlinear), "selfplay_config": asdict(config), "trajectory_id": trajectory.trajectory_id, "trajectory_terminal": trajectory.terminal, "trajectory_truncated": trajectory.truncated, "trajectory_bootstrap_value": trajectory.bootstrap_value, "training_root_count": len(data), "training_action_row_count": sum(len(row["keys"]) for row in data), "optimizer": fit, "objective_before": objective_before, "objective_after": objective_after}
    training_hash = stable_sha256(identity)
    candidate = parent.child_checkpoint(board_weights=parent.board_weights, hand_weights=parent.hand_weights, dynamic_weights=parent.dynamic_weights, spatial_occupancy_weights=parent.spatial_occupancy_weights, localized_control_weights=parent.localized_control_weights, compact_nonlinear=raw_model.to_dict(), games_seen_delta=0, positions_seen_delta=0, training_updates_delta=1, training_config_hash=training_hash, training_seed=None)
    candidate.validate_ruleset(compiled)
    descriptor = {"schema": "generic-chess-f86-native-search-distillation-descriptor-v1", "work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id, "candidate_checkpoint_id": candidate.checkpoint_id, "candidate_checkpoint": candidate.to_dict(), "parent_model_sha256": stable_sha256(parent.compact_nonlinear), "candidate_model_sha256": stable_sha256(candidate.compact_nonlinear), "training_config_hash": training_hash, "selfplay_config": asdict(config), "trajectory_id": trajectory.trajectory_id, "trajectory_terminal": trajectory.terminal, "trajectory_truncated": trajectory.truncated, "trajectory_bootstrap_value": trajectory.bootstrap_value, "training_root_count": len(data), "training_action_row_count": sum(len(row["keys"]) for row in data), "target_action_keys": [row["target_action_key"] for row in data], "optimizer": fit, "objective_before": objective_before, "objective_after": objective_after, "parent_max_abs_residual": float(np.max(np.abs(parent_residual))), "candidate_max_abs_residual": float(np.max(np.abs(candidate_residual))), "allocation_sha256": allocation["allocation_sha256"]}
    descriptor["descriptor_sha256"] = stable_sha256(descriptor)
    result = {"schema": "generic-chess-f86-native-search-distillation-v1", "status": "SUCCESSOR_READY_FOR_APPROVED_ARENA", "work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id, "candidate_checkpoint_id": candidate.checkpoint_id, "candidate_descriptor_path": str(DESCRIPTOR.relative_to(ROOT)).replace("\\", "/"), "candidate_descriptor_sha256": descriptor["descriptor_sha256"], "training_config_hash": training_hash, "trajectory_id": trajectory.trajectory_id, "trajectory_terminal": trajectory.terminal, "trajectory_truncated": trajectory.truncated, "trajectory_bootstrap_value": trajectory.bootstrap_value, "training_root_count": len(data), "training_action_row_count": sum(len(row["keys"]) for row in data), "objective_before": objective_before, "objective_after": objective_after, "parent_max_abs_residual": descriptor["parent_max_abs_residual"], "candidate_max_abs_residual": descriptor["candidate_max_abs_residual"], "behavior_changed": True}
    OUT.mkdir(parents=True, exist_ok=True)
    DESCRIPTOR.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_arena4_opening(*, opening_index: int, progress_dir: Path, result_path: Path, stage_wall_seconds: int = 7200) -> dict:
    if stage_wall_seconds <= 0:
        raise ValueError("stage_wall_seconds must be positive")
    allocation, compiled, native, parent = _load_parent()
    descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
    candidate = LearnableMaterialCheckpoint.from_dict(descriptor["candidate_checkpoint"])
    candidate.validate_ruleset(compiled)
    payload = allocation["selection_and_strength_corpora"]["Arena4"]
    registered = ArenaOpeningCorpus.from_dict(payload["corpus"])
    registered.validate(compiled)
    source = registered.openings[opening_index]
    openings = replace(registered, openings=(replace(source, index=0),))
    config = ArenaConfig(pairs=1, nodes_per_move=512, parent_nodes_per_move=512, child_nodes_per_move=512, max_depth=12, tt_megabytes=8, opening_seed=registered.seed, opening_count=1, min_plies=registered.min_plies, max_plies=registered.max_plies, workers=2, tt_reset_each_move=True)
    caps = ArenaExecutionCaps(per_game_wall_seconds=7200, per_game_nodes=262144, per_game_plies=512, max_stage_games=2, max_concurrent_games=2, stage_wall_seconds=stage_wall_seconds, logical_cpu_count=4)
    stage_id = "f86-native-search-distillation-arena4"
    identity_caps = caps
    execution_progress_dir = progress_dir
    legacy_manifest = progress_dir / "manifest.json"
    if stage_wall_seconds != 7200:
        # The prior F86 manifest is immutable identity evidence.  Try it with
        # its original 7200s identity cap while applying the new execution
        # cap; an identity failure falls back to a fresh, deterministic tree.
        if legacy_manifest.is_file():
            identity_caps = replace(caps, stage_wall_seconds=7200)
            try:
                run = run_arena_game_resumable(
                    compiled, native, parent, candidate, config,
                    progress_dir=execution_progress_dir, openings=openings,
                    capture_search_metrics=True, execution_caps=caps,
                    identity_caps=identity_caps, stage_id=stage_id, max_pairs=1,
                )
            except ArenaExecutionError:
                execution_progress_dir = progress_dir.parent / "f86r1-stage-b-arena4" / "progress"
                identity_caps = caps
                run = run_arena_game_resumable(
                    compiled, native, parent, candidate, config,
                    progress_dir=execution_progress_dir, openings=openings,
                    capture_search_metrics=True, execution_caps=caps,
                    identity_caps=identity_caps, stage_id=stage_id, max_pairs=1,
                )
        else:
            execution_progress_dir = progress_dir.parent / "f86r1-stage-b-arena4" / "progress"
            run = run_arena_game_resumable(
                compiled, native, parent, candidate, config,
                progress_dir=execution_progress_dir, openings=openings,
                capture_search_metrics=True, execution_caps=caps,
                identity_caps=identity_caps, stage_id=stage_id, max_pairs=1,
            )
    else:
        run = run_arena_game_resumable(
            compiled, native, parent, candidate, config,
            progress_dir=execution_progress_dir, openings=openings,
            capture_search_metrics=True, execution_caps=caps,
            identity_caps=identity_caps, stage_id=stage_id, max_pairs=1,
        )
    summary = run.summary
    output = {"schema": "generic-chess-f86-native-search-distillation-arena4-v1", "status": run.status, "reason": run.reason, "completed_games": run.completed_games, "completed_pairs": run.completed_pairs, "total_games": run.total_games, "registered_corpus_id": registered.corpus_id, "opening_index": source.index, "parent_checkpoint_id": parent.checkpoint_id, "candidate_checkpoint_id": candidate.checkpoint_id, "progress_dir": repo_relative_path(ROOT, execution_progress_dir), "execution_stage_wall_seconds": stage_wall_seconds, "identity_stage_wall_seconds": identity_caps.stage_wall_seconds, "summary": None if summary is None else {"pair_count": summary.pair_count, "pair_scores": list(summary.pair_scores), "mean_pair_score": summary.mean_pair_score, "game_wins": summary.game_wins, "game_draws": summary.game_draws, "game_losses": summary.game_losses}}
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--arena-only", action="store_true")
    parser.add_argument("--opening-index", type=int, default=2)
    parser.add_argument("--progress-dir", type=Path)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--stage-result-path", type=Path)
    parser.add_argument("--stage-wall-seconds", type=int, default=7200)
    args = parser.parse_args()
    if args.arena_only:
        if args.progress_dir is None or args.result_path is None: parser.error("--arena-only requires paths")
        print(json.dumps(run_arena4_opening(opening_index=args.opening_index, progress_dir=args.progress_dir, result_path=args.result_path, stage_wall_seconds=args.stage_wall_seconds), sort_keys=True))
    else:
        result = build()
        if args.stage_result_path is not None:
            args.stage_result_path.parent.mkdir(parents=True, exist_ok=True)
            args.stage_result_path.write_text(json.dumps({"stage": "A", "status": "VALID_SUCCESSOR", "result": result}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
