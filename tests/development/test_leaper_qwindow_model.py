"""Artificial finite-tree window contracts; explicitly NOT a legal Core witness."""
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from generic_chess.core.position import Hands
from scripts.leaper_quiet_root_intervention import S,SearchStatistics,SearchLimits,TranspositionTable,SearchTuning,root_intervention,bound,flip

class Tree:
 def __init__(self):self.node='root';self.generated=0
 @property
 def terminal_status(self):return SimpleNamespace(is_terminal=False)
 @property
 def state(self):return SimpleNamespace(position=SimpleNamespace(board=(None,)*4,hands=(Hands.empty(),Hands.empty()),side_to_move=0 if self.node=='root' else 1),terminal_status=self.terminal_status)
 def in_check(self,*args,**kwargs):return False
 def legal_actions(self,checkpoint=None):self.generated+=1;return ('n','q') if self.node=='root' else ()
 @contextmanager
 def pushed(self,action,checkpoint=None):
  old=self.node;self.node=action
  try:yield self.state
  finally:self.node=old

@pytest.fixture
def evaluate(monkeypatch):
 monkeypatch.setattr(S,'_declaration_options',lambda *args:())
 monkeypatch.setattr(S,'semantic_engine_for',lambda compiled:object())
 monkeypatch.setattr(S,'noisy_child',lambda action,*args,**kwargs:action=='n')
 def run(mode,a,b):
  rt=Tree();ev=SimpleNamespace(evaluate=lambda state:{'root':2,'q':0,'n':1}[rt.node]);limits=SearchLimits(quiescence_max_depth=1,quiescence_hard_max_depth=8);ctx=S._Context(SimpleNamespace(),ev,TranspositionTable(1),SearchStatistics(),S._Budget(limits,None),SearchTuning(),False,False,1,8,None,runtime=rt);trace=dict(actions=[])
  v=S._quiescence_runtime(a,b,0,0,ctx) if mode=='BASELINE' else root_intervention(a,b,ctx,mode,trace)
  assert rt.node=='root'
  return v,trace,rt.generated
 return run


def test_actual_Q_code_virtual_pass_and_coverage_are_distinct(evaluate):
 expected={'BASELINE':2,'ADD_QUIET':2,'NO_SP_NOISY':-1,'NO_SP_ALL':0}
 for mode,true in expected.items():assert evaluate(mode,-3,3)[0]==true
 # Standpat cutoff occurs before any legal generation, including ADD_QUIET.
 assert evaluate('BASELINE',-1,1)[2]==evaluate('ADD_QUIET',-1,1)[2]==0
 assert evaluate('NO_SP_ALL',-1,1)[0]==0


def test_all_integer_windows_bound_their_own_finite_policy_value(evaluate):
 truth={'BASELINE':2,'ADD_QUIET':2,'NO_SP_NOISY':-1,'NO_SP_ALL':0}
 for a in range(-3,3):
  for b in range(a+1,4):
   for mode,true in truth.items():
    value=evaluate(mode,a,b)[0];kind=bound(value,a,b)
    assert (true<=value if kind=='UPPER' else true>=value if kind=='LOWER' else true==value),(a,b,mode,value,kind,true)


def test_parent_flip_needs_exact_or_separated_bounds(evaluate):
 competitor=-1;old=evaluate('BASELINE',-3,3)[0];forced=evaluate('NO_SP_ALL',-3,3)[0]
 assert -old<competitor<-forced  # Artificial two-branch parent only.
 inherited=evaluate('NO_SP_ALL',1,3)[0]
 assert inherited==1 and bound(inherited,1,3)=='UPPER'
 assert flip(bound(inherited,1,3))=='LOWER' and -inherited==competitor
 # Parent >= -1 overlaps competitor -1: the narrow result cannot certify flip.
