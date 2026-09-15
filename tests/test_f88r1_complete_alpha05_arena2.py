"""Static guardrails for the single-game F88R1 continuation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import f88r1_complete_alpha05_arena2 as f88r1  # noqa: E402


def test_f88r1_freezes_single_alpha05_scope():
    assert f88r1.WORK_ORDER == "GENERICCHESS_F88R1_COMPLETE_ALPHA05_ARENA2"
    assert f88r1.F88_ALPHA == 0.5
    assert f88r1.EXPECTED_CANDIDATE_ID == "0b318ea0a719971634abbc443e3334dfcef4a017d94d4dfd01c8a6ca69954316"
    assert f88r1.EXPECTED_CORPUS_ID == "6eca12faa0981e1c71f637eae7f66ee4a053193a752fbe592d2b0edafbdffd2a"
    assert f88r1.EXPECTED_PARTIAL_NODES == 104448
    assert f88r1.EXPECTED_PARTIAL_PLIES == 204


def test_f88r1_targets_only_alpha05_progress():
    assert f88r1.ALPHA_PROGRESS.name == "alpha-0.5"
    assert f88r1.ALPHA_PROGRESS.parent.name == "f88-f87-update-damping-arena2"
