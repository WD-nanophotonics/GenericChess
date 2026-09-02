"""Regression coverage for the R4 weighted-declaration correction."""

import pytest

from generic_chess.native import native_available
from scripts.audit_h50b1_r3_native_differential import _declaration_differential


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_h50b1_r5_weighted_declaration_differential_is_closed():
    result = _declaration_differential()
    assert result["status"] == "PASS"
    assert all(
        row["assessments"][0]["python"] == row["assessments"][0]["native"]
        for row in result["rows"]
    )
