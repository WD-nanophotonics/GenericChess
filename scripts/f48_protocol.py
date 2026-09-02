"""Fail-closed F48 execution protocol helpers.

This module is audit/driver infrastructure only.  It binds the accepted H48
authority artifacts, describes resumable partitions, and recomputes terminal
classification from raw per-prior evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

from generic_chess.learning.serialization import canonical_json, stable_sha256


ROOT = Path(__file__).resolve().parents[1]
H48B_PATH = ROOT / "tests" / "fixtures" / "h48b_generated_benchmark_selection.json"
H48B_BASELINE_SHA = "dc1fe20964354b6494e90830408c8747018d6102"
BASELINE_SHA = "742bc536f0ae2ed44e28c23b43b71a3ca859fb9f"
H48C_CHECKPOINT_SHA = BASELINE_SHA
H48C_PATH = ROOT / "tests" / "fixtures" / "h48c_corpus_disjointness_resolution.json"
H48C_COLLISION_PATH = ROOT / "tests" / "fixtures" / "h48c_corpus_disjointness_collision_keys.json"
H48B_SELECTED_FINGERPRINT = "9f7e7201a19f8f0ee6c0eacc766c2ac3a6c313e06bbc960d5d6dfb89137db923"
RULESET_FINGERPRINTS = {
    "A_CANONICAL_WESTERN_CHESS": "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35",
    "B_CANONICAL_STANDARD_SHOGI": "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
    "C_H48B_SELECTED_GENERATED": H48B_SELECTED_FINGERPRINT,
}

AUTHORITY = {
    "h48a": {
        "commit": "5446ae832aa518fa5ca544c75131bb08575a4177",
        "path": "tests/fixtures/h48a_learnable_material_recovery_manifest.json",
        "sha256": "684e33d261e08b89b74187e3b7fbcc02e514148869366dafcb155aa459214490",
    },
    "h48r1a": {
        "commit": "7e2f17bdc7ac46aabaa8b1a139c5866f1b0689ab",
        "path": "tests/fixtures/h48r1a_experimental_degrees_of_freedom_manifest.json",
        "sha256": "cfc9db0c0b25433a6b6c77f0adf41a7b0132dc017daf277f2467edab0270b3cf",
    },
    "h48r2a": {
        "commit": "d02212e85e9e0b50a946ec74b21e45a315dcb6d8",
        "path": "tests/fixtures/h48r2a_executable_training_screening_manifest.json",
        "sha256": "9db3a74f5e942e0c4bd89c99d8e275e1b1ce5273ce39dac5de0679d7e3dcdbb9",
    },
    "h48b": {
        "commit": H48B_BASELINE_SHA,
        "path": "tests/fixtures/h48b_generated_benchmark_selection.json",
    },
    "h48c": {
        "commit": H48C_CHECKPOINT_SHA,
        "path": "tests/fixtures/h48c_corpus_disjointness_resolution.json",
        "sha256": "ca7473e2e684f473060d0de82a13e853e3059591917c6fd3a4a0e0bfad7a9b01",
    },
}

_PHASES = ("corpus", "leverage", "stability", "calibration", "initial", "training", "holdout", "arena")
_LEARNERS = ("M48-0", "M48-1")
_PRIORS = ("P48-0", "P48-1", "P48-2", "P48-3")
CLASSIFICATION_BOUNDARY = {
    "TDLEAF_MATERIAL_RECOVERY_SUPPORTED": "F49_LEARNABLE_MATERIAL_CALIBRATION_INTEGRATION",
    "SEARCH_AWARE_MATERIAL_EVOLUTION_SUPPORTED": "F49_SEARCH_AWARE_CALIBRATION_INTEGRATION",
    "COLD_START_RECOVERY_SUPPORTED": "F49_COLD_START_LEARNING_PIPELINE",
    "LEARNING_DIRECTION_FAILURE": "F49_GENERIC_LEARNER_REDESIGN",
    "MATERIAL_ONLY_LEVERAGE_INSUFFICIENT": "F49_EVALUATION_FEATURE_EXPANSION_DIAGNOSIS",
    "SEARCH_ENGINE_LIMITS_LEARNING": "F49_NATIVE_SEARCH_STRENGTH_REASSESSMENT",
    "MIXED_OR_UNRESOLVED": "F49_LEARNING_ARCHITECTURE_REASSESSMENT",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_blob_sha(ref: str, path: str) -> str:
    raw = subprocess.run(
        ["git", "cat-file", "blob", f"{ref}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return _sha256_bytes(raw)


def _manifest_sha(value: dict[str, Any]) -> str:
    unsigned = {key: item for key, item in value.items() if key != "manifest_sha256"}
    return _sha256_bytes(canonical_json(unsigned).encode("utf-8"))


def verify_authority() -> dict[str, Any]:
    """Verify immutable authority files and H48B's pre-learning selection."""
    bound: dict[str, Any] = {}
    for name, spec in AUTHORITY.items():
        path = ROOT / spec["path"]
        if not path.is_file():
            raise RuntimeError(f"missing authority artifact: {spec['path']}")
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = spec.get("sha256") or _sha256_bytes(path.read_bytes())
        actual = _manifest_sha(data) if "manifest_sha256" in data else _sha256_bytes(path.read_bytes())
        if actual != expected:
            raise RuntimeError(f"authority hash mismatch for {name}: {actual} != {expected}")
        historical = _git_blob_sha(spec["commit"], spec["path"])
        if "manifest_sha256" in data:
            if historical != _sha256_bytes(path.read_bytes()):
                raise RuntimeError(f"working authority drift for {name}")
        else:
            historical_raw = subprocess.run(["git", "cat-file", "blob", f"{spec['commit']}:{spec['path']}"], cwd=ROOT, capture_output=True, check=True).stdout
            historical_data = json.loads(historical_raw.decode("utf-8"))
            if canonical_json(historical_data) != canonical_json(data):
                raise RuntimeError(f"working authority semantic drift for {name}")
        bound[name] = {"commit": spec["commit"], "path": spec["path"], "sha256": actual, "historical_blob_sha256": historical}

    h48b = json.loads(H48B_PATH.read_text(encoding="utf-8"))
    selected = h48b.get("selection", {}).get("selected", {})
    if selected.get("index") != 9 or selected.get("ruleset_fingerprint") != H48B_SELECTED_FINGERPRINT:
        raise RuntimeError("H48B selected benchmark binding is not the accepted pre-learning selection")
    if h48b.get("learned_checkpoint_input") is not False or h48b.get("selection_completed_before_learning") is not True:
        raise RuntimeError("H48B is not marked as a pre-learning selection")
    return {"artifacts": bound, "selected_h48b": selected}


