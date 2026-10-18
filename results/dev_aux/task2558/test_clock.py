from math import isclose,inf
import pytest
from results.dev_aux.task2558.clock import rate
from results.dev_aux.task2492.learning import TreeStrap,Receipt,Sample
from results.dev_aux.task2532.free_model import FreeModel

def test_cost_integral_partition_and_mean():
 # Clock mass telescopes over arbitrary partitions, including opponent cost.
 points=[0,23,555,3200000]
 assert isclose(sum(rate(.05,b,a,'CostClock')['eta'] for a,b in zip(points,points[1:])),.05*27795)
 assert rate(.05,555,23,'Mean')['eta']==.05

def test_analytic_one_sided_update_with_cost_clock():
 phi=(1.,0.,0.,0.,0.,0.); r=Receipt(None,0.,None,False,(Sample(phi,2.,inf,1),Sample(phi,-inf,0.,1)),100,True,0,0.,'complete')
 # At zero predictions only the lower bound is violated; upper bound at0 inactive.
 from math import tanh
 m=FreeModel([0.]*6); eta=rate(.05,100,0,'CostClock')['eta'];s=TreeStrap(eta).update(m,r)
 assert isclose(m.weights[0],eta*tanh(.2)*.1/2)
 assert s['active']==1

def test_unresolved_no_gradient_or_clock_credit():
 m=FreeModel([1.]*6); r=Receipt(None,None,None,False,(),12,False,0,0.,'resource limit')
 assert not TreeStrap(.5).update(m,r)['changed'] and m.weights==[1.]*6

@pytest.mark.parametrize('args',[(.05,0,0,'CostClock'),(.05,9,10,'Mean'),(-1,10,0,'Mean'),(.05,10,0,'TD')])
def test_bad_clock(args):
 with pytest.raises(ValueError):rate(*args)
