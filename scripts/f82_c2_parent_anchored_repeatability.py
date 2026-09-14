"""F82 C2 parent-anchored full-residual repeatability harness.

The default mode only creates and validates a deterministic, corpus-disjoint
allocation.  Training and Arena execution are deliberately opt-in so the
workflow can bind a versioned compute plan before Heavy is authorized.
"""

from __future__ import annotations

from dataclasses import asdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.openings import ArenaOpeningCorpus, generate_arena_openings  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f50_generic_learnable_evaluator as f50  # noqa: E402
from scripts import f78_parent_anchored_full_residual_arena2 as f78  # noqa: E402
from scripts import f79_parent_anchored_full_residual_arena4 as f79  # noqa: E402


WORK_ORDER = "GENERICCHESS-C2-PARENT-ANCHORED-FULL-RESIDUAL-REPEATABILITY"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
PARENT_CHECKPOINT_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
PARENT_MODEL_SHA = "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
TRAIN_ROOT_CORPUS = ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json"
TEACHER_EVIDENCE = ROOT / "artifacts/f85_c2_train_teacher_evidence/training_evidence.json"
ARTIFACTS = ROOT / "artifacts/f82_c2_repeatability"
ALLOCATION_PATH = ARTIFACTS / "c2_allocation_manifest.json"
RESULT_PATH = ROOT / ".generic_chess_flow/f82-c2-parent-anchored-repeatability/c2_results.json"
CANDIDATE_ARTIFACT = ARTIFACTS / "c2_candidate_result.json"
CANDIDATE_DESCRIPTOR = ARTIFACTS / "c2_candidate_descriptor.json"
TEACHER_EVIDENCE_SHA = "c0a5e69f5d3345bbf4ab699d67b14b0fcbad745003ca17ac5beec3a1f4fbb4c2"
ARENA2_RESULT_PATH = ROOT / ".generic_chess_flow/f82-c2-arena2-v2/arena2_result.json"
ARENA2_PROGRESS = ROOT / ".generic_chess_flow/f82-c2-arena2-v2/progress"

# These values are fixed before inspecting any C2 result.
TRAIN_ROOT_COUNT = 36
SELECTION_SEED = 820201
SELECTION_PAIRS = 2
ARENA4_SEED = 820401
ARENA4_PAIRS = 4
ARENA8_SEED = 820801
ARENA8_PAIRS = 8
FINAL_SEED = 821601
FINAL_PAIRS = 8
NODES = 512
MAX_DEPTH = 12
TT_MEGABYTES = 8
MIN_PLIES = 2
MAX_PLIES = 6
BACKTRACKING_ALPHAS = f78.BACKTRACKING_ALPHAS


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _parent(compiled):
    _gen1, champion, descriptor = f79._load_frozen_candidate(compiled)
    if champion.checkpoint_id != PARENT_CHECKPOINT_ID or descriptor["candidate_model_sha256"] != PARENT_MODEL_SHA:
        raise RuntimeError("C2 parent checkpoint/model identity mismatch")
    champion.validate_ruleset(compiled)
    return champion, descriptor


def _root_positions() -> tuple[list[str], dict]:
    payload = json.loads(TRAIN_ROOT_CORPUS.read_text(encoding="utf-8"))
    roots = [root for root in payload["roots"] if root.get("role") == "train"]
    if len(roots) != TRAIN_ROOT_COUNT or len({root["position_key"] for root in roots}) != TRAIN_ROOT_COUNT:
        raise RuntimeError("C2 training allocation must contain 36 unique train roots")
    return [root["position_key"] for root in roots], {
        "path": str(TRAIN_ROOT_CORPUS.relative_to(ROOT)).replace("\\", "/"),
        "content_sha256": _sha(TRAIN_ROOT_CORPUS),
        "root_set_sha256": stable_sha256([
            {key: root[key] for key in ("root_id", "position_key", "stratum", "role", "replay_actions")}
            for root in roots
        ]),
        "root_count": len(roots),
        "stratum_counts": {name: sum(root["stratum"] == name for root in roots) for name in ("reachable_random", "c1_on_policy", "c1_pv_corridor")},
    }


def _corpus(compiled, *, seed: int, pairs: int) -> tuple[ArenaOpeningCorpus, dict]:
    corpus = generate_arena_openings(compiled, count=pairs, seed=seed, min_plies=MIN_PLIES, max_plies=MAX_PLIES)
    corpus.validate(compiled)
    keys = [opening.final_position_key for opening in corpus.openings]
    if len(keys) != pairs or len(set(keys)) != pairs:
        raise RuntimeError(f"C2 corpus {seed} is not unique")
    return corpus, {"seed": seed, "pairs": pairs, "opening_count": pairs, "corpus_id": corpus.corpus_id, "final_position_keys": keys, "corpus": corpus.to_dict()}


