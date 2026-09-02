"""Freeze the implementation and preflight boundary for the F49 diagnostic run.

This module is intentionally pre-measurement.  It verifies the accepted H49
authority chain and the accepted F48 control inputs, but it never invokes a
search, evaluator, learner, or F49 corpus-result writer.  The resulting
manifest is a durable description of the frozen runner and its partition
identity contract; it contains no observed corpus or search result.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

try:
    from scripts import f48_protocol, f49_protocol
except ImportError:  # direct ``python scripts/audit_*.py`` execution
    import f48_protocol  # type: ignore[no-redef]
    import f49_protocol  # type: ignore[no-redef]

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.ai.evaluation.config import EvaluationConfig, config_hash
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.learning.diagnostics import DiagnosticPosition, generate_diagnostic_corpus
from generic_chess.learning.features import non_anchor_type_ids
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import canonical_json, stable_sha256
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.engine import NativeSearchEngine
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49b_f49_diagnostic_runner_freeze_manifest.json"
SOURCE_PATH = ROOT / "scripts" / "audit_f49_learning_signal_architecture.py"
F48_RESULTS_PATH = ROOT / "tests" / "fixtures" / "f48_learnable_material_recovery_results.json"

H49B_KIND = "H49B_F49_DIAGNOSTIC_RUNNER_FREEZE"
H49B_WORK_ORDER_ID = "GENERICCHESS-F49-DIAGNOSTIC-MEASUREMENTS-AFTER-H49R4A"
H49B_SHA = "ad0a8cf02f645b35bdc4727b856595624c1065a8"
H49B_MANIFEST_SHA = "9de9d7d456bce18f3d2b6aecc4a40ac704aa86eae496dcfb0a146bb39cf3314e"
H49B_R1_KIND = "H49B-R1_F49_DIAGNOSTIC_RUNNER_FREEZE"
H49B_R1_WORK_ORDER_ID = "GENERICCHESS-F49-H49B-CORRECTIVE-R1-MEASUREMENT-RUNNER-CLOSURE"
H49B_R1_SHA = "42c521554c02e91bd62781c8dad7baabcbf6db1b"
H49B_R1_MANIFEST_SHA = "16dab8f5bf549849e8fe07fb81a46268b39c9d3a6c263311c5c904ceead62fc7"
H49B_R2_KIND = "H49B-R2_F49_DIAGNOSTIC_RUNNER_FREEZE"
H49B_R2_WORK_ORDER_ID = "GENERICCHESS-F49-H49B-CORRECTIVE-R2-RUNNER-SEMANTICS-AND-RESUMABILITY-CLOSURE"
H49R4A_SHA = "6f1038d91f9667625a59c73a97aec77c01e9f817"
H49R4A_MANIFEST_SHA = "929a7e9fc2d04cb24a15b66eb07e97966baef83048c755c9f2bc900320f7a2b0"
H49R3A_SOURCE_TREE_SHA = "10b3752af976844908a773ef3f017d92c2004b29fc82e9ffaf7c21acccd7bff7"
H49R3A_NATIVE_SHA = "ae6358d7caf71b3e5d33d4673c61b75fce3342ad25ae5d6482f29bf4761a1614"

H49_AUTHORITY = {
    "H49A": {
        "commit": "93eee26a090c5a83487046b9165356fa1187b44e",
        "path": "tests/fixtures/h49a_learning_signal_architecture_protocol_manifest.json",
        "manifest_sha256": "e294a27ed1a4ea4c03578321b1beeb61ba233aafe19fcad98e968a016ed14f90",
    },
    "H49R1A": {
        "commit": "cd43e9c97a04c5279ff9791ecf15270756b2f6fa",
        "path": "tests/fixtures/h49r1a_executable_diagnostic_protocol_manifest.json",
        "manifest_sha256": "57d2d189712138efa352b8e93edae83cb4938d74c5140717976aecf722a31215",
    },
    "H49R2A": {
        "commit": "628c4c5a34f547a413fb56d5295b71d2f4dcf1f1",
        "path": "tests/fixtures/h49r2a_nonmaterial_execution_protocol_manifest.json",
        "manifest_sha256": "9b6b98997b7656f845283b20297d325c83c8451c6da55255e3f481e638e9beaf",
    },
    "H49R3A": {
        "commit": f49_protocol.H49R3A_SHA,
        "path": "tests/fixtures/h49r3a_execution_dependency_and_ruleset_binding_manifest.json",
        "manifest_sha256": f49_protocol.H49R3A_MANIFEST_SHA,
    },
    "H49R4A": {
        "commit": H49R4A_SHA,
        "path": "tests/fixtures/h49r4a_nonmaterial_availability_and_selector_closure_manifest.json",
        "manifest_sha256": H49R4A_MANIFEST_SHA,
    },
}

P48_0_CHECKPOINTS = {
    "A_CANONICAL_WESTERN_CHESS": {
        "checkpoint_id": "86e8bacb6e3951544c41789f4b1eed5c47072bdbfaba77b4eb5376bc20dd3e56",
        "config_hash": "adfb0214d10474fc92effc3ed8a664bdb894aedf16140e937d3dc013a5a7e52f",
    },
    "B_CANONICAL_STANDARD_SHOGI": {
        "checkpoint_id": "918d0aafe1a9b68aeaf872db722cec17c7fd6da0b6213d86881bf6ec5d272298",
        "config_hash": "433032bd6ef193811808d7e332a771782dd8eb30d1c842a1cf3018680ffdd97e",
    },
    "C_H48B_SELECTED_GENERATED": {
        "checkpoint_id": "93e96b1b3448038a0d5bdc52c63f4176ce130f27d30fa1c0426c1948b0b9f423",
        "config_hash": "c7d6b56f2b05af9e64ce65a202f8c3fd65327ac7fd3f1b271fa742e1794a9cf1",
    },
}

CONTROL_CORPUS_EXPECTED = {
    "A_CANONICAL_WESTERN_CHESS": {
        "corpus_id": "21e79e6f617db06dec89229ea11ad2937228e513097ccd19228b6d852fd3fea5",
        "identity_set_hash": "3c400b59ce201d822cf0a07731f87965ac7bed7198fe24d731232a03dafe1e04",
        "identity_set_count": 34,
    },
    "B_CANONICAL_STANDARD_SHOGI": {
        "corpus_id": "d2d665ac08f4ddcb881f608836006a97967c8f05e8d1a9ded2a3237aa8e5c013",
        "identity_set_hash": "81e49c99f28153ca8a10f6f8d8e470079d19cdbd4b66b4a322aaf08b72baeba2",
        "identity_set_count": 32,
    },
    "C_H48B_SELECTED_GENERATED": {
        "corpus_id": "1172adc5c5f52a46d89e35a3c847c0539f7937c11531125692cddd7e37ffc9d7",
        "identity_set_hash": "e9932dc2e98ac172dc72bc8af47474e6178e84a789ded31727cbc6c6bb541001",
        "identity_set_count": 31,
    },
}

RULESET_IDS = tuple(f49_protocol.RULESET_FINGERPRINTS)
PARTITION_INPUT_FIELDS = (
    "H49B_runner_sha256",
    "H49R4A_manifest_sha256",
    "H49R3A_source_tree_aggregate_sha256",
    "native_binary_sha256",
    "ruleset_fingerprint",
    "corpus_id",
    "material_or_evaluator_config_or_checkpoint_id",
    "search_engine_route",
    "node_budget",
    "measurement_family",
)
PARTITION_ROUTES = {
    "EVALUATOR_NEUTRAL_CORE_CORPUS",
    "NATIVE_SEARCH_ENGINE_MATERIAL",
    "NATIVE_SEARCH_ENGINE_TEACHER",
    "PYTHON_ALPHABETA_FULL_EVALUATOR",
    "AUDIT_SELECTOR",
}
MEASUREMENT_FAMILIES = ("S49-M", "S49-E", "L49-0", "L49-1", "L49-2", "TEACHER", "PYTHON_NONMATERIAL", "SELECTOR")
R2_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49b_r2_f49_diagnostic_runner_freeze_manifest.json"
R1_PARTITION_INPUT_FIELDS = (
    "H49B_R1_runner_sha256",
    "H49R4A_manifest_sha256",
    "H49R3A_source_tree_aggregate_sha256",
    "native_binary_sha256",
    "ruleset_fingerprint",
    "corpus_id",
    "checkpoint_or_config_hash",
    "search_route",
    "node_budget",
    "measurement_family",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest_sha(value: dict[str, Any]) -> str:
    unsigned = {key: item for key, item in value.items() if key != "manifest_sha256"}
    return _sha256_bytes(canonical_json(unsigned).encode("utf-8"))


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(canonical_json(value) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _git_commit_exists(commit: str) -> None:
    subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, check=True, capture_output=True)


def _git_blob_sha256(ref: str, path: str) -> str:
    raw = subprocess.run(["git", "cat-file", "blob", f"{ref}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout
    return _sha256_bytes(raw)


def _require_zero_production_diff() -> None:
    result = subprocess.run(
        ["git", "diff", "--quiet", H49R4A_SHA, "HEAD", "--", "generic_chess"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError("H49B production diff is not ZERO")


def _load_h49_authority() -> dict[str, Any]:
    validators = {
        "H49A": f49_protocol.validate_h49a_manifest,
        "H49R1A": f49_protocol.validate_h49r1a_manifest,
        "H49R2A": f49_protocol.validate_h49r2a_manifest,
        "H49R3A": f49_protocol.validate_h49r3a_manifest,
        "H49R4A": f49_protocol.validate_h49r4a_manifest,
    }
    loaded: dict[str, Any] = {}
    for name, spec in H49_AUTHORITY.items():
        _git_commit_exists(spec["commit"])
        path = ROOT / spec["path"]
        if not path.is_file():
            raise RuntimeError(f"missing H49 authority: {spec['path']}")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if _manifest_sha(manifest) != spec["manifest_sha256"]:
            raise RuntimeError(f"H49 authority hash mismatch: {name}")
        validators[name](manifest)
        loaded[name] = {
            "commit": spec["commit"],
            "path": spec["path"],
            "manifest_sha256": spec["manifest_sha256"],
            "raw_sha256": _sha256_bytes(path.read_bytes()),
        }
    if loaded["H49R4A"]["commit"] != H49R4A_SHA:
        raise RuntimeError("H49R4A commit binding drift")
    return loaded


def _load_f48_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    authority = f48_protocol.verify_authority()
    resolution = f48_protocol.load_h48c_resolution()
    if resolution["resolved_seed_triple"] != {"training": 480700, "holdout": 480703, "arena": 480708}:
        raise RuntimeError("H49B H48C seed authority drift")
    result = json.loads(F48_RESULTS_PATH.read_text(encoding="utf-8"))
    if result.get("h48c_checkpoint_sha") != f48_protocol.H48C_CHECKPOINT_SHA or result.get("production_diff") != "ZERO":
        raise RuntimeError("H49B F48 durable result authority drift")
    for row in result.get("rulesets", []):
        ruleset_id = row["ruleset_id"]
        for field, expected in P48_0_CHECKPOINTS[ruleset_id].items():
            if row["priors"]["P48-0"].get(field) != expected:
                raise RuntimeError(f"H49B P48-0 {field} mismatch: {ruleset_id}")
    return authority, resolution


def _reconstruct_control_corpora(executions: dict[str, Any], resolution: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct only the accepted F48 holdout identities, never search."""
    output: dict[str, Any] = {}
    for ruleset_id, entry in executions.items():
        compiled = entry["legacy_transport"]
        openings = generate_arena_openings(compiled, count=16, seed=480703, min_plies=2, max_plies=6)
        corpus = generate_diagnostic_corpus(compiled, openings, count=64, seed=480703, min_plies=2, max_plies=6)
        identities = {position.position_key for position in corpus.positions}
        actual = {
            "corpus_id": corpus.corpus_id,
            "identity_set_hash": stable_sha256(sorted(identities)),
            "identity_set_count": len(identities),
        }
        expected = resolution["final_corpora"][ruleset_id]["holdout"]
        if actual != expected or actual != CONTROL_CORPUS_EXPECTED[ruleset_id]:
            raise RuntimeError(f"H49B F48_CONTROL discrepancy: {ruleset_id}")
        output[ruleset_id] = actual
    return output


