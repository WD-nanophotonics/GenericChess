"""F84: one native self-play trajectory followed by one TDLeaf update."""

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
from scripts import f82_c2_parent_anchored_repeatability as c2


WORK_ORDER = "F84_NATIVE_SELFPLAY_TDLEAF_SINGLE_UPDATE"
ALLOCATION = ROOT / "artifacts/f82_c2_repeatability/c2_allocation_manifest.json"
C2_ARTIFACT = ROOT / "artifacts/f82_c2_repeatability/c2_candidate_result.json"
F83_RESULT = ROOT / "artifacts/f83_c3_first_antecedent_successor/successor_candidate_result.json"
F83_DESCRIPTOR = ROOT / "artifacts/f83_c3_first_antecedent_successor/successor_candidate_descriptor.json"
OUT = ROOT / "artifacts/f84_native_selfplay_tdleaf"
DESCRIPTOR = OUT / "successor_candidate_descriptor.json"
ARTIFACT = OUT / "successor_candidate_result.json"
SEED = 840401


def _load_parent():
    allocation = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    _artifact, _descriptor, compiled, native, _c1, _c2_parent = c2._load_verified_arena2_candidate(allocation, C2_ARTIFACT)
    f83_result = json.loads(F83_RESULT.read_text(encoding="utf-8"))
    f83_descriptor = json.loads(F83_DESCRIPTOR.read_text(encoding="utf-8"))
    if stable_sha256({k: v for k, v in f83_descriptor.items() if k != "descriptor_sha256"}) != f83_descriptor["descriptor_sha256"]:
        raise RuntimeError("F83 parent descriptor hash mismatch")
    if f83_result["candidate_descriptor_sha256"] != f83_descriptor["descriptor_sha256"]:
        raise RuntimeError("F83 parent artifact/descriptor mismatch")
    parent = LearnableMaterialCheckpoint.from_dict(f83_descriptor["candidate_checkpoint"])
    parent.validate_ruleset(compiled)
    if parent.checkpoint_id != f83_result["candidate_checkpoint_id"]:
        raise RuntimeError("F83 parent checkpoint identity mismatch")
    return allocation, compiled, native, parent


