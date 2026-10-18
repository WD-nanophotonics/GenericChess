"""Complete remaining finite IR captured-source targets under one continuous120s clock."""
from pathlib import Path
import json,os,sys,zipfile,hashlib,subprocess,time,uuid
R=Path.cwd();D=Path(__file__).resolve().parent;A=R/'docs/archive/root_window_q4_service_20261019';m=json.loads((A/'manifest.json').read_bytes());assert hashlib.sha256((A/'evidence.zip').read_bytes()).hexdigest()==m['archive_sha256'];X=R/'.local_agent'/('q4-ir-source-'+uuid.uuid4().hex[:10]);X.mkdir();S=X/'source';start=time.perf_counter()
with zipfile.ZipFile(A/'evidence.zip')as z:
 for n,e in m['files'].items():
  if not n.startswith('source/'):continue
  b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256'];t=(X/n).resolve();assert t.is_relative_to(X.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
code=r'''

from pathlib import Path
import sys,os,json,time,hashlib,importlib.util
S=Path(os.environ['GC_ARCHIVE_SOURCE_ROOT']);D=Path(os.environ['GC_CONSUMER_DATA_ROOT']);R=Path(os.environ['GC_REPLAY_STOP_ROOT'])
sys.path.insert(0,str(S))
assert importlib.util.find_spec('generic_chess._native_core')is None
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.search import run_root_search,negamax,_Context,_Budget,INF,SearchAborted
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
deadline=float(os.environ['GC_GLOBAL_DEADLINE'])
class Stop:
 def __init__(self):self.next=0;self.stopped=False
 def is_cancelled(self):
  now=time.perf_counter()
  if now>=self.next:
   self.next=now+.1
   for n in ('rollout','advisor','slack'):
    f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes())
    self.stopped|=bool(f.get('stopped')or f.get('user_paused'))
  return self.stopped or now>=deadline
stop=Stop()
def poll():assert not stop.is_cancelled()
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
i=json.loads((D/'inputs.json').read_bytes());cases={c['name']:c for c in i['cases']}
compiled={n:compile_semantic_ruleset(ruleset_from_dict(c['rule']))for n,c in cases.items()}
parents={(p['case'],p['phase']):p for p in i['parents']}
cores={(c['case'],c['phase']):c for c in map(json.loads,(D/'core-queries.jsonl').read_bytes().splitlines())}
class Material:
 def __init__(self,p):self.p=p
 def evaluate(self,s):
  v=sum((1 if p.owner==0 else-1)*self.p['board_values'][p.current_type_id]for p in s.position.board if p)+sum((s.position.hands[0].count(t)-s.position.hands[1].count(t))*v for t,v in self.p['hand_values'].items())
  return v*(1 if s.position.side_to_move==0 else-1)
def restore(p):
 s=GameSession.replay(compiled[p['case']],deserialize_game_record(json.dumps(p['record'])))
 assert record_value(s.state)==p['state']and digest(s.state)==p['state_sha256']and digest(s._search_witnesses)==p['witness_sha256']
 return s
states=[];rows=[];children=[]
for p in i['parents']:
 poll();s=restore(p);states.append(dict(case=p['case'],phase=p['phase'],state_sha256=p['state_sha256']))
 if (p['case'],p['phase'])==('persistent',0):continue
 c=compiled[p['case']];before=(s.state,s.history,s.to_record(),s._search_witnesses)
 st=SearchStatistics();tick=time.perf_counter()
 a,score,pv,cause=run_root_search(s.state,c,Material(cases[p['case']]),TranspositionTable(max_entries=1),SearchLimits(max_depth=2,max_nodes=200000,max_time_seconds=min(30,max(.001,deadline-time.perf_counter())),quiescence_max_depth=4),stop,st,use_tt=False,use_ordering=False,tuning=SearchTuning(),_history_witnesses=s._search_witnesses)
 poll();assert before==(s.state,s.history,s.to_record(),s._search_witnesses)
 previous=cores[p['case'],p['phase']]
 complete=st.completed_depth==2 and st.result_ordinary_qdepth==4
 rows.append(dict(case=p['case'],phase=p['phase'],status='COMPLETE'if complete else'UNKNOWN',score=score,expected=previous['score'],equal_target=complete and score==previous['score'],action_equal=record_value(a)==previous['action'],nodes=st.nodes,qnodes=st.qnodes,seconds=time.perf_counter()-tick,cause=cause))
 if complete:assert score==previous['score']
selection=json.loads((D/'selected-action-result.json').read_bytes())['rows']
for v in selection:
 poll();p=parents[v['case'],v['phase']];c=compiled[v['case']];s=restore(p);raw=dict(v['action']);raw['to_square']=Square(**raw['to_square'])
 if 'from_square'in raw:raw['from_square']=Square(**raw['from_square']);a=SemanticBoardMove(**raw)
 else:a=SemanticDropMove(**raw)
 s.submit(a);before=(s.state,s.to_record(),s.history,s._search_witnesses)
 rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses);st=SearchStatistics();rt.attach_stats(st)
 lim=SearchLimits(max_depth=1,max_nodes=200000,max_time_seconds=min(30,max(.001,deadline-time.perf_counter())),quiescence_max_depth=4)
 ctx=_Context(c,Material(cases[v['case']]),TranspositionTable(max_entries=1),st,_Budget(lim,stop),SearchTuning(),False,False,4,8,None,runtime=rt,first_main_iteration_complete=True)
 tick=time.perf_counter()
 try:
  z=negamax(s.state,1,-INF,INF,1,ctx);r=dict(status='COMPLETE',child_score=z.score,backed_up=-z.score,equal_root_target=-z.score==v['expected']);assert r['equal_root_target']
 except SearchAborted as exc:r=dict(status='UNKNOWN',cause=str(exc))
 rt.assert_balanced();assert before==(s.state,s.to_record(),s.history,s._search_witnesses)
 children.append(dict(case=v['case'],phase=v['phase'],action=v['action'],expected=v['expected'],**r,nodes=st.nodes,qnodes=st.qnodes,seconds=time.perf_counter()-tick))
poll()
assert len(states)==9 and len(rows)==8 and len(children)==4
assert all(Path(v.__file__).resolve().is_relative_to(S)for k,v in sys.modules.items()if k.startswith('generic_chess')and getattr(v,'__file__',None))
out=dict(status='CLOSED',state_records_rebuilt=9,root_targets=rows,selected_children=children,previous_root_reused=dict(case='persistent',phase=0,evidence='source-admission-result.json',not_rerun=True),native_absent=True,python_S_extracted_origins=True,real_primary_stops=True,stop_poll_seconds=.1,global_cap_seconds=120,new_Native_queries=0,new_games=0,new_training=0,scope='Remaining finite captured-source targets only. No all-domain correctness, utility or WDL admission gate.')
Path(os.environ['GC_ADMISSION_OUTPUT']).write_bytes((json.dumps(out,indent=2)+'\n').encode())

'''
env=dict(os.environ);env.update(PYTHONPATH='',GC_ARCHIVE_SOURCE_ROOT=str(S),GC_CONSUMER_DATA_ROOT=str(D),GC_REPLAY_STOP_ROOT=str(R),GC_ADMISSION_OUTPUT=str(X/'admission.json'),GC_GLOBAL_DEADLINE=str(start+120));site=Path(sys.prefix)/'Lib/site-packages';wrapped='import sys;sys.path[:0]='+repr([str(S),str(site)])+';exec('+repr(code)+')'
subprocess.run([sys.executable,'-S','-X','utf8','-c',wrapped],cwd=S,env=env,check=True,timeout=max(.1,120-(time.perf_counter()-start)))
out=json.loads((X/'admission.json').read_bytes());out.update(archive_sha256=m['archive_sha256'],seconds=time.perf_counter()-start)
tmp=D/'source-complete-result.tmp';tmp.write_bytes((json.dumps(out,indent=2)+'\n').encode());os.replace(tmp,D/'source-complete-result.json');print('IR_SOURCE_COMPLETE',len(out['root_targets']),len(out['selected_children']),out['seconds'])
