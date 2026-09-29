"""Initial Chess histories lack most type-balance variation at depth three."""

from scripts.audit_chess_shallow_inventory_rank import audit


def test_depth_three_only_exposes_pawn_and_knight_balance():
    result = audit()
    assert result["types"] == ("P", "N", "B", "R", "Q")
    assert [row["histories"] for row in result["layers"]] == [1, 20, 400, 8902]
    assert [row["distinct_balance_vectors"] for row in result["layers"]] == [1, 1, 1, 3]
    assert result["layers"][3]["balance_counts"] == {
        "(0, 0, 0, 0, 0)": 8868,
        "(0, 1, 0, 0, 0)": 4,
        "(1, 0, 0, 0, 0)": 30,
    }
