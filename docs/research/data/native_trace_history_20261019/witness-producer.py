"""Replay saved interior witnesses as actual public Sessions; four cold calls."""
from pathlib import Path
import sys,json,time,hashlib
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.ai.limits import SearchLimits
D=Path(__file__).resolve().parent;start=time.perf_counter();r=json.loads((D/'reader-result.json').read_bytes());w=next(x for x in r['within_query_witnesses']if x['trace']['bound_class']=='EXACT');i=json.loads((D/'branch-input.json').read_bytes());c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(i['rule']));cp=LearnableMaterialCheckpoint.from_dict(i['checkpoint']);nr=compile_native_semantic_rules(c);parents=[];count=nodes=0
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
with(D/'witness-queries.jsonl').open('x',encoding='utf8',newline='\n')as log:
 for wi,m in enumerate(w['contexts']):
  s=GameSession(c)
  for action in m['path']:
   aa=[a for a in s.legal_actions()if record_value(a)==action];assert len(aa)==1;s.submit(aa[0])
  assert record_value(s.state)==m['state']and digest(s.state)==m['full_state_sha256']
  parents.append(dict(witness=wi,expected_score_native=m['value_native'],record=json.loads(serialize_game_record(s.to_record())),state=record_value(s.state),history=record_value(s.history),state_sha256=digest(s.state),witness_sha256=digest(s._search_witnesses)))
  for mode in (False,True):
   for name in ('rollout','advisor','slack'):
    f=json.loads((Path.cwd()/'.local_agent'/(name+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
   assert 20+count<32 and time.perf_counter()-start<119
   before=(s.state,s.to_record(),s.history,s._search_witnesses);e=SemanticSearchEngine(c,nr,checkpoint=cp,tt_megabytes=0);tick=time.perf_counter();rr=e.search(s,SearchLimits(max_depth=1,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),root_window_pruning=mode,trace_enabled=True)
   row=dict(witness=wi,mode=mode,parent_sha256=digest(s.state),parent_unchanged=before==(s.state,s.to_record(),s.history,s._search_witnesses),expected_score_native=m['value_native'],result=record_value(rr),caller_seconds=time.perf_counter()-tick);log.write(json.dumps(row,separators=(',',':'))+'\n');log.flush();count+=1;nodes+=rr.nodes;del e
   assert row['parent_unchanged']and rr.completed_depth==1 and rr.score*cp.semantic_native_scale==m['value_native']and not rr.used_fallback
write_json(D/'witness-inputs.json',dict(rule=i['rule'],checkpoint=i['checkpoint'],selected_from=dict(query=w['query'],row=w['row'],trace=w['trace']),parents=parents))
write_json(D/'witness-result.json',dict(status='COMPLETE',queries=count,nodes=nodes,seconds=time.perf_counter()-start,total_history_queries=20+count,remaining_cap=32-20-count))
print(count,nodes,time.perf_counter()-start)
