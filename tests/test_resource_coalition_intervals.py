from fractions import Fraction as F
from itertools import permutations,product
import pytest
from scripts.resource_coalition_intervals import (
    allocation_intervals,allocation_total_interval,context_marginal_interval,pair_interaction_interval,
)


def table(values):
    return {frozenset(k):(F(v),F(v)) for k,v in values.items()}


def independently_average_orders(names,values):
    totals={r:F(0) for r in names};orders=list(permutations(names))
    for order in orders:
        before=frozenset()
        for r in order:
            after=before|{r}
            totals[r]+=values[after]-values[before]
            before=after
    return {r:v/len(orders) for r,v in totals.items()}


def test_pin_complementarity_allocates_joint_gain_but_marginals_depend_on_background():
    t=table({():0,('P',):0,('R',):0,('P','R'):1})
    assert allocation_intervals(('P','R'),t)=={'P':(F(1,2),F(1,2)),'R':(F(1,2),F(1,2))}
    assert context_marginal_interval(('P','R'),t,'P',frozenset())==(0,0)
    assert context_marginal_interval(('P','R'),t,'P',frozenset({'R'}))==(1,1)


def test_three_resource_replica_changes_attribution_not_total_success():
    names=('P1','P2','R');values={}
    for bits in product((False,True),repeat=3):
        s=frozenset(n for n,b in zip(names,bits) if b)
        values[s]=int('R' in s and bool(s&{'P1','P2'}))
    result=allocation_intervals(names,{s:(v,v) for s,v in values.items()})
    exact=independently_average_orders(names,values)
    assert exact=={'P1':F(1,6),'P2':F(1,6),'R':F(2,3)}
    assert result=={k:(v,v) for k,v in exact.items()}
    assert allocation_total_interval(names,{s:(v,v) for s,v in values.items()})==(1,1)


def test_all_small_binary_task_tables_match_independent_order_enumeration():
    names=('a','b','c')
    subsets=[frozenset(n for n,b in zip(names,bits) if b) for bits in product((False,True),repeat=3)]
    for values in product((0,1),repeat=8):
        exact=dict(zip(subsets,values))
        expected=independently_average_orders(names,exact)
        observed=allocation_intervals(names,{s:(v,v) for s,v in exact.items()})
        assert observed=={k:(v,v) for k,v in expected.items()}
        assert sum(expected.values())==exact[frozenset(names)]-exact[frozenset()]


def test_unknown_coalitions_keep_signed_bounds_and_shared_efficiency():
    known={frozenset():(0,0),frozenset(('a','b')):(1,1)}
    observed=allocation_intervals(('a','b'),known)
    assert observed=={'a':(0,1),'b':(0,1)}
    assert allocation_total_interval(('a','b'),known)==(1,1)
    for a,b in product((0,1),repeat=2):
        full={**known,frozenset({'a'}):(a,a),frozenset({'b'}):(b,b)}
        for r,(lo,hi) in allocation_intervals(('a','b'),full).items():
            assert observed[r][0]<=lo<=hi<=observed[r][1]


def test_nonmonotone_task_has_negative_allocation_without_clipping():
    t=table({():0,('a',):1,('b',):0,('a','b'):0})
    assert allocation_intervals(('a','b'),t)=={'a':(F(1,2),F(1,2)),'b':(-F(1,2),-F(1,2))}
    assert allocation_total_interval(('a','b'),t)==(0,0)


def test_resource_identity_or_value_errors_fail_closed():
    for names,t in [(('a','a'),{}),(tuple('abcdefgh'),{}),(('a',),{frozenset({'b'}):(0,1)}),
                    (('a',),{frozenset():(0.0,1)}),(('a',),{frozenset():(1,0)})]:
        with pytest.raises(ValueError):allocation_intervals(names,t)
    with pytest.raises(ValueError):
        context_marginal_interval(('a',),{},'a',frozenset({'a'}))


def test_mixed_difference_reconstructs_every_binary_two_resource_table():
    for empty,a,b,joint in product((0,1),repeat=4):
        t=table({():empty,('a',):a,('b',):b,('a','b'):joint})
        lo,hi=pair_interaction_interval(('a','b'),t,'a','b')
        assert lo==hi==joint-a-b+empty
        for x,y in product((0,1),repeat=2):
            expected=[empty,b,a,joint][2*x+y]
            assert empty+(a-empty)*x+(b-empty)*y+lo*x*y==expected


def test_unknown_interaction_and_common_background_are_preserved():
    t=table({():0,('a','b'):1})
    assert pair_interaction_interval(('a','b'),t,'a','b')==(-1,1)
    t=table({('c',):0,('a','c'):0,('b','c'):0,('a','b','c'):1})
    assert pair_interaction_interval(('a','b','c'),t,'a','b',frozenset({'c'}))==(1,1)
    for a,b,background in [('a','a',frozenset()),('a','missing',frozenset()),('a','b',frozenset({'a'}))]:
        with pytest.raises(ValueError):pair_interaction_interval(('a','b'),{},a,b,background)


def test_additive_uniform_error_lower_bounds_are_attained_on_pin_table():
    # Four residuals determine I=1: with an intercept max error>=1/4.
    # With empty baseline fixed, three residuals give max error>=1/3.
    for intercept,wa,wb,limit in [(F(-1,4),F(1,2),F(1,2),F(1,4)),
                                  (F(0),F(1,3),F(1,3),F(1,3))]:
        errors=[intercept+wa*x+wb*y-x*y for x,y in product((0,1),repeat=2)]
        assert max(abs(e) for e in errors)==limit
        assert errors[3]-errors[2]-errors[1]+errors[0]==-1


def test_physical_obstruction_allocates_negative_credit_and_keeps_same_event():
    names=('N','R','P');values={}
    for bits in product((False,True),repeat=3):
        s=frozenset(n for n,b in zip(names,bits) if b)
        values[s]=int('N' in s and 'R' in s and 'P' not in s)
    exact=independently_average_orders(names,values)
    assert exact=={'N':F(1,6),'R':F(1,6),'P':-F(1,3)}
    supplied={s:(v,v) for s,v in values.items()}
    assert allocation_intervals(names,supplied)=={r:(v,v) for r,v in exact.items()}
    assert context_marginal_interval(names,supplied,'P',frozenset({'N','R'}))==(-1,-1)
    assert allocation_total_interval(names,supplied)==(0,0)
