"""Consequential controls for same-search all-node learning contrast."""
import math,random
import pytest
from results.dev_aux.task2492.learning import Model,TreeStrap,Sample,Receipt
from results.dev_aux.task2492.test_learning import Tree
from results.dev_aux.task2504.search import TrainingSearch

def test_pathseeded_bounds_contain_independent_minimax_and_leaf_gradient():
 for seed in range(64):
  rng=random.Random(seed);leaves=[[rng.randint(-9,9)for _ in range(2)]for _ in range(2)];env=Tree(leaves);m=Model([1,1]);r=TrainingSearch(2,quiet=False).search(env,m,seed=seed)
  assert r.complete and r.value==max(map(min,leaves))and env.path==[]
  assert m.raw(r.pv_phi)==r.value
  for s in r.samples:
   exact=max(map(min,leaves))if s.depth==2 else min(leaves[int(s.phi[1]-100)])
   assert s.lower<=exact<=s.upper

def test_tree_frozen_mean_update_uses_one_sided_interval_and_discards_partial():
 m=Model([1,.7,1.3]);samples=(Sample((1,2,-1),4,math.inf,1),Sample((0,1,2),-math.inf,1,1),Sample((0,2,1),-math.inf,8,1));r=Receipt(None,0,None,False,samples,50,True,0,.1,'complete');before=list(m.weights)
 def loss(w):
  z=Model(w);total=0.
  for s in samples:
   v=z.prediction(s.phi);a=math.tanh(s.lower/10);b=math.tanh(s.upper/10);e=max(a-v,0)+min(b-v,0);total+=e*e/2
  return total/len(samples)
 expected=list(before)
 for j in(1,2):
  a=list(before);b=list(before);a[j]+=1e-6;b[j]-=1e-6;expected[j]-=.05*(loss(a)-loss(b))/2e-6
 stats=TreeStrap(.05).update(m,r)
 assert m.weights==pytest.approx(expected,abs=1e-10)and stats['active']==2 and m.weights[0]==1
 snapshot=list(m.weights);failed=Receipt(None,None,None,False,(),2,False,0,.1,'resource limit');TreeStrap(.05).update(m,failed);assert m.weights==snapshot
