"""F88: test two deterministic dampings of the frozen F87 update in Arena2."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import (  # noqa: E402
    ArenaConfig,
    ArenaExecutionCaps,
    ArenaOpeningCorpus,
    run_arena_game_resumable,
)
from generic_chess.learning.compact_checkpoint import load_compact_checkpoint  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from scripts.f84_native_selfplay_tdleaf import _load_parent  # noqa: E402


WORK_ORDER = "GENERICCHESS_F88_F87_UPDATE_DAMPING_ARENA2"
BASELINE_SHA = "e315307525987d0833a7bb7f7e761f433f77e8c7"
PARENT_ID = "c45623c0b905780ed1fd896a8f9364fd369bed1e641519f45fb40a3faf014d71"
RAW_F87_ID = "0c94b1d6b0a0b66939707d1e4184e23cc1391678c7bda67267d834a7565a5c42"
ALPHAS = (0.5, 0.25)
ALLOCATION = ROOT / "artifacts/f82_c2_repeatability/c2_allocation_manifest.json"
COMPACT_CHECKPOINT = ROOT / "checkpoints/f86_compact_checkpoint.json"
DEFAULT_RESULT = ROOT / "artifacts/f88_f87_update_damping_arena2/arena2_full_result.json"


def _load_context():
    allocation, compiled, native, parent = _load_parent()
    if allocation != json.loads(ALLOCATION.read_text(encoding="utf-8")):
        raise RuntimeError("F88 allocation identity changed")
    raw = load_compact_checkpoint(COMPACT_CHECKPOINT, "candidate")
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("F88 parent checkpoint identity mismatch")
    if raw.checkpoint_id != RAW_F87_ID:
        raise RuntimeError("F88 raw F87 checkpoint identity mismatch")
    parent.validate_ruleset(compiled)
    raw.validate_ruleset(compiled)
    corpus_payload = allocation["selection_and_strength_corpora"]["Arena2"]
    if corpus_payload["corpus_id"] != "6eca12faa0981e1c71f637eae7f66ee4a053193a752fbe592d2b0edafbdffd2a":
        raise RuntimeError("F88 Arena2 corpus identity mismatch")
    corpus = ArenaOpeningCorpus.from_dict(corpus_payload["corpus"])
    corpus.validate(compiled)
    if tuple(opening.index for opening in corpus.openings) != (0, 1):
        raise RuntimeError("F88 requires the registered Arena2 openings 0 and 1")
    return allocation, compiled, native, parent, raw, corpus


def _interpolate(parent_model: CompactNonlinearResidual, raw_model: CompactNonlinearResidual, alpha: float):
    if alpha not in ALPHAS:
        raise ValueError(f"unsupported F88 alpha: {alpha}")
    parent_hidden = np.asarray(parent_model.hidden_weights, dtype=np.float64)
    raw_hidden = np.asarray(raw_model.hidden_weights, dtype=np.float64)
    return replace(
        parent_model,
        hidden_weights=tuple(tuple(row) for row in (parent_hidden + alpha * (raw_hidden - parent_hidden)).tolist()),
        hidden_bias=tuple((np.asarray(parent_model.hidden_bias) + alpha * (np.asarray(raw_model.hidden_bias) - np.asarray(parent_model.hidden_bias))).tolist()),
        output_weights=tuple((np.asarray(parent_model.output_weights) + alpha * (np.asarray(raw_model.output_weights) - np.asarray(parent_model.output_weights))).tolist()),
    )


def build_candidate(parent, raw, alpha: float):
    parent_model = CompactNonlinearResidual.from_dict(parent.compact_nonlinear)
    raw_model = CompactNonlinearResidual.from_dict(raw.compact_nonlinear)
    model = _interpolate(parent_model, raw_model, alpha)
    identity = {
        "work_order": WORK_ORDER,
        "baseline_sha": BASELINE_SHA,
        "parent_checkpoint_id": parent.checkpoint_id,
        "raw_f87_checkpoint_id": raw.checkpoint_id,
        "raw_f87_model_sha256": stable_sha256(raw.compact_nonlinear),
        "alpha": alpha,
        "interpolation": "parent + alpha * (raw_f87 - parent)",
        "trainable_fields": ["hidden_weights", "hidden_bias", "output_weights"],
    }
    training_hash = stable_sha256(identity)
    candidate = parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        spatial_occupancy_weights=parent.spatial_occupancy_weights,
        localized_control_weights=parent.localized_control_weights,
        compact_nonlinear=model.to_dict(),
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=training_hash,
        training_seed=None,
    )
    delta = {
        "hidden_weights": np.asarray(model.hidden_weights) - np.asarray(parent_model.hidden_weights),
        "hidden_bias": np.asarray(model.hidden_bias) - np.asarray(parent_model.hidden_bias),
        "output_weights": np.asarray(model.output_weights) - np.asarray(parent_model.output_weights),
    }
    return candidate, {
        "alpha": alpha,
        "candidate_checkpoint_id": candidate.checkpoint_id,
        "candidate_model_sha256": stable_sha256(model.to_dict()),
        "training_config_hash": training_hash,
        "parameter_delta_norms": {name: float(np.linalg.norm(value)) for name, value in delta.items()},
        "parent_checkpoint_id": parent.checkpoint_id,
        "raw_f87_checkpoint_id": raw.checkpoint_id,
        "raw_f87_model_sha256": stable_sha256(raw.compact_nonlinear),
        "candidate": candidate,
    }


def _game_payload(game):
    return {
        "pair": game.pair,
        "opening_id": game.opening_id,
        "child_owner": game.child_owner,
        "winner": game.winner,
        "result": game.result,
        "plies": game.plies,
        "completed": True,
        "truncated": False,
    }


def run_candidate(compiled, native, parent, candidate, corpus, metadata, progress_dir: Path):
    config = ArenaConfig(
        pairs=2,
        nodes_per_move=512,
        parent_nodes_per_move=512,
        child_nodes_per_move=512,
        max_depth=12,
        tt_megabytes=8,
        opening_seed=corpus.seed,
        opening_count=2,
        min_plies=corpus.min_plies,
        max_plies=corpus.max_plies,
        workers=2,
        tt_reset_each_move=True,
    )
    caps = ArenaExecutionCaps(
        per_game_wall_seconds=7200,
        per_game_nodes=262144,
        per_game_plies=512,
        max_stage_games=4,
        max_concurrent_games=2,
        stage_wall_seconds=14400,
        logical_cpu_count=4,
    )
    run = run_arena_game_resumable(
        compiled,
        native,
        parent,
        candidate,
        config,
        progress_dir=progress_dir,
        openings=corpus,
        capture_search_metrics=True,
        execution_caps=caps,
        identity_caps=caps,
        stage_id="f88-f87-update-damping-arena2",
        max_pairs=2,
    )
    summary = run.summary
    result = {
        **{key: value for key, value in metadata.items() if key != "candidate"},
        "corpus_id": corpus.corpus_id,
        "opening_indices": [opening.index for opening in corpus.openings],
        "config": asdict(config),
        "execution_caps": asdict(caps),
        "status": run.status,
        "reason": run.reason,
        "completed_games": run.completed_games,
        "completed_pairs": run.completed_pairs,
        "total_games": run.total_games,
        "summary": None,
        "games": [],
    }
    if summary is not None:
        result["summary"] = {
            "pair_scores": list(summary.pair_scores),
            "mean_pair_score": summary.mean_pair_score,
            "game_wins": summary.game_wins,
            "game_draws": summary.game_draws,
            "game_losses": summary.game_losses,
        }
        for pair in summary.pairs:
            result["games"].extend((_game_payload(pair.game_child_owner0), _game_payload(pair.game_child_owner1)))
    return result


def run_all(progress_root: Path, result_path: Path) -> dict:
    _allocation, compiled, native, parent, raw, corpus = _load_context()
    results = []
    for alpha in ALPHAS:
        candidate, metadata = build_candidate(parent, raw, alpha)
        candidate.validate_ruleset(compiled)
        results.append(run_candidate(compiled, native, parent, candidate, corpus, metadata, progress_root / f"alpha-{alpha}"))
    if any(item["status"] != "COMPLETE" or item["completed_games"] != 4 or item["completed_pairs"] != 2 for item in results):
        status = "INCOMPLETE"
    else:
        status = "COMPLETE"
    output = {
        "schema": "generic-chess-f88-f87-update-damping-arena2-v1",
        "work_order": WORK_ORDER,
        "status": status,
        "baseline_sha": BASELINE_SHA,
        "parent_checkpoint_id": parent.checkpoint_id,
        "raw_f87_checkpoint_id": raw.checkpoint_id,
        "raw_f87_arena4_context": {"artifact": "artifacts/f87_two_trajectory_native_search_distillation/arena4_full_result.json", "mean_pair_score": 0.3125, "game_wins": 2, "game_draws": 1, "game_losses": 5},
        "arena2_corpus_id": corpus.corpus_id,
        "candidates": results,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--arena-all", action="store_true")
    parser.add_argument("--progress-root", type=Path, default=ROOT / ".generic_chess_flow/f88-f87-update-damping-arena2")
    parser.add_argument("--result-path", type=Path, default=DEFAULT_RESULT)
    args = parser.parse_args()
    if not args.arena_all:
        parser.error("F88 requires --arena-all")
    print(json.dumps(run_all(args.progress_root, args.result_path), sort_keys=True))