def _partition_templates(runtime: dict[str, Any], p48: dict[str, Any]) -> list[dict[str, Any]]:
    templates = []
    families = ("S49-M", "S49-E", "L49-0", "L49-1", "L49-2", "TEACHER", "PYTHON_NONMATERIAL", "SELECTOR")
    corpus_slots = ("F48_CONTROL", "S49-M", "S49-E")
    for ruleset_id, fingerprint in f49_protocol.RULESET_FINGERPRINTS.items():
        for corpus_slot in corpus_slots:
            for family in families:
                corpus_id = CONTROL_CORPUS_EXPECTED[ruleset_id]["corpus_id"] if corpus_slot == "F48_CONTROL" else f"<generated-{corpus_slot}-corpus-id>"
                checkpoint = p48[ruleset_id]["checkpoint_id"] if family.startswith("L49") or family == "TEACHER" else "none"
                identity = {
                    "H49B_runner_sha256": _sha256_bytes(SOURCE_PATH.read_bytes()),
                    "H49R4A_manifest_sha256": H49R4A_MANIFEST_SHA,
                    "H49R3A_source_tree_aggregate_sha256": H49R3A_SOURCE_TREE_SHA,
                    "native_binary_sha256": runtime["native_module_sha256"],
                    "ruleset_fingerprint": fingerprint,
                    "corpus_id": corpus_id,
                    "material_or_evaluator_config_or_checkpoint_id": checkpoint,
                    "search_engine_route": "PLANNED_ONLY_NO_EXECUTION",
                    "node_budget": "PLANNED_ONLY_NO_EXECUTION",
                    "measurement_family": family,
                }
                templates.append({
                    "ruleset_id": ruleset_id,
                    "corpus_slot": corpus_slot,
                    "measurement_family": family,
                    "reusable_before_observation": corpus_slot == "F48_CONTROL",
                    "input_identity": identity,
                    "input_hash": stable_sha256(identity),
                    "observed_results_present": False,
                })
    return templates


def build_preflight_manifest() -> dict[str, Any]:
    h49 = _load_h49_authority()
    r3 = h49["H49R3A"]
    r3_manifest = json.loads((ROOT / r3["path"]).read_text(encoding="utf-8"))
    runtime = f49_protocol.current_native_runtime_provenance()
    if runtime != r3_manifest["native_runtime_provenance"] or runtime["native_module_sha256"] != H49R3A_NATIVE_SHA:
        raise RuntimeError("H49B native runtime provenance drift")
    if r3_manifest["generic_chess_source_tree"]["aggregate_sha256"] != H49R3A_SOURCE_TREE_SHA:
        raise RuntimeError("H49B source-tree authority drift")
    executions = f49_protocol.build_h49r3a_primary_execution()
    if set(executions) != set(RULESET_IDS) or any(entry["semantic_execution"].ruleset_fingerprint != f49_protocol.RULESET_FINGERPRINTS[name] for name, entry in executions.items()):
        raise RuntimeError("H49B RuleSet fingerprint reproduction failed")
    python_bindings = f49_protocol.validate_h49r4a_python_legality_bindings()
    if any(row["legality_route"] != "PYTHON_AUTHORITY" or row["native_legality_provider"] is not None for row in python_bindings.values()):
        raise RuntimeError("H49B Python-authority binding failed")
    _require_zero_production_diff()
    f48_authority, resolution = _load_f48_authority()
    control_corpora = _reconstruct_control_corpora(executions, resolution)
    f48_result = json.loads(F48_RESULTS_PATH.read_text(encoding="utf-8"))
    p48 = {row["ruleset_id"]: row["priors"]["P48-0"] for row in f48_result["rulesets"]}
    return {
        "checkpoint_name": "H49B",
        "kind": H49B_KIND,
        "work_order_id": H49B_WORK_ORDER_ID,
        "parent_h49r4a_sha": H49R4A_SHA,
        "h49r4a_manifest_sha256": H49R4A_MANIFEST_SHA,
        "protocol_status": "PRE_REGISTERED_NO_OBSERVED_RESULTS",
        "observed_results_present": False,
        "measurements_invoked": False,
        "learning_invoked": False,
        "production_diff_required": "ZERO",
        "master_promotion": False,
        "runner": {
            "path": "scripts/audit_f49_learning_signal_architecture.py",
            "source_sha256": _sha256_bytes(SOURCE_PATH.read_bytes()),
            "preflight_entry_point": "build_preflight_manifest",
            "measurement_entry_points": [],
            "measurement_invoked_by_checkpoint": False,
            "search_invocations": 0,
            "learner_invocations": 0,
        },
        "frozen_files_after_first_observation": [
            "scripts/audit_f49_learning_signal_architecture.py",
            "scripts/f49_protocol.py",
            "tests/fixtures/h49a_learning_signal_architecture_protocol_manifest.json",
            "tests/fixtures/h49r1a_executable_diagnostic_protocol_manifest.json",
            "tests/fixtures/h49r2a_nonmaterial_execution_protocol_manifest.json",
            "tests/fixtures/h49r3a_execution_dependency_and_ruleset_binding_manifest.json",
            "tests/fixtures/h49r4a_nonmaterial_availability_and_selector_closure_manifest.json",
        ],
        "authority": {
            "h49": h49,
            "h49r3a_source_tree_aggregate_sha256": H49R3A_SOURCE_TREE_SHA,
            "native_runtime_provenance": runtime,
            "ruleset_fingerprints": f49_protocol.RULESET_FINGERPRINTS,
            "python_legality_bindings": python_bindings,
            "generic_chess_diff_from_h49r4a": "ZERO",
            "f48": f48_authority,
        },
        "f48_control": {
            "source": "accepted H48C holdout corpus reconstructed through the accepted F48 path",
            "seed": 480703,
            "count": 64,
            "source_openings": {"count": 16, "min_plies": 2, "max_plies": 6},
            "min_plies": 2,
            "max_plies": 6,
            "authority_only": True,
            "corpora": control_corpora,
        },
        "p48_0_checkpoints": p48,
        "structural_generation": {
            "S49-M": {"seed": 490100, "source_openings": 16, "source_plies": [2, 6], "count": 64, "target_plies": [8, 20], "minimum_legal_actions": 1, "attempt_cap": 100000},
            "S49-E": {"seed": 490200, "source_openings": 16, "source_plies": [2, 6], "count": 64, "target_plies": [6, 24], "minimum_legal_actions": 2, "attempt_cap": 100000},
            "cross_corpus_intersections": "reported_only; never used for selection",
        },
        "measurement_surfaces": {
            "L49-0": {"factors": [0.75, 1.25], "budgets": [500, 2000, 8000]},
            "L49-1": {"direction_families": ["alternating_sign", "first_half_positive", "board_hand_differential", "seeded_normalized_pseudorandom"], "magnitude": "0.10 × P48-0 vector L2 magnitude", "budgets": [500, 2000, 8000]},
            "L49-2": {"factors": [0.50, 1.50], "budget": 2000},
            "teacher": {"budgets": [10000, 20000, 40000, 80000], "adjacent_pairs": [[10000, 20000], [20000, 40000], [40000, 80000]]},
            "python_nonmaterial": {"fields": ["dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"], "factors": [0.75, 1.25], "budget": 2000, "route": "PYTHON_AUTHORITY"},
        },
        "partition_input_fields": list(PARTITION_INPUT_FIELDS),
        "partition_templates": _partition_templates(runtime, P48_0_CHECKPOINTS),
        "selector": {"implementation": "scripts/f49_protocol.py::select_f49_classification", "direct_recompute_required": True, "manual_override": False},
        "next_boundary": "GENERICCHESS-F49-DIAGNOSTIC-MEASUREMENTS-AFTER-H49R4A",
    }


