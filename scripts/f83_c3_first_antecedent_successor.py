"""F83 C3: change the learner at the first teacher-disagreed antecedent.

This is intentionally narrower than the F83 C2 selective successor.  It uses
the first frozen root where C2 disagrees with the deep teacher, fits only that
root, and refuses to emit a candidate unless the learner's top action actually
changes to the teacher action.  The resulting checkpoint is then suitable for
the minimum approved Arena4 strength probe.
"""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, ArenaOpeningCorpus, run_arena_game_resumable
from generic_chess.learning.nonlinear import CompactNonlinearResidual
from generic_chess.learning.serialization import stable_sha256
from scripts import f78_parent_anchored_full_residual_arena2 as f78
from scripts import f82_c2_parent_anchored_repeatability as c2


WORK_ORDER = "GENERICCHESS-F83-C3-FIRST-TEACHER-DISAGREED-ANTECEDENT"
LABEL = c2.LABEL
ALLOCATION = ROOT / "artifacts/f82_c2_repeatability/c2_allocation_manifest.json"
C2_ARTIFACT = ROOT / "artifacts/f82_c2_repeatability/c2_candidate_result.json"
EVIDENCE = ROOT / "artifacts/f85_c2_train_teacher_evidence/training_evidence.json"
OUT = ROOT / "artifacts/f83_c3_first_antecedent_successor"
ARTIFACT = OUT / "successor_candidate_result.json"
DESCRIPTOR = OUT / "successor_candidate_descriptor.json"
ALPHAS = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125)
FIRST_ANTECEDENT = "c1_on_policy-a-01"


def _root_row(parent_model: CompactNonlinearResidual) -> dict:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    root = next(row for row in evidence["roots"] if row["root_id"] == FIRST_ANTECEDENT)
    rows = root["teacher_rows"]
    keys = [row["action_key"] for row in rows]
    target_key = root["root_metadata"]["root_80k"]["action_key"]
    target = keys.index(target_key)
    features = np.asarray([row["features"] for row in rows], dtype=float)
    base = np.asarray([row["base_q"] for row in rows], dtype=float)
    prediction = parent_model.predict(features)
    order = sorted(range(len(keys)), key=lambda i: (-float(base[i] + prediction[i]), keys[i]))
    if keys[order[0]] == target_key:
        raise RuntimeError("first antecedent is no longer a teacher disagreement")
    return {"root_id": FIRST_ANTECEDENT, "features": features, "base": base,
            "target": target, "target_key": target_key, "keys": keys,
            "parent_top_index": order[0], "parent_top_key": keys[order[0]]}


def _top(model: CompactNonlinearResidual, row: dict) -> int:
    scores = row["base"] + model.predict(row["features"])
    return min(range(len(scores)), key=lambda i: (-float(scores[i]), row["keys"][i]))


