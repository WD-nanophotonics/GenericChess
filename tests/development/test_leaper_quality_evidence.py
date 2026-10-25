"""Observed certificate joins must not turn UNKNOWN into engine error/success."""
import pytest
from scripts.leaper_quality_evidence import classify_certified_choice, summarize_certified_choices


def fixture(values):
    return dict(root_state_sha256="full-history-root", certified_actions=[
        dict(action={"id": name}, own_WDL=value) for name, value in values.items()],
        source_graph_actions=[dict(action={"id": "unknown"}, own_WDL=-1)])


def score(c, name):
    return classify_certified_choice(c, {"id": name}, root_state_sha256="full-history-root")


def test_source_label_does_not_fill_uncertified_action():
    row = score(fixture({"win": 1}), "unknown")
    assert row["chosen_own_WDL"] is None
    assert row["category"] == "UNCERTIFIED_ACTION"


def test_named_loss_alone_does_not_establish_inferiority():
    row = score(fixture({"loss": -1}), "loss")
    assert row["root_own_WDL_interval"] == [-1, 1]
    assert row["category"] == "CERTIFIED_LOSS_OPTIMALITY_UNKNOWN"
    assert row["guaranteed_WDL_gap"] == 0


def test_safe_draw_is_not_automatically_globally_optimal():
    c = fixture({"safe": 0, "bad": -1})
    assert score(c, "safe")["category"] == "CERTIFIED_DRAW_OPTIMALITY_UNKNOWN"
    assert score(c, "bad")["guaranteed_WDL_gap"] == 1
    assert score(c, "bad")["category"] == "CERTIFIED_INFERIOR"


def test_win_certificate_makes_named_draw_strictly_inferior():
    c = fixture({"win": 1, "draw": 0})
    assert score(c, "win")["root_own_WDL_interval"] == [1, 1]
    assert score(c, "win")["category"] == "CERTIFIED_OPTIMAL"
    assert score(c, "draw")["category"] == "CERTIFIED_INFERIOR"


def test_unknowns_remain_in_full_returned_coverage_denominator():
    c = fixture({"win": 1})
    rows = [dict(action={"id": n}, root_state_sha256="full-history-root")
            for n in ("win", "unknown", "other")]
    s = summarize_certified_choices(c, rows)
    assert s["returned_actions"] == 3 and s["certified_value_returns"] == 1
    assert s["certified_value_coverage"] == 1/3
    assert s["categories"]["UNCERTIFIED_ACTION"] == 2


def test_source_parent_id_cannot_substitute_for_proof_root_history():
    c = fixture({"win": 1})
    with pytest.raises(ValueError, match="literal certified history"):
        classify_certified_choice(c, {"id": "win"}, root_state_sha256="source-parent-id")


def test_conflicting_proofs_are_not_last_writer_wins():
    c = fixture({"win": 1})
    c["certified_actions"].append(dict(action={"id": "win"}, own_WDL=0))
    with pytest.raises(ValueError, match="conflicting"):
        score(c, "win")


def test_boolean_wdl_is_not_silently_integer_truth():
    with pytest.raises(ValueError, match="integer"):
        score(fixture({"bad": True}), "bad")


def test_no_returns_has_unknown_coverage_not_zero_success():
    s = summarize_certified_choices(fixture({"win": 1}), [])
    assert s["certified_value_coverage"] is None
    assert s["returned_actions"] == 0


def test_certified_nonwinning_root_bound_can_close_a_draw_optimum():
    c = fixture({"safe": 0, "bad": -1})
    c["certified_root_upper_WDL"] = 0
    row = score(c, "safe")
    assert row["category"] == "CERTIFIED_OPTIMAL"
    assert row["root_own_WDL_interval"] == [0, 0]
    assert score(c, "bad")["category"] == "CERTIFIED_INFERIOR"


def test_root_bound_cannot_override_a_contradictory_win_certificate():
    c = fixture({"win": 1})
    c["certified_root_upper_WDL"] = 0
    with pytest.raises(ValueError, match="contradicts"):
        score(c, "win")


def test_boolean_root_bound_is_not_a_certificate():
    c = fixture({"win": 1})
    c["certified_root_upper_WDL"] = True
    with pytest.raises(ValueError, match="upper bound must be integer"):
        score(c, "win")
