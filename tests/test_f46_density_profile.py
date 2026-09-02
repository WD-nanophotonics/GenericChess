"""Focused deterministic contracts for F46 density reducer diagnosis."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_f46_density_profile.py"
EVIDENCE = ROOT / ".generic_chess_flow" / "f46_density_profile.json"
sys.path.insert(0, str(ROOT / "scripts"))
import audit_f46_density_profile as audit  # noqa: E402


@pytest.fixture(scope="module")
def evidence():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_f46_protocol_and_f44_witness_are_bound(evidence):
    assert evidence["status"] == "PASS"
    assert evidence["baseline"] == "b0fc4d2da1a6cb0b818b713305dce84cef3e8e6e"
    assert evidence["gates"]["f44_density_witness"] is True
    assert evidence["h46r1a"] == "tests/fixtures/f46r1_density_profile_manifest.json"


def test_all_four_fixed_reducers_are_present_and_structural(evidence):
    assert tuple(evidence["reducers"]) == audit.REDUCERS
    for row in evidence["reducers"].values():
        assert all(row["algebra_gates"].values())
        assert len(row["western"]["curves"]) >= 5
        assert len(row["standard_shogi"]["curves"]) >= 8


def test_arithmetic_control_reproduces_current_both_rulesets(evidence):
    control = evidence["reducers"][audit.REDUCERS[0]]
    assert control["arithmetic_reproduces_current"] is True
    assert control["western"]["reduced_mobility"]["P"] == pytest.approx(0.9496484375)


def test_reducer_algebra_controls_cover_identity_scale_monotonicity_and_zero():
    weights = (0.25, 0.2, 0.2, 0.18, 0.17)
    points = (0.0, 0.125, 0.25, 0.375, 0.5)
    for name in audit.REDUCERS:
        gates = audit._algebra_gates(name, points, weights)
        assert all(gates.values())
        assert audit._reduce(name, (0.0,) * 5, weights) == 0.0
        assert audit._reduce(name, (2.0,) * 5, weights) == pytest.approx(2.0)


def test_mean_order_and_matched_shape_control(evidence):
    control = evidence["controls"]
    assert control["arithmetic_equal"] is True
    assert control["arithmetic_control_curves_differ"] is True
    for name in audit.REDUCERS:
        row = control["reducers"][name]["matched_arithmetic_shape"]
        if name == audit.REDUCERS[0]:
            assert row["result_a"] == pytest.approx(row["result_b"])
        else:
            assert row["result_a"] != pytest.approx(row["result_b"])


def test_f44_blocker_control_preserves_long_path_penalty(evidence):
    for name, row in evidence["controls"]["reducers"].items():
        assert row["f44_short_long"]["long_minus_short"] < 0.0


def test_western_matrix_has_curves_ratios_and_band_gates(evidence):
    for name, row in evidence["reducers"].items():
        western = row["western"]
        assert set(("P", "N", "B", "R", "Q")) <= set(western["raw_capability"])
        assert set(("N", "B", "R", "Q")) <= set(western["raw_ratios_by_pawn"])
        assert set(("P", "N", "B", "R", "Q")) <= set(western["normalized_board_value"])
        assert isinstance(row["qualification"]["western_bands"], bool)
    base = evidence["reducers"][audit.REDUCERS[0]]["western"]["raw_ratios_by_pawn"]
    for name in audit.REDUCERS[1:]:
        candidate = evidence["reducers"][name]["western"]["raw_ratios_by_pawn"]
        assert all(candidate[piece] < base[piece] for piece in ("N", "B", "R", "Q"))


def test_shogi_gates_are_reported_for_every_reducer(evidence):
    for name, row in evidence["reducers"].items():
        metrics = row["shogi_gates"]
        assert metrics["cosine_vs_current"] >= 0.95
        assert metrics["spearman_vs_current"] >= 0.90
        assert metrics["pairwise_ordering"] >= 0.90
        assert 0.8 <= metrics["hand_board_ratio_range"][0] <= metrics["hand_board_ratio_range"][1] <= 1.0


def test_qualification_is_evidence_derived_and_does_not_qualify_control(evidence):
    assert evidence["reducers"][audit.REDUCERS[0]]["qualification"]["all"] is False
    assert evidence["selection"] == {
        "classification": "DENSITY_PROFILE_REDUCTION_INSUFFICIENT",
        "coherent_nonqualified": [audit.REDUCERS[1], audit.REDUCERS[2], audit.REDUCERS[3]],
        "next_boundary": "F47_ENDPOINT_DENSITY_COMPOSITE_DIAGNOSIS",
        "qualified": [],
    }


def test_cosine_is_dot_over_norm_not_pearson():
    left = {"a": 1.0, "b": 2.0}
    right = {"a": 2.0, "b": 1.0}
    assert audit._cosine(left, right) == pytest.approx(0.8)
    assert audit._correlation(left, right) == pytest.approx(-1.0)


def test_qualification_includes_semantic_control_for_every_reducer(evidence):
    assert all(row["qualification"]["semantic_control"] for row in evidence["reducers"].values())


def test_all_six_qualification_paths_are_reachable(evidence):
    assert set(evidence["selector_reachability"]["cases"]) == set(audit.QUALIFICATION_MAPPING)
    assert all(evidence["selector_reachability"].values())


def test_f46_has_no_production_change(evidence):
    assert evidence["production_changed"] is False
    assert evidence["gates"]["production_unchanged"] is True
