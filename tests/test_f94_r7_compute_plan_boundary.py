from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/architecture/GENERICCHESS_F94_R7_COMPUTE_PLAN_REQUEST_V1.md"


def test_r7_compute_plan_is_result_free_and_bound_to_frozen_inputs():
    text = PLAN.read_text(encoding="utf-8")
    assert "plan-only" in text
    assert "does not authorize Heavy, Arena" in text
    assert "4096_vs_256" in text
    assert "1024_vs_256" in text and "4096_vs_1024" in text
    assert "9811" in text and "9812" in text and "9813" in text
    assert "9801" in text and "9802" in text and "9803" in text
    assert "216 games" in text and "108 pairs" in text
    assert "compute-plan-status" in text
    assert "registered-Supervisor approval" in text


def test_r7_compute_plan_requires_exact_approval_before_heavy():
    text = PLAN.read_text(encoding="utf-8")
    assert "exact plan SHA" in text
    assert "envelope digest" in text
    assert "current sandbox SHA" in text
    assert "argv" in text
    assert "DEFER_CONTROL_NOT_READY" in text
