import pytest,chess,random
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2501.search import TrainingSearch as FullSearch
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.adapters import ChessEnv

def test_plain_arm_unchanged_under_bounded_engine():
 for seed in range(4):
  e=ChessEnv();rng=random.Random(71000+seed)
  for _ in range(16):e.push(rng.choice(sorted(e.actions(),key=lambda a:a.uci())))
  m=Model([1]*5);a=TrainingSearch().search(e,m,seed=seed);b=FullSearch().search(e,m,seed=seed)
  assert a==b or (a.complete,b.complete,a.action,b.action,a.value,b.value,a.nodes,b.nodes)==(True,True,b.action,a.action,b.value,a.value,b.nodes,a.nodes)

def test_bounded_tactical_target_is_finite_and_pv_consistent():
 e=ChessEnv();rng=random.Random(71000)
 for _ in range(16):e.push(rng.choice(sorted(e.actions(),key=lambda a:a.uci())))
 before=e.record();s=TrainingSearch(2,quiet=True,q_limit=2);m=Model([1]*5);r=s.search(e,m,nodes=32768)
 assert r.complete and r.value==m.raw(r.pv_phi) and e.record()==before
 assert r.q_caps==s.last_stats['q_truncated_leaf_labels'] and r.q_caps>0
 assert s.last_stats['q_cap_still_tactical']>0

def test_check_evasion_is_not_stopped_at_optional_tactical_cap():
 e=ChessEnv(chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1'));before=e.record();s=TrainingSearch(1,quiet=True,q_limit=1);r=s.search(e,Model([1]*5),nodes=8192)
 assert r.complete and r.value==1000000 and r.pv_terminal and e.record()==before
 assert s.last_stats['check_evasion_nodes']>0

def test_resource_censor_and_state_restoration():
 e=ChessEnv();before=e.record();r=TrainingSearch(2,quiet=True).search(e,Model([1]*5),nodes=2)
 assert not r.complete and not r.samples and r.action is None and r.value is None and e.record()==before

class BranchEnv:
 def __init__(self,standpat=False):self.path=[];self.standpat=standpat
 def player(self):return len(self.path)%2
 def terminal(self):return None
 def actions(self):return (0,1)if not self.path else(0,)if len(self.path)==1 else()
 def tactical(self,a):return True
 def in_check(self):return False
 def features(self):
  if not self.path:return(0.,0.,0.)
  x=2. if len(self.path)==2 or self.standpat else 5.
  if self.standpat and len(self.path)==2:x=3.
  return(0.,x,0.)if self.path[0]==0 else(0.,0.,x)
 def push(self,a):self.path.append(a)
 def pop(self):self.path.pop()

def test_selected_capture_leaf_features_follow_selected_root_not_last_tied_branch():
 for seed in range(20):
  e=BranchEnv();r=TrainingSearch(1,quiet=True).search(e,Model([1,1,1]),seed=seed)
  assert r.complete and r.value==2
  assert r.pv_phi==((0.,2.,0.)if r.action==0 else(0.,0.,2.)) and e.path==[]

def test_winning_standpat_keeps_its_own_features_after_other_leaf_visited():
 for seed in range(10):
  e=BranchEnv(standpat=True);r=TrainingSearch(1,quiet=True).search(e,Model([1,1,1]),seed=seed)
  assert r.complete and r.value==2
  assert r.pv_phi==((0.,2.,0.)if r.action==0 else(0.,0.,2.))

def test_real_train_check_evasions_extend_past_optional_two_ply_horizon():
 from pathlib import Path
 import json
 rows=[json.loads(x)for x in Path('results/dev_aux/task2505/queries.jsonl').read_text().splitlines()]
 row=next(r for r in rows if r['quiet']and r['complete']and r['stats']['max_qply']>2)
 b=chess.Board(row['record']['initial'])
 for u in row['record']['moves']:b.push_uci(u)
 e=ChessEnv(b);calls=[]
 class CheckedModel(Model):
  def raw(self,phi):
   assert not e.in_check(),'q static evaluation inside check'
   calls.append(e.board.fen());return super().raw(phi)
 s=TrainingSearch(2,quiet=True,q_limit=2);r=s.search(e,CheckedModel(row['initial']),seed=row['seed']*100000+row['family'])
 assert r.complete and r.value==row['value'] and r.action.uci()==row['action']
 assert r.pv_phi==tuple(row['pv_phi']) and s.last_stats['max_qply']>2 and calls
