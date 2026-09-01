"""Focused F41 audit contracts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
SCRIPT = ROOT / "scripts" / "audit_f41_semantic_material_prior.py"
EVIDENCE = ROOT / ".generic_chess_flow" / "f41_closeout_evidence.json"


def _run() -> dict:
    subprocess.run([PYTHON, str(SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_f41_semantic_source_coverage_and_pawn_omission_are_observed():
    result = _run()
    western = result["source_coverage"]["western_chess"]
    pawn = next(row for row in western["rows"] if row["type"] == "P")
    assert pawn["semantic_movement_source_omission"] is True
    assert pawn["semantic_destination_count"] > 0
    assert pawn["semantic_only_destinations"]
    assert pawn["semantic_only_destination_count"] == pawn["semantic_destination_count"]
    assert pawn["legacy_only_destinations"] == []
    assert pawn["conditional_pattern_count"] >= 1
    assert all(row["semantic_only_destinations"] == row["omitted_destinations"] for row in western["rows"])


def test_f41_legacy_controls_and_metamorphic_contracts_pass():
    result = _run()
    assert result["legacy_compatibility"]["status"] == "PASS"
    assert result["flags"]["SEMANTIC_ANALYZER_LEGACY_COMPATIBLE"] is True
    aggregate = result["legacy_compatibility"]["aggregate_gate"]
    assert aggregate["covered_classes"] == ["leap-only", "ray-only", "hybrid leap/ray"]
    assert aggregate["pass"] is True
    assert all(result["legacy_compatibility"]["rulesets"][name]["class_controls"]["hybrid leap/ray"]["pass"]
               for name in ("western_chess", "standard_shogi")
               if result["legacy_compatibility"]["rulesets"][name]["class_controls"]["hybrid leap/ray"]["present"])
    assert all(result["metamorphic"][name]["all_pass"] for name in ("western_chess", "standard_shogi"))


def test_f41_retest_is_not_silently_qualified_when_western_bands_fail():
    result = _run()
    assert result["western_gate"]["pawn_positive_no_floor_collapse"] is True
    assert result["western_gate"]["bands_pass"] is False
    assert result["classification"] == "SEMANTIC_MATERIAL_PRIOR_INSUFFICIENT"
    assert result["next_boundary"] == "F42_SEMANTIC_CAPABILITY_PRIOR_DIAGNOSIS"


def test_f41_shogi_uses_complete_frozen_gate_without_drop_independence_substitution():
    result = _run()
    gate = result["shogi_gate"]
    assert gate["board_value_cosine_vs_current"] >= 0.95
    assert gate["spearman_vs_current"] >= 0.90
    assert gate["pairwise_ordering_vs_current"] >= 0.90
    assert 0.8 <= min(gate["hand_board_ratios"]) <= max(gate["hand_board_ratios"]) <= 1.0
    assert gate["pass"] is True
    assert gate["drop_independence"] is False


def test_f41_drop_hand_audit_and_learning_span_are_explicit():
    result = _run()
    assert result["flags"]["DROP_SIGNAL_INDEPENDENCE_AUDITED"] is True
    assert result["static_learning_span"]["new_learning_capacity"] is False
    assert result["deployment_and_hand"]["standard_shogi"]["drop_signal_independent"] is False
