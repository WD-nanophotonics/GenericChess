"""Freeze the implementation and preflight boundary for the F49 diagnostic run.

This module is intentionally pre-measurement.  It verifies the accepted H49
authority chain and the accepted F48 control inputs, but it never invokes a
search, evaluator, learner, or F49 corpus-result writer.  The resulting
manifest is a durable description of the frozen runner and its partition
identity contract; it contains no observed corpus or search result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts import f48_protocol, f49_protocol
except ImportError:  # direct ``python scripts/audit_*.py`` execution
    import f48_protocol  # type: ignore[no-redef]
    import f49_protocol  # type: ignore[no-redef]

from generic_chess.learning.diagnostics import generate_diagnostic_corpus
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import canonical_json, stable_sha256


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49b_f49_diagnostic_runner_freeze_manifest.json"
SOURCE_PATH = ROOT / "scripts" / "audit_f49_learning_signal_architecture.py"
F48_RESULTS_PATH = ROOT / "tests" / "fixtures" / "f48_learnable_material_recovery_results.json"

H49B_KIND = "H49B_F49_DIAGNOSTIC_RUNNER_FREEZE"
H49B_WORK_ORDER_ID = "GENERICCHESS-F49-DIAGNOSTIC-MEASUREMENTS-AFTER-H49R4A"
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
    if runner.get("source_sha256") != _sha256_bytes(SOURCE_PATH.read_bytes()):
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-preflight", action="store_true", help="run preflight-only gates and atomically write the H49B manifest")
    args = parser.parse_args()
    if args.write_preflight:
        manifest = build_preflight_manifest()
        manifest["manifest_sha256"] = _manifest_sha(manifest)
        _atomic_write_json(MANIFEST_PATH, manifest)
        validate_preflight_manifest(manifest)
    else:
        manifest = load_preflight_manifest()
    print(json.dumps({"status": "PASS", "kind": manifest["kind"], "observed_results_present": manifest["observed_results_present"], "next_boundary": manifest["next_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
