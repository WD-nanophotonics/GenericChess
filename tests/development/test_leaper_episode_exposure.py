"""First-event bounds keep unknown prefixes and visit/event units separate."""
import pytest
from scripts.leaper_episode_exposure import event_bounds


def test_known_late_event_does_not_determine_its_first_time():
    r=event_bounds([None,False,True,True])
    assert r['occurs']is True
    assert (r['first_ply_lower'],r['first_ply_upper'],r['first_ply_exact'])==(0,2,None)
    assert r['known_event_visits']==2


def test_unknown_after_first_known_event_does_not_destroy_exact_first():
    r=event_bounds([False,True,None,True])
    assert r['first_ply_exact']==1


def test_no_observed_event_with_unknown_prefix_is_not_a_negative_label():
    r=event_bounds([False,None,False])
    assert r['occurs']is None and r['first_ply_lower']==1 and r['first_ply_upper']is None


def test_all_false_is_a_negative_event_label():
    r=event_bounds([False,False])
    assert r['occurs']is False and r['first_ply_lower']is None


def test_empty_episode_has_no_decision_event_and_integers_are_not_truth():
    assert event_bounds([])['occurs']is False
    with pytest.raises(ValueError):event_bounds([0])