def precompute_allocation() -> dict:
    """Create the fixed training/selection/strength allocation and envelope."""
    if not native_available():
        raise RuntimeError("C2 requires the native extension")
    compiled, _native, _profile = f50._ruleset(LABEL)
    parent, descriptor = _parent(compiled)
    train_keys, train_source = _root_positions()
    corpora = {}
    for name, seed, pairs in (("Arena2", SELECTION_SEED, SELECTION_PAIRS), ("Arena4", ARENA4_SEED, ARENA4_PAIRS), ("Arena8", ARENA8_SEED, ARENA8_PAIRS), ("fresh_final_confirmation", FINAL_SEED, FINAL_PAIRS)):
        _corpus_obj, payload = _corpus(compiled, seed=seed, pairs=pairs)
        corpora[name] = payload
    all_eval_keys = [key for payload in corpora.values() for key in payload["final_position_keys"]]
    if len(set(all_eval_keys)) != len(all_eval_keys) or set(train_keys) & set(all_eval_keys):
        raise RuntimeError("C2 training, selection, and final-confirmation identities overlap")
    envelope = {
        "hard_wall_minutes": 240,
        "expected_wall_minutes": 110,
        "hard_cpu_hours": 15,
        "logical_cpu_count": 4,
        "max_concurrent_games": 1,
        "per_game_wall_seconds": 3600,
        "per_game_nodes": 262144,
        "per_game_plies": 512,
        "max_stage_games": 16,
        "stage_wall_seconds": 3600,
        "total_arena_games": 4 + 8 + 16 + 16,
    }
    allocation = {
        "schema": "generic-chess-f82-c2-allocation-v1",
        "work_order": WORK_ORDER,
        "status": "PRE_REGISTERED_AWAITING_COMPUTE_APPROVAL",
        "ruleset": LABEL,
        "parent": {"checkpoint_id": parent.checkpoint_id, "model_sha256": PARENT_MODEL_SHA, "descriptor_sha256": _sha(f79.F78_CANDIDATE)},
        "training": {"source": train_source, "root_position_keys": train_keys, "root_count": len(train_keys), "sealed_history_excluded": True},
        "selection_and_strength_corpora": corpora,
        "optimizer": {"family": "PARENT_ANCHORED_FULL_RESIDUAL", "optimizer": "Adam", "batching": "full_batch", "steps": 100, "learning_rate": 0.001, "proximal_coefficient": 0.001, "parent_anchoring": True, "backtracking_alphas": list(BACKTRACKING_ALPHAS), "first_safe_alpha_only": True, "one_candidate": True, "allowed_trainable_fields": ["hidden_weights", "hidden_bias", "output_weights"]},
        "arena": {"nodes_per_move": NODES, "max_depth": MAX_DEPTH, "tt_megabytes": TT_MEGABYTES, "workers": 1, "symmetric_parent_child_settings": True, "funnel": ["bounded_correctness_safety", "Arena2", "Arena4", "Arena8", "fresh_final_confirmation"]},
        "resource_envelope": envelope,
        "sealed_corpora_are_diagnostic_only": ["F62", "F75", "F77", "F78", "F79", "F80", "F81"],
    }
    allocation["allocation_sha256"] = stable_sha256(allocation)
    if ALLOCATION_PATH.exists() and json.loads(ALLOCATION_PATH.read_text(encoding="utf-8")) != allocation:
        raise RuntimeError("C2 allocation identity changed after pre-registration")
    _atomic_json(ALLOCATION_PATH, allocation)
    return allocation


def _training_data() -> list[dict]:
    if not TEACHER_EVIDENCE.is_file():
        raise RuntimeError("C2 teacher evidence is not available; acquire it under a separately approved plan")
    evidence = json.loads(TEACHER_EVIDENCE.read_text(encoding="utf-8"))
    if evidence.get("c1_checkpoint_id") != PARENT_CHECKPOINT_ID or evidence.get("c1_model_sha256") != PARENT_MODEL_SHA:
        raise RuntimeError("C2 teacher evidence is bound to a different C1")
    data = []
    for root in evidence.get("roots", []):
        rows = root.get("teacher_rows", [])
        if len(rows) < 2:
            continue
        data.append({"root_index": root["root_id"], "features": __import__("numpy").asarray([row["features"] for row in rows], dtype=float), "base": __import__("numpy").asarray([row["base_q"] for row in rows], dtype=float), "target": int(__import__("numpy").argmax([row["q_20k"] for row in rows])), "keys": [row["action_key"] for row in rows]})
    if not data:
        raise RuntimeError("C2 teacher evidence contains no usable action rows")
    return data


