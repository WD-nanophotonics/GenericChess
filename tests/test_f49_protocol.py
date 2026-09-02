"""H49A protocol checkpoint tests; no F49 measurements are permitted here."""

from __future__ import annotations

import copy

import pytest

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square

from scripts.f49_protocol import (
    aggregate_leverage_cells,
    canonical_action_order_key,
    derive_stratum_candidate_seed,
    inventory_event_flags,
    load_h49a_manifest,
    load_h49r1a_manifest,
    material_vector_coordinate_order,
    raw_direction,
    select_f49_classification,
    teacher_pair_metrics,
    validate_h49a_manifest,
    validate_h49r1a_manifest,
    load_h49r2a_manifest,
    validate_h49r2a_manifest,
    verify_nonmaterial_liveness,
    build_h49r3a_primary_execution,
    current_native_runtime_provenance,
    load_h49r3a_manifest,
    source_tree_ledger,
    validate_h49r3a_execution_bindings,
    validate_h49r3a_manifest,
)


def test_h49a_is_signed_protocol_only_and_freezes_diagnostics():
    manifest = load_h49a_manifest()
    assert manifest["kind"] == "H49A_F49_LEARNING_SIGNAL_ARCHITECTURE_PROTOCOL"
    assert manifest["f48_classification"] == "MIXED_OR_UNRESOLVED"
    assert manifest["f48_next_boundary"] == "F49_LEARNING_ARCHITECTURE_REASSESSMENT"
    assert manifest["f49_status"] == "DIAGNOSIS_ONLY"
    assert manifest["observed_results_present"] is False
    assert manifest["measurements_invoked"] is False
    assert manifest["learning_invoked"] is False
    assert set(manifest["diagnostic_strata"]) == {"S49-M", "S49-E"}
    assert manifest["classification"]["precedence"] == list(manifest["classification"]["mapping"])


def test_h49a_rejects_tampered_manifest():
    original = load_h49a_manifest()
    tampered = copy.deepcopy(original)
    tampered["measurements_invoked"] = True
    with pytest.raises(RuntimeError, match="manifest hash"):
        validate_h49a_manifest(tampered)


def test_h49r1a_binds_all_executable_contracts_and_dependencies():
    manifest = load_h49r1a_manifest()
    assert manifest["checkpoint_name"] == "H49R1A"
    assert manifest["source_openings"]["count"] == 16
    assert manifest["stratum_generation"]["attempt_cap_semantics"] == "100000 attempts per output position"
    assert manifest["search_contract"]["accepted_termination_reasons"] == ["completed", "node_limit", "depth_limit"]
    assert manifest["non_material_control"]["fields"] == ["dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"]
    assert len(manifest["raw_git_blob_sha256"]) == 7
    assert manifest["observed_results_present"] is False


def test_h49r1a_executable_helpers_are_mechanical():
    assert material_vector_coordinate_order(("A", "B")) == ("board[A]", "board[B]", "hand[A]", "hand[B]")
    direction = raw_direction("seeded_normalized_pseudorandom", 8)
    assert len(direction) == 8
    assert sum(value * value for value in direction) == pytest.approx(1.0)
    assert derive_stratum_candidate_seed("S49-M", 490100, 0, 0) == derive_stratum_candidate_seed("S49-M", 490100, 0, 0)
    assert canonical_action_order_key(BoardMove(Square(0, 0), Square(0, 1))) == '{"from":[0,0],"kind":"board","promotion_target_id":null,"to":[0,1]}'
    assert inventory_event_flags({"board": {"A": 2}, "inventory": {}}, {"board": {"A": 1}, "inventory": {}})["remove_or_capture_effect"]
    assert inventory_event_flags({"board": {"A": 2}, "inventory": {}}, {"board": {"B": 2}, "inventory": {}})["type_or_promotion_transformation"]
    assert inventory_event_flags({"board": {"A": 2}, "inventory": {}}, {"board": {"A": 2}, "inventory": {"A": 1}})["hand_or_inventory_count_change"]
    assert aggregate_leverage_cells([{"status": "VALID", "failed_searches": 0, "flip_rate": 0.0}, {"status": "VALID", "failed_searches": 0, "flip_rate": 0.1}])["mean_flip_rate"] == pytest.approx(0.05)
    assert aggregate_leverage_cells([{"status": "CELL_INVALID_SEARCH_FAILURE", "failed_searches": 1, "flip_rate": 1.0}])["status"] == "CELL_INVALID_SEARCH_FAILURE"
    assert aggregate_leverage_cells([{"status": "VALID", "failed_searches": 0, "flip_rate": 0.1}, {"construction_failed": True, "status": "CONSTRUCTION_FAILED"}])["mean_flip_rate"] == pytest.approx(0.1)
    assert aggregate_leverage_cells([{"status": "VALID", "failed_searches": 0, "flip_rate": 0.1}, {"status": "CELL_INVALID_SEARCH_FAILURE", "failed_searches": 1, "flip_rate": 0.0}])["status"] == "CELL_INVALID_SEARCH_FAILURE"
    assert aggregate_leverage_cells([{"construction_failed": True}, {"construction_failed": True}])["status"] == "NO_USABLE_PERTURBATIONS"
    assert teacher_pair_metrics(["a", "b"], ["a", "c"], [-1.0, 0.0], [1.0, 0.0])["score_sign_agreement"] == pytest.approx(0.5)


