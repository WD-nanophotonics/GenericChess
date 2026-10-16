from pathlib import Path
import json
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2072.no_win_filter import CompleteGraphNoWinFilter
from scripts.generic_session_win_proof import SessionProofResult
@pytest.fixture(scope='module')
def pair():
 t=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2058','results/dev_aux/task2059');calls=[]
 def stub(*a,**k):calls.append(k);return SessionProofResult('UNKNOWN',None,'delegated_positive_or_foreign',0,0.,0)
 return t,CompleteGraphNoWinFilter(t,solver=stub),calls
def session(i):return GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(f'results/dev_aux/task2063/rules-{i}.json').read_text())))
def test_negative_skip_is_unknown_not_draw_and_positive_delegates(pair):
 t,f,calls=pair;seen=set()
 for i in range(16):
  s=session(i);l=t.label(s);before=len(calls);r=f(s,target=s.state.position.side_to_move)
  if l.value<=0:assert r.status=='UNKNOWN'and r.certificate is None and r.nodes==0 and r.reason=='certified_complete_graph_no_win'and len(calls)==before;seen.add('skip')
  else:assert r.reason=='delegated_positive_or_foreign'and len(calls)==before+1;seen.add('delegate')
 assert seen=={'skip','delegate'}
def test_noncanonical_history_never_gets_exact_positive_label(pair):
 t,f,calls=pair;s=session(0);s.submit(s.legal_actions()[0]);assert t.label(s).quality=='UNKNOWN'
 r=f(s);assert r.status=='UNKNOWN'and r.certificate is None
 if r.reason=='certified_complete_graph_no_win':assert r.nodes==0
def test_foreign_movement_always_delegates(pair):
 t,f,calls=pair;s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2064/rules.json').read_text())));before=len(calls);r=f(s);assert r.reason=='delegated_positive_or_foreign'and len(calls)==before+1


def test_same_real_session_two_targets_loss_and_draw(pair):
 t,f,calls=pair;done=set()
 for i in range(16):
  s=session(i);l=t.label(s)
  if l.value not in(-1,0)or l.value in done:continue
  before=s.to_record();side=s.state.position.side_to_move;count=len(calls);r=f(s,target=side)
  assert r.reason=='certified_complete_graph_no_win'and r.status=='UNKNOWN'and r.nodes==0 and len(calls)==count
  other=f(s,target=1-side)
  if l.value==-1:assert other.reason=='delegated_positive_or_foreign'and len(calls)==count+1 and calls[-1]['target']==1-side
  else:assert other.reason=='certified_complete_graph_no_win'and other.nodes==0 and len(calls)==count
  assert s.to_record()==before;done.add(l.value)
 assert done=={-1,0}

def test_cancel_and_zero_time_do_not_delegate(pair):
 t,f,calls=pair;s=session(0);before=len(calls)
 for kwargs in(dict(seconds=0),dict(cancel=lambda:True)):
  r=f(s,**kwargs);assert r.status=='UNKNOWN'and r.nodes==0 and r.certificate is None
 assert len(calls)==before
 with pytest.raises(ValueError):f(s,target=True)
