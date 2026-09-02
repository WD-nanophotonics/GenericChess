"""H49A protocol checkpoint tests; no F49 measurements are permitted here."""

from __future__ import annotations

import copy

import pytest

from scripts.f49_protocol import load_h49a_manifest, validate_h49a_manifest


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