def load_h48c_resolution() -> dict[str, Any]:
    """Load and validate the accepted H48C seed-resolution authority."""
    if not H48C_PATH.is_file() or not H48C_COLLISION_PATH.is_file():
        raise RuntimeError("missing H48C resolution authority")
    resolution = json.loads(H48C_PATH.read_text(encoding="utf-8"))
    collision_auxiliary = json.loads(H48C_COLLISION_PATH.read_text(encoding="utf-8"))
    if resolution.get("status") != "PASS":
        raise RuntimeError("H48C resolution is not accepted")
    if resolution.get("parent_h48r3a_sha") != "d829f14e4c7c939bb1c2e06bc8b7d2b6f4b9e510":
        raise RuntimeError("H48C parent binding drift")
    if resolution.get("ruleset_fingerprints") != RULESET_FINGERPRINTS:
        raise RuntimeError("H48C RuleSet fingerprint binding drift")
    if resolution.get("collision_auxiliary_path") != str(H48C_COLLISION_PATH.relative_to(ROOT)):
        raise RuntimeError("H48C collision auxiliary path drift")
    if stable_sha256(collision_auxiliary) != resolution.get("collision_auxiliary_sha256"):
        raise RuntimeError("H48C collision auxiliary hash drift")
    if any(resolution.get(name) is not False for name in ("evaluator_invoked", "search_invoked", "learner_invoked", "selfplay_invoked", "arena_games_invoked")):
        raise RuntimeError("H48C contains a forbidden execution flag")
    return resolution


