from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.audit_f50a_semantic_native_search_architecture import build_audit


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "h50a_semantic_native_search_architecture_audit.json"


def test_h50a_audit_is_complete_and_source_hashes_are_current():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    audit = build_audit()
    assert fixture["schema"] == audit["schema"]
    assert fixture["checkpoint"] == audit["checkpoint"]
    assert fixture["work_order_id"] == audit["work_order_id"]
    assert fixture["parent_sha"] == audit["parent_sha"]
    assert fixture["production_diff"] == "ZERO"
    assert fixture["dependency_ledger_sha256"] == audit["dependency_ledger_sha256"]
    assert fixture["source_hashes"] == {
        row["path"]: row["sha256"] for row in audit["dependency_ledger"]
    }
    assert all(row["present"] for row in audit["source_marker_evidence"].values())


def test_h50a_matrix_and_route_selection_freeze_the_next_boundary():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    audit = build_audit()
    observed_matrix = [(row["capability"], row["status"]) for row in audit["capability_matrix"]]
    assert fixture["capability_matrix"] == [list(row) for row in observed_matrix]
    assert fixture["route_comparison"] == {
        "A_EXTEND_EXISTING_NATIVE_SEMANTIC_IR_RUNTIME": "SELECTED",
        "B_NEW_SEMANTIC_NATIVE_SEARCH_STATE": "NOT_SELECTED",
        "C_PYTHON_SEMANTIC_DIAGNOSTIC_CONTROL": "CONTROL_ONLY",
    }
    assert fixture["selected_route"] == "F50B_EXTEND_EXISTING_NATIVE_SEMANTIC_SEARCH"
    assert fixture["F50B_status"] == "NOT_STARTED"
    assert fixture["F49_status"] == "CLOSED_ARCHITECTURAL_PREREQUISITE_FAILURE"
    assert fixture["S49_regenerated"] is False
    assert fixture["F49_measurements_started"] is False


def test_h50a_preserves_special_action_and_history_boundaries():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    western = fixture["western_special_action_coverage"]
    assert western["pawn_double_step"] == "SUPPORTED_BY_SEMANTIC_IR_RUNTIME"
    assert western["en_passant"].endswith("AUX_SLOT")
    assert western["castling_rights"] == "SUPPORTED_BY_AUX_SLOTS_AND_TRIGGERS"
    assert western["legacy_fallback_allowed"] is False
    shogi = fixture["standard_shogi_coverage"]
    assert shogi["continuous_check_repetition"] == "MISSING_NATIVE_TERMINAL_CAPABILITY"
    assert shogi["declarations_nyugyoku"] == "OUTSIDE_NATIVE_PAYLOAD_CONTRACT"
    generated = fixture["generated_ruleset_coverage"]
    assert generated["H48B_selected_fingerprint"] == "9f7e7201a19f8f0ee6c0eacc766c2ac3a6c313e06bbc960d5d6dfb89137db923"
    assert generated["semantic_native_execution"] == "NOT_CERTIFIED_ON_SELECTED_GENERATED_SURFACE"


def test_h50a_dependency_ledger_hash_is_reproducible():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    audit = build_audit()
    ledger = audit["dependency_ledger"]
    canonical = json.dumps(ledger, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == fixture["dependency_ledger_sha256"]
