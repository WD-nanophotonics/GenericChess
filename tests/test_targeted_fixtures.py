"""Targeted fixtures for previously-uncovered position categories."""

from generic_chess.ai.benchmark.targeted_fixtures import (
    build_targeted_fixtures,
    uncovered_targeted_categories,
)
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions


def test_all_six_targeted_categories_covered():
    fixtures = {f.fixture_id: f for f in build_targeted_fixtures()}
    assert set(fixtures) == {
        "targeted_multi_evasion",
        "targeted_near_repetition",
        "targeted_checking_drop",
        "targeted_nonchecking_drop",
        "targeted_low_anchor_escape",
        "targeted_low_branching",
    }
    assert uncovered_targeted_categories() == ()


def test_multi_evasion_predicate_real():
    fixture = next(
        f for f in build_targeted_fixtures() if f.fixture_id == "targeted_multi_evasion"
    )
    side = fixture.state.position.side_to_move
    assert is_in_check(fixture.state.position, side, fixture.compiled)
    assert len(legal_actions(fixture.state, fixture.compiled)) >= 3


def test_near_repetition_replays_and_counts():
    fixture = next(
        f
        for f in build_targeted_fixtures()
        if f.fixture_id == "targeted_near_repetition"
    )
    assert len(fixture.action_prefix) == 4
    counts = dict(fixture.state.repetition_counts)
    assert max(counts.values()) >= 2


def test_checking_drop_predicate_real():
    fixture = next(
        f for f in build_targeted_fixtures() if f.fixture_id == "targeted_checking_drop"
    )
    from generic_chess.core.actions import DropMove
    from generic_chess.core.transition import apply_action

    side = fixture.state.position.side_to_move
    actions = legal_actions(fixture.state, fixture.compiled)
    drops = [a for a in actions if isinstance(a, DropMove)]
    assert drops
    assert any(
        is_in_check(apply_action(fixture.state, a, fixture.compiled).position, 1 - side, fixture.compiled)
        for a in drops
    )


def test_nonchecking_drop_predicate_real():
    fixture = next(
        f
        for f in build_targeted_fixtures()
        if f.fixture_id == "targeted_nonchecking_drop"
    )
    from generic_chess.core.actions import DropMove
    from generic_chess.core.transition import apply_action

    side = fixture.state.position.side_to_move
    drops = [
        a
        for a in legal_actions(fixture.state, fixture.compiled)
        if isinstance(a, DropMove)
    ]
    assert drops
    assert not any(
        is_in_check(apply_action(fixture.state, a, fixture.compiled).position, 1 - side, fixture.compiled)
        for a in drops
    )


def test_low_branching_predicate_real():
    fixture = next(
        f for f in build_targeted_fixtures() if f.fixture_id == "targeted_low_branching"
    )
    assert len(legal_actions(fixture.state, fixture.compiled)) <= 3