def _observation(stable=True, control_learner=0.0, structural=0.0, nonmaterial=False):
    teacher = {"status": "VALID", "failed_searches": 0, "exact_best_move_agreement": 0.9} if stable else {"status": "UNAVAILABLE", "failed_searches": 0, "exact_best_move_agreement": 0.0}
    def corpus(value, nonmaterial_value=False):
        return {"teacher_40_80": teacher, "L49_0_2000": {"status": "VALID", "failed_searches": 0, "mean_flip_rate": 0.0}, "L49_1_2000": {"status": "VALID", "failed_searches": 0, "mean_flip_rate": value}, "non_material_signal": nonmaterial_value}
    return {"F48_CONTROL": corpus(control_learner, nonmaterial), "S49-M": corpus(structural, nonmaterial), "S49-E": corpus(structural, nonmaterial)}


def test_h49r1a_selector_reaches_all_six_frozen_paths():
    cases = [
        ({"a": _observation(True, 0.1, 0.0, False), "b": _observation(True, 0.1, 0.0, False), "c": _observation(True, 0.0, 0.0, False)}, "LEARNER_ALIGNED_SIGNAL_SUPPORTED"),
        ({"a": _observation(True, 0.0, 0.1, False), "b": _observation(True, 0.0, 0.1, False), "c": _observation(True, 0.0, 0.0, False)}, "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING"),
        ({"a": _observation(False), "b": _observation(False), "c": _observation(True, 0.0, 0.0, False)}, "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING"),
        ({"a": _observation(True, 0.0, 0.0, True), "b": _observation(True, 0.0, 0.0, True), "c": _observation(True, 0.0, 0.0, False)}, "MATERIAL_ONLY_REPRESENTATION_LIMITING"),
        ({"a": _observation(True), "b": _observation(True), "c": _observation(True)}, "EVALUATION_SIGNAL_BROADLY_WEAK"),
        ({"a": _observation(True, 0.0, 0.0, True), "b": _observation(True, 0.1, 0.0, False), "c": _observation(False)}, "MIXED_OR_UNRESOLVED"),
    ]
    for observations, expected in cases:
        assert select_f49_classification(observations)[0] == expected


def test_h49r1a_rejects_tampered_manifest():
    manifest = load_h49r1a_manifest()
    tampered = copy.deepcopy(manifest)
    tampered["search_contract"]["tt_megabytes"] = 16
    with pytest.raises(RuntimeError, match="manifest hash"):
        validate_h49r1a_manifest(tampered)


def test_h49r1a_selector_uses_exact_teacher_schema_without_agreement_alias():
    stable = _observation(True)
    for corpus in stable.values():
        corpus["teacher_40_80"].pop("agreement", None)
        corpus["teacher_40_80"]["exact_best_move_agreement"] = 0.9
    assert select_f49_classification({"a": stable, "b": stable, "c": stable}) == ("EVALUATION_SIGNAL_BROADLY_WEAK", "F50_SEARCH_DOMINANCE_AND_EVALUATION_ROLE_DIAGNOSIS", {"A": False, "B": False, "C": False, "D": False, "E": True})
    unstable = _observation(True)
    for corpus in unstable.values():
        corpus["teacher_40_80"] = {"status": "VALID", "failed_searches": 0, "exact_best_move_agreement": 0.5, "agreement": 0.99}
    assert select_f49_classification({"a": unstable, "b": unstable, "c": unstable})[0] == "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING"


def test_h49r2a_binds_python_nonmaterial_path_and_live_coefficients():
    manifest = load_h49r2a_manifest()
    assert manifest["python_nonmaterial_execution"]["player_entry_point"].endswith("AlphaBetaPlayer.choose_action")
    assert manifest["coefficient_control"]["candidate_formula"] == "candidate_field = baseline_field * factor"
    assert manifest["observed_results_present"] is False
    assert len(manifest["raw_git_blob_sha256"]) >= 40
    proof = verify_nonmaterial_liveness()
    assert set(proof["generic_chess/ai/evaluation/evaluator.py"]) == {"dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"}


def test_h49r2a_rejects_tampered_contract():
    manifest = load_h49r2a_manifest()
    tampered = copy.deepcopy(manifest)
    tampered["python_nonmaterial_execution"]["limits"]["max_nodes"] = 4000
    with pytest.raises(RuntimeError, match="manifest hash"):
        validate_h49r2a_manifest(tampered)