def resolved_corpus_config() -> dict[str, Any]:
    """Return execution corpus settings sourced only from H48C."""
    resolution = load_h48c_resolution()
    seeds = resolution["resolved_seed_triple"]
    return {
        "training": [64, seeds["training"], 2, 6],
        "holdout": [64, seeds["holdout"], 2, 6],
        "arena": [16, seeds["arena"], 2, 6],
    }


def partition_id(*, ruleset_id: str, prior_id: str = "none", learner_id: str = "none", generation: int = 0, phase: str) -> str:
    if phase not in _PHASES:
        raise ValueError(f"unknown F48 phase: {phase}")
    safe = lambda value: value.replace("_", "-").replace("/", "-")
    return f"F48.{safe(ruleset_id)}.{safe(prior_id)}.{safe(learner_id)}.G{generation:02d}.{phase}"


def build_partition_plan() -> list[dict[str, Any]]:
    """Return the complete deterministic partition inventory."""
    rows: list[dict[str, Any]] = []
    for ruleset_id in RULESET_FINGERPRINTS:
        rows.extend({"partition_id": partition_id(ruleset_id=ruleset_id, phase=phase), "ruleset_id": ruleset_id, "prior_id": "none", "learner_id": "none", "generation": 0, "phase": phase} for phase in ("corpus", "leverage", "stability"))
        for prior_id in _PRIORS:
            rows.append({"partition_id": partition_id(ruleset_id=ruleset_id, prior_id=prior_id, phase="calibration"), "ruleset_id": ruleset_id, "prior_id": prior_id, "learner_id": "none", "generation": 0, "phase": "calibration"})
            rows.append({"partition_id": partition_id(ruleset_id=ruleset_id, prior_id=prior_id, phase="initial"), "ruleset_id": ruleset_id, "prior_id": prior_id, "learner_id": "none", "generation": 0, "phase": "initial"})
            for learner_id in _LEARNERS:
                for generation in (1, 2, 3):
                    for phase in ("training", "holdout", "arena"):
                        rows.append({"partition_id": partition_id(ruleset_id=ruleset_id, prior_id=prior_id, learner_id=learner_id, generation=generation, phase=phase), "ruleset_id": ruleset_id, "prior_id": prior_id, "learner_id": learner_id, "generation": generation, "phase": phase})
    return rows


