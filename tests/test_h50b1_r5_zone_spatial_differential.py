"""Generic zone-selector Native/Python differential controls for R5."""

import pytest

from generic_chess.native import native_available
from scripts.audit_h50b1_r3_native_differential import _zone_guard_differential


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_h50b1_r5_generic_zone_guard_matches_python():
    result = _zone_guard_differential()
    assert result["status"] == "PASS"
    assert result["native_python_equal"] is True
    assert result["inside_zone"]["selected_transitions"]
    assert result["outside_zone"]["selected_transitions"]
