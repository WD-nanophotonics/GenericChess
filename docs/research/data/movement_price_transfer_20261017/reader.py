"""Search-disabled full receipt replay and independent quantized PV-value check."""
from pathlib import Path
from collections import defaultdict,Counter
from copy import copy
import sys,json,time,hashlib,os
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));D=ROOT/'.local_agent/movement-transfer-20261017';STOP_ROOT=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(ROOT))).resolve()
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native.engine import NativeSearchEngine

def forbidden(*args,**kwargs):raise AssertionError('Search disabled in independent receipt reader')
SemanticSearchEngine.search=forbidden;NativeSearchEngine.search=forbidden

def digest(value):return hashlib.sha256(json.dumps(record_value(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def decode(a):
 if isinstance(a,str):return a
 k=dict(a);k['to_square']=Square(**k['to_square'])
 if 'from_square'in k:k['from_square']=Square(**k['from_square']);return SemanticBoardMove(**k)
 return SemanticDropMove(**k)

start=time.monotonic();p=json.loads((D/'plan.json').read_bytes());done=json.loads((D/'result.json').read_bytes());assert done['status']=='COMPLETE'and done['returned_physical']==7040;roots={(r['rule'],r['family']):r for r in json.loads((D/'roots.json').read_bytes())['rows']};models={r['checkpoint_id']:r['checkpoint']for r in json.loads((D/'models.json').read_bytes())['rows']};compiled={gs:compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(json.loads((D/f'rule-{gs}.json').read_bytes())))for gs in p['rules']};query_stream=(json.loads(line)for line in(D/'queries.jsonl').open(encoding='utf8'));next_query=next(query_stream,None);games=(json.loads(line)for line in(D/'games.jsonl').open(encoding='utf8'));counts=Counter();mismatches=[];missingpv=[];badscorekinds=Counter();native_causes=Counter()
for g in games:
 if time.monotonic()-start>900:raise TimeoutError('Frozen replay cap, noextension')
 for n in('rollout','advisor','slack'):
  f=json.loads((STOP_ROOT/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('stopped')and not f.get('user_paused'),'EXPLICIT_STOP'
 c=compiled[g['rule']];root=roots[g['rule'],g['family']];s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));assert digest(s.state)==root['state_sha256']and digest(s._search_witnesses)==root['witnesses_sha256'];final=deserialize_game_record(json.dumps(g['record']));prefix=len(s.to_record().actions);assert final.actions[:prefix]==s.to_record().actions;counts['root_full_states']+=1
 local_queries=[]
 while next_query is not None and next_query['slot']==g['slot']:
  local_queries.append(next_query);next_query=next(query_stream,None)
 assert len(local_queries)==g['queries']
 for relative,q in enumerate(local_queries):
  assert relative==q['relative_ply'];assert q['requested_depth']==q['completed_depth']==2 and q['requested_nodes']==8192 and q['requested_seconds']==2. and not q['used_fallback'];native_causes[q['cause']]+=1;assert digest(s.state)==q['before_sha256'];assert s.state.position.side_to_move==q['actor'];parent=(s.state,s.to_record(),s.history,s._search_witnesses);leaf=copy(s)
  for raw in q['decision_line']:
   move=decode(raw)
   if isinstance(move,str):leaf.declare(move)
   else:leaf.submit(move);counts['PV_core_edges']+=1
  assert parent==(s.state,s.to_record(),s.history,s._search_witnesses)
  if not q['decision_line']:missingpv.append(dict(slot=g['slot'],relative_ply=relative,rule=g['rule'],score=q['score']))
  else:
   cp=models[q['checkpoint_id']]
   if leaf.result.status.value!='ongoing':
    assert leaf.result.declaration_outcome not in('RESTART','NO_CONTEST')
    expected=0 if leaf.result.winner is None else(100000000-len(q['decision_line']))*(1 if leaf.result.winner==0 else-1);kind='actual_terminal';counts['terminal_PV']+=1
   else:
    board=sum((1 if x.owner==0 else-1)*round(cp['board_weights'].get(x.current_type_id,0.)*256)for x in leaf.state.position.board if x is not None)
    hand=sum((leaf.state.position.hands[0].count(t)-leaf.state.position.hands[1].count(t))*round(w*256)for t,w in cp['hand_weights'].items());expected=board+hand;kind='ordinary_material';counts['ordinary_PV']+=1
   actual=q['score']*(1 if q['actor']==0 else-1)
   if expected!=actual:
    mismatches.append(dict(slot=g['slot'],rule=g['rule'],family=g['family'],label=g['label'],candidate_owner=g['candidate_owner'],relative_ply=relative,kind=kind,expected=expected,actual=actual,PV=q['decision_line'],parent_record=record_value(s.to_record()),leaf_record=record_value(leaf.to_record())));badscorekinds[kind]+=1
  action=final.actions[prefix+relative];assert record_value(action)==q['committed']==q['returned_action'];s.submit(action);assert digest(s.state)==q['after_sha256'];counts['committed_core_edges']+=1
 assert len(s.to_record().actions)==len(final.actions);assert s.to_record()==final;assert digest(s.state)==g['final_state_sha256']and digest(s._search_witnesses)==g['final_witnesses_sha256'];assert record_value(s.result)==g['result'];expected=None if s.result.status.value=='ongoing'else 0 if s.result.winner is None else 1 if s.result.winner==g['candidate_owner']else-1;assert expected==g['reward'];counts['final_full_states']+=1
 if counts['final_full_states']%64==0:print('REPLAYED_GAMES',counts['final_full_states'],round(time.monotonic()-start,3),flush=True)
assert next_query is None
assert counts['final_full_states']==done['returned_physical']
assert counts['committed_core_edges']==done['queries']
write_json(D/'reader-result.json',dict(status='PASS_ALL_PHYSICAL_RECEIPTS',counts=dict(counts),score_leaf_mismatch_count=len(mismatches),score_leaf_mismatch_kinds=dict(badscorekinds),missing_pv_count=len(missingpv),missing_pv=missingpv,score_leaf_mismatches=mismatches,native_causes=dict(native_causes),seconds=time.monotonic()-start,scope='Everyactualphysicalroot/query/PV/finalrecord fullstate/history replay, searchdisabled. PosthocscoringleafcheckisNOTindependentoptimalWDL/oldwallclockproof ornewsearch. Gameoutcomesscopepreserved evenifscore-leafmismatchfound.'))
write_json(D/'reader-source-files.json',dict(files=sorted(str(Path(v.__file__).resolve().relative_to(ROOT)).replace('\\','/')for k,v in sys.modules.items()if k.startswith('generic_chess')and getattr(v,'__file__',None)and str(v.__file__).endswith('.py')and Path(v.__file__).resolve().is_relative_to(ROOT))))
print('READER_CLOSED',dict(counts),'PV-score mismatches',len(mismatches),'missingPV',len(missingpv),'seconds',round(time.monotonic()-start,3),flush=True)
