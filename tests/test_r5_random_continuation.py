"""Freeze the small seeded random-policy observation on R5 DEVELOPMENT."""

from scripts.audit_r5_random_continuation import audit


def test_seeded_random_continuation_is_draw_dominated_under_six_ply_cap():
    result = audit()
    assert result["seed"] == 20260929
    assert result["samples_per_action"] == 100
    assert result["actions_applied"] == 2479
    assert len(result["results"]) == 5
    draw_rows = [row for row in result["results"].values()
                 if row["exact_minimax"] == "DRAW"]
    loss_rows = [row for row in result["results"].values()
                 if row["exact_minimax"] == "LOSS"]
    assert len(draw_rows) == 4 and len(loss_rows) == 1
    assert all(row["random_draws"] == 100 for row in draw_rows)
    assert loss_rows[0]["random_draws"] == 98
    assert loss_rows[0]["random_losses"] == 2
    assert loss_rows[0]["random_wins"] == 0
    statuses = [row["terminal_status_counts"] for row in result["results"].values()]
    assert sum(row.get("max_ply", 0) for row in statuses) == 482
    assert sum(row.get("repetition", 0) for row in statuses) == 15
    assert loss_rows[0]["terminal_status_counts"]["checkmate"] == 2
    assert loss_rows[0]["terminal_status_counts"] == {
        "checkmate": 2, "max_ply": 96, "repetition": 1, "stalemate": 1,
    }
