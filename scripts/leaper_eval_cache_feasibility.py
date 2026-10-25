"""Three frozen evaluation-request samples and finite exact-cache break-even.
No search memoization or production changes. Every sampled evaluation is executed.
"""
from pathlib import Path
from collections import deque
from dataclasses import replace
from types import SimpleNamespace,MappingProxyType
from datetime import datetime,timezone
import argparse,json,hashlib,time,traceback,sys,tracemalloc
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def frozen_profile(p):
 return replace(p,**{k:MappingProxyType(dict(getattr(p,k)))for k in('piece_profiles','board_value_by_type','hand_value_by_base_type','promotion_gain_by_type')})

def replay_cost(evaluator,positions,requests,capacity,enabled):
 cache={}if enabled else None;fifo=deque()if enabled else None;hits=miss=evictions=peak=0;check=SimpleNamespace(position=None);tick=time.perf_counter();cpu=time.process_time()
 for item in requests:
  pos=positions[item['id']];check.position=pos
  if enabled and pos in cache:value=cache[pos];hits+=1
  else:
   value=evaluator.evaluate(check);miss+=1
   if enabled:
    if len(cache)>=capacity:del cache[fifo.popleft()];evictions+=1
    cache[pos]=value;fifo.append(pos);peak=max(peak,len(cache))
  assert value==item['raw'],'raw integer parity, before search clipping'
 elapsed=time.perf_counter()-tick
 # Conservative retained-object size; shared objects deduplicated, not peak RSS.
 objects={}if not enabled else{ id(x):x for pos in cache for x in(pos,pos.board,pos.hands,pos.aux_state,*pos.board,*pos.hands)}
 retained=0 if not enabled else sys.getsizeof(cache)+sys.getsizeof(fifo)+sum(sys.getsizeof(v)for v in objects.values())
 return dict(enabled=enabled,seconds=elapsed,cpu_seconds=time.process_time()-cpu,requests=len(requests),computed=miss,hits=hits,evictions=evictions,peak_entries=peak,retained_object_bytes_lower_bound=retained,scope='In-process replay of actually sampled request sequence; no search speed claim, no peak-RSS claim. FullPositionvaluekey; disabled allocates no table.')

def run(d):
 plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert sha(__file__)==plan['source_sha256']and sha(d/'inputs.json')==plan['inputs_sha256'];assert not(d/'queries.jsonl').exists()and not(d/'receipt.json').exists()
 for p,h in plan['dependencies'].items():assert sha(p)==h
 begin=stamp();tick=time.perf_counter();attempted=0;count=0;status='FAILED'
 class Stop:
  last=0.;flag=False
  def is_cancelled(self):
   now=time.perf_counter()
   if now-self.last>=.25:self.last=now;self.flag=stopped()or now-tick>=plan['batch_seconds']
   return self.flag
 try:
  for case in data['cases']:
   if Stop().is_cancelled():raise RuntimeError('batch/role stop; no refill')
   c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256'];player=AlphaBetaPlayer(c,use_disk_cache=False);ev=player._evaluator;assert type(ev)is Evaluator;profile=L.record_value(ev._profile);config=L.record_value(ev._config);raw=ev.evaluate;positions=[];ids={};requests=[];cost=0.
   def observe(state):
    nonlocal cost
    t=time.perf_counter();value=raw(state);elapsed=time.perf_counter()-t;cost+=elapsed;pos=state.position
    if pos not in ids:ids[pos]=len(positions);positions.append(pos)
    requests.append(dict(id=ids[pos],raw=value,seconds=elapsed));return value
   ev.evaluate=observe;start=stamp();qt=time.perf_counter();attempted+=1
   try:decision=player.choose_action(s,SearchLimits(**plan['limits']),cancel_token=Stop())
   finally:ev.evaluate=raw
   end=stamp();row=dict(key=case['key'],started_at=start,ended_at=end,seconds=time.perf_counter()-qt,decision=L.record_value(decision),evaluate_requests=len(requests),unique_positions=len(positions),original_evaluate_seconds=cost,instrumented=True);append(d/'queries.jsonl',row);count+=1
   assert L.record_value(ev._profile)==profile and L.record_value(ev._config)==config
   for a in decision.principal_variation:assert a in s.legal_actions();s.submit(a)
   write_json(d/(case['key']+'-sequence.json'),dict(key=case['key'],positions=[L.record_value(p)for p in positions],requests=requests,profile=profile,config=config))
   frozen=Evaluator(c,frozen_profile(ev._profile),ev._config);bench=[]
   for enabled in(False,True,True,False):
    if Stop().is_cancelled():raise RuntimeError('batch/role stop during replay')
    bench.append(replay_cost(frozen,positions,requests,plan['capacity'],enabled))
   memory=[]
   for enabled in(False,True):
    tracemalloc.start();replay_cost(frozen,positions,requests,plan['capacity'],enabled);current,peak=tracemalloc.get_traced_memory();tracemalloc.stop();memory.append(dict(enabled=enabled,current_bytes=current,peak_incremental_python_bytes=peak,scope='Separate untimed tracing pass; preloaded request/Position inputs excluded; not process RSS.'))
   append(d/'qualification.jsonl',dict(memory_probe=memory,key=case['key'],raw_values_equal=True,pv_steps=len(decision.principal_variation),profile_unchanged=True,benchmarks=bench,limits='Actual requests only; shadow instrumentation contaminates search time; no independent WDL or search-cache parity claim.'))
   print('EVAL-CACHE',case['key'],'N',len(requests),'unique',len(positions),'bench',[round(x['seconds'],5)for x in bench],flush=True)
  status='CLOSED'
 except Exception:write_json(d/'failure.json',dict(at=stamp(),attempted=attempted,queries=count,traceback=traceback.format_exc()));raise
 finally:write_json(d/'receipt.json',dict(status=status,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=count,source_sha256=plan['source_sha256']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