def validate_preflight_manifest(manifest: dict[str, Any]) -> None:
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise RuntimeError("H49B manifest hash mismatch")
    for key, expected in {
        "checkpoint_name": "H49B",
        "kind": H49B_KIND,
        "work_order_id": H49B_WORK_ORDER_ID,
        "parent_h49r4a_sha": H49R4A_SHA,
        "h49r4a_manifest_sha256": H49R4A_MANIFEST_SHA,
        "protocol_status": "PRE_REGISTERED_NO_OBSERVED_RESULTS",
        "production_diff_required": "ZERO",
    }.items():
        if manifest.get(key) != expected:
            raise RuntimeError(f"H49B {key} drift")
    if any(manifest.get(key) is not False for key in ("observed_results_present", "measurements_invoked", "learning_invoked", "master_promotion")):
        raise RuntimeError("H49B contains observed or executed work")
    runner = manifest.get("runner", {})
    if runner.get("measurement_entry_points") != [] or runner.get("measurement_invoked_by_checkpoint") is not False or runner.get("search_invocations") != 0 or runner.get("learner_invocations") != 0:
        raise RuntimeError("H49B runner is not implementation-freeze-only")
    if runner.get("source_sha256") != _git_blob_sha256(H49B_SHA, "scripts/audit_f49_learning_signal_architecture.py"):
        raise RuntimeError("H49B runner source drift")
    if manifest.get("authority", {}).get("h49r3a_source_tree_aggregate_sha256") != H49R3A_SOURCE_TREE_SHA or manifest.get("authority", {}).get("native_runtime_provenance", {}).get("native_module_sha256") != H49R3A_NATIVE_SHA:
        raise RuntimeError("H49B authority provenance drift")
    if manifest.get("authority", {}).get("generic_chess_diff_from_h49r4a") != "ZERO":
        raise RuntimeError("H49B production scope drift")
    if manifest.get("partition_input_fields") != list(PARTITION_INPUT_FIELDS):
        raise RuntimeError("H49B partition input contract drift")
    if not manifest.get("partition_templates") or any(item.get("observed_results_present") is not False for item in manifest["partition_templates"]):
        raise RuntimeError("H49B partition templates contain observations")
    if manifest.get("f48_control", {}).get("authority_only") is not True:
        raise RuntimeError("H49B control corpus is not authority-only")


def load_preflight_manifest() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_preflight_manifest(manifest)
    return manifest


def run_preflight() -> dict[str, Any]:
    """Run all no-observation gates and return a preflight description."""
    return build_preflight_manifest()


def partition_identity(
    *,
    corpus_id: str,
    checkpoint_or_config_hash: str,
    search_route: str,
    node_budget: int | None,
    measurement_family: str,
    ruleset_fingerprint: str,
    runner_sha256: str | None = None,
) -> dict[str, Any]:
    """Build one concrete, immutable identity for an observed partition."""
    if not corpus_id or corpus_id.startswith("<") or "PLANNED_ONLY_NO_EXECUTION" in corpus_id:
        raise ValueError("partition corpus_id must be concrete")
    if search_route not in PARTITION_ROUTES:
        raise ValueError(f"unknown or non-concrete partition route: {search_route}")
    if measurement_family not in MEASUREMENT_FAMILIES:
        raise ValueError(f"unknown measurement family: {measurement_family}")
    if not checkpoint_or_config_hash:
        raise ValueError("partition checkpoint/config identity is required")
    if node_budget is not None and (not isinstance(node_budget, int) or node_budget <= 0):
        raise ValueError("node_budget must be a positive integer or None")
    identity = {
        "H49B_R1_runner_sha256": runner_sha256 or _sha256_bytes(SOURCE_PATH.read_bytes()),
        "H49R4A_manifest_sha256": H49R4A_MANIFEST_SHA,
        "H49R3A_source_tree_aggregate_sha256": H49R3A_SOURCE_TREE_SHA,
        "native_binary_sha256": H49R3A_NATIVE_SHA,
        "ruleset_fingerprint": ruleset_fingerprint,
        "corpus_id": corpus_id,
        "checkpoint_or_config_hash": checkpoint_or_config_hash,
        "search_route": search_route,
        "node_budget": node_budget,
        "measurement_family": measurement_family,
    }
    return {"partition_id": "F49." + stable_sha256(identity)[:32], "input_identity": identity, "input_hash": stable_sha256(identity)}


class AtomicPartitionStore:
    """Audit-side partition store with exact identity and atomic writes."""

    def __init__(self, root: Path):
        self.root = root

    def _path(self, partition: dict[str, Any]) -> Path:
        return self.root / (partition["partition_id"] + ".json")

    def load(self, partition: dict[str, Any]) -> dict[str, Any] | None:
        path = self._path(partition)
        if not path.is_file():
            return None
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("partition_id") != partition["partition_id"] or saved.get("input_hash") != partition["input_hash"] or saved.get("input_identity") != partition["input_identity"]:
            raise RuntimeError(f"stale or mismatched F49 partition: {partition['partition_id']}")
        return saved["data"]

    def write(self, partition: dict[str, Any], data: dict[str, Any]) -> None:
        _atomic_write_json(self._path(partition), {"schema_version": 1, "partition_id": partition["partition_id"], "input_identity": partition["input_identity"], "input_hash": partition["input_hash"], "data": data})

    def run(self, partition: dict[str, Any], producer) -> dict[str, Any]:
        cached = self.load(partition)
        if cached is not None:
            return cached
        data = producer()
        self.write(partition, data)
        return data


def run_partition(store: AtomicPartitionStore, partition: dict[str, Any], producer) -> dict[str, Any]:
    """Return an exact cached partition or execute and atomically persist it."""
    return store.run(partition, producer)


def _position_summary(position) -> dict[str, Any]:
    board = collections.Counter((piece.owner, piece.current_type_id) for piece in position.board if piece is not None)
    inventory = collections.Counter()
    for owner, hand in enumerate(position.hands):
        for type_id, count in hand.items():
            inventory[(owner, type_id)] = count
    return {"board": dict(board), "inventory": dict(inventory)}


def _event_between(before, after) -> dict[str, bool]:
    return f49_protocol.inventory_event_flags(_position_summary(before), _position_summary(after))


def _merge_event_flags(target: dict[str, bool], event: dict[str, bool]) -> None:
    for key, value in event.items():
        target[key] = target.get(key, False) or bool(value)


def _replay(compiled, action_history: list[Any] | tuple[Any, ...]) -> GameSession:
    session = GameSession(compiled)
    for action in action_history:
        session.submit(action)
    return session


def _replay_with_events(compiled, action_history: list[Any] | tuple[Any, ...]) -> tuple[GameSession, dict[str, bool]]:
    session = GameSession(compiled)
    events = {"remove_or_capture_effect": False, "type_or_promotion_transformation": False, "hand_or_inventory_count_change": False}
    for action in action_history:
        before = session.state.position
        session.submit(action)
        _merge_event_flags(events, _event_between(before, session.state.position))
    return session, events


def generate_structural_corpus(
    compiled,
    *,
    stratum_id: str,
    seed: int,
    target_plies: tuple[int, int],
    minimum_legal_actions: int,
    count: int = 64,
    attempt_cap: int = 100_000,
) -> dict[str, Any]:
    """Generate one registered structural stratum deterministically."""
    source_openings = generate_arena_openings(compiled, count=16, seed=seed, min_plies=2, max_plies=6)
    config = {"stratum_id": stratum_id, "seed": seed, "count": count, "target_plies": list(target_plies), "minimum_legal_actions": minimum_legal_actions, "attempt_cap": attempt_cap, "source_openings": {"count": 16, "min_plies": 2, "max_plies": 6}}
    base_rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    identities: set[str] = set()
    for output_index in range(count):
        target = base_rng.randint(*target_plies)
        opening = source_openings.openings[output_index % len(source_openings.openings)]
        selected = None
        for attempt in range(attempt_cap):
            candidate_seed = f49_protocol.derive_stratum_candidate_seed(stratum_id, seed, output_index, attempt)
            rng = random.Random(candidate_seed)
            session = GameSession(compiled)
            events = {"remove_or_capture_effect": False, "type_or_promotion_transformation": False, "hand_or_inventory_count_change": False}
            for action in opening.actions:
                before = session.state.position
                session.submit(action)
                _merge_event_flags(events, _event_between(before, session.state.position))
            history = list(opening.actions)
            accepted = True
            while len(history) < target:
                legal = session.legal_actions()
                if not legal or session.result.status.value != "ongoing":
                    accepted = False
                    break
                ordered = sorted(legal, key=f49_protocol.canonical_action_order_key)
                before = session.state.position
                action = ordered[rng.randrange(len(ordered))]
                session.submit(action)
                _merge_event_flags(events, _event_between(before, session.state.position))
                history.append(action)
            if not accepted or session.result.status.value != "ongoing" or len(session.legal_actions()) < minimum_legal_actions:
                continue
            identity = position_identity_key(session.state.position, compiled)
            if identity in identities:
                continue
            if stratum_id == "S49-E" and not any(events.values()):
                continue
            identities.add(identity)
            selected = {
                "output_index": output_index,
                "target_ply": target,
                "selected_attempt": attempt,
                "candidate_rng_seed": candidate_seed,
                "action_history": [action_to_dict(action) for action in history],
                "position_identity_key": identity,
                "legal_action_count": len(session.legal_actions()),
                "event_flags": events,
            }
            break
        if selected is None:
            return {"status": "STRUCTURAL_STRATUM_UNAVAILABLE", "stratum_id": stratum_id, "seed": seed, "generation_config": config, "failed_output_index": output_index, "records": [], "corpus_id": None, "attempt_cap": attempt_cap}
        records.append(selected)
    return {"status": "VALID", "stratum_id": stratum_id, "generation_config": config, "records": records, "corpus_id": stable_sha256({"generation_config": config, "records": records})}


