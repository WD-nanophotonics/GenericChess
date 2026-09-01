import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_f37r1_preserves_original_evidence_and_recertifies_gate():
    result = load("f37r1_gate_recertification.json")
    assert result["status"] == "PASS"
    assert result["original_artifacts_byte_identical"] is True
    assert all(result["original_f37_hashes"].values())
    assert result["static_gate_recertification"]["R37A"]["static_gate_exact"] is False
    assert result["static_gate_recertification"]["R37B"]["static_gate_exact"] is True
    assert result["static_gate_recertification"]["R37C"]["static_gate_exact"] is True
    assert result["eligible_candidates"] == ["R37B", "R37C"]
    assert result["selected_candidate"] == "R37C"
    assert result["defect_classification"] == "NON_OUTCOME_CHANGING_GATE_IMPLEMENTATION_DEFECT"
    assert result["flags"]["F37_EXACT_STATIC_GATE_RECERTIFIED"] is True
    assert result["flags"]["F37_FULL_REGRESSION_CURRENT_TREE_CERTIFIED"] is True
    assert result["focused_regression"] == {"total": 28, "passed": 28, "failed": 0}
    full = result["full_regression"]
    assert full["total"] == 1251
    assert full["passed"] == 1238
    assert full["failed"] == 13
    assert full["unexpected_failures"] == []
    assert len(full["historical_failures"]) == 13


def test_f37r1_production_scope():
    assert subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