def test_h49r3a_freezes_parent_execution_routes_and_no_measurements():
    manifest = load_h49r3a_manifest()
    assert manifest["checkpoint_name"] == "H49R3A"
    assert manifest["parent_h49r2a_sha"] == "628c4c5a34f547a413fb56d5295b71d2f4dcf1f1"
    assert manifest["h49r2a_manifest_sha256"] == "9b6b98997b7656f845283b20297d325c83c8451c6da55255e3f481e638e9beaf"
    assert manifest["observed_results_present"] is False
    assert manifest["measurements_invoked"] is False
    assert manifest["learning_invoked"] is False
    assert manifest["execution_compilation"]["separate_ruleset_compilation"] is False
    assert manifest["execution_compilation"]["generated_candidate"] == {
        "seed": 20260807009,
        "board_size": 6,
        "setup_preset": "free_random",
        "source": "H48B candidate index 9 high-level RuleSet",
    }


def test_h49r3a_primary_rulesets_reproduce_fingerprints_and_legacy_binding():
    executions = build_h49r3a_primary_execution()
    assert set(executions) == {
        "A_CANONICAL_WESTERN_CHESS",
        "B_CANONICAL_STANDARD_SHOGI",
        "C_H48B_SELECTED_GENERATED",
    }
    for entry in executions.values():
        semantic = entry["semantic_execution"]
        legacy = entry["legacy_transport"]
        assert semantic.ruleset_fingerprint == legacy.ruleset_fingerprint
        assert semantic._legacy_compiled is legacy
    assert executions["C_H48B_SELECTED_GENERATED"]["ruleset"].metadata["seed"] == 20260807009
    assert executions["C_H48B_SELECTED_GENERATED"]["ruleset"].metadata["setup_preset"] == "free_random"


def test_h49r3a_requires_nonnull_native_legality_provider_without_fallback():
    bound = validate_h49r3a_execution_bindings()
    assert set(bound) == {
        "A_CANONICAL_WESTERN_CHESS",
        "B_CANONICAL_STANDARD_SHOGI",
        "C_H48B_SELECTED_GENERATED",
    }
    assert bound["C_H48B_SELECTED_GENERATED"]["native_legality_provider"] is True
    assert bound["C_H48B_SELECTED_GENERATED"]["status"] == "VALID"
    assert all(
        row["native_legality_provider"] is True
        or row["status"] == "NONMATERIAL_CONTROL_NATIVE_LEGALITY_UNAVAILABLE"
        for row in bound.values()
    )
    assert all(row["player_compiled_type"] == "ExecutableSemanticRuleset" for row in bound.values())
    assert bound["C_H48B_SELECTED_GENERATED"]["ruleset_fingerprint"] == bound["C_H48B_SELECTED_GENERATED"]["provider_compiled_fingerprint"]
    assert all(row["ruleset_fingerprint"] == row["legacy_transport_fingerprint"] for row in bound.values())


def test_h49r3a_complete_source_tree_and_native_provenance_are_frozen():
    manifest = load_h49r3a_manifest()
    tree = manifest["generic_chess_source_tree"]
    assert tree["file_count"] == 212
    assert tree["aggregate_sha256"] == "10b3752af976844908a773ef3f017d92c2004b29fc82e9ffaf7c21acccd7bff7"
    assert tree == source_tree_ledger()
    paths = {item["path"] for item in tree["files"]}
    assert {
        "generic_chess/ai/evaluation/mobility.py",
        "generic_chess/ai/evaluation/movement_graph.py",
        "generic_chess/rules/compiler.py",
        "generic_chess/rules/ir.py",
        "generic_chess/native/semantic.py",
        "generic_chess/_native/native_module.c",
        "generic_chess/_native/native_semantic_rules.c",
    } <= paths
    runtime = manifest["native_runtime_provenance"]
    current = current_native_runtime_provenance()
    assert runtime == current
    assert runtime["native_schema_version"] == "native-0.5.0"
    assert runtime["semantic_payload_version"] == 2
    assert runtime["native_module_sha256"] == "ae6358d7caf71b3e5d33d4673c61b75fce3342ad25ae5d6482f29bf4761a1614"
    assert set(runtime["build_authority"]) == {"pyproject.toml", "scripts/build_native_zig.py"}


def test_h49r3a_rejects_tampered_parent_or_provenance():
    manifest = load_h49r3a_manifest()
    tampered = copy.deepcopy(manifest)
    tampered["parent_h49r2a_sha"] = "wrong"
    tampered["manifest_sha256"] = __import__("scripts.f49_protocol", fromlist=["_manifest_sha"])._manifest_sha(tampered)
    with pytest.raises(RuntimeError, match="parent binding"):
        validate_h49r3a_manifest(tampered)
