"""Begin the next IR captured-source check: nine records and one q4 root only."""
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
S=Path(os.environ['GC_ARCHIVE_SOURCE_ROOT']);D=Path(os.environ['GC_CONSUMER_DATA_ROOT']);R=Path(os.environ['GC_REPLAY_STOP_ROOT']);sys.path.insert(0,str(S))
assert importlib.util.find_spec('generic_chess._native_core')is None
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
def poll():
 for n in ('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
i=json.loads((D/'inputs.json').read_bytes());cases={c['name']:c for c in i['cases']};compiled={n:compile_semantic_ruleset(ruleset_from_dict(c['rule']))for n,c in cases.items()};states=[]
for p in i['parents']:
 poll();s=GameSession.replay(compiled[p['case']],deserialize_game_record(json.dumps(p['record'])));assert record_value(s.state)==p['state']and digest(s.state)==p['state_sha256']and digest(s._search_witnesses)==p['witness_sha256'];states.append(dict(case=p['case'],phase=p['phase'],state_sha256=p['state_sha256']))
p=next(p for p in i['parents']if p['case']=='persistent'and p['phase']==0);c=compiled['persistent'];profile=cases['persistent'];s=GameSession.replay(c,deserialize_game_record(json.dumps(p['record'])));before=(s.state,s.history,s.to_record(),s._search_witnesses)
class Material:
 def evaluate(self,s):
  v=sum((1 if p.owner==0 else-1)*profile['board_values'][p.current_type_id]for p in s.position.board if p)+sum((s.position.hands[0].count(t)-s.position.hands[1].count(t))*v for t,v in profile['hand_values'].items());return v*(1 if s.position.side_to_move==0 else-1)
st=SearchStatistics();a,score,pv,cause=run_root_search(s.state,c,Material(),TranspositionTable(max_entries=1),SearchLimits(max_depth=2,max_nodes=200000,max_time_seconds=30,quiescence_max_depth=4),None,st,use_tt=False,use_ordering=False,tuning=SearchTuning(),_history_witnesses=s._search_witnesses);poll();assert before==(s.state,s.history,s.to_record(),s._search_witnesses)
old=next(x for x in map(json.loads,(D/'core-queries.jsonl').read_bytes().splitlines())if x['case']=='persistent'and x['phase']==0);assert st.completed_depth==2 and st.result_ordinary_qdepth==4 and score==old['score']
assert all(Path(v.__file__).resolve().is_relative_to(S)for k,v in sys.modules.items()if k.startswith('generic_chess')and getattr(v,'__file__',None))
out=dict(status='PASS_BOUNDED_IR_SOURCE_ADMISSION_AND_ONE_TARGET',states=states,state_records_rebuilt=9,Core_q4_root_targets_rebuilt=1,root_case='persistent',root_phase=0,root_score=score,root_action_equal=record_value(a)==old['action'],remaining_root_targets=8,selected_child_targets_not_rebuilt=4,native_absent=True,python_S_extracted_origins=True,real_primary_stops=True,new_Native_queries=0,new_games=0,new_training=0,scope='Nextcheckactuallybegun: all9completeIRrecords matchcapturedsource, ONLYoneCoreq4target rebuilt. Notfreshqualificationofall18Nativevalues/4selectedchildren, utility orall-domain proof.')
Path(os.environ['GC_ADMISSION_OUTPUT']).write_bytes((json.dumps(out,indent=2)+'\n').encode())
'''
env=dict(os.environ);env.update(PYTHONPATH='',GC_ARCHIVE_SOURCE_ROOT=str(S),GC_CONSUMER_DATA_ROOT=str(D),GC_REPLAY_STOP_ROOT=str(R),GC_ADMISSION_OUTPUT=str(X/'admission.json'));site=Path(sys.prefix)/'Lib/site-packages';wrapped='import sys;sys.path[:0]='+repr([str(S),str(site)])+';exec('+repr(code)+')'
subprocess.run([sys.executable,'-S','-X','utf8','-c',wrapped],cwd=S,env=env,check=True,timeout=45)
out=json.loads((X/'admission.json').read_bytes());out.update(archive_sha256=m['archive_sha256'],seconds=time.perf_counter()-start)
tmp=D/'source-admission-result.tmp';tmp.write_bytes((json.dumps(out,indent=2)+'\n').encode());os.replace(tmp,D/'source-admission-result.json');print('IR_SOURCE_ADMISSION',out['state_records_rebuilt'],out['Core_q4_root_targets_rebuilt'],out['seconds'])
