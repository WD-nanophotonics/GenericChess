from fractions import Fraction

import pytest

from scripts.secured_exchange_contract import Action, context_success, observations, task_score


def test_observable_context_choice_is_not_route_or_policy_average():
    assert observations() == {
        'context_adaptive_A': Fraction(1), 'broad_B': Fraction(1),
        'redundant_options': Fraction(1), 'before_new_success': Fraction(1, 2),
        'after_new_success': Fraction(1), 'after_refutation': Fraction(1, 2),
        'wrong_action_average_A': Fraction(1, 2),
        'wrong_max_after_average_A': Fraction(1, 2),
    }


def test_action_set_dominance_and_adversarial_refutation():
    fail = Action('fail', (False,))
    success = Action('success', (True, True))
    assert context_success(()) == 0  # task failure, not a game draw
    assert context_success((fail, success)) >= context_success((fail,))
    assert context_success((Action('success', (True, False)),)) == 0


@pytest.mark.parametrize('action', [Action('x', (True,), False), Action('x', ()), Action('x', (1,))])
def test_incomplete_or_invalid_evidence_never_becomes_failure(action):
    with pytest.raises(ValueError):
        context_success((Action('already_wins', (True,)), action))


def test_conflicting_physical_descriptions_are_not_silently_selected():
    with pytest.raises(ValueError, match='conflicting'):
        context_success((Action('same', (True,)), Action('same', (False,))))


def test_common_measure_cannot_be_silently_renormalized():
    with pytest.raises(ValueError, match='sum to one'):
        task_score(((Fraction(1, 2), (Action('x', (True,)),)),))


def test_two_ply_success_does_not_certify_longer_horizon_gain():
    # Declared finite inventory witness, not a purported legal Chess position:
    # one gain followed by one quiet reply, then a forced loss of two tokens.
    custody_deltas = (1, 0, -2)
    assert sum(custody_deltas[:2]) > 0
    assert sum(custody_deltas) < 0
