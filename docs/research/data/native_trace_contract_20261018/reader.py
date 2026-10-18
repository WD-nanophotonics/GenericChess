"""No-Native finite integer trace-bound check; full history remains a separate contract."""
from pathlib import Path
from collections import Counter,defaultdict
import sys,json,time,hashlib,os
R=Path.cwd();sys.path.insert(0,str(R))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.core.transition import apply_action,legal_actions
from generic_chess.core.identity import position_identity_key
D=Path(__file__).resolve().parent;P=json.loads((D/'plan.json').read_bytes());I=json.loads((D/'inputs.json').read_bytes());qs=list(map(json.loads,(D/'queries.jsonl').read_bytes().splitlines()));refs={r['source_index']:r for r in json.loads((D/'references.json').read_bytes())['rows']};start=time.perf_counter();count=Counter();catalogs={};compiled={int(g):compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(v))for g,v in I['rules'].items()}
def poll():
 assert time.perf_counter()-start<120
 for n in('rollout','advisor','slack'):
  f=json.loads((Path(os.environ.get('GC_REPLAY_STOP_ROOT',R))/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
for inp in I['rows']:
 idx=inp['source_index']
 if idx not in P['source_indices']:continue
 item=inp['item'];c=compiled[item['rule']];s=GameSession.replay(c,deserialize_game_record(json.dumps(item['query']['record_before'])));cp=LearnableMaterialCheckpoint.from_dict(inp['published_checkpoint']);cat=defaultdict(list);tids=sorted(c.types_by_id)
 def walk(st,depth,dist):
  poll();count['Core_visits']+=1
  if st.terminal_status.is_terminal:
   w=st.terminal_status.winner;val=0 if w is None else(100000000-dist)*(1 if w==0 else-1)
  elif not depth:val=sum((1 if p.owner==0 else-1)*round(cp.board_weights[p.current_type_id]*256)for p in st.position.board if p is not None)+sum((st.position.hands[0].count(t)-st.position.hands[1].count(t))*round(w*256)for t,w in cp.hand_weights.items())
  else:
   vals=[walk(apply_action(st,a,c),depth-1,dist+1)for a in legal_actions(st,c)];val=(max if st.position.side_to_move==0 else min)(vals)
  side=st.position.side_to_move;key=(str(position_identity_key(st.position,c)),side,depth,dist);cat[key].append(dict(state=st,value=val*(1 if side==0 else-1),context=digest(st)))
  return val
 walk(s.state,1,0);best=walk(s.state,2,0);assert best==refs[idx]['quantized_best'];catalogs[idx]=(s,cat,tids,c)
arms={}
for q in qs:
 poll();idx=q['source_index'];s,cat,tids,c=catalogs[idx];assert digest(s.state)==q['parent_sha256']and digest(s._search_witnesses)==q['parent_witness_sha256']and q['parent_unchanged'];assert q['depth']==2 and not q['fallback']and q['trace_enabled'];assert q['trace_count']==len(q['training_trace'])<=q['trace_raw_count'];assert q['score']*(1 if s.state.position.side_to_move==0 else-1)==refs[idx]['quantized_best'];assert refs[idx]['actions'].index(q['action'])in refs[idx]['quantized_optimal_indices']
 a=arms.setdefault(str(q['mode']),Counter());a['queries']+=1;a['raw_records']+=q['trace_raw_count'];a['rows']+=q['trace_count'];a['nodes']+=q['nodes']
 for row in q['training_trace']:
  key=(row['position_identity'],row['side_to_move'],row['remaining_depth'],row['search_ply']);matches=cat.get(key,[]);assert matches,('UNMATCHED_TRACE_CONTEXT',idx,key);contexts={x['context']for x in matches};count['ambiguous_rows']+=len(contexts)>1
  for m in matches:
   state=m['state'];v=m['value'];b=row['bound_class'];z=row['score_native'];assert(v==z if b=='EXACT'else v>=z if b=='LOWER'else v<=z if b=='UPPER'else False),('UNSOUND_BOUND',idx,key,b,z,v)
   assert row['terminal']==state.terminal_status.is_terminal
   board=[sum(p is not None and p.owner==owner and p.current_type_id==tid for p in state.position.board)for owner in(0,1)for tid in tids];hand=[state.position.hands[owner].count(tid)for owner in(0,1)for tid in tids];features=[int(p is not None and p.owner==owner and p.current_type_id==tid)for owner in(0,1)for tid in tids for p in state.position.board]
   assert board==row['board_counts']and hand==row['hand_counts']and features==row['board_features']and row['ruleset_fingerprint']==c.ruleset_fingerprint
  count['trace_rows_checked']+=1;a[row['bound_class']]+=1;a['terminal_rows']+=row['terminal'];a['nonterminal_interiors']+=not row['terminal']and row['remaining_depth']>0
 count['queries']+=1
assert len(qs)==count['queries']==30 and count['trace_rows_checked']==1506
write_json(D/'reader-result.json',dict(status='PASS_SCOPED_NATIVE_TRACE_INTEGER_BOUNDS',counts=dict(count),arms=arms,seconds=time.perf_counter()-start,scope='All1506tracebounds/countfeatures matched freshfullCore D1/D2 contexts for15signedparents/twoexposedrules. Dynamic/auxfeaturelearningnotvalidated; Native traceidentitydoesnotcarryfullhistory/path andthissampledoesnotcertifyhistory-safeall-domaindedup orAUXlearningequivalence. No Native/trainingrerun.'))
print('TRACE_READER',dict(count),arms,time.perf_counter()-start)
