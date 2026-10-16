"""Same graph proof semantics under a changed bounded frontier scheduler."""
import pytest
import results.dev_aux.task2180.test_graph as original
from results.dev_aux.task2180.test_graph import *
from results.dev_aux.task2189.frontier import prove_frontier_graph,select_frontier
from results.dev_aux.task2187.trace import Trace
from scripts.generic_win_proof import _Budget
from types import SimpleNamespace
from collections import deque

@pytest.fixture(autouse=True)
def frontier_under_test(monkeypatch):
 monkeypatch.setattr(original,'prove_graph',prove_frontier_graph)

def test_selection_cycles_are_unknown_and_fifo_fallback_is_finite():
 pos=[SimpleNamespace(side_to_move=0),SimpleNamespace(side_to_move=1),SimpleNamespace(side_to_move=0)]
 sessions=[SimpleNamespace(result=SimpleNamespace(status=SessionStatus.ONGOING))for _ in pos]
 stats=dict(visits=0,fallbacks=0,cycles=0)
 i=select_frontier(deque([2]),pos,sessions,[[('x',1)],[('y',0),('z',2)],[]],[True,True,False],[None]*3,0,_Budget(100,1.,None,__import__('time').perf_counter),96,stats)
 assert i==2 and stats['cycles']>=1
 # No reachable open frontier: heuristic MUST return FIFO, never a proof.
 stats=dict(visits=0,fallbacks=0,cycles=0)
 i=select_frontier(deque([2]),pos,sessions,[[('x',1)],[('y',0)],[]],[True,True,False],[None]*3,0,_Budget(100,1.,None,__import__('time').perf_counter),96,stats)
 assert i==2 and stats['fallbacks']==1

def test_observation_hooks_restore_on_error_and_trace_buffer_is_bounded():
 import scripts.generic_session_win_proof_batch_pn as pn
 import results.dev_aux.task2179.graph as graph
 before=(pn.legal_successors,graph.canonical,GameSession.__init__,GameSession.legal_actions)
 t=Trace(1);s,_=small_defender()
 with pytest.raises(RuntimeError):
  with t.hooks('GRAPH'):raise RuntimeError('deliberate')
 assert before==(pn.legal_successors,graph.canonical,GameSession.__init__,GameSession.legal_actions)
 t.observe(s.state,s.to_record(),'test');t.observe(s.state,s.to_record(),'test')
 assert len(t.events)==1 and t.dropped==1
