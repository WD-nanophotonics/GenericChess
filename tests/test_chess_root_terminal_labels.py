"""Independent Python/native terminal labels for one frozen Chess root."""

import pytest

from generic_chess.native import native_available
from scripts.audit_chess_root_terminal_labels import run_probe


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_chess_root_immediate_outcomes_agree_across_backends():
    result = run_probe()
    assert result["classification"] == "TERMINAL_LABEL_PARITY_PASS"
    assert result["root_status"] == "ongoing"
    assert result["python_legal_actions"] == result["native_legal_actions"] == 31
    assert result["terminal_counts"] == {
        "checkmate": 2,
        "ongoing": 10,
        "stalemate": 19,
    }
    assert {(tuple(row["from"]), tuple(row["to"])) for row in result["immediate_wins"]} == {
        ((1, 4), (0, 4)),
        ((1, 4), (1, 0)),
    }