def build() -> dict:
    allocation, compiled, native, parent = _load_parent()
    if DESCRIPTOR.is_file() and ARTIFACT.is_file():
        descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
        result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        if descriptor.get("parent_checkpoint_id") == parent.checkpoint_id and result.get("candidate_descriptor_sha256") == descriptor.get("descriptor_sha256"):
            return result
    config = SelfPlayConfig(
        games=1, nodes_per_move=512, max_depth=12, seed=SEED,
        epsilon=0.10, tt_megabytes=8, max_plies=64,
    )
    trajectories = collect_self_play(compiled, native, parent, config)
    if len(trajectories) != 1:
        raise RuntimeError("F84 requires exactly one self-play trajectory")
    trajectory = trajectories[0]
    if not trajectory.points or (trajectory.truncated and trajectory.bootstrap_value is None):
        raise RuntimeError("F84 requires training points and an explicit cutoff bootstrap")
    update = tdleaf_update(trajectories, parent, TDLeafConfig())
    if update.positions_seen <= 0 or update.weight_l2_delta <= 0.0:
        raise RuntimeError("native self-play TDLeaf update did not change learner weights")
    identity = {"work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id,
                "parent_model_sha256": stable_sha256(parent.compact_nonlinear), "selfplay_config": asdict(config),
                "tdleaf_config": asdict(TDLeafConfig()), "trajectory_id": trajectory.trajectory_id,
                "trajectory_terminal": trajectory.terminal, "trajectory_winner": trajectory.winner,
                "trajectory_points": len(trajectory.points), "trajectory_plies": len(trajectory.actions),
                "objective": "one_native_selfplay_trajectory_one_default_tdleaf_update"}
    training_hash = stable_sha256(identity)
    candidate = parent.child_checkpoint(board_weights=update.board_weights, hand_weights=update.hand_weights,
        dynamic_weights=update.dynamic_weights, games_seen_delta=1, positions_seen_delta=update.positions_seen,
        training_updates_delta=1, training_config_hash=training_hash, training_seed=SEED)
    candidate.validate_ruleset(compiled)
    if candidate.checkpoint_id == parent.checkpoint_id:
        raise RuntimeError("native TDLeaf candidate checkpoint did not change")
    descriptor_payload = {"schema": "generic-chess-f84-native-selfplay-tdleaf-descriptor-v1", "work_order": WORK_ORDER,
        "parent_checkpoint_id": parent.checkpoint_id, "parent_model_sha256": stable_sha256(parent.compact_nonlinear),
        "candidate_checkpoint_id": candidate.checkpoint_id, "candidate_checkpoint": candidate.to_dict(),
        "candidate_model_sha256": stable_sha256(candidate.compact_nonlinear), "training_config_hash": training_hash,
        "selfplay_config": asdict(config), "tdleaf_config": asdict(TDLeafConfig()),
        "trajectory_id": trajectory.trajectory_id, "trajectory_terminal": trajectory.terminal,
        "trajectory_winner": trajectory.winner, "trajectory_plies": len(trajectory.actions),
        "trajectory_points": len(trajectory.points), "tdleaf_update": asdict(update),
        "allocation_sha256": allocation["allocation_sha256"]}
    descriptor_payload["descriptor_sha256"] = stable_sha256(descriptor_payload)
    result = {"schema": "generic-chess-f84-native-selfplay-tdleaf-v1", "status": "SUCCESSOR_READY_FOR_APPROVED_ARENA",
        "work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id, "candidate_checkpoint_id": candidate.checkpoint_id,
        "candidate_descriptor_path": str(DESCRIPTOR.relative_to(ROOT)).replace("\\", "/"),
        "candidate_descriptor_sha256": descriptor_payload["descriptor_sha256"], "training_config_hash": training_hash,
        "trajectory_id": trajectory.trajectory_id, "trajectory_terminal": trajectory.terminal, "trajectory_winner": trajectory.winner,
        "trajectory_plies": len(trajectory.actions), "trajectory_points": len(trajectory.points),
        "positions_seen": update.positions_seen, "weight_l2_delta": update.weight_l2_delta,
        "behavior_changed": candidate.checkpoint_id != parent.checkpoint_id}
    OUT.mkdir(parents=True, exist_ok=True)
    DESCRIPTOR.write_text(json.dumps(descriptor_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_arena4_opening(*, opening_index: int, progress_dir: Path, result_path: Path) -> dict:
    allocation, compiled, native, parent = _load_parent()
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
    if stable_sha256({k: v for k, v in descriptor.items() if k != "descriptor_sha256"}) != descriptor["descriptor_sha256"] or result["candidate_descriptor_sha256"] != descriptor["descriptor_sha256"]:
        raise RuntimeError("F84 candidate artifact hash mismatch")
    candidate = LearnableMaterialCheckpoint.from_dict(descriptor["candidate_checkpoint"])
    candidate.validate_ruleset(compiled)
    if descriptor["parent_checkpoint_id"] != parent.checkpoint_id:
        raise RuntimeError("F84 parent binding mismatch")
    payload = allocation["selection_and_strength_corpora"]["Arena4"]
    registered = ArenaOpeningCorpus.from_dict(payload["corpus"])
    registered.validate(compiled)
    if registered.corpus_id != payload["corpus_id"] or not 0 <= opening_index < len(registered.openings):
        raise RuntimeError("Arena4 registered corpus identity/index mismatch")
    source = registered.openings[opening_index]
    openings = replace(registered, openings=(replace(source, index=0),))
    config = ArenaConfig(pairs=1, nodes_per_move=512, parent_nodes_per_move=512, child_nodes_per_move=512, max_depth=12, tt_megabytes=8, opening_seed=registered.seed, opening_count=1, min_plies=registered.min_plies, max_plies=registered.max_plies, workers=2, tt_reset_each_move=True)
    caps = ArenaExecutionCaps(per_game_wall_seconds=7200, per_game_nodes=262144, per_game_plies=512, max_stage_games=2, max_concurrent_games=2, stage_wall_seconds=7200, logical_cpu_count=4)
    run = run_arena_game_resumable(compiled, native, parent, candidate, config, progress_dir=progress_dir, openings=openings, capture_search_metrics=True, caps=caps, identity_caps=caps, stage_id="f84-native-selfplay-tdleaf-arena4", max_pairs=1)
    summary = run.summary
    output = {"schema": "generic-chess-f84-native-selfplay-tdleaf-arena4-v1", "status": run.status, "reason": run.reason, "completed_games": run.completed_games, "completed_pairs": run.completed_pairs, "total_games": run.total_games, "registered_corpus_id": registered.corpus_id, "opening_index": source.index, "opening_final_position_key": source.final_position_key, "parent_checkpoint_id": parent.checkpoint_id, "candidate_checkpoint_id": candidate.checkpoint_id, "config": asdict(config), "execution_caps": asdict(caps), "summary": None if summary is None else {"pair_count": summary.pair_count, "pair_scores": list(summary.pair_scores), "mean_pair_score": summary.mean_pair_score, "game_wins": summary.game_wins, "game_draws": summary.game_draws, "game_losses": summary.game_losses}}
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def execute(*, opening_index: int, progress_dir: Path, result_path: Path) -> dict:
    build()
    return run_arena4_opening(opening_index=opening_index, progress_dir=progress_dir, result_path=result_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--arena-only", action="store_true")
    parser.add_argument("--opening-index", type=int, default=0)
    parser.add_argument("--progress-dir", type=Path)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--stage-result-path", type=Path)
    args = parser.parse_args()
    if args.execute:
        if args.progress_dir is None or args.result_path is None:
            parser.error("--execute requires --progress-dir and --result-path")
        print(json.dumps(execute(opening_index=args.opening_index, progress_dir=args.progress_dir, result_path=args.result_path), sort_keys=True))
    elif args.build_only:
        result = build()
        if args.stage_result_path is not None:
            args.stage_result_path.parent.mkdir(parents=True, exist_ok=True)
            args.stage_result_path.write_text(json.dumps({"stage": "A", "status": "VALID_SUCCESSOR" if result["behavior_changed"] else "NO_CHANGE", "result": result}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.arena_only:
        if args.progress_dir is None or args.result_path is None:
            parser.error("--arena-only requires --progress-dir and --result-path")
        print(json.dumps(run_arena4_opening(opening_index=args.opening_index, progress_dir=args.progress_dir, result_path=args.result_path), sort_keys=True))
    else:
        print(json.dumps(build(), indent=2, sort_keys=True))
