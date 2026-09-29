"""The authoritative safe state key does not compress this R5 prefix."""

from scripts.audit_r5_random_safe_key import audit


def test_safe_key_reaches_state_budget_without_reuse():
    result = audit()
    assert result["classification"] == "COST_ABORT"
    assert result["abort_reason"] == "states"
    assert result["state_identities_seen"] == result["max_states"] == 10_000
    assert result["cache_hits"] == 0
    assert result["random_outcome_probabilities_win_draw_loss"] is None
