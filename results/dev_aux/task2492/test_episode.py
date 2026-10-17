import pytest
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.test_learning import receipt

def test_episode_backward_matches_independent_forward_lambda_sum():
 m=Model([1,1]);t=TDLeafEpisode(.1,.95)
 values=[.1,-.2,.3];phis=[(0.,1.),(0.,2.),(0.,-1.)]
 gradients=[m.gradient(p)for p in phis]
 for value,phi in zip(values,phis):t.observe(m,receipt(value=value*10,phi=phi))
 # Targets are tanh(score/scale), gradients from corresponding frozen PV phi.
 from math import tanh
 vs=list(map(tanh,values));ds=[vs[1]-vs[0],vs[2]-vs[1],1-vs[2]]
 expected=sum(gradients[i][1]*sum(.95**(j-i)*ds[j]for j in range(i,3))for i in range(3))
 t.finish(m,1);assert m.weights[1]==pytest.approx(1+.1*expected) and m.weights[0]==1

def test_episode_unknown_no_terminal_error_and_reject_weight_drift():
 m=Model([1,1]);t=TDLeafEpisode();t.observe(m,receipt(value=1));before=list(m.weights)
 stats=t.finish(m,None);assert m.weights==before and stats['samples']==0
 t.observe(m,receipt(value=1));m.weights[1]+=1
 with pytest.raises(ValueError):t.finish(m,1)

def test_real_short_mate_trajectory_keeps_nonzero_pv_credit():
 import chess
 from results.dev_aux.task2492.adapters import ChessEnv
 from results.dev_aux.task2492.learning import AlphaBeta
 e=ChessEnv(chess.Board('7k/p7/5KQ1/8/8/8/8/8 b - - 0 1'))
 m=Model([1]*5);td=TDLeafEpisode(eta=.1,lam=.95)
 for ply in range(3):
  if e.terminal()is not None:break
  r=AlphaBeta(1,0).search(e,m,seed=ply)
  assert r.complete;td.observe(m,r);e.push(r.action)
 assert e.terminal()==1
 stats=td.finish(m,e.terminal())
 assert stats['changed'] and m.weights[4]>1 and m.weights[0]==1
