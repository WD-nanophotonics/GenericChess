"""Validation-only authority for the pre-registered F49 H49A protocol."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from generic_chess.core.actions import action_to_dict
from generic_chess.learning.serialization import canonical_json, stable_sha256


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49a_learning_signal_architecture_protocol_manifest.json"
H49R1A_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49r1a_executable_diagnostic_protocol_manifest.json"
H49R2A_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49r2a_nonmaterial_execution_protocol_manifest.json"
H49R3A_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49r3a_execution_dependency_and_ruleset_binding_manifest.json"
H49R4A_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49r4a_nonmaterial_availability_and_selector_closure_manifest.json"
F48_BASELINE_SHA = "4bd25d405af0890668c2940eefc8b68faae1b594"
H49A_MANIFEST_SHA = "e294a27ed1a4ea4c03578321b1beeb61ba233aafe19fcad98e968a016ed14f90"
H49R1A_MANIFEST_SHA = "57d2d189712138efa352b8e93edae83cb4938d74c5140717976aecf722a31215"
H49R2A_MANIFEST_SHA = "9b6b98997b7656f845283b20297d325c83c8451c6da55255e3f481e638e9beaf"
H49R3A_SHA = "f3146f7e31f07b15e39fcd50f0f18138c3c28024"
H49R3A_MANIFEST_SHA = "6279a3e12bd9e397fea02e210c0f936ed5afe657888f125829ddc111a455a8ab"
RULESET_FINGERPRINTS = {
    "A_CANONICAL_WESTERN_CHESS": "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35",
    "B_CANONICAL_STANDARD_SHOGI": "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
    "C_H48B_SELECTED_GENERATED": "9f7e7201a19f8f0ee6c0eacc766c2ac3a6c313e06bbc960d5d6dfb89137db923",
}


def _manifest_sha(manifest: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()


def load_h49a_manifest() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49a_manifest(manifest)
    return manifest


def validate_h49a_manifest(manifest: dict[str, Any]) -> None:
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise RuntimeError("H49A manifest hash mismatch")
    if manifest.get("baseline_sha") != F48_BASELINE_SHA:
        raise RuntimeError("H49A baseline drift")
    if manifest.get("protocol_status") != "PRE_REGISTERED_NO_OBSERVED_RESULTS":
        raise RuntimeError("H49A is not a no-observations protocol checkpoint")
    if manifest.get("observed_results_present") or manifest.get("measurements_invoked") or manifest.get("learning_invoked"):
        raise RuntimeError("H49A contains observed or executed work")
    if manifest.get("production_diff_required") != "ZERO" or manifest.get("master_promotion") is not False:
        raise RuntimeError("H49A production or promotion scope drift")
    if manifest.get("f49_status") != "DIAGNOSIS_ONLY" or manifest.get("f50_status") != "NOT_STARTED":
        raise RuntimeError("H49A stage status drift")
    if manifest["authority"]["rulesets"] != RULESET_FINGERPRINTS:
        raise RuntimeError("H49A RuleSet fingerprint drift")
    if manifest["authority"]["resolved_seed_triple"] != {"training": 480700, "holdout": 480703, "arena": 480708}:
        raise RuntimeError("H49A H48C seed drift")
    if manifest["control_corpus"]["preserve_results"] is not True:
        raise RuntimeError("H49A does not preserve the F48 control")
    strata = manifest["diagnostic_strata"]
    if set(strata) != {"S49-M", "S49-E"} or any(strata[name]["count"] != 64 for name in strata):
        raise RuntimeError("H49A structural strata drift")
    if any(strata[name]["attempt_cap"] != 100000 for name in strata):
        raise RuntimeError("H49A structural attempt cap drift")
    if manifest["leverage_surfaces"]["L49-0"]["budgets"] != [500, 2000, 8000] or manifest["leverage_surfaces"]["L49-1"]["budgets"] != [500, 2000, 8000]:
        raise RuntimeError("H49A leverage budget surface drift")
    if manifest["teacher_stability_surface"]["adjacent_budget_pairs"] != [[10000, 20000], [20000, 40000], [40000, 80000]]:
        raise RuntimeError("H49A teacher stability surface drift")
    classification = manifest["classification"]
    if classification["precedence"] != list(classification["mapping"]):
        raise RuntimeError("H49A classification precedence is not frozen")
    if manifest["authority"]["f48_r4_erratum"]["fresh_r4_partition_root"] != ".generic_chess_flow/f48-r4-prerequisite-closure-final-v3":
        raise RuntimeError("H49A F48 R4 root erratum drift")
    if len(manifest["authority"]["f48_r4_erratum"]["actual_diff_files"]) != 6:
        raise RuntimeError("H49A F48 R4 diff erratum is incomplete")


def derive_stratum_candidate_seed(stratum_id: str, seed: int, index: int, attempt: int) -> int:
    return int(stable_sha256({"stage": "F49_STRATUM_POSITION", "stratum": stratum_id, "seed": seed, "index": index, "attempt": attempt})[:16], 16)


def canonical_action_order_key(action: Any) -> str:
    return canonical_json(action_to_dict(action))


def material_vector_coordinate_order(type_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    ordered = tuple(type_ids)
    return tuple(f"board[{type_id}]" for type_id in ordered) + tuple(f"hand[{type_id}]" for type_id in ordered)


def raw_direction(name: str, dimension: int) -> list[float]:
    if name == "alternating_sign":
        raw = [1.0 if index % 2 == 0 else -1.0 for index in range(dimension)]
    elif name == "first_half_positive":
        raw = [1.0 if index < math.ceil(dimension / 2) else -1.0 for index in range(dimension)]
    elif name == "board_hand_differential":
        half = dimension // 2
        raw = [1.0] * half + [-1.0] * (dimension - half)
    elif name == "seeded_normalized_pseudorandom":
        rng = random.Random(480703)
        raw = [rng.uniform(-1.0, 1.0) for _ in range(dimension)]
    else:
        raise ValueError(name)
    norm = math.sqrt(sum(value * value for value in raw))
    if norm == 0.0:
        raise RuntimeError("zero F49 direction")
    return [value / norm for value in raw]


def direction_candidates(reference_vector: list[float], direction_name: str) -> list[tuple[int, list[float]]]:
    norm = math.sqrt(sum(value * value for value in reference_vector))
    direction = raw_direction(direction_name, len(reference_vector))
    candidates = []
    for sign in (-1, 1):
        candidate = [value + sign * 0.10 * norm * delta for value, delta in zip(reference_vector, direction)]
        if not all(math.isfinite(value) and value > 0 for value in candidate):
            continue
        candidates.append((sign, candidate))
    return candidates


def rescale_to_reference_median(vector: list[float], board_count: int, reference_median: float) -> list[float]:
    board = vector[:board_count]
    ordered = sorted(board)
    median = ordered[board_count // 2] if board_count % 2 else (ordered[board_count // 2 - 1] + ordered[board_count // 2]) / 2.0
    if not math.isfinite(median) or median <= 0:
        raise RuntimeError("invalid F49 median")
    scale = reference_median / median
    result = [value * scale for value in vector]
    if not all(math.isfinite(value) and value > 0 for value in result):
        raise RuntimeError("invalid F49 rescaled candidate")
    return result


def inventory_event_flags(before: dict[str, Any], after: dict[str, Any]) -> dict[str, bool]:
    board_before = before.get("board", {})
    board_after = after.get("board", {})
    board_total_before = sum(board_before.values())
    board_total_after = sum(board_after.values())
    return {
        "remove_or_capture_effect": board_total_after < board_total_before,
        "type_or_promotion_transformation": board_total_after == board_total_before and board_before != board_after,
        "hand_or_inventory_count_change": before.get("inventory", {}) != after.get("inventory", {}),
    }


def aggregate_leverage_cells(cells: list[dict[str, Any]]) -> dict[str, Any]:
    constructed = [cell for cell in cells if not cell.get("construction_failed", False)]
    if any(cell.get("status") != "VALID" or cell.get("failed_searches", 1) != 0 for cell in constructed):
        return {"status": "CELL_INVALID_SEARCH_FAILURE", "mean_flip_rate": None, "usable_perturbations": 0}
    usable = constructed
    if not usable:
        return {"status": "NO_USABLE_PERTURBATIONS", "mean_flip_rate": None, "usable_perturbations": 0}
    return {"status": "VALID", "mean_flip_rate": sum(cell["flip_rate"] for cell in usable) / len(usable), "usable_perturbations": len(usable)}


def teacher_pair_metrics(low_actions: list[Any], high_actions: list[Any], low_scores: list[float], high_scores: list[float]) -> dict[str, Any]:
    if not (len(low_actions) == len(high_actions) == len(low_scores) == len(high_scores)):
        raise RuntimeError("teacher metric vectors have different lengths")
    sign = lambda value: -1 if value < 0 else 1 if value > 0 else 0
    n = len(low_actions)
    return {
        "exact_best_move_agreement": sum(left == right for left, right in zip(low_actions, high_actions)) / n if n else 0.0,
        "score_sign_agreement": sum(sign(left) == sign(right) for left, right in zip(low_scores, high_scores)) / n if n else 0.0,
        "failed_searches": 0,
        "top_action_stability": sum(left == right for left, right in zip(low_actions, high_actions)) / n if n else 0.0,
        "top_k_ranking_available": False,
    }


def _valid_cell(corpus: dict[str, Any], key: str) -> bool:
    cell = corpus.get(key, {})
    return cell.get("status") == "VALID" and cell.get("failed_searches", 1) == 0


def _signal(corpus: dict[str, Any], key: str) -> bool:
    return _valid_cell(corpus, key) and corpus[key].get("mean_flip_rate", -1.0) >= 0.05


NONMATERIAL_CELL_STATUSES = {
    "VALID",
    "NOT_RUN_NO_STABLE_TEACHER",
    "UNMEASURABLE_IN_SELECTED_SEARCH_PATH",
    "CELL_INVALID_SEARCH_FAILURE",
}


def _nonmaterial_valid(corpus: dict[str, Any], stable: bool) -> bool:
    control = corpus.get("non_material_control", {})
    return stable and control.get("status") == "VALID"


def _nonmaterial_signal(corpus: dict[str, Any], stable: bool) -> bool:
    return _nonmaterial_valid(corpus, stable) and corpus["non_material_control"].get("non_material_signal") is True


def select_f49_classification(observations: dict[str, dict[str, dict[str, Any]]]) -> tuple[str, str, dict[str, bool]]:
    """Apply the frozen H49R1A selector to structured observations."""
    witnesses = {name: [] for name in ("A", "B", "C", "D", "E")}
    for ruleset_id, corpora in observations.items():
        control = corpora["F48_CONTROL"]
        stable = {name for name, value in corpora.items() if _valid_cell(value, "teacher_40_80") and value["teacher_40_80"].get("exact_best_move_agreement", -1.0) >= 0.85}
        learner_control = _signal(control, "L49_1_2000")
        single_control = _signal(control, "L49_0_2000")
        if "F48_CONTROL" in stable and not single_control and learner_control:
            witnesses["A"].append(ruleset_id)
        structural = [corpora[name]["L49_1_2000"]["mean_flip_rate"] for name in ("S49-M", "S49-E") if name in stable and _signal(corpora[name], "L49_1_2000")]
        if structural and max(structural) - control["L49_1_2000"].get("mean_flip_rate", 0.0) >= 0.05:
            witnesses["B"].append(ruleset_id)
        if not stable:
            witnesses["C"].append(ruleset_id)
        material = any(name in stable and _signal(corpora[name], "L49_1_2000") for name in corpora)
        nonmaterial_valid = any(_nonmaterial_valid(corpora[name], name in stable) for name in corpora)
        nonmaterial = any(_nonmaterial_signal(corpora[name], name in stable) for name in corpora)
        if stable and not material and nonmaterial:
            witnesses["D"].append(ruleset_id)
        if stable and not material and nonmaterial_valid and not nonmaterial:
            witnesses["E"].append(ruleset_id)
    if len(witnesses["A"]) >= 2:
        classification = "LEARNER_ALIGNED_SIGNAL_SUPPORTED"
    elif len(witnesses["B"]) >= 2:
        classification = "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING"
    elif len(witnesses["C"]) >= 2:
        classification = "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING"
    elif len(witnesses["D"]) >= 2:
        classification = "MATERIAL_ONLY_REPRESENTATION_LIMITING"
    elif len(witnesses["E"]) >= 2:
        classification = "EVALUATION_SIGNAL_BROADLY_WEAK"
    else:
        classification = "MIXED_OR_UNRESOLVED"
    mapping = {
        "LEARNER_ALIGNED_SIGNAL_SUPPORTED": "F50_LEARNABLE_MATERIAL_RECOVERY_PROTOCOL_V2",
        "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING": "F50_STRUCTURAL_CORPUS_RECOVERY_PROTOCOL",
        "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING": "F50_NATIVE_SEARCH_STRENGTH_REASSESSMENT",
        "MATERIAL_ONLY_REPRESENTATION_LIMITING": "F50_GENERIC_LEARNABLE_EVALUATOR_EXPANSION",
        "EVALUATION_SIGNAL_BROADLY_WEAK": "F50_SEARCH_DOMINANCE_AND_EVALUATION_ROLE_DIAGNOSIS",
        "MIXED_OR_UNRESOLVED": "F50_LEARNING_ARCHITECTURE_REASSESSMENT",
    }
    return classification, mapping[classification], {name: bool(value) for name, value in witnesses.items()}


def validate_h49r1a_manifest(manifest: dict[str, Any]) -> None:
    if hashlib.sha256(canonical_json({key: value for key, value in manifest.items() if key != "manifest_sha256"}).encode("utf-8")).hexdigest() != manifest.get("manifest_sha256"):
        raise RuntimeError("H49R1A manifest hash mismatch")
    if manifest.get("parent_h49a_sha") != "93eee26a090c5a83487046b9165356fa1187b44e" or manifest.get("h49a_manifest_sha256") != H49A_MANIFEST_SHA:
        raise RuntimeError("H49R1A parent binding drift")
    if manifest.get("protocol_status") != "PRE_REGISTERED_NO_OBSERVED_RESULTS" or manifest.get("measurements_invoked") or manifest.get("learning_invoked"):
        raise RuntimeError("H49R1A contains observed or executed work")
    if manifest.get("production_diff_required") != "ZERO" or manifest.get("master_promotion") is not False:
        raise RuntimeError("H49R1A production scope drift")
    if manifest.get("h48r1a") != {"commit": "7e2f17bdc7ac46aabaa8b1a139c5866f1b0689ab", "manifest_sha256": "cfc9db0c0b25433a6b6c77f0adf41a7b0132dc017daf277f2467edab0270b3cf"}:
        raise RuntimeError("H49R1A inherited direction authority drift")
    expected_dependencies = manifest.get("raw_git_blob_sha256", {})
    if set(expected_dependencies) != {"generic_chess/ai/evaluation/config.py", "generic_chess/learning/features.py", "generic_chess/learning/openings.py", "generic_chess/core/actions.py", "generic_chess/core/identity.py", "generic_chess/native/compiler.py", "generic_chess/native/engine.py"}:
        raise RuntimeError("H49R1A dependency ledger incomplete")
    for path, expected in expected_dependencies.items():
        actual = hashlib.sha256(subprocess.run(["git", "show", f"{manifest['baseline_sha']}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout).hexdigest()
        if actual != expected:
            raise RuntimeError(f"H49R1A dependency hash drift: {path}")
    if manifest.get("source_openings") != {"generator": "generic_chess.learning.openings.generate_arena_openings", "count": 16, "min_plies": 2, "max_plies": 6, "evaluator_or_search_used": False, "strata": {"S49-M": {"seed": 490100}, "S49-E": {"seed": 490200}}}:
        raise RuntimeError("H49R1A source-opening contract drift")
    if manifest.get("stratum_generation", {}).get("attempt_cap_semantics") != "100000 attempts per output position":
        raise RuntimeError("H49R1A attempt-cap semantics drift")
    if manifest.get("event_predicate", {}).get("piece_values_used") is not False or manifest.get("event_predicate", {}).get("game_name_used") is not False:
        raise RuntimeError("H49R1A event predicate is not evaluator neutral")
    if not manifest.get("material_vector_and_directions", {}).get("candidate", "").startswith("P48-0_vector + sign * 0.10 * ||P48-0_vector||2 * normalized_direction"):
        raise RuntimeError("H49R1A direction candidate formula drift")
    if manifest.get("search_contract") != {"max_depth": 12, "quiescence_max_depth": 0, "quiescence_max_nodes": 0, "tt_megabytes": 8, "fresh_engine_per_search": True, "tt_sharing": False, "accepted_termination_reasons": ["completed", "node_limit", "depth_limit"], "null_action_policy": "failed_search", "failed_search_policy": "CELL_INVALID_SEARCH_FAILURE; retain failed positions in denominator"}:
        raise RuntimeError("H49R1A search contract drift")
    if manifest.get("non_material_control", {}).get("fields") != ["dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"] or manifest.get("non_material_control", {}).get("factors") != [0.75, 1.25] or manifest.get("non_material_control", {}).get("budget") != 2000 or manifest.get("non_material_control", {}).get("threshold") != 0.05:
        raise RuntimeError("H49R1A non-material control drift")
    if set(manifest.get("selector", {}).get("mapping", {})) != {"A", "B", "C", "D", "E", "otherwise"}:
        raise RuntimeError("H49R1A selector mapping incomplete")


def load_h49r1a_manifest() -> dict[str, Any]:
    manifest = json.loads(H49R1A_MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49r1a_manifest(manifest)
    return manifest


def validate_h49r2a_manifest(manifest: dict[str, Any]) -> None:
    if hashlib.sha256(canonical_json({key: value for key, value in manifest.items() if key != "manifest_sha256"}).encode("utf-8")).hexdigest() != manifest.get("manifest_sha256"):
        raise RuntimeError("H49R2A manifest hash mismatch")
    if manifest.get("parent_h49r1a_sha") != "cd43e9c97a04c5279ff9791ecf15270756b2f6fa" or manifest.get("h49r1a_manifest_sha256") != H49R1A_MANIFEST_SHA:
        raise RuntimeError("H49R2A parent binding drift")
    if manifest.get("protocol_status") != "PRE_REGISTERED_NO_OBSERVED_RESULTS" or manifest.get("observed_results_present") or manifest.get("measurements_invoked") or manifest.get("learning_invoked"):
        raise RuntimeError("H49R2A contains observed or executed work")
    if manifest.get("production_diff_required") != "ZERO" or manifest.get("master_promotion") is not False:
        raise RuntimeError("H49R2A production scope drift")
    execution = manifest.get("python_nonmaterial_execution", {})
    if execution.get("player_entry_point") != "generic_chess.ai.alphabeta.player.AlphaBetaPlayer.choose_action" or execution.get("search_entry_point") != "generic_chess.ai.alphabeta.search.run_root_search" or execution.get("evaluator_entry_point") != "generic_chess.ai.evaluation.evaluator.Evaluator.evaluate":
        raise RuntimeError("H49R2A Python execution path drift")
    if manifest.get("coefficient_control", {}).get("fields") != ["dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"] or manifest.get("coefficient_control", {}).get("factors") != [0.75, 1.25] or manifest.get("coefficient_control", {}).get("budget") != 2000:
        raise RuntimeError("H49R2A coefficient control drift")
    dependencies = manifest.get("raw_git_blob_sha256", {})
    if len(dependencies) < 40:
        raise RuntimeError("H49R2A expanded dependency ledger is incomplete")
    for path, expected in dependencies.items():
        actual = hashlib.sha256(subprocess.run(["git", "show", f"{manifest['baseline_sha']}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout).hexdigest()
        if actual != expected:
            raise RuntimeError(f"H49R2A dependency hash drift: {path}")
    if manifest.get("liveness_proof") != {"generic_chess/ai/evaluation/evaluator.py": ["dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"], "generic_chess/ai/alphabeta/search.py": ["ctx.evaluator.evaluate", "evaluator.evaluate"], "generic_chess/ai/alphabeta/player.py": ["run_root_search", "self._evaluator"]}:
        raise RuntimeError("H49R2A liveness proof binding drift")
    if set(manifest.get("selector", {}).get("mapping", {})) != {"LEARNER_ALIGNED_SIGNAL_SUPPORTED", "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING", "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING", "MATERIAL_ONLY_REPRESENTATION_LIMITING", "EVALUATION_SIGNAL_BROADLY_WEAK", "MIXED_OR_UNRESOLVED"}:
        raise RuntimeError("H49R2A selector mapping incomplete")


def load_h49r2a_manifest() -> dict[str, Any]:
    manifest = json.loads(H49R2A_MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49r2a_manifest(manifest)
    verify_nonmaterial_liveness()
    return manifest


def _git_blob_sha256(ref: str, path: str) -> str:
    raw = subprocess.run(
        ["git", "cat-file", "blob", f"{ref}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return hashlib.sha256(raw).hexdigest()


def source_tree_ledger(ref: str = F48_BASELINE_SHA) -> dict[str, Any]:
    """Return the fail-closed raw ledger for every tracked generic_chess file."""
    paths = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "generic_chess/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    files = [{"path": path, "sha256": _git_blob_sha256(ref, path)} for path in paths]
    files.sort(key=lambda item: item["path"])
    aggregate = hashlib.sha256(canonical_json(files).encode("utf-8")).hexdigest()
    return {"baseline_sha": ref, "file_count": len(files), "aggregate_sha256": aggregate, "files": files}


def current_native_runtime_provenance() -> dict[str, Any]:
    """Capture the exact loaded native binary and its build/runtime identity."""
    from generic_chess.native import native_capabilities, native_version
    import generic_chess._native_core as native_module

    binary = Path(native_module.__file__).resolve()
    try:
        relative = binary.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise RuntimeError("NATIVE_BINARY_OUTSIDE_REPOSITORY_ROOT") from exc
    capabilities = dict(native_capabilities())
    return {
        "python_implementation": sys.implementation.name,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "native_module_path": relative,
        "native_module_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "native_module_size_bytes": binary.stat().st_size,
        "native_version": native_version(),
        "native_schema_version": capabilities.get("native_schema"),
        "semantic_payload_version": capabilities.get("semantic_payload_version"),
        "native_capabilities": capabilities,
        "build_authority": {
            "pyproject.toml": _git_blob_sha256(F48_BASELINE_SHA, "pyproject.toml"),
            "scripts/build_native_zig.py": _git_blob_sha256(F48_BASELINE_SHA, "scripts/build_native_zig.py"),
        },
    }


def historical_native_runtime_provenance(runtime: dict[str, Any]) -> dict[str, Any]:
    """Validate an immutable runtime record without substituting today's binary.

    H49R3A is historical evidence.  Its binary is intentionally not tracked in
    Git, so reloading the current extension cannot certify its old hash.  The
    record remains bound to the historical build-authority blobs and its own
    immutable manifest hash; current runtime checks belong to the active
    checkpoint, not this historical validator.
    """
    required = {
        "native_module_path", "native_module_sha256", "native_module_size_bytes",
        "native_schema_version", "semantic_payload_version", "native_capabilities",
        "build_authority",
    }
    if not required.issubset(runtime):
        raise RuntimeError("historical native runtime record is incomplete")
    if not str(runtime["native_module_path"]).startswith("generic_chess/"):
        raise RuntimeError("historical native module path escaped repository")
    digest = str(runtime["native_module_sha256"])
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise RuntimeError("historical native module hash is malformed")
    if int(runtime["native_module_size_bytes"]) <= 0:
        raise RuntimeError("historical native module size is invalid")
    if runtime["build_authority"] != {
        "pyproject.toml": _git_blob_sha256(F48_BASELINE_SHA, "pyproject.toml"),
        "scripts/build_native_zig.py": _git_blob_sha256(F48_BASELINE_SHA, "scripts/build_native_zig.py"),
    }:
        raise RuntimeError("historical native build authority drift")
    return runtime


def build_h49r3a_primary_execution() -> dict[str, Any]:
    """Build the three bound execution objects without running a search."""
    from generic_chess.generation.config import GeneratorConfig
    from generic_chess.generation.generator import generate_game
    from generic_chess.rules.compiler import (
        _build_semantic_support,
        compile_ruleset_for_execution,
        compile_semantic_ir,
    )
    from generic_chess.rules.execution import ExecutableSemanticRuleset
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from generic_chess.rules.western_chess import build_western_chess_ruleset

    definitions = {
        "A_CANONICAL_WESTERN_CHESS": build_western_chess_ruleset(),
        "B_CANONICAL_STANDARD_SHOGI": build_standard_shogi_ruleset(),
        "C_H48B_SELECTED_GENERATED": generate_game(
            GeneratorConfig(seed=20260807009, board_size=6, setup_preset="free_random")
        ).ruleset,
    }
    output: dict[str, Any] = {}
    for ruleset_id, ruleset in definitions.items():
        compiled = compile_ruleset_for_execution(ruleset)
        if isinstance(compiled, ExecutableSemanticRuleset):
            executable = compiled
        else:
            # H48B candidate 9 is intentionally legacy-shaped.  Lower that
            # exact compiled object into the existing semantic execution
            # adapter; do not compile a second RuleSet or change its identity.
            legacy_ir = compile_semantic_ir(compiled)
            legacy_ir = replace(
                legacy_ir,
                capabilities=replace(legacy_ir.capabilities, new_ir_core_executable=True),
            )
            executable = ExecutableSemanticRuleset(
                ir=legacy_ir,
                _legacy_compiled=compiled,
                support=_build_semantic_support(compiled),
            )
        legacy = executable._legacy_compiled
        if legacy.ruleset_fingerprint != executable.ruleset_fingerprint:
            raise RuntimeError(f"RULESET_TRANSPORT_FINGERPRINT_MISMATCH: {ruleset_id}")
        if executable.ruleset_fingerprint != RULESET_FINGERPRINTS[ruleset_id]:
            raise RuntimeError(f"RULESET_FINGERPRINT_MISMATCH: {ruleset_id}")
        output[ruleset_id] = {
            "ruleset": ruleset,
            "semantic_execution": executable,
            "legacy_transport": legacy,
        }
    return output


def validate_h49r3a_execution_bindings() -> dict[str, Any]:
    """Require native legality or an explicit fail-closed stop status."""
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.rules.execution import ExecutableSemanticRuleset

    executions = build_h49r3a_primary_execution()
    result = {}
    for ruleset_id, entry in executions.items():
        executable = entry["semantic_execution"]
        if not isinstance(executable, ExecutableSemanticRuleset):
            raise RuntimeError(f"NONMATERIAL_CONTROL_NATIVE_LEGALITY_UNAVAILABLE: {ruleset_id}")
        player = AlphaBetaPlayer(
            executable,
            tt_max_entries=250000,
            use_disk_cache=False,
            use_tt=True,
            use_ordering=True,
            use_native_semantic_legality=True,
        )
        if player.compiled is not executable:
            raise RuntimeError(f"NONMATERIAL_CONTROL_EXECUTION_OBJECT_MISMATCH: {ruleset_id}")
        expected = RULESET_FINGERPRINTS[ruleset_id]
        provider = player.native_legality_provider
        if provider is None:
            result[ruleset_id] = {
                "semantic_execution_type": type(executable).__name__,
                "ruleset_fingerprint": executable.ruleset_fingerprint,
                "legacy_transport_fingerprint": entry["legacy_transport"].ruleset_fingerprint,
                "player_compiled_type": type(player.compiled).__name__,
                "native_legality_provider": False,
                "status": "NONMATERIAL_CONTROL_NATIVE_LEGALITY_UNAVAILABLE",
            }
            continue
        if provider.compiled.ruleset_fingerprint != expected:
            raise RuntimeError(f"NATIVE_LEGALITY_FINGERPRINT_MISMATCH: {ruleset_id}")
        if provider.native_rules.fingerprint != expected:
            raise RuntimeError(f"NATIVE_LEGALITY_FINGERPRINT_MISMATCH: {ruleset_id}")
        result[ruleset_id] = {
            "semantic_execution_type": type(executable).__name__,
            "ruleset_fingerprint": executable.ruleset_fingerprint,
            "legacy_transport_fingerprint": entry["legacy_transport"].ruleset_fingerprint,
            "player_compiled_type": type(player.compiled).__name__,
            "native_legality_provider": True,
            "provider_compiled_fingerprint": provider.native_rules.fingerprint,
            "status": "VALID",
        }
    return result


def validate_h49r3a_manifest(manifest: dict[str, Any]) -> None:
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise RuntimeError("H49R3A manifest hash mismatch")
    if manifest.get("checkpoint_name") != "H49R3A":
        raise RuntimeError("H49R3A checkpoint drift")
    if manifest.get("parent_h49r2a_sha") != "628c4c5a34f547a413fb56d5295b71d2f4dcf1f1" or manifest.get("h49r2a_manifest_sha256") != H49R2A_MANIFEST_SHA:
        raise RuntimeError("H49R3A parent binding drift")
    if manifest.get("baseline_sha") != F48_BASELINE_SHA:
        raise RuntimeError("H49R3A baseline drift")
    if manifest.get("protocol_status") != "PRE_REGISTERED_NO_OBSERVED_RESULTS" or manifest.get("observed_results_present") or manifest.get("measurements_invoked") or manifest.get("learning_invoked"):
        raise RuntimeError("H49R3A contains observed or executed work")
    if manifest.get("production_diff_required") != "ZERO" or manifest.get("master_promotion") is not False:
        raise RuntimeError("H49R3A production scope drift")
    if manifest.get("ruleset_fingerprints") != RULESET_FINGERPRINTS:
        raise RuntimeError("H49R3A RuleSet fingerprint drift")
    execution = manifest.get("execution_compilation", {})
    if execution.get("entry_point") != "generic_chess.rules.compiler.compile_ruleset_for_execution":
        raise RuntimeError("H49R3A execution compiler drift")
    if execution.get("generated_candidate") != {"seed": 20260807009, "board_size": 6, "setup_preset": "free_random", "source": "H48B candidate index 9 high-level RuleSet"}:
        raise RuntimeError("H49R3A generated candidate construction drift")
    if execution.get("semantic_execution_type") != "generic_chess.rules.execution.ExecutableSemanticRuleset":
        raise RuntimeError("H49R3A semantic execution type drift")
    if execution.get("legacy_transport") != "semantic_execution_ruleset._legacy_compiled":
        raise RuntimeError("H49R3A legacy transport drift")
    if execution.get("separate_ruleset_compilation") is not False:
        raise RuntimeError("H49R3A permits an alternative RuleSet compilation")
    legality = manifest.get("python_nonmaterial_legality", {})
    if legality.get("use_native_semantic_legality") is not True or legality.get("provider_required") is not True or legality.get("silent_fallback") is not False:
        raise RuntimeError("H49R3A Python legality binding drift")
    if legality.get("unavailable_status") != "NONMATERIAL_CONTROL_NATIVE_LEGALITY_UNAVAILABLE":
        raise RuntimeError("H49R3A Python legality failure status drift")
    source_tree = manifest.get("generic_chess_source_tree", {})
    actual_tree = source_tree_ledger(manifest["baseline_sha"])
    if source_tree != actual_tree:
        raise RuntimeError("H49R3A complete source-tree ledger drift")
    omitted_required = {
        "generic_chess/ai/evaluation/mobility.py",
        "generic_chess/ai/evaluation/movement_graph.py",
        "generic_chess/rules/compiler.py",
        "generic_chess/rules/ir.py",
        "generic_chess/native/semantic.py",
        "generic_chess/_native/native_module.c",
        "generic_chess/_native/native_semantic_rules.c",
    }
    if not omitted_required.issubset({item["path"] for item in source_tree["files"]}):
        raise RuntimeError("H49R3A source-tree ledger omitted required execution files")
    runtime = manifest.get("native_runtime_provenance", {})
    for key in ("python_implementation", "python_version", "platform", "machine", "native_module_path", "native_module_sha256", "native_version", "native_schema_version", "semantic_payload_version", "build_authority"):
        if key not in runtime:
            raise RuntimeError(f"H49R3A native provenance missing: {key}")
    if runtime["build_authority"] != {
        "pyproject.toml": _git_blob_sha256(F48_BASELINE_SHA, "pyproject.toml"),
        "scripts/build_native_zig.py": _git_blob_sha256(F48_BASELINE_SHA, "scripts/build_native_zig.py"),
    }:
        raise RuntimeError("H49R3A native build authority drift")
    historical_native_runtime_provenance(runtime)
    if set(manifest.get("selector", {}).get("mapping", {})) != {"LEARNER_ALIGNED_SIGNAL_SUPPORTED", "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING", "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING", "MATERIAL_ONLY_REPRESENTATION_LIMITING", "EVALUATION_SIGNAL_BROADLY_WEAK", "MIXED_OR_UNRESOLVED"}:
        raise RuntimeError("H49R3A selector mapping incomplete")


def load_h49r3a_manifest() -> dict[str, Any]:
    manifest = json.loads(H49R3A_MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49r3a_manifest(manifest)
    verify_nonmaterial_liveness()
    return manifest


def validate_h49r4a_python_legality_bindings() -> dict[str, Any]:
    """Freeze one explicit Python-authority legality route for all RuleSets."""
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.rules.execution import ExecutableSemanticRuleset

    executions = build_h49r3a_primary_execution()
    result = {}
    for ruleset_id, entry in executions.items():
        executable = entry["semantic_execution"]
        if not isinstance(executable, ExecutableSemanticRuleset):
            raise RuntimeError(f"NONMATERIAL_CONTROL_EXECUTION_OBJECT_MISMATCH: {ruleset_id}")
        player = AlphaBetaPlayer(
            executable,
            tt_max_entries=250000,
            use_disk_cache=False,
            use_tt=True,
            use_ordering=True,
            use_native_semantic_legality=False,
        )
        if player.compiled is not executable or player.native_legality_provider is not None:
            raise RuntimeError(f"NONMATERIAL_CONTROL_PYTHON_LEGALITY_BINDING_MISMATCH: {ruleset_id}")
        if player.compiled.ruleset_fingerprint != RULESET_FINGERPRINTS[ruleset_id]:
            raise RuntimeError(f"RULESET_FINGERPRINT_MISMATCH: {ruleset_id}")
        result[ruleset_id] = {
            "player_compiled_type": type(player.compiled).__name__,
            "ruleset_fingerprint": player.compiled.ruleset_fingerprint,
            "native_legality_provider": None,
            "legality_route": "PYTHON_AUTHORITY",
        }
    return result


def validate_h49r4a_manifest(manifest: dict[str, Any]) -> None:
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise RuntimeError("H49R4A manifest hash mismatch")
    if manifest.get("checkpoint_name") != "H49R4A":
        raise RuntimeError("H49R4A checkpoint drift")
    if manifest.get("work_order_id") != "GENERICCHESS-F49-CORRECTIVE-R4-NONMATERIAL-AVAILABILITY-AND-SELECTOR-CLOSURE":
        raise RuntimeError("H49R4A work order drift")
    if manifest.get("parent_h49r3a_sha") != H49R3A_SHA or manifest.get("h49r3a_manifest_sha256") != H49R3A_MANIFEST_SHA:
        raise RuntimeError("H49R4A parent binding drift")
    if manifest.get("protocol_status") != "PRE_REGISTERED_NO_OBSERVED_RESULTS" or manifest.get("observed_results_present") or manifest.get("measurements_invoked") or manifest.get("learning_invoked"):
        raise RuntimeError("H49R4A contains observed or executed work")
    if manifest.get("production_diff_required") != "ZERO" or manifest.get("master_promotion") is not False:
        raise RuntimeError("H49R4A production scope drift")
    if manifest.get("h49r3a_erratum") != {
        "historical_manifest_field": "work_order_id",
        "historical_value": "GENERICCHESS-F49-CORRECTIVE-R2-METRIC-SCHEMA-AND-NONMATERIAL-EXECUTION-CLOSURE",
        "correct_value": "GENERICCHESS-F49-CORRECTIVE-R3-EXECUTION-DEPENDENCY-AND-RULESET-BINDING-CLOSURE",
        "immutable_commit": H49R3A_SHA,
        "immutable_manifest_sha256": H49R3A_MANIFEST_SHA,
    }:
        raise RuntimeError("H49R4A H49R3A erratum drift")
    legality = manifest.get("python_full_evaluator_nonmaterial_control", {})
    if legality.get("label") != "PYTHON_FULL_EVALUATOR_NONMATERIAL_CONTROL" or legality.get("use_native_semantic_legality") is not False or legality.get("native_legality_provider") is not None or legality.get("route") != "PYTHON_AUTHORITY":
        raise RuntimeError("H49R4A non-material legality route drift")
    if legality.get("player_entry_point") != "generic_chess.ai.alphabeta.player.AlphaBetaPlayer.choose_action" or legality.get("search_entry_point") != "generic_chess.ai.alphabeta.search.run_root_search" or legality.get("evaluator_entry_point") != "generic_chess.ai.evaluation.evaluator.Evaluator.evaluate":
        raise RuntimeError("H49R4A Python evaluator path drift")
    if legality.get("settings") != {
        "tt_max_entries": 250000,
        "use_disk_cache": False,
        "use_tt": True,
        "use_ordering": True,
        "max_nodes": 2000,
        "max_depth": None,
        "max_time_seconds": None,
        "qsearch_depth": 4,
        "qsearch_hard_depth": 8,
        "qsearch_nodes": None,
        "deterministic": True,
        "fresh_player_evaluator_profile_cache_tt_session_context_per_evaluator_position": True,
    }:
        raise RuntimeError("H49R4A Python search settings drift")
    statuses = manifest.get("non_material_cell_status", {})
    if set(statuses.get("allowed", ())) != NONMATERIAL_CELL_STATUSES or statuses.get("non_valid_signal") is not None or statuses.get("valid_requires") != ["every coefficient family", "factors 0.75 and 1.25", "per-factor flip rates", "failed searches", "family_mean_flip", "non_material_signal"]:
        raise RuntimeError("H49R4A non-material cell schema drift")
    selector = manifest.get("selector", {})
    if selector.get("unavailable_is_negative_evidence") is not False or selector.get("nonmaterial_valid_definition") != "stable AND non_material_control.status == VALID" or selector.get("nonmaterial_signal_definition") != "nonmaterial_valid AND non_material_control.non_material_signal == true":
        raise RuntimeError("H49R4A selector validity drift")
    if set(selector.get("mapping", {})) != {"LEARNER_ALIGNED_SIGNAL_SUPPORTED", "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING", "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING", "MATERIAL_ONLY_REPRESENTATION_LIMITING", "EVALUATION_SIGNAL_BROADLY_WEAK", "MIXED_OR_UNRESOLVED"}:
        raise RuntimeError("H49R4A selector mapping incomplete")


def load_h49r4a_manifest() -> dict[str, Any]:
    manifest = json.loads(H49R4A_MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49r4a_manifest(manifest)
    load_h49r3a_manifest()
    verify_nonmaterial_liveness()
    return manifest


def verify_nonmaterial_liveness() -> dict[str, Any]:
    """Prove the selected Python path reads each non-material coefficient."""
    sources = {
        "generic_chess/ai/evaluation/evaluator.py": ("dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"),
        "generic_chess/ai/alphabeta/search.py": ("ctx.evaluator.evaluate", "evaluator.evaluate"),
        "generic_chess/ai/alphabeta/player.py": ("run_root_search", "self._evaluator"),
    }
    proof = {}
    for path, needles in sources.items():
        source = subprocess.run(["git", "show", f"{F48_BASELINE_SHA}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
        missing = [needle for needle in needles if needle not in source]
        if missing:
            raise RuntimeError(f"UNMEASURABLE_IN_SELECTED_SEARCH_PATH: {path}: {missing}")
        proof[path] = {needle: True for needle in needles}
    return proof


if __name__ == "__main__":
    value = load_h49r4a_manifest()
    validate_h49r4a_python_legality_bindings()
    print(json.dumps({"status": "PASS", "kind": value["kind"], "next_boundary": value["next_authorized_boundary"]}))