def partition_input_hash(partition: dict[str, Any], *, config: dict[str, Any]) -> str:
    bound_partition = {key: value for key, value in partition.items() if key != "input_hash"}
    return stable_sha256({"authority": AUTHORITY, "ruleset_fingerprints": RULESET_FINGERPRINTS, "partition": bound_partition, "config": config})


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Write one complete partition atomically; never expose a partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(canonical_json(value) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def guard_corpus_identities(
    *,
    ruleset_id: str,
    ruleset_fingerprint: str,
    identities: dict[str, set[str]],
    authority_hash: str,
    config_hash: str,
    input_hash: str,
    proceed: Any,
) -> Any:
    """Record a collision witness and abort before any later partition.

    ``proceed`` is deliberately invoked only after all pairwise identity
    checks pass.  The witness is ignored runtime evidence, never a Git input.
    """
    collisions = []
    for left, right in (("training", "holdout"), ("training", "arena"), ("holdout", "arena")):
        shared = sorted(identities[left] & identities[right])
        if shared:
            collisions.append({"left": left, "right": right, "keys": shared})
    if collisions:
        witness_path = ROOT / ".generic_chess_flow" / "f48" / "collision-witnesses" / f"{ruleset_id}.json"
        atomic_write_json(witness_path, {"kind": "F48_CORPUS_IDENTITY_COLLISION_WITNESS", "status": "FAIL_CLOSED_COLLISION", "ruleset_id": ruleset_id, "ruleset_fingerprint": ruleset_fingerprint, "collisions": collisions, "authority_hash": authority_hash, "config_hash": config_hash, "input_hash": input_hash})
        raise RuntimeError(f"corpus identity collision for {ruleset_id}; witness={witness_path}")
    ledger = {name: sorted(values) for name, values in sorted(identities.items())}
    return proceed({"sets": ledger, "counts": {name: len(values) for name, values in sorted(identities.items())}, "pairwise_disjoint": True})


def resource_estimate(partitions: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = list(partitions or build_partition_plan())
    search_units = {
        "prerequisites": 3 * 64 * 2 * 2,
        "initial": 3 * 4 * 64,
        "tdleaf_training": 3 * 4 * 3 * 16 * 40,
        "m48_training_ranking": 3 * 4 * 3 * 8 * 64,
        "holdout_evaluation": 3 * 4 * 2 * 3 * 64,
        "arena_games": 3 * 4 * 2 * 3 * 16 * 2,
    }
    total_units = sum(search_units.values())
    estimated_runtime_seconds = total_units * 0.20
    estimated_evidence_bytes = max(1_048_576, len(rows) * 12_288)
    return {"partition_count": len(rows), "search_units": search_units, "total_search_units": total_units, "estimated_runtime_seconds": estimated_runtime_seconds, "estimated_evidence_bytes": estimated_evidence_bytes}


def preflight(*, output_dir: Path | None = None, partition_root: Path | None = None, minimum_free_bytes: int = 256 * 1024 * 1024) -> dict[str, Any]:
    authority = verify_authority()
    partitions = build_partition_plan()
    config = {"search": {"max_depth": 12, "student_nodes": 2000, "teacher_nodes": 20000, "stability_nodes": 40000, "arena_nodes": 1000}, "corpora": resolved_corpus_config(), "h48c": {"checkpoint_sha": H48C_CHECKPOINT_SHA, "resolution_fixture": str(H48C_PATH.relative_to(ROOT)), "collision_auxiliary": str(H48C_COLLISION_PATH.relative_to(ROOT)), "collision_auxiliary_sha256": load_h48c_resolution()["collision_auxiliary_sha256"]}, "holdout_in_ranking": False}
    relative_partition_root = partition_root.relative_to(ROOT) if partition_root is not None else Path(".generic_chess_flow") / "f48" / "partitions"
    for row in partitions:
        row["output_path"] = str(relative_partition_root / (row["partition_id"] + ".json"))
        row["input_hash"] = partition_input_hash(row, config=config)
    estimate = resource_estimate(partitions)
    capacity_path = output_dir if output_dir is not None and output_dir.exists() else ROOT
    usage = shutil.disk_usage(capacity_path)
    capacity = {"free_bytes": usage.free, "required_free_bytes": max(minimum_free_bytes, estimate["estimated_evidence_bytes"] * 2), "pass": usage.free >= max(minimum_free_bytes, estimate["estimated_evidence_bytes"] * 2)}
    if not capacity["pass"]:
        raise RuntimeError("F48 preflight capacity guard failed")
    return {"kind": "F48_PREFLIGHT_PLAN", "baseline_sha": BASELINE_SHA, "authority": authority, "ruleset_fingerprints": RULESET_FINGERPRINTS, "config": config, "holdout_separation": {"holdout_in_training": False, "holdout_in_ranking": False, "holdout_in_arena_opening_generation": False, "mechanically_checked": True}, "partitions": partitions, "resource_estimate": estimate, "capacity": capacity, "status": "PASS"}


def _flag(value: Any) -> bool:
    return value is True


def recompute_aggregation(ruleset: dict[str, Any], learner_id: str) -> dict[str, Any]:
    """Recompute recovery and beyond-prior gates from raw learner rows."""
    initial = ruleset["initial_competence"]
    learner = ruleset["learners"][learner_id]
    p0_initial = initial["P48-0"]["holdout_vs_p0_teacher"]["agreement"]
    raw_by_prior = learner["by_prior"]
    recovered: dict[str, bool] = {}
    for prior_id in ("P48-1", "P48-2", "P48-3"):
        threshold = 0.90 * p0_initial
        disturbed = initial[prior_id]["holdout_vs_p0_teacher"]["agreement"]
        recovered[prior_id] = any(
            row["holdout_teacher_agreement"]["agreement"] >= threshold
            and row["holdout_teacher_agreement"]["agreement"] - disturbed >= 0.05
            and not _flag(row.get("catastrophic_arena_regression"))
            for row in raw_by_prior[prior_id]["generations"]
        )
    p0_rows = raw_by_prior["P48-0"]["generations"]
    beyond_by_generation = {}
    for row in p0_rows:
        arena = row["arena_vs_p48_0"]
        beyond_by_generation[str(row["generation"])] = row["holdout_teacher_agreement"]["agreement"] - p0_initial >= 0.02 and arena["mean_pair_score"] > 0.5 and arena["bootstrap_low"] > 0.5 and _flag(row.get("integrity_gates", True))
    qualifying = [int(generation) for generation, passed in beyond_by_generation.items() if passed]
    return {"disturbed_recovery_by_prior": recovered, "ruleset_recovered": sum(recovered.values()) >= 2, "beyond_prior_by_generation": beyond_by_generation, "beyond_prior": bool(qualifying), "first_beyond_prior_generation": min(qualifying) if qualifying else None}


def recompute_selector(rulesets: list[dict[str, Any]]) -> str:
    admissible = [row for row in rulesets if row["prerequisites"]["admissible"]]
    if len(admissible) < 2:
        leverage_bad = any(not row["prerequisites"]["leverage_pass"] for row in rulesets)
        stability_bad = any(not row["prerequisites"]["teacher_stability_pass"] for row in rulesets)
        if leverage_bad and stability_bad:
            return "MIXED_OR_UNRESOLVED"
        if leverage_bad:
            return "MATERIAL_ONLY_LEVERAGE_INSUFFICIENT"
        return "SEARCH_ENGINE_LIMITS_LEARNING"
    aggregation = {learner: [recompute_aggregation(row, learner) for row in admissible] for learner in _LEARNERS}
    recovered = {learner: sum(item["ruleset_recovered"] for item in values) >= 2 for learner, values in aggregation.items()}
    beyond = {learner: sum(item["beyond_prior"] and item["ruleset_recovered"] for item in values) >= 2 for learner, values in aggregation.items()}
    if any(recovered.values()) and not any(recovered[learner] and beyond[learner] for learner in _LEARNERS):
        return "COLD_START_RECOVERY_SUPPORTED"
    if recovered["M48-0"] and beyond["M48-0"]:
        return "TDLEAF_MATERIAL_RECOVERY_SUPPORTED"
    if recovered["M48-1"] and beyond["M48-1"]:
        return "SEARCH_AWARE_MATERIAL_EVOLUTION_SUPPORTED"
    if not any(recovered.values()):
        return "LEARNING_DIRECTION_FAILURE"
    return "MIXED_OR_UNRESOLVED"


def next_boundary_for(classification: str) -> str:
    try:
        return CLASSIFICATION_BOUNDARY[classification]
    except KeyError as exc:
        raise RuntimeError(f"unknown F48 classification: {classification}") from exc


def _validate_r4_authoritative_inventory(payload: dict[str, Any]) -> None:
    """Validate the six content-addressed prerequisite files independently."""
    root_value = payload.get("r4_partition_root")
    if not isinstance(root_value, str) or not root_value.replace("\\", "/").startswith(".generic_chess_flow/f48-r4-prerequisite-closure-final"):
        raise RuntimeError("F48 R4 partition root binding is missing or incorrect")
    root = (ROOT / Path(root_value)).resolve()
    if not root.is_dir():
        raise RuntimeError("F48 R4 partition root is missing")
    forbidden = {"initial", "training", "holdout", "arena"}
    forbidden_paths = [path for path in root.rglob("*.json") if path.is_file() and path.stem.rsplit(".", 1)[-1] in forbidden]
    if forbidden_paths:
        raise RuntimeError("F48 R4 contains a forbidden post-prerequisite partition")
    inventory = payload.get("authoritative_partition_inventory")
    if not isinstance(inventory, list):
        raise RuntimeError("F48 R4 authoritative partition inventory is missing")
    expected_keys = {(ruleset_id, phase) for ruleset_id in RULESET_FINGERPRINTS for phase in ("corpus", "leverage")}
    actual_keys = {(item.get("ruleset_id"), item.get("phase")) for item in inventory if isinstance(item, dict)}
    if len(inventory) != 6 or actual_keys != expected_keys:
        raise RuntimeError("F48 R4 authoritative partition inventory is incomplete")
    for item in inventory:
        try:
            path = (ROOT / Path(item["path"])).resolve()
            relative = path.relative_to(root)
            if path not in {candidate.resolve() for candidate in root.glob("*.json")}:
                raise RuntimeError("F48 R4 authoritative inventory path is not a root partition")
            actual_sha = _sha256_bytes(path.read_bytes())
            if actual_sha != item.get("sha256"):
                raise RuntimeError("F48 R4 authoritative partition hash mismatch")
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved.get("partition_id") != item.get("partition_id"):
                raise RuntimeError("F48 R4 authoritative partition identity mismatch")
            if saved.get("input_hash") != item.get("input_hash"):
                raise RuntimeError("F48 R4 authoritative partition input binding mismatch")
            if saved["partition_id"].rsplit(".", 1)[-1] != item.get("phase"):
                raise RuntimeError("F48 R4 authoritative partition phase mismatch")
            if relative.name != Path(item["path"]).name:
                raise RuntimeError("F48 R4 authoritative partition path mismatch")
        except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("F48 R4 authoritative partition inventory is invalid") from exc
    for row in payload["rulesets"]:
        entries = [item for item in inventory if item["ruleset_id"] == row["ruleset_id"]]
        leverage_entry = next(item for item in entries if item["phase"] == "leverage")
        leverage = json.loads((ROOT / leverage_entry["path"]).read_text(encoding="utf-8"))["data"]
        rows = leverage["material_leverage"]["rows"]
        valid_perturbations = sum(not item.get("skipped", False) for item in rows)
        if leverage["material_leverage"]["valid_perturbations"] != valid_perturbations:
            raise RuntimeError("F48 R4 raw leverage inventory count mismatch")
        expected_searches = 64 + 64 + 64 + 64 * valid_perturbations
        expected_tables = 3 + valid_perturbations
        expected_budgets = {"20000": 64, "40000": 64, "2000": 64 + 64 * valid_perturbations}
        efficiency = row.get("efficiency", {})
        if efficiency.get("search_count") != expected_searches:
            raise RuntimeError("F48 R4 search count is not derived from raw prerequisite inventory")
        if efficiency.get("evaluation_table_compile_count") != expected_tables:
            raise RuntimeError("F48 R4 evaluation-table count is not derived from raw prerequisite inventory")
        if efficiency.get("engine_creation_count") != expected_searches:
            raise RuntimeError("F48 R4 engine count is not derived from raw prerequisite inventory")
        if efficiency.get("requested_node_budgets") != expected_budgets or efficiency.get("selfplay_calls") != 0:
            raise RuntimeError("F48 R4 requested-budget or self-play ledger mismatch")
        total = efficiency.get("total_authoritative_prerequisite_cost_seconds")
        search = efficiency.get("search_wall_seconds")
        if not isinstance(total, (int, float)) or not isinstance(search, (int, float)) or total <= 0 or search < 0 or search > total:
            raise RuntimeError("F48 R4 authoritative timing ledger is invalid")
        expected_outside_fraction = (total - search) / total
        if not math.isclose(efficiency.get("fraction_outside_native_search", -1), expected_outside_fraction, rel_tol=1e-9, abs_tol=1e-9):
            raise RuntimeError("F48 R4 outside-native-search fraction is not derived")
        if efficiency.get("learning_fraction_status") != "NOT_APPLICABLE_PREREQUISITE_ONLY" or efficiency.get("non_native_learning_fraction") != 0.0:
            raise RuntimeError("F48 R4 learning fraction is not marked not applicable")


def validate_raw_result(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("baseline_sha") != BASELINE_SHA or payload.get("production_diff") != "ZERO":
        raise RuntimeError("F48 result is not bound to the authorized baseline or production-diff contract")
    if payload.get("observed_results_present") is not True:
        raise RuntimeError("F48 raw result does not declare observed results")
    for row in payload["rulesets"]:
        if row["ruleset_fingerprint"] != RULESET_FINGERPRINTS[row["ruleset_id"]]:
            raise RuntimeError("RuleSet fingerprint drift in F48 result")
    classification = recompute_selector(payload["rulesets"])
    if classification != payload.get("final_classification"):
        raise RuntimeError(f"driver classification disagrees with raw evidence: {payload.get('final_classification')} != {classification}")
    if payload.get("next_boundary") != next_boundary_for(classification):
        raise RuntimeError("F48 classification-to-boundary mapping mismatch")
    equivalence = payload.get("h48c_execution_equivalence", {})
    if set(equivalence) != set(RULESET_FINGERPRINTS) or any(not row.get("passed") for row in equivalence.values()):
        raise RuntimeError("H48C execution equivalence is incomplete")
    admissible_count = sum(bool(row["prerequisites"].get("admissible")) for row in payload["rulesets"])
    if payload.get("admissible_ruleset_count") != admissible_count:
        raise RuntimeError("F48 admissible RuleSet count mismatch")
    if admissible_count >= 2:
        for row in payload["rulesets"]:
            row["validated_aggregation"] = {learner: recompute_aggregation(row, learner) for learner in _LEARNERS}
    if admissible_count < 2:
        if payload.get("F49_status") != "NOT_STARTED":
            raise RuntimeError("F49 status is not explicitly NOT_STARTED")
        _validate_r4_authoritative_inventory(payload)
        if payload.get("early_stop_status") != "NOT_RUN_GLOBAL_PREREQUISITE_EARLY_STOP":
            raise RuntimeError("F48 global prerequisite early-stop status missing")
        for row in payload["rulesets"]:
            if row.get("initial_competence_status") != "NOT_RUN_GLOBAL_PREREQUISITE_EARLY_STOP":
                raise RuntimeError("initial competence evidence present after global prerequisite stop")
            if "initial_competence" in row:
                raise RuntimeError("initial competence evidence present after global prerequisite stop")
            if row.get("learner_statuses") != {learner: "NOT_RUN_PREREQUISITE_SHORTAGE" for learner in _LEARNERS}:
                raise RuntimeError("learner evidence present after global prerequisite stop")
            if row.get("executed_partitions", {}).get("initial") is not False or row.get("executed_partitions", {}).get("training") is not False:
                raise RuntimeError("initial/training partition executed after global prerequisite stop")
            if row.get("efficiency", {}).get("ledger_scope") != "TOTAL_AUTHORITATIVE_PREREQUISITE_COST":
                raise RuntimeError("F48 efficiency ledger is not authoritative total work")
    return {"status": "PASS", "classification": classification, "rulesets": len(payload["rulesets"]), "holdout_separation": payload.get("holdout_separation", {})}
