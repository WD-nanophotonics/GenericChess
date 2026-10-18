import pytest
from math import tanh
from results.dev_aux.task2566.tc import CoordinateTC,TCEpisode
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2492.test_learning import receipt

def test_cancellation_and_rate_recovery_uses_unscaled_impulses():
 m=FreeModel([1.]);t=CoordinateTC(1,.1);a=t.update(m,[[1.],[-1.]])
 assert m.weights==[1.]and a['rates_before']==[1.]and t.rates==[0.]and t.absolute==[2.]
 b=t.update(m,[[1.]]);assert b['delta']==[0.]and t.rates==pytest.approx([1/3])and m.weights==[1.]
 c=t.update(m,[[1.]]);assert c['delta']==pytest.approx([.1/3])and t.rates==[.5]

def test_coordinate_specific_and_old_rate_order():
 m=FreeModel([1.,1.]);t=CoordinateTC(2,.1);a=t.update(m,[[2.,-1.],[-1.,-1.]])
 assert a['delta']==pytest.approx([.1,-.2]);assert t.rates==pytest.approx([1/3,1.]);b=t.update(m,[[3.,1.]])
 assert b['delta']==pytest.approx([.1,.1]);assert t.net==[4.,-1.]and t.absolute==[6.,3.]

def test_first_tc_episode_equals_independent_reverse_td_and_raw_abs():
 m=FreeModel([1.,1.]);before=list(m.weights);t=TCEpisode(2,.1,.7);phis=[(0.,1.),(1.,0.),(0.,-1.)];vs=[.2,-.1,.3];grads=[m.gradient(p)for p in phis]
 for v,p in zip(vs,phis):t.observe(m,receipt(value=v*10,phi=p))
 ds=[tanh(vs[1])-tanh(vs[0]),tanh(vs[2])-tanh(vs[1]),1-tanh(vs[2])];expect=[sum(grads[i][j]*sum(.7**(k-i)*ds[k]for k in range(i,3))for i in range(3))for j in range(2)];a=t.finish(m,1)
 assert m.weights==pytest.approx([w+.1*x for w,x in zip(before,expect)]);assert a['recommended_net']==pytest.approx(expect)
 independent_abs=[sum(abs(ds[k]*sum(.7**(k-i)*grads[i][j]for i in range(k+1)))for k in range(3))for j in range(2)]
 assert a['recommended_absolute']==pytest.approx(independent_abs);assert t.tc.rates==pytest.approx([abs(n)/d for n,d in zip(expect,independent_abs)])

def test_unknown_one_observation_cannot_create_terminal_credit_or_TC_change():
 m=FreeModel([1.,1.]);t=TCEpisode(2);t.observe(m,receipt(value=.5));a=t.finish(m,None)
 assert m.weights==[1.,1.]and a['samples']==0 and t.tc.absolute==[0.,0.]and t.tc.rates==[1.,1.]

def test_unknown_retains_only_completed_td_transitions():
 m=FreeModel([1.,1.]);t=TCEpisode(2,.1,.95);g=m.gradient((0.,1.));t.observe(m,receipt(value=1,phi=(0.,1.)));t.observe(m,receipt(value=2,phi=(0.,1.)));a=t.finish(m,None)
 assert a['samples']==1 and a['terminal_credit_l1']==0;assert m.weights==pytest.approx([1+.1*x*(tanh(.2)-tanh(.1))for x in g])

def test_invalid_impulse_does_not_mutate_model_or_counters():
 m=FreeModel([1.,1.]);t=CoordinateTC(2)
 for rows in [[[1.]],[[float('nan'),1.]]]:
  with pytest.raises(ValueError):t.update(m,rows)
  assert m.weights==[1.,1.]and t.net==[0.,0.]and t.absolute==[0.,0.]