def _percentile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))])


def structural_ledger(corpus: dict[str, Any]) -> dict[str, Any]:
    records = list(corpus.get("records", []))
    identities = [record["position_identity_key"] for record in records]
    legal_counts = [int(record["legal_action_count"]) for record in records]
    ply_counts = [int(record["target_ply"]) for record in records]
    multiplicity = collections.Counter(collections.Counter(identities).values())
    event_names = ("remove_or_capture_effect", "type_or_promotion_transformation", "hand_or_inventory_count_change")
    frequencies = {name: sum(bool(record.get("event_flags", {}).get(name)) for record in records) / len(records) if records else 0.0 for name in event_names}
    return {
        "status": corpus.get("status"),
        "total_positions": len(records),
        "unique_identities": len(set(identities)),
        "multiplicity_histogram": {str(key): value for key, value in sorted(multiplicity.items())},
        "effective_unique_fraction": len(set(identities)) / len(records) if records else 0.0,
        "ply_histogram": {str(key): value for key, value in sorted(collections.Counter(ply_counts).items())},
        "raw_legal_action_count_vector": legal_counts,
        "legal_action_count": {"min": min(legal_counts) if legal_counts else 0, "median": statistics.median(legal_counts) if legal_counts else 0.0, "mean": statistics.fmean(legal_counts) if legal_counts else 0.0, "p90": _percentile(legal_counts, 0.90), "max": max(legal_counts) if legal_counts else 0},
        "any_inventory_changing_history_event_frequency": sum(any(record.get("event_flags", {}).values()) for record in records) / len(records) if records else 0.0,
        "remove_or_capture_event_frequency": frequencies["remove_or_capture_effect"],
        "type_or_promotion_transformation_frequency": frequencies["type_or_promotion_transformation"],
        "hand_or_inventory_state_change_frequency": frequencies["hand_or_inventory_count_change"],
    }


def _checkpoint_vector(checkpoint: LearnableMaterialCheckpoint, compiled) -> tuple[tuple[str, ...], list[float]]:
    types = tuple(non_anchor_type_ids(compiled))
    return types, [checkpoint.board_weights[type_id] for type_id in types] + [checkpoint.hand_weights[type_id] for type_id in types]


def _checkpoint_from_vector(start: LearnableMaterialCheckpoint, compiled, vector: list[float], tag: str) -> LearnableMaterialCheckpoint:
    types = tuple(non_anchor_type_ids(compiled))
    count = len(types)
    checkpoint = replace(start, board_weights=dict(zip(types, vector[:count])), hand_weights=dict(zip(types, vector[count:])), training_config_hash=tag)
    checkpoint.ensure_within_limits()
    return checkpoint


def reconstruct_p48_0(ruleset_id: str, compiled) -> LearnableMaterialCheckpoint:
    payload = json.loads(F48_RESULTS_PATH.read_text(encoding="utf-8"))
    row = next(item for item in payload["rulesets"] if item["ruleset_id"] == ruleset_id)
    checkpoint = LearnableMaterialCheckpoint.from_dict(row["priors"]["P48-0"])
    expected = P48_0_CHECKPOINTS[ruleset_id]
    if checkpoint.checkpoint_id != expected["checkpoint_id"] or checkpoint.config_hash != expected["config_hash"]:
        raise RuntimeError(f"P48-0 checkpoint drift: {ruleset_id}")
    checkpoint.validate_ruleset(compiled)
    return checkpoint


def _native_transport(compiled):
    legacy = getattr(compiled, "_legacy_compiled", None) or compiled
    changes = {}
    if getattr(legacy, "max_ply", 0) > 512:
        changes["max_ply"] = 512
    if getattr(legacy, "repetition_policy", "draw") not in ("draw", "none"):
        changes["repetition_policy"] = "draw"
    return replace(legacy, **changes) if changes else legacy


def _native_profile(compiled, checkpoint):
    from generic_chess.ai.evaluation.profile import build_ruleset_profile

    return build_ruleset_profile(compiled, EvaluationConfig())


def _native_search_once(compiled, native_rules, native_evaluation, record: dict[str, Any], node_budget: int, metrics: dict[str, Any]) -> dict[str, Any]:
    session = _replay(compiled, [action_from_dict(action) for action in record["action_history"]])
    started = time.perf_counter()
    engine = NativeSearchEngine(compiled, native_rules, native_evaluation, tt_megabytes=8)
    metrics["engine_creation_count"] += 1
    metrics["engine_creation_wall_seconds"] += time.perf_counter() - started
    metrics["requested_nodes"] += node_budget
    search_started = time.perf_counter()
    result = engine.search(session, SearchLimits(max_depth=12, max_nodes=node_budget, quiescence_max_depth=0, quiescence_max_nodes=0))
    metrics["search_count"] += 1
    metrics["actual_nodes"] += result.nodes
    metrics["search_wall_seconds"] += time.perf_counter() - search_started
    allowed = {"completed", "node_limit", "depth_limit"}
    failed = result.termination_reason not in allowed or (session.result.status.value == "ongoing" and result.action is None)
    return {"action_key": f49_protocol.canonical_action_order_key(result.action) if result.action is not None else None, "score": int(result.score), "nodes": int(result.nodes), "qnodes": int(result.qnodes), "elapsed_seconds": float(result.elapsed_seconds), "completed_depth": int(result.completed_depth), "termination_reason": result.termination_reason, "failed_search": failed}


def _concrete_corpus_id(corpus: dict[str, Any]) -> str:
    if corpus.get("corpus_id"):
        return str(corpus["corpus_id"])
    if corpus.get("status") == "STRUCTURAL_STRATUM_UNAVAILABLE":
        return "UNAVAILABLE." + stable_sha256({"status": corpus["status"], "stratum_id": corpus["stratum_id"], "generation_config": corpus["generation_config"], "failed_output_index": corpus["failed_output_index"], "attempt_cap": corpus["attempt_cap"]})
    raise ValueError("partition corpus_id must be concrete")


def _native_search_matrix(compiled, checkpoint, corpus, budgets: list[int], route: str, family: str, metrics: dict[str, Any], cache: dict[tuple[str, str, str, str, int], dict[str, Any]], context_cache: dict[tuple[str, str], tuple[Any, Any]] | None = None, partition_store: AtomicPartitionStore | None = None) -> dict[str, Any]:
    native_compiled = _native_transport(compiled)
    contexts = context_cache if context_cache is not None else {}
    rules_key = (compiled.ruleset_fingerprint, "native_rules")
    checkpoint_key = (compiled.ruleset_fingerprint, checkpoint.checkpoint_id)
    if rules_key not in contexts:
        started = time.perf_counter()
        contexts[rules_key] = (compile_native_rules(native_compiled), None)
        metrics["ruleset_compile_count"] = metrics.get("ruleset_compile_count", 0) + 1
        metrics["ruleset_compile_wall_seconds"] = metrics.get("ruleset_compile_wall_seconds", 0.0) + time.perf_counter() - started
    native_rules = contexts[rules_key][0]
    if checkpoint_key not in contexts:
        started = time.perf_counter()
        profile = _native_profile(native_compiled, checkpoint)
        table = compile_native_evaluation(native_rules, profile, EvaluationConfig(), material_override=checkpoint)
        contexts[checkpoint_key] = (native_rules, table)
        metrics["evaluation_table_compile_count"] = metrics.get("evaluation_table_compile_count", 0) + 1
        metrics["evaluation_table_compile_wall_seconds"] = metrics.get("evaluation_table_compile_wall_seconds", 0.0) + time.perf_counter() - started
    table = contexts[checkpoint_key][1]
    results = {}
    for budget in budgets:
        rows = []
        for record in corpus["records"]:
            key = (compiled.ruleset_fingerprint, corpus["corpus_id"], record["position_identity_key"], checkpoint.checkpoint_id, budget)
            if key not in cache:
                if partition_store is None:
                    cache[key] = _native_search_once(native_compiled, native_rules, table, record, budget, metrics)
                else:
                    partition = partition_identity(corpus_id=_concrete_corpus_id(corpus), checkpoint_or_config_hash=checkpoint.checkpoint_id, search_route=route, node_budget=budget, measurement_family=family, ruleset_fingerprint=compiled.ruleset_fingerprint)
                    cache[key] = run_partition(partition_store, partition, lambda: _native_search_once(native_compiled, native_rules, table, record, budget, metrics))
            rows.append(cache[key])
        results[str(budget)] = rows
    return results


