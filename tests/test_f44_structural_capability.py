"""Focused deterministic contracts for the F44 structural diagnosis."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_f44_structural_capability.py"
EVIDENCE = ROOT / ".generic_chess_flow" / "f44_structural_capability.json"


@pytest.fixture(scope="module")
def evidence():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_f44_baseline_and_production_boundary_are_frozen(evidence):
    assert evidence["status"] == "PASS"
    assert evidence["baseline"] == "7166a743911926156de75825cd02c7c622aaa172"
    assert evidence["production_changed"] is False
    assert evidence["frozen_inputs"]["current_components"] == ["mobility", "coverage", "reachability", "path_efficiency"]


def test_endpoint_controls_expose_current_representation_collision(evidence):
    family = evidence["signals"]["S44-A_ENDPOINT_CONTROL_SEMANTICS"]
    witness = family["independence"]["witness"]
    assert family["independence"]["pass"] is True
    assert witness["current_four_component_equal"] is True
    assert witness["signal_differs"] is True
    cases = evidence["synthetic"]["cases"]
    assert cases["quiet_plus_capture_same_targets"]["endpoint"]["dual_use_overlap_mass"] > 0
    assert cases["disjoint_quiet_capture_same_union"]["endpoint"]["dual_use_overlap_mass"] == 0


def test_conditional_reserve_remains_separate_from_ordinary_mass(evidence):
    family = evidence["signals"]["S44-B_CONDITIONAL_CAPABILITY_RESERVE"]
    assert family["independence"]["pass"] is True
    pawn = family["real_rulesets"]["western_chess"]["P"]["conditional_reserve"]
    assert pawn["ordinary_pattern_count"] == 3
    assert pawn["conditional_pattern_count"] == 3
    assert pawn["conditional_reserve_over_ordinary_mass"] > 0
    guarded = evidence["synthetic"]["guarded_reserve"]
    assert guarded["ordinary_base"]["component_values"] == guarded["ordinary_base_plus_guarded_identical_capability"]["component_values"]


def test_channel_and_density_ledgers_are_canonical_and_complete(evidence):
    channel = evidence["signals"]["S44-C_CHANNEL_DIVERSITY_CONCENTRATION"]
    assert channel["independence"]["pass"] is False
    for row in channel["real_rulesets"]["western_chess"].values():
        assert row["channel_diversity"]["sample_count"] > 0
        assert row["channel_diversity"]["effective_channel_count_mean"] >= 1.0
    density = evidence["signals"]["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]
    assert density["independence"]["pass"] is True
    assert density["blocker_fragility_ordering"]["western_chess"]
    for row in density["real_rulesets"]["standard_shogi"].values():
        profile = row["density_profile"]
        assert len(profile["mobility_retention_by_density"]) == 5
        assert len(profile["discrete_curvature"]) == 3


def test_all_real_ruleset_structural_families_have_metrics(evidence):
    required = {"P", "N", "B", "R", "Q"}
    for family in evidence["signals"].values():
        assert required <= set(family["real_rulesets"]["western_chess"])
        assert family["real_rulesets"]["standard_shogi"]
    assert evidence["endpoint_algebra"] == {
        "empty_only": "1-density/2",
        "enemy_only": "density/2",
        "empty_plus_enemy": "1-density/2; quiet relation takes precedence in current candidate mass",
    }


def test_exactly_one_frozen_selection_and_boundary(evidence):
    selection = evidence["selection"]
    assert selection["classification"] == "MULTIPLE_STRUCTURAL_INFORMATION_GAPS"
    assert selection["next_boundary"] == "F45_STRUCTURAL_FEATURE_DISCRIMINATION"
