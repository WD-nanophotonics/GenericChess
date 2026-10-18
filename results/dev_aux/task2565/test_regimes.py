import pytest
from results.dev_aux.task2565.train import observes,model,restore,environment,prefix
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2492.test_learning import receipt

def test_clock_truth_table():
 for method in ['Fixed','SelfCandidate','SelfEvery']:
  for color in [0,1]:
   assert not observes(method,color,color,False)
   assert observes(method,color,color,True)
   assert observes(method,1-color,color,True)==(method=='SelfEvery')

def test_selfevery_white_coordinates_no_extra_color_sign():
 from math import tanh
 for color in [0,1]:
  m=model('generic',[1.,1.,1.,1.,1.,1.]);before=list(m.weights);td=TDLeafEpisode(.05,.95);phis=[(0,1,0,0,0,0),(0,-1,0,0,0,0)];vals=[.1,-.2];grads=[m.gradient(p)for p in phis]
  for actor,value,phi in zip([color,1-color],vals,phis):
   if observes('SelfEvery',actor,color,True):td.observe(m,receipt(value=value*10,phi=phi))
  td.finish(m,-1)
  ds=[tanh(vals[1])-tanh(vals[0]),-1-tanh(vals[1])]
  expected=.05*sum(grads[i][1]*sum(.95**(j-i)*ds[j]for j in range(i,2))for i in range(2))
  assert m.weights[1]==pytest.approx(before[1]+expected)

def test_chess_full_stack_and_scale():
 e=environment(0,None);prefix(e,0,311000,8);r=restore(0,None,e.record());assert r.record()==e.record();assert r.features()==e.features();m=model('chess',[7.,1.,1.,1.,1.]);assert m.weights[0]==1
