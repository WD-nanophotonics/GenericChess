"""Contract tests for the bounded F85 lane-scaling diagnostic."""

from pathlib import Path

from scripts import f85_lane_scaling_calibration as probe


ROOT = Path(__file__).resolve().parents[1]


def test_f85_lane_probe_is_resource_only_and_bounded():
    source = (ROOT / "scripts/f85_lane_scaling_calibration.py").read_text(encoding="utf-8")
    assert probe.LANE_COUNTS == (2, 3, 4)
    assert probe.SMOKE is True
    assert probe.WHOLE_PROBE_HARD_WALL_SECONDS == 900
    assert "f85-c2-train-teacher-acquisition" not in source
    assert "training_evidence" not in source
    assert "C2" not in source


def test_f85_lane_probe_uses_only_frozen_f84_resource_roots():
    source = (ROOT / "scripts/f85_lane_scaling_calibration.py").read_text(encoding="utf-8")
    assert "_load_frozen_resource_roots" in source
    assert "ROOT_IDS" in source
    assert "_spectrum_for_root" in source
    assert "peak_worker_rss_bytes" in source
    assert "result_signature" in source