def _flip_surface(baseline: list[dict[str, Any]], perturbed: list[dict[str, Any]]) -> dict[str, Any]:
    failed = sum(row["failed_search"] for row in perturbed) + sum(row["failed_search"] for row in baseline)
    flips = [left.get("action_key") != right.get("action_key") for left, right in zip(baseline, perturbed)]
    return {"status": "CELL_INVALID_SEARCH_FAILURE" if failed else "VALID", "failed_searches": failed, "positions": len(flips), "flip_rate": sum(flips) / len(flips) if flips else 0.0, "rows": [{"baseline_action_key": left.get("action_key"), "perturbed_action_key": right.get("action_key"), "baseline_score": left.get("score"), "perturbed_score": right.get("score"), "flip": flip, "absolute_score_displacement": abs(left.get("score", 0) - right.get("score", 0)), "nodes": right.get("nodes"), "termination_reason": right.get("termination_reason")} for left, right, flip in zip(baseline, perturbed, flips)]}


def _l49_candidate_vectors(compiled, start, surface: str) -> list[tuple[str, list[float]]]:
    types, vector = _checkpoint_vector(start, compiled)
    candidates = []
    if surface == "L49-0":
        for type_id in types:
            for factor in (0.75, 1.25):
                values = list(vector)
                index = types.index(type_id)
                values[index] *= factor
                values[len(types) + index] *= factor
                candidates.append((f"{type_id}:{factor}", values))
    elif surface == "L49-2":
        for type_id in types:
            for factor in (0.50, 1.50):
                values = list(vector)
                index = types.index(type_id)
                values[index] *= factor
                values[len(types) + index] *= factor
                candidates.append((f"{type_id}:{factor}", values))
    else:
        for direction_name in ("alternating_sign", "first_half_positive", "board_hand_differential", "seeded_normalized_pseudorandom"):
            direction_candidates = f49_protocol.direction_candidates(vector, direction_name)
            present_signs = {sign for sign, _ in direction_candidates}
            for sign, candidate_vector in direction_candidates:
                candidates.append((f"{direction_name}:{sign}", f49_protocol.rescale_to_reference_median(candidate_vector, len(types), start.reference_median)))
            for sign in (-1, 1):
                if sign not in present_signs:
                    candidates.append((f"{direction_name}:{sign}", [math.nan]))
    return candidates


def _l49_checkpoints(compiled, start, surface: str) -> list[tuple[str, LearnableMaterialCheckpoint]]:
    return [(name, _checkpoint_from_vector(start, compiled, values, f"F49:{surface}")) for name, values in _l49_candidate_vectors(compiled, start, surface)]


def _l49_checkpoint_rows(compiled, start, surface: str) -> list[dict[str, Any]]:
    try:
        candidates = _l49_checkpoints(compiled, start, surface)
    except Exception:
        candidates = [(name, values) for name, values in _l49_candidate_vectors(compiled, start, surface)]
        rows = []
        for name, values in candidates:
            try:
                checkpoint = _checkpoint_from_vector(start, compiled, values, f"F49:{surface}")
            except Exception as exc:
                rows.append({"name": name, "checkpoint": None, "construction_failed": True, "reason": type(exc).__name__ + ": " + str(exc)})
            else:
                rows.append({"name": name, "checkpoint": checkpoint, "construction_failed": False, "reason": None})
        return rows
    return [{"name": name, "checkpoint": checkpoint, "construction_failed": False, "reason": None} for name, checkpoint in candidates]


def _independent_selector(observations: dict[str, dict[str, dict[str, Any]]]) -> tuple[str, str, dict[str, bool]]:
    witnesses = {name: [] for name in ("A", "B", "C", "D", "E")}
    for ruleset_id, corpora in observations.items():
        stable = {name for name, value in corpora.items() if value.get("teacher_40_80", {}).get("status") == "VALID" and value["teacher_40_80"].get("failed_searches", 1) == 0 and value["teacher_40_80"].get("exact_best_move_agreement", -1.0) >= 0.85}
        control = corpora["F48_CONTROL"]
        control_l1 = control.get("L49_1_2000", {})
        control_l0 = control.get("L49_0_2000", {})
        signal = lambda cell: cell.get("status") == "VALID" and cell.get("failed_searches", 1) == 0 and cell.get("mean_flip_rate", -1.0) >= 0.05
        if "F48_CONTROL" in stable and not signal(control_l0) and signal(control_l1):
            witnesses["A"].append(ruleset_id)
        structural = [corpora[name]["L49_1_2000"].get("mean_flip_rate") for name in ("S49-M", "S49-E") if name in stable and signal(corpora[name].get("L49_1_2000", {}))]
        if structural and max(structural) - control_l1.get("mean_flip_rate", 0.0) >= 0.05:
            witnesses["B"].append(ruleset_id)
        if not stable:
            witnesses["C"].append(ruleset_id)
        valid_nonmaterial = [name for name in corpora if name in stable and corpora[name].get("non_material_control", {}).get("status") == "VALID"]
        positive_nonmaterial = [name for name in valid_nonmaterial if corpora[name]["non_material_control"].get("non_material_signal") is True]
        material = any(name in stable and signal(corpora[name].get("L49_1_2000", {})) for name in corpora)
        if stable and not material and positive_nonmaterial:
            witnesses["D"].append(ruleset_id)
        if stable and not material and valid_nonmaterial and not positive_nonmaterial:
            witnesses["E"].append(ruleset_id)
    names = ("LEARNER_ALIGNED_SIGNAL_SUPPORTED", "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING", "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING", "MATERIAL_ONLY_REPRESENTATION_LIMITING", "EVALUATION_SIGNAL_BROADLY_WEAK", "MIXED_OR_UNRESOLVED")
    mapping = dict(zip(names, ("F50_LEARNABLE_MATERIAL_RECOVERY_PROTOCOL_V2", "F50_STRUCTURAL_CORPUS_RECOVERY_PROTOCOL", "F50_NATIVE_SEARCH_STRENGTH_REASSESSMENT", "F50_GENERIC_LEARNABLE_EVALUATOR_EXPANSION", "F50_SEARCH_DOMINANCE_AND_EVALUATION_ROLE_DIAGNOSIS", "F50_LEARNING_ARCHITECTURE_REASSESSMENT")))
    if len(witnesses["A"]) >= 2:
        classification = names[0]
    elif len(witnesses["B"]) >= 2:
        classification = names[1]
    elif len(witnesses["C"]) >= 2:
        classification = names[2]
    elif len(witnesses["D"]) >= 2:
        classification = names[3]
    elif len(witnesses["E"]) >= 2:
        classification = names[4]
    else:
        classification = names[5]
    return classification, mapping[classification], {key: bool(value) for key, value in witnesses.items()}

def _python_decision(semantic_execution, record: dict[str, Any], config: EvaluationConfig, metrics: dict[str, Any]) -> dict[str, Any]:
    session = _replay(semantic_execution, [action_from_dict(action) for action in record["action_history"]])
    started = time.perf_counter()
    player = AlphaBetaPlayer(semantic_execution, evaluation_config=config, tt_max_entries=250000, profile_cache=EvaluationProfileCache(use_disk=False), use_disk_cache=False, use_tt=True, use_ordering=True, use_native_semantic_legality=False)
    metrics["player_construction_count"] += 1
    metrics["profile_construction_count"] += 1
    metrics["evaluator_construction_count"] += 1
    metrics["player_construction_wall_seconds"] += time.perf_counter() - started
    if player.native_legality_provider is not None:
        raise RuntimeError("H49B-R1 Python path unexpectedly enabled native legality")
    search_started = time.perf_counter()
    try:
        limits = SearchLimits(max_nodes=2000, max_depth=None, max_time_seconds=None, quiescence_max_depth=4, quiescence_hard_max_depth=8, quiescence_max_nodes=None, deterministic=True)
        decision = player.choose_action(session, limits)
        exception = None
    except Exception as exc:  # recorded as a cell failure by the frozen contract
        decision = None
        exception = type(exc).__name__ + ": " + str(exc)
    metrics["search_count"] += 1
    metrics["requested_nodes"] += 2000
    metrics["actual_nodes"] += (decision.nodes + decision.qnodes) if decision is not None else 0
    metrics["search_wall_seconds"] += time.perf_counter() - search_started
    legal = set(session.legal_actions())
    valid = exception is None and decision is not None and decision.choice_kind == "ACTION" and decision.action is not None and decision.action in legal
    return {"action_key": f49_protocol.canonical_action_order_key(decision.action) if valid else None, "score": int(decision.score) if decision is not None else None, "nodes": int(decision.nodes) if decision is not None else 0, "qnodes": int(decision.qnodes) if decision is not None else 0, "completed_depth": int(decision.completed_depth) if decision is not None else None, "termination_reason": decision.termination_reason if decision is not None else "exception", "valid": valid, "exception": exception}


def _python_liveness_precheck(semantic_execution) -> tuple[bool, str | None]:
    required = ("dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight")
    if not getattr(semantic_execution, "ruleset_fingerprint", None):
        return False, "missing ruleset fingerprint"
    if any(not hasattr(EvaluationConfig(), field) for field in required):
        return False, "coefficient field unavailable"
    return True, None


