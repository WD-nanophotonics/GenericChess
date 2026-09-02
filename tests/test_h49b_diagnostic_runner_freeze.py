"""Tests for the pre-measurement H49B runner-freeze checkpoint."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest

from scripts.audit_f49_learning_signal_architecture import (
    H49B_KIND,
    H49B_WORK_ORDER_ID,
    H49R4A_MANIFEST_SHA,
    H49R4A_SHA,
    H49R3A_NATIVE_SHA,
    H49R3A_SOURCE_TREE_SHA,
    MANIFEST_PATH,
    PARTITION_INPUT_FIELDS,
    ROOT,
    load_preflight_manifest,
    validate_preflight_manifest,
)


def test_h49b_freezes_only_the_pre_measurement_boundary():
    manifest = load_preflight_manifest()
    assert manifest["kind"] == H49B_KIND
    assert manifest["checkpoint_name"] == "H49B"
    assert manifest["work_order_id"] == H49B_WORK_ORDER_ID
    assert manifest["parent_h49r4a_sha"] == H49R4A_SHA
    assert manifest["h49r4a_manifest_sha256"] == H49R4A_MANIFEST_SHA
    assert manifest["observed_results_present"] is False
    assert manifest["measurements_invoked"] is False
    assert manifest["learning_invoked"] is False
    assert manifest["master_promotion"] is False
    assert manifest["production_diff_required"] == "ZERO"
    assert manifest["next_boundary"] == H49B_WORK_ORDER_ID


def test_h49b_binds_authority_runtime_rulesets_and_python_legality():
    manifest = load_preflight_manifest()
    authority = manifest["authority"]
    assert authority["h49r3a_source_tree_aggregate_sha256"] == H49R3A_SOURCE_TREE_SHA
    assert authority["native_runtime_provenance"]["native_module_sha256"] == H49R3A_NATIVE_SHA
    assert authority["generic_chess_diff_from_h49r4a"] == "ZERO"
    assert set(authority["ruleset_fingerprints"]) == {
        "A_CANONICAL_WESTERN_CHESS",
        "B_CANONICAL_STANDARD_SHOGI",
        "C_H48B_SELECTED_GENERATED",
    }
    assert all(row["legality_route"] == "PYTHON_AUTHORITY" for row in authority["python_legality_bindings"].values())
    assert all(row["native_legality_provider"] is None for row in authority["python_legality_bindings"].values())


def test_h49b_preserves_exact_f48_control_and_p48_zero_authority():
    manifest = load_preflight_manifest()
    control = manifest["f48_control"]
    assert control["authority_only"] is True
    assert (control["seed"], control["count"], control["min_plies"], control["max_plies"]) == (480703, 64, 2, 6)
    assert control["source_openings"] == {"count": 16, "min_plies": 2, "max_plies": 6}
    assert {row["identity_set_count"] for row in control["corpora"].values()} == {31, 32, 34}
    for row in manifest["p48_0_checkpoints"].values():
        assert row["checkpoint_id"]
        assert row["config_hash"]
        assert row["generation"] == 0


def test_h49b_partition_hashes_bind_every_required_input_without_observations():
    manifest = load_preflight_manifest()
    assert manifest["partition_input_fields"] == list(PARTITION_INPUT_FIELDS)
    assert len(manifest["partition_templates"]) == 3 * 3 * 8
    for partition in manifest["partition_templates"]:
        assert partition["observed_results_present"] is False
        assert set(partition["input_identity"]) == set(PARTITION_INPUT_FIELDS)
        assert len(partition["input_hash"]) == 64
        if partition["corpus_slot"] != "F48_CONTROL":
            assert partition["reusable_before_observation"] is False


def test_h49b_manifest_has_no_observed_position_or_search_result_payload():
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    assert "position_keys" not in raw
    assert "search_results" not in raw
    assert "observed_results_present\":true" not in raw


def test_h49b_rejects_observation_or_runner_entrypoint_drift():
    manifest = load_preflight_manifest()
    observed = copy.deepcopy(manifest)
    observed["observed_results_present"] = True
    from scripts.audit_f49_learning_signal_architecture import _manifest_sha

    observed["manifest_sha256"] = _manifest_sha(observed)
    with pytest.raises(RuntimeError, match="observed"):
        validate_preflight_manifest(observed)

    entrypoint = copy.deepcopy(manifest)
    entrypoint["runner"]["measurement_entry_points"] = ["forbidden"]
    entrypoint["manifest_sha256"] = _manifest_sha(entrypoint)
    with pytest.raises(RuntimeError, match="implementation-freeze"):
        validate_preflight_manifest(entrypoint)


def test_h49b_keeps_production_tree_unchanged_from_h49r4a():
    assert subprocess.run(["git", "diff", "--quiet", H49R4A_SHA, "HEAD", "--", "generic_chess"], cwd=ROOT).returncode == 0
