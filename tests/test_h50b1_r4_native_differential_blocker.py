"""Regression detector for the R4 weighted-declaration differential blocker."""

import pytest

from generic_chess.native import native_available
from scripts.audit_h50b1_r3_native_differential import _declaration_differential


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_h50b1_r4_weighted_declaration_differential_is_preserved():
    with pytest.raises(AssertionError, match="declaration mismatch at score=23"):
        _declaration_differential()
