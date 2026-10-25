"""Research-only completed-iteration choice observer, no policy or semantic calls."""
import sys,time
from scripts import leaper_design as L
from generic_chess.ai.alphabeta.search import SearchResult
class IterationChoiceObserver:
 def __init__(self,started):self.started=started;self.events=[]
 def __call__(self,depth,nodes,qnodes):
  frame=sys._getframe(1)
  assert frame.f_code.co_name=='run_root_search','unsupported caller frame'
  best=frame.f_locals['best'];stats=frame.f_locals['stats']
  assert isinstance(best,SearchResult)and stats.completed_depth==depth
  self.events.append(dict(depth=depth,nodes=nodes,qnodes=qnodes,seconds=time.perf_counter()-self.started,action=L.record_value(best.best_action),score=best.score,pv=L.record_value(best.pv),source='completed_main_iteration'))
