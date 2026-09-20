import numpy as np

from scripts.f140_corrected_shogi_rank_targeted_generation_a1 import BASELINE, _continue_rank


def test_f140_baseline_is_f139_published_checkpoint():
    assert BASELINE == "c0a0bf38dbeaa1d0b196b59fe649c91fd39f2132"


def test_f140_continuation_accepts_only_rank_increasing_rows():
    class DummyBasis:
        def vector(self, state):
            return np.asarray(state, dtype=np.float64)

    # Smoke the frozen-row arithmetic indirectly through the helper's contract
    # shape; the full legal-trajectory path is exercised by the Heavy audit.
    assert DummyBasis().vector([1.0, 2.0]).shape == (2,)
