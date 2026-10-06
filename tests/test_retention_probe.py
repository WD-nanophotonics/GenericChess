from fractions import Fraction as F
import itertools
import pytest
from scripts.retention_probe import probe_values


def test_incompatible_losses_cannot_be_one_worst_exchange():
    r = probe_values({'a':(0,1),'b':(1,0),'c':(1,1)})
    assert r['hidden'] == F(1,2) and r['revealed'] == 0
    assert r['common_witnesses'] == [] and not r['marginal_vector_is_actual']
    assert r['marginal_witnesses'] == [['a'],['b']]


def test_one_joint_witness_makes_quantifiers_equal():
    r = probe_values({'a':(0,0),'b':(1,1)})
    assert r['hidden'] == r['revealed'] == 0
    assert r['common_witnesses'] == ['a'] and r['marginal_vector_is_actual']


def test_exhaustive_information_monotonicity_independent_formula():
    vectors = tuple(itertools.product((0,1),repeat=3))
    for mask in range(1,1<<len(vectors)):
        rows = {str(i):v for i,v in enumerate(vectors) if mask>>i&1}
        r = probe_values(rows)
        # Explicitly enumerate all tag-dependent enemy policies.
        oracle = min(sum(rows[a][j] for j,a in enumerate(policy)) for policy in
                     itertools.product(rows, repeat=3))
        assert r['revealed'] == F(oracle,3) <= r['hidden']
        assert r['marginal_vector_is_actual'] == (tuple(r['marginal_minimum']) in rows.values())


@pytest.mark.parametrize('rows',[{}, {'x':()}, {'x':(True,0)}, {'x':(1,0),'y':(1,)}, {'x':(2,0)}])
def test_invalid_or_empty_physical_tables_fail(rows):
    with pytest.raises(ValueError):probe_values(rows)
