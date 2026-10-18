"""Frozen Native trace interface diagnostic, not a learner or AUX execution."""
from pathlib import Path
from collections import Counter
import json,sys,time,hashlib
R=Path.cwd();sys.path.insert(0,str(R))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits
D=Path(__file__).resolve().parent;P=json.loads((D/'plan.json').read_bytes());I=json.loads((D/'inputs.json').read_bytes());start=time.perf_counter();counts=Counter();status='COMPLETE';error=None
compiled={int(g):compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r))for g,r in I['rules'].items()};native={g:compile_native_semantic_rules(c)for g,c in compiled.items()}
assert not(D/'queries.jsonl').exists()
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def poll():
 assert time.perf_counter()-start<P['global_seconds']
 for n in('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
try:
 with(D/'queries.jsonl').open('x',encoding='utf8')as log:
  for inp in I['rows']:
   idx=inp['source_index']
   if idx not in P['source_indices']:continue
   item=inp['item'];c=compiled[item['rule']];s=GameSession.replay(c,deserialize_game_record(json.dumps(item['query']['record_before'])));cp=LearnableMaterialCheckpoint.from_dict(inp['published_checkpoint'])
   for mode in P['modes']:
    poll();before=(s.state,s.to_record(),s.history,s._search_witnesses);e=SemanticSearchEngine(c,native[item['rule']],checkpoint=cp,tt_megabytes=0);tick=time.perf_counter();r=e.search(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),root_window_pruning=mode,trace_enabled=True);elapsed=time.perf_counter()-tick
    q=dict(source_index=idx,mode=mode,parent_sha256=digest(s.state),parent_witness_sha256=digest(s._search_witnesses),checkpoint_id=cp.checkpoint_id,parent_unchanged=before==(s.state,s.to_record(),s.history,s._search_witnesses),depth=r.completed_depth,nodes=r.nodes,cause=r.termination_reason,fallback=r.used_fallback,score=r.score,action=record_value(r.action),decision_line=record_value(r.decision_line),training_trace=record_value(r.training_trace),trace_enabled=r.training_trace_enabled,trace_count=r.training_trace_count,trace_raw_count=r.training_trace_raw_count,kernel_seconds=r.elapsed_seconds,caller_seconds=elapsed)
    log.write(json.dumps(q,separators=(',',':'))+'\n');log.flush();counts['queries']+=1;counts['nodes']+=r.nodes;counts['retained_trace_rows']+=r.training_trace_count;counts['raw_trace_records']+=r.training_trace_raw_count;del e;assert q['parent_unchanged']and r.completed_depth==2 and not r.used_fallback and r.training_trace_enabled;assert log.tell()<P['max_output_bytes']
except BaseException as exc:status='ERROR';error=repr(exc)
write_json(D/'result.json',dict(status=status,error=error,counts=dict(counts),planned=30,returned=counts['queries'],seconds=time.perf_counter()-start,scope='CurrentNative traceinterface/cost on15existingfullsignedparents; noCoreAUXlearner execution/training/API/defaultchange. Boundvalidation andhistoryidentity scope separate.'))
print('TRACE_CONTRACT_CLOSED',status,error,dict(counts),time.perf_counter()-start)
