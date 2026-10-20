"""Input-integrity checks for the supplemental exposure diagnostic."""
from __future__ import annotations

from results.dev_aux.task2628.feature_exposure import active_channels, added_patterns


def test_nonzero_features_reported_by_channel_without_labeling_value():
    assert active_channels([5, 2, 0, 1], [("board", "P"), ("board", "N"),
                           ("hand", "P"), ("hand", "N")]) == ["board:N", "hand:N"]


def test_action_exposure_counts_only_actions_after_full_root_history():
    start = {"actions": [{"pattern_id": "old"}]}
    final = {"actions": [{"pattern_id": "old"}, {"pattern_id": "unlock"}, {"pattern_id": "unlock"}]}
    assert added_patterns(start, final) == {"unlock": 2}


def test_action_exposure_rejects_changed_starting_history():
    try:
        added_patterns({"actions": [{"pattern_id": "root"}]}, {"actions": [{"pattern_id": "other"}]})
    except ValueError as error:
        assert "starting history" in str(error)
    else:
        raise AssertionError("mismatched full history accepted")