def python_nonmaterial_control(semantic_execution, corpus: dict[str, Any], *, teacher_stable: bool, metrics: dict[str, Any] | None = None, partition_store: AtomicPartitionStore | None = None, ruleset_fingerprint: str | None = None) -> dict[str, Any]:
    """Run the H49R4A Python coefficient control only on stable teachers."""
    if not teacher_stable:
        return {"status": "NOT_RUN_NO_STABLE_TEACHER", "non_material_signal": None, "families": []}
    live, reason = _python_liveness_precheck(semantic_execution)
    if not live:
        return {"status": "UNMEASURABLE_IN_SELECTED_SEARCH_PATH", "non_material_signal": None, "families": [], "liveness_failure": reason}
    metrics = metrics if metrics is not None else {"player_construction_count": 0, "player_construction_wall_seconds": 0.0, "profile_construction_count": 0, "evaluator_construction_count": 0, "search_count": 0, "requested_nodes": 0, "actual_nodes": 0, "search_wall_seconds": 0.0}
    baseline_config = EvaluationConfig()
    baseline: dict[int, dict[str, Any]] = {}
    families = []
    for record in corpus["records"]:
        if partition_store is None:
            baseline[record["output_index"]] = _python_decision(semantic_execution, record, baseline_config, metrics)
        else:
            partition = partition_identity(corpus_id=_concrete_corpus_id(corpus), checkpoint_or_config_hash=config_hash(baseline_config), search_route="PYTHON_ALPHABETA_FULL_EVALUATOR", node_budget=2000, measurement_family="PYTHON_NONMATERIAL", ruleset_fingerprint=ruleset_fingerprint or semantic_execution.ruleset_fingerprint)
            baseline[record["output_index"]] = run_partition(partition_store, partition, lambda: _python_decision(semantic_execution, record, baseline_config, metrics))
    for field in ("dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"):
        factor_rows = []
        for factor in (0.75, 1.25):
            candidate_config = replace(baseline_config, **{field: getattr(baseline_config, field) * factor})
            rows = []
            for record in corpus["records"]:
                if partition_store is None:
                    candidate = _python_decision(semantic_execution, record, candidate_config, metrics)
                else:
                    partition = partition_identity(corpus_id=_concrete_corpus_id(corpus), checkpoint_or_config_hash=config_hash(candidate_config), search_route="PYTHON_ALPHABETA_FULL_EVALUATOR", node_budget=2000, measurement_family="PYTHON_NONMATERIAL", ruleset_fingerprint=ruleset_fingerprint or semantic_execution.ruleset_fingerprint)
                    candidate = run_partition(partition_store, partition, lambda: _python_decision(semantic_execution, record, candidate_config, metrics))
                base = baseline[record["output_index"]]
                rows.append({"baseline_action_key": base["action_key"], "perturbed_action_key": candidate["action_key"], "baseline_score": base["score"], "perturbed_score": candidate["score"], "flip": base["action_key"] != candidate["action_key"], "nodes": candidate["nodes"], "qnodes": candidate["qnodes"], "termination_reason": candidate["termination_reason"], "valid": base["valid"] and candidate["valid"], "exception": candidate["exception"]})
            factor_rows.append({"factor": factor, "flip_rate": sum(row["flip"] for row in rows) / len(rows) if rows else 0.0, "failed_searches": sum(not row["valid"] for row in rows), "rows": rows})
        families.append({"field": field, "factors": factor_rows, "family_mean_flip": sum(row["flip_rate"] for row in factor_rows) / 2.0})
    failed = sum(row["failed_searches"] for family in families for row in family["factors"])
    valid = failed == 0
    return {"status": "VALID" if valid else "CELL_INVALID_SEARCH_FAILURE", "non_material_signal": max((family["family_mean_flip"] for family in families), default=0.0) >= 0.05 if valid else None, "families": families, "metrics": metrics}


def native_material_surface(compiled, corpus: dict[str, Any], start: LearnableMaterialCheckpoint, surface: str, *, metrics: dict[str, Any], cache: dict[tuple[str, str, str, str, int], dict[str, Any]], context_cache: dict[tuple[str, str], tuple[Any, Any]], partition_store: AtomicPartitionStore | None = None) -> dict[str, Any]:
    budgets = [500, 2000, 8000] if surface in ("L49-0", "L49-1") else [2000]
    baseline = _native_search_matrix(compiled, start, corpus, budgets, "NATIVE_SEARCH_ENGINE_MATERIAL", surface, metrics, cache, context_cache) if partition_store is None else _native_search_matrix(compiled, start, corpus, budgets, "NATIVE_SEARCH_ENGINE_MATERIAL", surface, metrics, cache, context_cache, partition_store)
    candidate_rows = _l49_checkpoint_rows(compiled, start, surface)
    unique: dict[str, tuple[str, LearnableMaterialCheckpoint]] = {}
    aliases: dict[str, list[str]] = {}
    construction_failures = []
    for row in candidate_rows:
        if row["construction_failed"]:
            construction_failures.append({"name": row["name"], "reason": row["reason"]})
            continue
        name, checkpoint = row["name"], row["checkpoint"]
        if checkpoint.checkpoint_id in unique:
            aliases.setdefault(checkpoint.checkpoint_id, []).append(name)
        else:
            unique[checkpoint.checkpoint_id] = (name, checkpoint)
            aliases.setdefault(checkpoint.checkpoint_id, [])
    cells = {}
    for checkpoint_id, (name, checkpoint) in unique.items():
        perturbed = _native_search_matrix(compiled, checkpoint, corpus, budgets, "NATIVE_SEARCH_ENGINE_MATERIAL", surface, metrics, cache, context_cache) if partition_store is None else _native_search_matrix(compiled, checkpoint, corpus, budgets, "NATIVE_SEARCH_ENGINE_MATERIAL", surface, metrics, cache, context_cache, partition_store)
        cells[checkpoint_id] = {"name": name, "aliases": aliases[checkpoint_id], "checkpoint": checkpoint.to_dict(), "budgets": {str(budget): _flip_surface(baseline[str(budget)], perturbed[str(budget)]) for budget in budgets}}
    return {"surface": surface, "baseline": baseline, "cells": cells, "deduplicated_checkpoint_count": len(unique), "candidate_count": len(candidate_rows), "construction_failures": construction_failures, "aliases": aliases}


def teacher_surface(compiled, corpus: dict[str, Any], checkpoint: LearnableMaterialCheckpoint, *, metrics: dict[str, Any], cache: dict[tuple[str, str, str, str, int], dict[str, Any]], context_cache: dict[tuple[str, str], tuple[Any, Any]], partition_store: AtomicPartitionStore | None = None) -> dict[str, Any]:
    budgets = [10000, 20000, 40000, 80000]
    results = _native_search_matrix(compiled, checkpoint, corpus, budgets, "NATIVE_SEARCH_ENGINE_TEACHER", "TEACHER", metrics, cache, context_cache) if partition_store is None else _native_search_matrix(compiled, checkpoint, corpus, budgets, "NATIVE_SEARCH_ENGINE_TEACHER", "TEACHER", metrics, cache, context_cache, partition_store)
    pairs = {}
    for low, high in ((10000, 20000), (20000, 40000), (40000, 80000)):
        low_rows, high_rows = results[str(low)], results[str(high)]
        metric = f49_protocol.teacher_pair_metrics([row["action_key"] for row in low_rows], [row["action_key"] for row in high_rows], [row["score"] for row in low_rows], [row["score"] for row in high_rows])
        failed = sum(row["failed_search"] for row in low_rows + high_rows)
        metric["failed_searches"] = failed
        metric["status"] = "VALID" if failed == 0 else "CELL_INVALID_SEARCH_FAILURE"
        pairs[f"{low}_{high}"] = metric
    stable = pairs["40000_80000"]["status"] == "VALID" and pairs["40000_80000"]["failed_searches"] == 0 and pairs["40000_80000"]["exact_best_move_agreement"] >= 0.85
    agreements = [pairs[key]["exact_best_move_agreement"] for key in ("10000_20000", "20000_40000", "40000_80000")]
    return {"results": results, "adjacent": pairs, "teacher_convergence": {"agreement_10_20": agreements[0], "agreement_20_40": agreements[1], "agreement_40_80": agreements[2], "adjacent_deltas": [agreements[1] - agreements[0], agreements[2] - agreements[1]]}, "teacher_40_80": {**pairs["40000_80000"], "stable": stable}}


