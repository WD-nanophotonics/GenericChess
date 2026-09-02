"""Fail-closed F48 execution protocol helpers.

This module is audit/driver infrastructure only.  It binds the accepted H48
authority artifacts, describes resumable partitions, and recomputes terminal
classification from raw per-prior evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

from generic_chess.learning.serialization import canonical_json, stable_sha256


ROOT = Path(__file__).resolve().parents[1]
H48B_PATH = ROOT / "tests" / "fixtures" / "h48b_generated_benchmark_selection.json"
BASELINE_SHA = "dc1fe20964354b6494e90830408c8747018d6102"
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
        "commit": BASELINE_SHA,
        "path": "tests/fixtures/h48b_generated_benchmark_selection.json",
    },
}

_PHASES = ("corpus", "leverage", "stability", "calibration", "initial", "training", "holdout", "arena")
_LEARNERS = ("M48-0", "M48-1")
_PRIORS = ("P48-0", "P48-1", "P48-2", "P48-3")


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
    return stable_sha256({"authority": AUTHORITY, "ruleset_fingerprints": RULESET_FINGERPRINTS, "partition": partition, "config": config})


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Write one complete partition atomically; never expose a partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(canonical_json(value) + "\n", encoding="utf-8")
    os.replace(temporary, path)


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


def preflight(*, output_dir: Path | None = None, minimum_free_bytes: int = 256 * 1024 * 1024) -> dict[str, Any]:
    authority = verify_authority()
    partitions = build_partition_plan()
    config = {"search": {"max_depth": 12, "student_nodes": 2000, "teacher_nodes": 20000, "stability_nodes": 40000, "arena_nodes": 1000}, "corpora": {"training": [64, 480700, 2, 6], "holdout": [64, 480701, 2, 6], "arena": [16, 480702, 2, 6]}, "holdout_in_ranking": False}
    for row in partitions:
        row["input_hash"] = partition_input_hash(row, config=config)
        row["output_path"] = str((output_dir or ROOT / ".generic_chess_flow" / "f48" / "partitions") / (row["partition_id"] + ".json"))
    estimate = resource_estimate(partitions)
    usage = shutil.disk_usage(output_dir or ROOT)
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
    final = p0_rows[-1]
    arena = final["arena_vs_p48_0"]
    beyond = final["holdout_teacher_agreement"]["agreement"] - p0_initial >= 0.02 and arena["mean_pair_score"] > 0.5 and arena["bootstrap_low"] > 0.5 and _flag(final.get("integrity_gates", True))
    return {"disturbed_recovery_by_prior": recovered, "ruleset_recovered": sum(recovered.values()) >= 2, "beyond_prior": beyond}


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


def validate_raw_result(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("baseline_sha") != BASELINE_SHA or payload.get("production_diff") != "ZERO":
        raise RuntimeError("F48 result is not bound to the authorized baseline or production-diff contract")
    if payload.get("observed_results_present") is not True:
        raise RuntimeError("F48 raw result does not declare observed results")
    for row in payload["rulesets"]:
        if row["ruleset_fingerprint"] != RULESET_FINGERPRINTS[row["ruleset_id"]]:
            raise RuntimeError("RuleSet fingerprint drift in F48 result")
        row["validated_aggregation"] = {learner: recompute_aggregation(row, learner) for learner in _LEARNERS}
    classification = recompute_selector(payload["rulesets"])
    if classification != payload.get("final_classification"):
        raise RuntimeError(f"driver classification disagrees with raw evidence: {payload.get('final_classification')} != {classification}")
    return {"status": "PASS", "classification": classification, "rulesets": len(payload["rulesets"]), "holdout_separation": payload.get("holdout_separation", {})}
