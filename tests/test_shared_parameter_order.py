from fractions import Fraction as F
from itertools import product
import pytest
from scripts.shared_parameter_order import certify_order


def row(constant=0, alpha=0): return (F(constant), F(alpha), 0, 0, 0, 0, 0, 0)


def gate(first, second, **kwargs):
    return certify_order(first, second, denominator=row(1), retained_id='a', discarded_id='b', **kwargs)


def test_naive_backed_up_corner_order_rejected_at_switching_interior():
    # A=0,B=min(h,1-h): endpoint equality does not authorize A>=B.
    bound = gate([row()], [row(0, 1), row(1, -1)], first_kind='min', second_kind='min', proofs=[(F(1, 2), F(1, 2))])
    assert bound['normalized_lower'] == F(-1, 2)
    assert not bound['value_cutoff_proved']


def test_maxmax_reverse_negation_and_convex_certificate():
    # max(h,1-h)>=1/2, even though neither single leaf dominates everywhere.
    result = gate([row(0, 1), row(1, -1)], [row(F(1, 2))], first_kind='max', second_kind='max', proofs=[(F(1, 2), F(1, 2))])
    assert result['numerator_lower'] == 0
    assert result['value_cutoff_proved'] and result['canonical_action_prune_proved']


def test_mixed_orders_and_canonical_equality():
    result = gate([row(0, 1), row(1, -1)], [row()], first_kind='min', second_kind='max')
    assert result['numerator_lower'] == 0
    result = certify_order([row(0, 1), row(1, -1)], [row()], first_kind='min', second_kind='max',
        denominator=row(1), retained_id='z', discarded_id='a')
    assert result['value_cutoff_proved'] and not result['canonical_action_prune_proved']
    assert gate([row(2)], [row(1)], first_kind='max', second_kind='min', pair_witness=(0, 0))['normalized_lower'] == 1


def test_common_denominator_sign_and_negative_lower():
    result = certify_order([row(-1)], [row()], first_kind='min', second_kind='max',
        denominator=row(1, 1), retained_id='a', discarded_id='b')
    assert result['normalized_lower'] == -1
    assert result['denominator_range'] == (1, 2)
    for denominator in (row(), row(-1), row(1, -1)):
        with pytest.raises(ValueError): certify_order([row(1)], [row()], first_kind='min', second_kind='max',
            denominator=denominator, retained_id='a', discarded_id='b')


def test_all_four_lower_gates_hold_on_independent_rational_grid():
    a = [row(1, 2), row(3, -1)]; b = [row(-1, 1), row(0, -2)]
    for first_kind, second_kind in product(('min', 'max'), repeat=2):
        kwargs = {}
        if first_kind == second_kind:
            count = len(a) if first_kind == 'min' else len(b)
            width = len(b) if first_kind == 'min' else len(a)
            kwargs['proofs'] = [(F(1, width),)*width]*count
        elif first_kind == 'max': kwargs['pair_witness'] = (0, 0)
        result = gate(a, b, first_kind=first_kind, second_kind=second_kind, **kwargs)
        op_a = min if first_kind == 'min' else max
        op_b = min if second_kind == 'min' else max
        for x in (F(i, 32) for i in range(33)):
            actual = op_a(r[0]+r[1]*x for r in a)-op_b(r[0]+r[1]*x for r in b)
            assert actual >= result['normalized_lower']
