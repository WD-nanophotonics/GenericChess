from pathlib import Path
import ast,json,time,pytest
from scripts.generic_win_proof import _Budget,_Interrupted
from results.dev_aux.task2382.incremental import SelectorPoll
from results.dev_aux.task109.adapter import PersistentStop

def test_only_selector_helper_changed():
 a=ast.parse(Path('results/dev_aux/task2273/incremental_adapted.py').read_text(encoding='utf-8-sig'));b=ast.parse(Path('results/dev_aux/task2382/incremental.py').read_text(encoding='utf-8-sig'));old={n.name:n for n in a.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};new={n.name:n for n in b.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 for name,node in old.items():
  candidate=new['_select_frontier'if name=='select_frontier'else name]
  if name=='select_frontier':candidate.name='select_frontier'
  assert ast.dump(node)==ast.dump(candidate),name

def test_entry_every16_and_return_have_fresh_authority():
 calls=[];b=_Budget(1,10,lambda:calls.append(True)or False,lambda:0);p=SelectorPoll(b);assert len(calls)==1
 for _ in range(15):p.poll()
 assert len(calls)==1;p.poll();assert len(calls)==2
 for _ in range(16):p.poll()
 assert len(calls)==3

def test_stop_first_eligible_boundary_propagates_without_retry():
 calls=[]
 def stop():
  calls.append(True)
  if len(calls)==2:raise PersistentStop('controlled stop whilepurehelper')
 b=_Budget(1,10,stop,lambda:0);p=SelectorPoll(b)
 for _ in range(15):p.poll()
 with pytest.raises(PersistentStop):p.poll()
 assert len(calls)==2

def test_deadline_still_checked_every_internal_unit():
 clock=[0.];b=_Budget(1,1,lambda:False,lambda:clock[0]);p=SelectorPoll(b);clock[0]=1.
 with pytest.raises(_Interrupted):p.poll()
 assert b.reason=='time_budget'and p.units==1

def test_stop_at_selector_return_cannot_escape():
 import results.dev_aux.task2382.incremental as m
 old=m._select_frontier;calls=[]
 def stop():
  calls.append(True)
  if len(calls)==2:raise PersistentStop('controlledstopatreturn')
 b=_Budget(1,10,stop,lambda:0)
 try:
  m._select_frontier=lambda *args:7
  with pytest.raises(PersistentStop):m.select_frontier(None,None,None,None,None,None,None,None,b,None,None,None)
 finally:m._select_frontier=old
 assert len(calls)==2
