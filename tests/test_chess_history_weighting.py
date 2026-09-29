"""A fixed-depth history measure can weight one position multiple times."""

from scripts.audit_chess_history_weighting import audit


def test_commuting_knight_histories_share_one_position():
    result = audit()
    assert result == {
        "histories": 5,
        "shared_position_histories": 4,
        "distinct_positions": 2,
        "history_uniform_shared_mass": "4/5",
        "position_uniform_shared_mass": "1/2",
        "shared_position_same_ply": True,
        "shared_position_same_auxiliary": True,
    }
