"""Controls for actual bound-aware six-free TreeStrap batch semantics."""
from math import inf,tanh
import pytest
from results.dev_aux.task2492.learning import Sample,Receipt,TreeStrap
from results.dev_aux.task2532.free_model import FreeModel

def receipt(samples,complete=True):return Receipt(None,0.,None,False,tuple(samples),100,complete,0,.01,'test')
def objective(w,samples):
 value=0.
 for s in samples:
  x=tanh(sum(a*b for a,b in zip(w,s.phi))/10);lo=tanh(s.lower/10);hi=tanh(s.upper/10);e=min(0,x-lo)+max(0,x-hi);value+=e*e/2
 return value/len(samples)
def test_free6_tree_update_matches_mean_finite_difference():
 samples=[Sample((1,0,-1,2,0,1),2.,inf,2),Sample((-1,1,0,0,2,0),-inf,-2.,1),Sample((0,0,1,0,-1,0),-inf,inf,1),Sample((2,1,0,0,0,-1),1.,1.,2)]
 m=FreeModel([1,.8,1.2,.6,1.4,.9]);before=list(m.weights);st=TreeStrap(.05).update(m,receipt(samples));assert st['samples']==4;h=1e-5
 for j in range(6):
  a=list(before);b=list(before);a[j]+=h;b[j]-=h;expected=before[j]-.05*(objective(a,samples)-objective(b,samples))/(2*h);assert m.weights[j]==pytest.approx(expected,abs=1e-10)
 assert m.weights[0]!=before[0]
def test_bound_satisfied_is_not_fitted_as_exact():
 for lo,hi in [(-inf,2.),(-2.,inf),(-inf,inf)]:
  m=FreeModel([1]*6);before=list(m.weights);r=TreeStrap().update(m,receipt([Sample((1,-1,0,0,0,0),lo,hi,1)]));assert m.weights==before and r['loss']==0 and r['active']==0
def test_incomplete_receipt_discards_all_partial_samples():
 m=FreeModel([1]*6);before=list(m.weights);r=TreeStrap().update(m,receipt([Sample((1,0,0,0,0,0),100.,inf,2)],False));assert m.weights==before and r['samples']==0 and r['loss']is None
def test_terminal_search_target_can_update_current_material_node():
 m=FreeModel([1]*6);before=list(m.weights);r=TreeStrap().update(m,receipt([Sample((1,0,0,0,0,0),1000000.,1000000.,2)]));assert r['active']==1 and m.weights[0]>before[0]
def test_mean_update_independent_of_identical_sample_duplication():
 s=Sample((1,2,-1,0,0,0),-3.,-3.,1);a=FreeModel([1]*6);b=FreeModel([1]*6);TreeStrap().update(a,receipt([s]));TreeStrap().update(b,receipt([s]*13));assert a.weights==pytest.approx(b.weights,abs=1e-14)