def production_observations(cells: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Translate durable measurement cells into the real-selector shape."""
    return cells


def _measurement_metrics() -> dict[str, Any]:
    return {"ruleset_compile_count": 0, "ruleset_compile_wall_seconds": 0.0, "evaluation_table_compile_count": 0, "evaluation_table_compile_wall_seconds": 0.0, "engine_creation_count": 0, "engine_creation_wall_seconds": 0.0, "player_construction_count": 0, "player_construction_wall_seconds": 0.0, "profile_construction_count": 0, "evaluator_construction_count": 0, "search_count": 0, "requested_nodes": 0, "actual_nodes": 0, "search_wall_seconds": 0.0}


def _write_partition(store: AtomicPartitionStore, *, ruleset_id: str, ruleset_fingerprint: str, corpus: dict[str, Any], checkpoint_id: str, route: str, node_budget: int | None, family: str, data: dict[str, Any]) -> None:
    partition = partition_identity(corpus_id=_concrete_corpus_id(corpus), checkpoint_or_config_hash=checkpoint_id, search_route=route, node_budget=node_budget, measurement_family=family, ruleset_fingerprint=ruleset_fingerprint)
    run_partition(store, partition, lambda: data)


def write_evidence_bundle(result: dict[str, Any], root: Path) -> Path:
    """Persist a complete post-measurement result bundle; never called by R1 preflight."""
    path = root / "f49_evidence_bundle.json"
    _atomic_write_json(path, result)
    return path


def _control_records(legacy, control) -> list[dict[str, Any]]:
    records = []
    for position in control.positions:
        session, events = _replay_with_events(legacy, position.action_history)
        records.append({"output_index": position.index, "target_ply": position.ply, "selected_attempt": None, "candidate_rng_seed": None, "action_history": [action_to_dict(action) for action in position.action_history], "position_identity_key": position.position_key, "legal_action_count": len(session.legal_actions()), "event_flags": events})
    return records


def run_measurements(*, partition_root: Path | None = None) -> dict[str, Any]:
    """Run the complete registered F49 sequence after the R1 freeze."""
    validate_r2_measurement_freeze()
    preflight = run_preflight()
    executions = f49_protocol.build_h49r3a_primary_execution()
    root = partition_root or (ROOT / ".generic_chess_flow" / "f49")
    store = AtomicPartitionStore(root)
    result_cache: dict[tuple[str, str, str, str, int], dict[str, Any]] = {}
    context_cache: dict[tuple[str, str], tuple[Any, Any]] = {}
    observations: dict[str, dict[str, dict[str, Any]]] = {}
    efficiency: dict[str, Any] = {}
    corpus_ledgers: dict[str, Any] = {}
    for ruleset_id, entry in executions.items():
        legacy = entry["legacy_transport"]
        control_openings = generate_arena_openings(legacy, count=16, seed=480703, min_plies=2, max_plies=6)
        control = generate_diagnostic_corpus(legacy, control_openings, count=64, seed=480703, min_plies=2, max_plies=6)
        control_data = {"status": "VALID", "corpus_id": control.corpus_id, "records": _control_records(legacy, control)}
        structural = {"S49-M": generate_structural_corpus(legacy, stratum_id="S49-M", seed=490100, target_plies=(8, 20), minimum_legal_actions=1), "S49-E": generate_structural_corpus(legacy, stratum_id="S49-E", seed=490200, target_plies=(6, 24), minimum_legal_actions=2)}
        corpora = {"F48_CONTROL": control_data, **structural}
        p0 = reconstruct_p48_0(ruleset_id, legacy)
        metrics = _measurement_metrics()
        for corpus_name, corpus in corpora.items():
            _write_partition(store, ruleset_id=ruleset_id, ruleset_fingerprint=entry["semantic_execution"].ruleset_fingerprint, corpus=corpus, checkpoint_id="NONE", route="EVALUATOR_NEUTRAL_CORE_CORPUS", node_budget=None, family=corpus_name if corpus_name in ("S49-M", "S49-E") else "SELECTOR", data=corpus)
            if corpus["status"] != "VALID":
                corpus["teacher_40_80"] = {"status": "UNMEASURABLE_IN_SELECTED_SEARCH_PATH", "failed_searches": 0, "exact_best_move_agreement": 0.0}
                corpus["non_material_control"] = {"status": "UNMEASURABLE_IN_SELECTED_SEARCH_PATH", "non_material_signal": None}
                continue
            corpus["structural_ledger"] = structural_ledger(corpus)
            for surface in ("L49-0", "L49-1", "L49-2"):
                surface_data = native_material_surface(legacy, corpus, p0, surface, metrics=metrics, cache=result_cache, context_cache=context_cache, partition_store=store)
                corpus[surface] = surface_data
                for budget in ([500, 2000, 8000] if surface != "L49-2" else [2000]):
                    values = [cell["budgets"][str(budget)] for cell in surface_data["cells"].values()]
                    corpus[f"{surface}_{budget}"] = f49_protocol.aggregate_leverage_cells(values)
            teacher = teacher_surface(legacy, corpus, p0, metrics=metrics, cache=result_cache, context_cache=context_cache, partition_store=store)
            corpus.update(teacher)
            corpus["non_material_control"] = python_nonmaterial_control(entry["semantic_execution"], corpus, teacher_stable=teacher["teacher_40_80"]["stable"], metrics=metrics, partition_store=store, ruleset_fingerprint=entry["semantic_execution"].ruleset_fingerprint)
        corpus_ledgers[ruleset_id] = {name: structural_ledger(corpus) for name, corpus in corpora.items()}
        for left, right in (("F48_CONTROL", "S49-M"), ("F48_CONTROL", "S49-E"), ("S49-M", "S49-E")):
            corpus_ledgers[ruleset_id][f"intersection_{left}_{right}"] = sorted({row["position_identity_key"] for row in corpora[left].get("records", [])} & {row["position_identity_key"] for row in corpora[right].get("records", [])})
        observations[ruleset_id] = corpora
        efficiency[ruleset_id] = metrics
    classification, boundary, witnesses = f49_protocol.select_f49_classification(production_observations(observations))
    direct_classification, direct_boundary, direct_witnesses = _independent_selector(observations)
    if (classification, boundary, witnesses) != (direct_classification, direct_boundary, direct_witnesses):
        raise RuntimeError("F49 selector disagreement")
    python_efficiency_fields = ("player_construction_count", "profile_construction_count", "evaluator_construction_count", "search_count", "requested_nodes", "actual_nodes", "search_wall_seconds")
    python_efficiency = {field: sum(int(values.get(field, 0)) if field not in ("search_wall_seconds",) else float(values.get(field, 0.0)) for values in efficiency.values()) for field in python_efficiency_fields}
    result = {"kind": "F49_DIAGNOSTIC_RESULTS", "preflight": preflight, "observations": observations, "structural_ledgers": corpus_ledgers, "efficiency": efficiency, "python_efficiency": python_efficiency, "classification": classification, "next_boundary": boundary, "witnesses": witnesses, "direct_selector_agreement": True, "observed_results_present": True, "learning_invoked": False, "F50_status": "NOT_STARTED", "partition_root": str(root)}
    for ruleset_id, corpora in observations.items():
        selector_corpus = {"corpus_id": stable_sha256({name: corpus.get("corpus_id") for name, corpus in corpora.items()}), "records": []}
        _write_partition(store, ruleset_id=ruleset_id, ruleset_fingerprint=executions[ruleset_id]["semantic_execution"].ruleset_fingerprint, corpus=selector_corpus, checkpoint_id="NONE", route="AUDIT_SELECTOR", node_budget=None, family="SELECTOR", data={"classification": classification, "next_boundary": boundary, "witnesses": witnesses, "direct_selector_agreement": True})
    result["evidence_bundle_path"] = str(root / "f49_evidence_bundle.json")
    write_evidence_bundle(result, root)
    return result


def build_h49b_r1_manifest() -> dict[str, Any]:
    """Build the no-observation R1 runner-freeze manifest."""
    preflight = run_preflight()
    return {"checkpoint_name": "H49B-R1", "kind": H49B_R1_KIND, "work_order_id": H49B_R1_WORK_ORDER_ID, "parent_h49b_sha": H49B_SHA, "h49b_manifest_sha256": H49B_MANIFEST_SHA, "runner_raw_sha256": _sha256_bytes(SOURCE_PATH.read_bytes()), "protocol_raw_sha256": _sha256_bytes((ROOT / "scripts" / "f49_protocol.py").read_bytes()), "h49r4a_manifest_sha256": H49R4A_MANIFEST_SHA, "h49r3a_source_tree_aggregate_sha256": H49R3A_SOURCE_TREE_SHA, "native_binary_sha256": H49R3A_NATIVE_SHA, "measurement_entry_point": "scripts.audit_f49_learning_signal_architecture.run_measurements", "preflight_entry_point": "scripts.audit_f49_learning_signal_architecture.run_preflight", "evidence_writer": "scripts.audit_f49_learning_signal_architecture.write_evidence_bundle", "orchestration_phases": ["preflight", "reconstruct accepted control", "construct S49-M/S49-E", "structural ledgers/intersections", "reconstruct P48-0", "compile Native rules", "Native material leverage surfaces", "Native teacher surfaces", "stable-corpus determination", "Python non-material controls only where authorized", "observation assembly", "real selector", "independent selector", "fail closed on selector disagreement", "assemble complete evidence bundle"], "concrete_partition_routes": sorted(PARTITION_ROUTES), "measurement_families": list(MEASUREMENT_FAMILIES), "partition_input_fields": list(R1_PARTITION_INPUT_FIELDS), "partition_identity_entry_point": "scripts.audit_f49_learning_signal_architecture.partition_identity", "atomic_partition_writer": "scripts.audit_f49_learning_signal_architecture.AtomicPartitionStore.write", "observed_results_present": False, "measurements_invoked": False, "learning_invoked": False, "F50_status": "NOT_STARTED", "production_diff_required": "ZERO", "master_promotion": False, "preflight_authority": {"h49r3a_source_tree_aggregate_sha256": preflight["authority"]["h49r3a_source_tree_aggregate_sha256"], "native_binary_sha256": preflight["authority"]["native_runtime_provenance"]["native_module_sha256"], "ruleset_fingerprints": preflight["authority"]["ruleset_fingerprints"], "generic_chess_diff_from_h49r4a": "ZERO"}, "freeze_rule": "runner and scripts/f49_protocol.py byte-identical after acceptance and before first observed position/search result"}


def validate_h49b_r1_manifest(manifest: dict[str, Any]) -> None:
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise RuntimeError("H49B-R1 manifest hash mismatch")
    expected = {"checkpoint_name": "H49B-R1", "kind": H49B_R1_KIND, "work_order_id": H49B_R1_WORK_ORDER_ID, "parent_h49b_sha": H49B_SHA, "h49b_manifest_sha256": H49B_MANIFEST_SHA, "h49r4a_manifest_sha256": H49R4A_MANIFEST_SHA, "h49r3a_source_tree_aggregate_sha256": H49R3A_SOURCE_TREE_SHA, "native_binary_sha256": H49R3A_NATIVE_SHA, "measurement_entry_point": "scripts.audit_f49_learning_signal_architecture.run_measurements", "preflight_entry_point": "scripts.audit_f49_learning_signal_architecture.run_preflight", "evidence_writer": "scripts.audit_f49_learning_signal_architecture.write_evidence_bundle", "F50_status": "NOT_STARTED", "production_diff_required": "ZERO"}
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"H49B-R1 {key} drift")
    if any(manifest.get(key) is not False for key in ("observed_results_present", "measurements_invoked", "learning_invoked", "master_promotion")):
        raise RuntimeError("H49B-R1 contains observations or learning")
    if manifest.get("concrete_partition_routes") != sorted(PARTITION_ROUTES) or set(manifest.get("measurement_families", ())) != set(MEASUREMENT_FAMILIES):
        raise RuntimeError("H49B-R1 runner surface drift")
    if manifest.get("partition_input_fields") != list(R1_PARTITION_INPUT_FIELDS):
        raise RuntimeError("H49B-R1 partition input contract drift")
    if manifest.get("runner_raw_sha256") != _git_blob_sha256(H49B_R1_SHA, "scripts/audit_f49_learning_signal_architecture.py") or manifest.get("protocol_raw_sha256") != _git_blob_sha256(H49B_R1_SHA, "scripts/f49_protocol.py"):
        raise RuntimeError("H49B-R1 source hash drift")


def load_h49b_r1_manifest() -> dict[str, Any]:
    path = ROOT / "tests" / "fixtures" / "h49b_r1_f49_diagnostic_runner_freeze_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_h49b_r1_manifest(manifest)
    return manifest


def _native_transport_provenance(executions: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for ruleset_id, entry in executions.items():
        original = entry["legacy_transport"]
        native = _native_transport(original)
        result[ruleset_id] = {"original_max_ply": getattr(original, "max_ply", None), "native_transport_max_ply": getattr(native, "max_ply", None), "original_repetition_policy": getattr(original, "repetition_policy", None), "native_transport_repetition_policy": getattr(native, "repetition_policy", None), "ruleset_fingerprint": entry["semantic_execution"].ruleset_fingerprint}
    return result


def build_h49b_r2_manifest() -> dict[str, Any]:
    preflight = run_preflight()
    executions = f49_protocol.build_h49r3a_primary_execution()
    return {"checkpoint_name": "H49B-R2", "kind": H49B_R2_KIND, "work_order_id": H49B_R2_WORK_ORDER_ID, "parent_h49b_r1_sha": H49B_R1_SHA, "h49b_r1_manifest_sha256": H49B_R1_MANIFEST_SHA, "runner_raw_sha256": _sha256_bytes(SOURCE_PATH.read_bytes()), "protocol_raw_sha256": _sha256_bytes((ROOT / "scripts" / "f49_protocol.py").read_bytes()), "h49r4a_manifest_sha256": H49R4A_MANIFEST_SHA, "h49r3a_source_tree_aggregate_sha256": H49R3A_SOURCE_TREE_SHA, "native_binary_sha256": H49R3A_NATIVE_SHA, "measurement_entry_point": "scripts.audit_f49_learning_signal_architecture.run_measurements", "preflight_entry_point": "scripts.audit_f49_learning_signal_architecture.run_preflight", "evidence_writer": "scripts.audit_f49_learning_signal_architecture.write_evidence_bundle", "partition_runner": "scripts.audit_f49_learning_signal_architecture.run_partition", "orchestration_phases": ["verify accepted R2 freeze", "preflight", "reconstruct accepted control", "construct S49-M/S49-E", "reconstruct P48-0", "compile Native rules", "per-corpus structural ledger", "Native material leverage surfaces", "Native teacher surfaces", "stable-corpus determination", "Python non-material controls only where authorized", "cross-corpus intersections and observation assembly", "real selector", "independent selector", "fail closed on selector disagreement", "assemble and atomically write complete evidence bundle"], "concrete_partition_routes": sorted(PARTITION_ROUTES), "measurement_families": list(MEASUREMENT_FAMILIES), "partition_input_fields": list(R1_PARTITION_INPUT_FIELDS), "observed_results_present": False, "measurements_invoked": False, "learning_invoked": False, "F50_status": "NOT_STARTED", "production_diff_required": "ZERO", "master_promotion": False, "native_transport_provenance": _native_transport_provenance(executions), "preflight_authority": {"h49r3a_source_tree_aggregate_sha256": preflight["authority"]["h49r3a_source_tree_aggregate_sha256"], "native_binary_sha256": preflight["authority"]["native_runtime_provenance"]["native_module_sha256"], "ruleset_fingerprints": preflight["authority"]["ruleset_fingerprints"], "generic_chess_diff_from_h49r4a": "ZERO"}, "freeze_rule": "runner and scripts/f49_protocol.py byte-identical after R2 acceptance and before first observed position/search result"}


def validate_h49b_r2_manifest(manifest: dict[str, Any]) -> None:
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise RuntimeError("H49B-R2 manifest hash mismatch")
    expected = {"checkpoint_name": "H49B-R2", "kind": H49B_R2_KIND, "work_order_id": H49B_R2_WORK_ORDER_ID, "parent_h49b_r1_sha": H49B_R1_SHA, "h49b_r1_manifest_sha256": H49B_R1_MANIFEST_SHA, "h49r4a_manifest_sha256": H49R4A_MANIFEST_SHA, "h49r3a_source_tree_aggregate_sha256": H49R3A_SOURCE_TREE_SHA, "native_binary_sha256": H49R3A_NATIVE_SHA, "measurement_entry_point": "scripts.audit_f49_learning_signal_architecture.run_measurements", "preflight_entry_point": "scripts.audit_f49_learning_signal_architecture.run_preflight", "partition_runner": "scripts.audit_f49_learning_signal_architecture.run_partition", "evidence_writer": "scripts.audit_f49_learning_signal_architecture.write_evidence_bundle", "F50_status": "NOT_STARTED", "production_diff_required": "ZERO"}
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"H49B-R2 {key} drift")
    if any(manifest.get(key) is not False for key in ("observed_results_present", "measurements_invoked", "learning_invoked", "master_promotion")):
        raise RuntimeError("H49B-R2 contains observations or learning")
    if manifest.get("concrete_partition_routes") != sorted(PARTITION_ROUTES) or set(manifest.get("measurement_families", ())) != set(MEASUREMENT_FAMILIES) or manifest.get("partition_input_fields") != list(R1_PARTITION_INPUT_FIELDS):
        raise RuntimeError("H49B-R2 partition surface drift")
    if manifest.get("runner_raw_sha256") != _sha256_bytes(SOURCE_PATH.read_bytes()) or manifest.get("protocol_raw_sha256") != _sha256_bytes((ROOT / "scripts" / "f49_protocol.py").read_bytes()):
        raise RuntimeError("H49B-R2 source hash drift")


def load_h49b_r2_manifest() -> dict[str, Any]:
    manifest = json.loads(R2_MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49b_r2_manifest(manifest)
    return manifest


def validate_r2_measurement_freeze() -> None:
    manifest = load_h49b_r2_manifest()
    if manifest.get("h49r4a_manifest_sha256") != H49R4A_MANIFEST_SHA or manifest.get("h49r3a_source_tree_aggregate_sha256") != H49R3A_SOURCE_TREE_SHA or manifest.get("native_binary_sha256") != H49R3A_NATIVE_SHA:
        raise RuntimeError("STOP_ON_H49_RUNNER_FREEZE_DRIFT")
    if manifest.get("runner_raw_sha256") != _sha256_bytes(SOURCE_PATH.read_bytes()) or manifest.get("protocol_raw_sha256") != _sha256_bytes((ROOT / "scripts" / "f49_protocol.py").read_bytes()):
        raise RuntimeError("STOP_ON_H49_RUNNER_FREEZE_DRIFT")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-preflight", action="store_true", help="deprecated; H49B historical preflight is immutable")
    parser.add_argument("--write-r1-manifest", action="store_true", help="run no-observation preflight and atomically write H49B-R1 manifest")
    parser.add_argument("--write-r2-manifest", action="store_true", help="run no-observation preflight and atomically write H49B-R2 manifest")
    parser.add_argument("--measure", action="store_true", help="execute the full frozen F49 measurement runner")
    args = parser.parse_args()
    if args.measure:
        result = run_measurements()
        print(json.dumps({"status": "PASS", "kind": result["kind"], "observed_results_present": result["observed_results_present"], "next_boundary": result["next_boundary"]}, sort_keys=True))
        return
    if args.write_preflight:
        raise RuntimeError("historical H49B preflight is immutable; use --write-r1-manifest")
    if args.write_r2_manifest:
        manifest = build_h49b_r2_manifest()
        manifest["manifest_sha256"] = _manifest_sha(manifest)
        _atomic_write_json(R2_MANIFEST_PATH, manifest)
        validate_h49b_r2_manifest(manifest)
    elif args.write_r1_manifest:
        manifest = build_h49b_r1_manifest()
        manifest["manifest_sha256"] = _manifest_sha(manifest)
        path = ROOT / "tests" / "fixtures" / "h49b_r1_f49_diagnostic_runner_freeze_manifest.json"
        _atomic_write_json(path, manifest)
        validate_h49b_r1_manifest(manifest)
    else:
        manifest = load_h49b_r2_manifest()
    print(json.dumps({"status": "PASS", "kind": manifest["kind"], "observed_results_present": manifest["observed_results_present"], "next_boundary": H49B_WORK_ORDER_ID}, sort_keys=True))


if __name__ == "__main__":
    main()