def run_fit_and_write_result(allocation: dict) -> dict:
    """Fit exactly one candidate; Arena execution remains a separately gated step."""
    import numpy as np
    compiled, _native, _profile = f50._ruleset(LABEL)
    parent_checkpoint, _descriptor = _parent(compiled)
    parent_model = CompactNonlinearResidual.from_dict(parent_checkpoint.compact_nonlinear)
    data = _training_data()
    raw_model, fit_summary = f78._adam_fit(parent_model, data)
    # Candidate safety is evaluated against the same fresh training rows only;
    # no historical corpus is admitted to selection.
    fit_roots = [{"root_index": row["root_index"], "metadata": {"action_rows": [{"action_key": key, "features": feature.tolist(), "base_q": float(base)} for key, feature, base in zip(row["keys"], row["features"], row["base"])]}} for row in data]
    alpha, selected, attempts = f78._select_alpha(fit_roots, data, parent_model, raw_model)
    if alpha is None or selected is None:
        raise RuntimeError("C2 has no safe registered alpha; candidate is stopped")
    candidate_model = f78._interpolate(parent_model, raw_model, alpha)
    identity = {"work_order": WORK_ORDER, "parent_checkpoint_id": PARENT_CHECKPOINT_ID, "parent_model_sha256": PARENT_MODEL_SHA, "allocation_sha256": allocation["allocation_sha256"], "optimizer": allocation["optimizer"], "alpha": alpha, "candidate_model_sha256": stable_sha256(candidate_model.to_dict())}
    candidate, training_hash = f78._make_candidate(parent_checkpoint, candidate_model, identity)
    if candidate.checkpoint_id == PARENT_CHECKPOINT_ID:
        raise RuntimeError("C2 candidate checkpoint did not change")
    result = {"schema": "generic-chess-f82-c2-parent-anchored-repeatability-v1", "work_order": WORK_ORDER, "status": "CANDIDATE_READY_FOR_APPROVED_ARENA", "parent_checkpoint_id": PARENT_CHECKPOINT_ID, "candidate_checkpoint_id": candidate.checkpoint_id, "candidate_model_sha256": stable_sha256(candidate_model.to_dict()), "training_config_hash": training_hash, "fit": fit_summary, "backtracking": {"alphas": list(BACKTRACKING_ALPHAS), "chosen_alpha": alpha, "attempts": attempts, "selected_metrics": selected}, "allocation_sha256": allocation["allocation_sha256"], "arena": None}
    _atomic_json(RESULT_PATH, result)
    return result


def _candidate_fit(allocation: dict):
    """Reconstruct the already published fit without selecting a new result."""
    import numpy as np
    compiled, _native, _profile = f50._ruleset(LABEL)
    parent_checkpoint, _descriptor = _parent(compiled)
    parent_model = CompactNonlinearResidual.from_dict(parent_checkpoint.compact_nonlinear)
    data = _training_data()
    raw_model, fit_summary = f78._adam_fit(parent_model, data)
    fit_roots = [{"root_index": row["root_index"], "metadata": {"action_rows": [{"action_key": key, "features": feature.tolist(), "base_q": float(base)} for key, feature, base in zip(row["keys"], row["features"], row["base"]) ]}} for row in data]
    alpha, selected, attempts = f78._select_alpha(fit_roots, data, parent_model, raw_model)
    if alpha is None or selected is None:
        raise RuntimeError("deterministic candidate reconstruction found no safe alpha")
    candidate_model = f78._interpolate(parent_model, raw_model, alpha)
    identity = {"work_order": WORK_ORDER, "parent_checkpoint_id": PARENT_CHECKPOINT_ID, "parent_model_sha256": PARENT_MODEL_SHA, "allocation_sha256": allocation["allocation_sha256"], "optimizer": allocation["optimizer"], "alpha": alpha, "candidate_model_sha256": stable_sha256(candidate_model.to_dict())}
    candidate, training_hash = f78._make_candidate(parent_checkpoint, candidate_model, identity)
    return compiled, parent_checkpoint, parent_model, candidate, candidate_model, training_hash, fit_summary, alpha, selected, attempts


