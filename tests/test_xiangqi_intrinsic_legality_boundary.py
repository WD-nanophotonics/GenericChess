"""Focused executable boundary between Xiangqi local events and legal moves."""

from scripts.audit_xiangqi_intrinsic_legality_boundary import audit


def test_initial_and_last_screen_static_event_boundaries():
    result = audit()
    initial = result["initial"]
    assert initial["intrinsic_count"] == initial["legal_count"] == 43
    assert initial["intrinsic_only"] == initial["legal_only"] == []
    assert initial["intrinsic_by_type"] == {
        "A": 2, "C": 24, "E": 4, "H": 4, "R": 4, "S": 5,
    }
    screen = result["last_screen"]
    assert screen["intrinsic_count"] == 3
    assert screen["legal_count"] == 1
    assert screen["intrinsic_only"] == [("S", 49, 48), ("S", 49, 50)]
    assert screen["legal_only"] == []
