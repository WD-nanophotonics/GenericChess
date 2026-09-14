"""F85: calibrate TDLeaf alpha on one bounded native trajectory, then probe once."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, ArenaOpeningCorpus, run_arena_game_resumable
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.serialization import stable_sha256
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from scripts.f84_native_selfplay_tdleaf import _load_parent


WORK_ORDER = "F85_NATIVE_CALIBRATED_TDLEAF_SINGLE_UPDATE"
OUT = ROOT / "artifacts/f85_native_calibrated_tdleaf"
DESCRIPTOR = OUT / "successor_candidate_descriptor.json"
ARTIFACT = OUT / "successor_candidate_result.json"
SEED = 840401


def build() -> dict:
    allocation, compiled, native, parent = _load_parent()
    if DESCRIPTOR.is_file() and ARTIFACT.is_file():
        return json.loads(ARTIFACT.read_text(encoding="utf-8"))
    selfplay_config = SelfPlayConfig(games=1, nodes_per_move=512, max_depth=12, seed=SEED, epsilon=0.10, tt_megabytes=8, max_plies=64)
    trajectories = collect_self_play(compiled, native, parent, selfplay_config)
    if len(trajectories) != 1:
        raise RuntimeError("F85 requires exactly one trajectory")
    trajectory = trajectories[0]
    if not trajectory.points or (trajectory.truncated and trajectory.bootstrap_value is None):
        raise RuntimeError("F85 trajectory gate failed")
    nominal_config = TDLeafConfig()
    nominal = tdleaf_update(trajectories, parent, nominal_config)
    median = parent.reference_median
    nominal_alpha = 0.01 * max(median, 1.0)
    target_l2 = 0.10 * median
    measured_l2 = max(nominal.weight_l2_delta, 1e-9)
    calibrated_alpha = min(nominal_alpha * (target_l2 / measured_l2), nominal_alpha * 200.0)
    calibrated_alpha = max(calibrated_alpha, nominal_alpha)
    calibrated_config = TDLeafConfig(gamma=1.0, lambd=0.7, alpha=calibrated_alpha, value_scale=None)
    applied = tdleaf_update(trajectories, parent, calibrated_config)
    if not (nominal.weight_l2_delta > 0 and applied.positions_seen > 0 and applied.weight_l2_delta > 0):
        raise RuntimeError("F85 TDLeaf gate failed")
    identity = {"work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id,
        "parent_model_sha256": stable_sha256(parent.compact_nonlinear), "selfplay_config": asdict(selfplay_config),
        "nominal_tdleaf_config": asdict(nominal_config), "calibrated_tdleaf_config": asdict(calibrated_config),
        "trajectory_id": trajectory.trajectory_id, "trajectory_terminal": trajectory.terminal,
        "trajectory_truncated": trajectory.truncated, "trajectory_bootstrap_value": trajectory.bootstrap_value,
        "trajectory_points": len(trajectory.points), "trajectory_plies": len(trajectory.actions),
        "reference_median": median, "nominal_alpha": nominal_alpha, "target_l2": target_l2,
        "measured_nominal_l2": measured_l2, "calibrated_alpha": calibrated_alpha,
        "nominal_update": asdict(nominal), "applied_update": asdict(applied)}
    training_hash = stable_sha256(identity)
    candidate = parent.child_checkpoint(board_weights=applied.board_weights, hand_weights=applied.hand_weights,
        dynamic_weights=applied.dynamic_weights, games_seen_delta=1, positions_seen_delta=applied.positions_seen,
        training_updates_delta=1, training_config_hash=training_hash, training_seed=SEED)
    candidate.validate_ruleset(compiled)
    if candidate.checkpoint_id == parent.checkpoint_id:
        raise RuntimeError("F85 candidate did not change")
    descriptor = {"schema": "generic-chess-f85-native-calibrated-tdleaf-descriptor-v1", "work_order": WORK_ORDER,
        "parent_checkpoint_id": parent.checkpoint_id, "parent_model_sha256": stable_sha256(parent.compact_nonlinear),
        "candidate_checkpoint_id": candidate.checkpoint_id, "candidate_checkpoint": candidate.to_dict(),
        "candidate_model_sha256": stable_sha256(candidate.compact_nonlinear), "training_config_hash": training_hash,
        "selfplay_config": asdict(selfplay_config), "nominal_tdleaf_config": asdict(nominal_config),
        "calibrated_tdleaf_config": asdict(calibrated_config), "trajectory_id": trajectory.trajectory_id,
        "trajectory_terminal": trajectory.terminal, "trajectory_truncated": trajectory.truncated,
        "trajectory_bootstrap_value": trajectory.bootstrap_value, "trajectory_points": len(trajectory.points),
        "trajectory_plies": len(trajectory.actions), "reference_median": median, "nominal_alpha": nominal_alpha,
        "target_l2": target_l2, "measured_nominal_l2": measured_l2, "calibrated_alpha": calibrated_alpha,
        "nominal_update": asdict(nominal), "applied_update": asdict(applied), "allocation_sha256": allocation["allocation_sha256"]}
    descriptor["descriptor_sha256"] = stable_sha256(descriptor)
    result = {"schema": "generic-chess-f85-native-calibrated-tdleaf-v1", "status": "SUCCESSOR_READY_FOR_APPROVED_ARENA",
        "work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id, "candidate_checkpoint_id": candidate.checkpoint_id,
        "candidate_descriptor_path": str(DESCRIPTOR.relative_to(ROOT)).replace("\\", "/"), "candidate_descriptor_sha256": descriptor["descriptor_sha256"],
        "training_config_hash": training_hash, "trajectory_id": trajectory.trajectory_id, "trajectory_terminal": trajectory.terminal,
        "trajectory_truncated": trajectory.truncated, "trajectory_bootstrap_value": trajectory.bootstrap_value,
        "trajectory_points": len(trajectory.points), "trajectory_plies": len(trajectory.actions), "nominal_alpha": nominal_alpha,
        "measured_nominal_l2": measured_l2, "calibrated_alpha": calibrated_alpha, "positions_seen": applied.positions_seen,
        "weight_l2_delta": applied.weight_l2_delta, "behavior_changed": True}
    OUT.mkdir(parents=True, exist_ok=True)
    DESCRIPTOR.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_arena4_opening(*, opening_index: int, progress_dir: Path, result_path: Path) -> dict:
    allocation, compiled, native, parent = _load_parent()
    descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    if stable_sha256({k: v for k, v in descriptor.items() if k != "descriptor_sha256"}) != descriptor["descriptor_sha256"]:
        raise RuntimeError("F85 descriptor hash mismatch")
    candidate = LearnableMaterialCheckpoint.from_dict(descriptor["candidate_checkpoint"])
    candidate.validate_ruleset(compiled)
    payload = allocation["selection_and_strength_corpora"]["Arena4"]
    registered = ArenaOpeningCorpus.from_dict(payload["corpus"])
    registered.validate(compiled)
    source = registered.openings[opening_index]
    openings = replace(registered, openings=(replace(source, index=0),))
    config = ArenaConfig(pairs=1, nodes_per_move=512, parent_nodes_per_move=512, child_nodes_per_move=512, max_depth=12, tt_megabytes=8, opening_seed=registered.seed, opening_count=1, min_plies=registered.min_plies, max_plies=registered.max_plies, workers=2, tt_reset_each_move=True)
    caps = ArenaExecutionCaps(per_game_wall_seconds=7200, per_game_nodes=262144, per_game_plies=512, max_stage_games=2, max_concurrent_games=2, stage_wall_seconds=7200, logical_cpu_count=4)
    run = run_arena_game_resumable(compiled, native, parent, candidate, config, progress_dir=progress_dir, openings=openings, capture_search_metrics=True, caps=caps, identity_caps=caps, stage_id="f85-native-calibrated-tdleaf-arena4", max_pairs=1)
    summary = run.summary
    output = {"schema": "generic-chess-f85-native-calibrated-tdleaf-arena4-v1", "status": run.status, "reason": run.reason, "completed_games": run.completed_games, "completed_pairs": run.completed_pairs, "total_games": run.total_games, "registered_corpus_id": registered.corpus_id, "opening_index": source.index, "parent_checkpoint_id": parent.checkpoint_id, "candidate_checkpoint_id": candidate.checkpoint_id, "summary": None if summary is None else {"pair_count": summary.pair_count, "pair_scores": list(summary.pair_scores), "mean_pair_score": summary.mean_pair_score, "game_wins": summary.game_wins, "game_draws": summary.game_draws, "game_losses": summary.game_losses}}
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--arena-only", action="store_true")
    parser.add_argument("--opening-index", type=int, default=1)
    parser.add_argument("--progress-dir", type=Path)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--stage-result-path", type=Path)
    args = parser.parse_args()
    if args.arena_only:
        if args.progress_dir is None or args.result_path is None: parser.error("--arena-only requires paths")
        print(json.dumps(run_arena4_opening(opening_index=args.opening_index, progress_dir=args.progress_dir, result_path=args.result_path), sort_keys=True))
    else:
        result = build()
        if args.stage_result_path is not None:
            args.stage_result_path.parent.mkdir(parents=True, exist_ok=True)
            args.stage_result_path.write_text(json.dumps({"stage": "A", "status": "VALID_SUCCESSOR", "result": result}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