def materialize_candidate(allocation: dict, artifact_path: Path = CANDIDATE_ARTIFACT) -> dict:
    """Recover the sealed candidate payload, failing closed before any write."""
    expected = json.loads(artifact_path.read_text(encoding="utf-8"))
    if expected.get("teacher_evidence_sha256") != TEACHER_EVIDENCE_SHA:
        raise RuntimeError("candidate artifact teacher evidence identity mismatch")
    if expected.get("allocation_sha256") != allocation.get("allocation_sha256"):
        raise RuntimeError("candidate artifact allocation identity mismatch")
    if expected.get("parent_checkpoint_id") != PARENT_CHECKPOINT_ID or (expected.get("parent_model_sha256") not in (None, PARENT_MODEL_SHA)):
        raise RuntimeError("candidate artifact parent identity mismatch")
    values = _candidate_fit(allocation)
    compiled, parent_checkpoint, parent_model, candidate, candidate_model, training_hash, fit_summary, alpha, selected, attempts = values
    failures = f78._representation_guard(compiled, parent_checkpoint, candidate, parent_model, candidate_model)
    if failures:
        raise RuntimeError("candidate representation guard failed: " + ", ".join(failures))
    model_sha = stable_sha256(candidate_model.to_dict())
    checks = {
        "candidate_checkpoint_id": candidate.checkpoint_id,
        "candidate_model_sha256": model_sha,
        "training_config_hash": training_hash,
        "chosen_alpha": alpha,
    }
    for key, actual in checks.items():
        expected_value = expected.get(key) if key != "chosen_alpha" else expected.get("backtracking", {}).get("chosen_alpha")
        if actual != expected_value:
            raise RuntimeError(f"deterministic candidate mismatch for {key}: {actual!r} != {expected_value!r}")
    descriptor = {
        "schema": "generic-chess-f82-c2-candidate-descriptor-v1",
        "work_order": WORK_ORDER,
        "ruleset": LABEL,
        "teacher_evidence_sha256": TEACHER_EVIDENCE_SHA,
        "parent_checkpoint_id": PARENT_CHECKPOINT_ID,
        "parent_model_sha256": PARENT_MODEL_SHA,
        "allocation_sha256": allocation["allocation_sha256"],
        "candidate_checkpoint_id": candidate.checkpoint_id,
        "candidate_model_sha256": model_sha,
        "training_config_hash": training_hash,
        "chosen_alpha": alpha,
        "candidate_checkpoint": candidate.to_dict(),
        "compact_model": candidate_model.to_dict(),
        "frozen_field_identity": expected.get("frozen_field_identity"),
        "serialization": {"checkpoint_id_from_payload": candidate.checkpoint_id, "model_sha256_from_payload": model_sha},
    }
    descriptor["descriptor_sha256"] = stable_sha256(descriptor)
    updated = dict(expected)
    updated["parent_model_sha256"] = PARENT_MODEL_SHA
    updated["candidate_descriptor_path"] = str(CANDIDATE_DESCRIPTOR.relative_to(ROOT)).replace("\\", "/")
    updated["candidate_descriptor_sha256"] = descriptor["descriptor_sha256"]
    updated["candidate_checkpoint_serialization_sha256"] = stable_sha256(candidate.to_dict())
    # All validation above is complete; these are the first writes in this path.
    _atomic_json(CANDIDATE_DESCRIPTOR, descriptor)
    _atomic_json(artifact_path, updated)
    return {"status": "CANDIDATE_MATERIALIZED", "descriptor_path": str(CANDIDATE_DESCRIPTOR.relative_to(ROOT)).replace("\\", "/"), "descriptor_sha256": descriptor["descriptor_sha256"], "candidate_checkpoint_id": candidate.checkpoint_id, "candidate_model_sha256": model_sha}