def build() -> dict:
    allocation = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    _artifact, descriptor, compiled, _native, _c1, parent = c2._load_verified_arena2_candidate(allocation, C2_ARTIFACT)
    parent_model = CompactNonlinearResidual.from_dict(parent.compact_nonlinear)
    row = _root_row(parent_model)
    fit_data = [{"root_index": row["root_id"], "features": row["features"], "base": row["base"], "target": row["target"], "keys": row["keys"]}]
    raw_model, fit_summary = f78._adam_fit(parent_model, fit_data)
    attempts = []
    chosen = None
    chosen_model = None
    for alpha in ALPHAS:
        model = f78._interpolate(parent_model, raw_model, alpha)
        top = _top(model, row)
        scores = row["base"] + model.predict(row["features"])
        loss = f78._pairwise_loss(model, fit_data)
        safe = (top == row["target"] and top != row["parent_top_index"] and np.isfinite(scores).all() and loss < f78._pairwise_loss(parent_model, fit_data))
        attempts.append({"alpha": alpha, "top_index": top, "top_key": row["keys"][top], "target_key": row["target_key"], "pairwise_objective": loss, "safe": safe})
        if chosen_model is None and safe:
            chosen, chosen_model = alpha, model
    if chosen_model is None:
        raise RuntimeError("no alpha changed the first antecedent to the teacher action")
    identity = {"work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id,
                "parent_model_sha256": stable_sha256(parent.compact_nonlinear),
                "source_c2_candidate_descriptor_sha256": descriptor["descriptor_sha256"],
                "teacher_evidence_sha256": c2.TEACHER_EVIDENCE_SHA,
                "antecedent_root_id": FIRST_ANTECEDENT, "target_action_key": row["target_key"],
                "objective": "single_antecedent_teacher_correction", "alpha": chosen}
    successor, training_hash = f78._make_candidate(parent, chosen_model, identity)
    successor.validate_ruleset(compiled)
    model_sha = stable_sha256(chosen_model.to_dict())
    descriptor_payload = {"schema": "generic-chess-f83-c3-first-antecedent-descriptor-v1", "work_order": WORK_ORDER,
        "ruleset": LABEL, "parent_checkpoint_id": parent.checkpoint_id,
        "parent_model_sha256": stable_sha256(parent.compact_nonlinear),
        "source_c2_candidate_descriptor_sha256": descriptor["descriptor_sha256"],
        "teacher_evidence_sha256": c2.TEACHER_EVIDENCE_SHA, "antecedent_root_id": FIRST_ANTECEDENT,
        "parent_top_key": row["parent_top_key"], "target_action_key": row["target_key"],
        "candidate_checkpoint_id": successor.checkpoint_id, "candidate_model_sha256": model_sha,
        "training_config_hash": training_hash, "chosen_alpha": chosen,
        "candidate_checkpoint": successor.to_dict(), "compact_model": chosen_model.to_dict(),
        "fit_summary": fit_summary, "selection": {"attempts": attempts, "behavior_changed": True}}
    descriptor_payload["descriptor_sha256"] = stable_sha256(descriptor_payload)
    result = {"schema": "generic-chess-f83-c3-first-antecedent-successor-v1", "status": "SUCCESSOR_READY_FOR_APPROVED_ARENA",
        "work_order": WORK_ORDER, "parent_checkpoint_id": parent.checkpoint_id,
        "parent_model_sha256": stable_sha256(parent.compact_nonlinear), "candidate_checkpoint_id": successor.checkpoint_id,
        "candidate_model_sha256": model_sha, "candidate_descriptor_path": str(DESCRIPTOR.relative_to(ROOT)).replace("\\", "/"),
        "candidate_descriptor_sha256": descriptor_payload["descriptor_sha256"], "teacher_evidence_sha256": c2.TEACHER_EVIDENCE_SHA,
        "antecedent_root_id": FIRST_ANTECEDENT, "parent_top_key": row["parent_top_key"], "target_action_key": row["target_key"],
        "chosen_alpha": chosen, "training_config_hash": training_hash, "selection": {"attempts": attempts, "behavior_changed": True}}
    OUT.mkdir(parents=True, exist_ok=True)
    DESCRIPTOR.write_text(json.dumps(descriptor_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_arena4_opening(*, opening_index: int, progress_dir: Path, result_path: Path) -> dict:
    allocation = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    _artifact, _descriptor, compiled, native, _c1, parent = c2._load_verified_arena2_candidate(allocation, C2_ARTIFACT)
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8"))
    if stable_sha256({k: v for k, v in descriptor.items() if k != "descriptor_sha256"}) != descriptor["descriptor_sha256"] or result["candidate_descriptor_sha256"] != descriptor["descriptor_sha256"]:
        raise RuntimeError("successor artifact hash mismatch")
    from generic_chess.learning.material import LearnableMaterialCheckpoint
    successor = LearnableMaterialCheckpoint.from_dict(descriptor["candidate_checkpoint"])
    successor.validate_ruleset(compiled)
    payload = allocation["selection_and_strength_corpora"]["Arena4"]
    registered = ArenaOpeningCorpus.from_dict(payload["corpus"])
    registered.validate(compiled)
    if registered.corpus_id != payload["corpus_id"] or not 0 <= opening_index < len(registered.openings):
        raise RuntimeError("Arena4 registered corpus identity/index mismatch")
    source = registered.openings[opening_index]
    openings = replace(registered, openings=(replace(source, index=0),))
    config = ArenaConfig(pairs=1, nodes_per_move=512, parent_nodes_per_move=512, child_nodes_per_move=512, max_depth=12, tt_megabytes=8, opening_seed=registered.seed, opening_count=1, min_plies=registered.min_plies, max_plies=registered.max_plies, workers=2, tt_reset_each_move=True)
    caps = ArenaExecutionCaps(per_game_wall_seconds=7200, per_game_nodes=262144, per_game_plies=512, max_stage_games=2, max_concurrent_games=2, stage_wall_seconds=7200, logical_cpu_count=4)
    run = run_arena_game_resumable(compiled, native, parent, successor, config, progress_dir=progress_dir, openings=openings, capture_search_metrics=True, caps=caps, identity_caps=caps, stage_id="f83-c3-first-antecedent-arena4", max_pairs=1)
    summary = run.summary
    output = {"schema": "generic-chess-f83-c3-first-antecedent-arena4-v1", "status": run.status, "reason": run.reason, "completed_games": run.completed_games, "completed_pairs": run.completed_pairs, "total_games": run.total_games, "registered_corpus_id": registered.corpus_id, "opening_index": source.index, "opening_final_position_key": source.final_position_key, "parent_checkpoint_id": parent.checkpoint_id, "candidate_checkpoint_id": successor.checkpoint_id, "config": asdict(config), "execution_caps": asdict(caps), "summary": None if summary is None else {"pair_count": summary.pair_count, "pair_scores": list(summary.pair_scores), "mean_pair_score": summary.mean_pair_score, "game_wins": summary.game_wins, "game_draws": summary.game_draws, "game_losses": summary.game_losses}}
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena4-opening", action="store_true")
    parser.add_argument("--opening-index", type=int)
    parser.add_argument("--progress-dir", type=Path)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    if args.run_arena4_opening:
        if args.opening_index is None or args.progress_dir is None or args.result_path is None:
            parser.error("--run-arena4-opening requires --opening-index, --progress-dir, and --result-path")
        print(json.dumps(run_arena4_opening(opening_index=args.opening_index, progress_dir=args.progress_dir, result_path=args.result_path), sort_keys=True))
    else:
        print(json.dumps(build(), indent=2, sort_keys=True))
