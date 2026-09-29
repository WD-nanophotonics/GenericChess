"""Chess historical capture missing from an intentionally local event ledger."""

from scripts.audit_chess_en_passant_ledger_boundary import audit


def test_en_passant_is_legal_after_double_step_but_outside_intrinsic_ledger():
    result = audit()
    assert result["intrinsic"] == [(28, 20)]
    assert result["legal"] == [(28, 19), (28, 20)]
    assert result["intrinsic_only"] == []
    assert result["legal_only"] == result["en_passant"] == [(28, 19)]
    assert any("en_passant" in name for name in result["excluded_history_patterns"])