def run_arena2(allocation: dict, artifact_path: Path = CANDIDATE_ARTIFACT) -> dict:
    """Run only the preregistered two-pair Arena2 stage with exact caps."""
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    descriptor_path = ROOT / artifact.get("candidate_descriptor_path", "")
    if not descriptor_path.is_file():
        raise RuntimeError("verified candidate descriptor is missing")
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if stable_sha256({k: v for k, v in descriptor.items() if k != "descriptor_sha256"}) != descriptor.get("descriptor_sha256"):
        raise RuntimeError("candidate descriptor hash mismatch")
    for key in ("candidate_checkpoint_id", "candidate_model_sha256", "training_config_hash", "allocation_sha256", "teacher_evidence_sha256"):
        expected = artifact.get(key) if key != "teacher_evidence_sha256" else TEACHER_EVIDENCE_SHA
        if descriptor.get(key) != expected:
            raise RuntimeError(f"candidate descriptor identity mismatch for {key}")
    if allocation.get("allocation_sha256") != descriptor["allocation_sha256"]:
        raise RuntimeError("Arena2 allocation identity mismatch")
    if not native_available():
        raise RuntimeError("Arena2 requires the native extension")
    compiled, native, _profile = f50._ruleset(LABEL)
    parent, _parent_descriptor = _parent(compiled)
    candidate = LearnableMaterialCheckpoint.from_dict(descriptor["candidate_checkpoint"])
    candidate.validate_ruleset(compiled)
    if candidate.checkpoint_id != descriptor["candidate_checkpoint_id"] or stable_sha256(candidate.compact_nonlinear) != descriptor["candidate_model_sha256"]:
        raise RuntimeError("Arena2 candidate serialization identity mismatch")
    corpus_payload = allocation["selection_and_strength_corpora"]["Arena2"]
    openings = ArenaOpeningCorpus.from_dict(corpus_payload["corpus"])
    openings.validate(compiled)
    if openings.corpus_id != corpus_payload["corpus_id"] or len(openings.openings) != 2:
        raise RuntimeError("Arena2 corpus identity or size mismatch")
    config = ArenaConfig(pairs=2, nodes_per_move=NODES, parent_nodes_per_move=NODES, child_nodes_per_move=NODES, max_depth=MAX_DEPTH, tt_megabytes=TT_MEGABYTES, opening_seed=SELECTION_SEED, opening_count=2, min_plies=MIN_PLIES, max_plies=MAX_PLIES, workers=1)
    caps = ArenaExecutionCaps(per_game_wall_seconds=3600, per_game_nodes=262144, per_game_plies=512, max_stage_games=4, max_concurrent_games=1, stage_wall_seconds=3600, logical_cpu_count=4)
    def pause_after_first_pair() -> bool:
        # Preserve the v2 progress identity and stop before scheduling pair 1
        # once the first role-swapped pair is atomically complete.
        return all((ARENA2_PROGRESS / f"game-000000-owner-{owner}.json").is_file() for owner in (0, 1))
    run = run_arena_game_resumable(compiled, native, parent, candidate, config, progress_dir=ARENA2_PROGRESS, openings=openings, capture_search_metrics=True, caps=caps, stage_id="f82-c2-arena2", pause_requested=pause_after_first_pair)
    result = {"schema": "generic-chess-f82-c2-arena2-v2", "status": run.status, "candidate_checkpoint_id": candidate.checkpoint_id, "candidate_model_sha256": descriptor["candidate_model_sha256"], "parent_checkpoint_id": PARENT_CHECKPOINT_ID, "allocation_sha256": allocation["allocation_sha256"], "corpus_id": openings.corpus_id, "config": asdict(config), "execution_caps": asdict(caps), "completed_games": run.completed_games, "completed_pairs": run.completed_pairs, "total_games": run.total_games, "reason": run.reason}
    _atomic_json(ARENA2_RESULT_PATH, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precompute-only", action="store_true")
    parser.add_argument("--run-c2", action="store_true")
    parser.add_argument("--materialize-candidate", action="store_true")
    parser.add_argument("--run-arena2", action="store_true")
    parser.add_argument("--candidate-artifact", type=Path, default=CANDIDATE_ARTIFACT)
    parser.add_argument("--allocation", type=Path, default=ALLOCATION_PATH)
    args = parser.parse_args()
    allocation = precompute_allocation()
    if args.allocation != ALLOCATION_PATH:
        allocation = json.loads(args.allocation.read_text(encoding="utf-8"))
    if args.materialize_candidate:
        print(json.dumps(materialize_candidate(allocation, args.candidate_artifact), sort_keys=True), flush=True)
        return
    if args.run_arena2:
        print(json.dumps(run_arena2(allocation, args.candidate_artifact), sort_keys=True), flush=True)
        return
    if args.run_c2:
        result = run_fit_and_write_result(allocation)
        print(json.dumps({"status": result["status"], "candidate_checkpoint_id": result["candidate_checkpoint_id"], "candidate_model_sha256": result["candidate_model_sha256"], "chosen_alpha": result["backtracking"]["chosen_alpha"]}, sort_keys=True), flush=True)
    else:
        print(json.dumps({"status": allocation["status"], "allocation_path": str(ALLOCATION_PATH.relative_to(ROOT)).replace("\\", "/"), "allocation_sha256": allocation["allocation_sha256"], "total_arena_games": allocation["resource_envelope"]["total_arena_games"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
