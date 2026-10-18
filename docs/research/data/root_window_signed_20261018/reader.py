"""Search-disabled independent signed Core tree and PV receipt check."""
from pathlib import Path
from copy import copy
from collections import Counter
import sys,json,time,hashlib,os
R=Path.cwd();sys.path.insert(0,str(R))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
D=Path(__file__).resolve().parent;I=json.loads((D/'inputs.json').read_bytes());refs={r['source_index']:r for r in json.loads((D/'references.json').read_bytes())['rows']};qs=list(map(json.loads,(D/'queries.jsonl').read_bytes().splitlines()));start=time.perf_counter();count=Counter();compiled={int(g):compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(v))for g,v in I['rules'].items()};parents={};cps={}
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def poll():
 assert time.perf_counter()-start<120
 for n in('rollout','advisor','slack'):
  f=json.loads((Path(os.environ.get('GC_REPLAY_STOP_ROOT',R))/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
def decode(a):
 if isinstance(a,str):return a
 a=dict(a);a['to_square']=Square(**a['to_square'])
 if 'from_square'in a:a['from_square']=Square(**a['from_square']);return SemanticBoardMove(**a)
 return SemanticDropMove(**a)
for inp in I['rows']:
 poll();idx=inp['source_index'];item=inp['item'];c=compiled[item['rule']];s=GameSession.replay(c,deserialize_game_record(json.dumps(item['query']['record_before'])));cp=LearnableMaterialCheckpoint.from_dict(inp['published_checkpoint']);cp.validate_ruleset(c);assert cp.board_weights['P']<0;ref=refs[idx];assert cp.checkpoint_id==ref['checkpoint_id'];assert digest(s.state)==ref['parent_state_sha256']and digest(s._search_witnesses)==ref['parent_witness_sha256'];aa=s.legal_actions();assert record_value(aa)==ref['actions'];vv=[]
 def leafval(t,dist):
  if t.result.status.value!='ongoing':
   z=0 if t.result.winner is None else 1 if t.result.winner==0 else-1;return[1000000*z,(100000000-dist)*z]
  channels=item['channels'];weights=item['query']['weights'];phi=[sum((1 if p.owner==0 else-1)for p in t.state.position.board if p and p.current_type_id==tid)if kind=='board'else t.state.position.hands[0].count(tid)-t.state.position.hands[1].count(tid)for kind,tid in channels];return[sum(v*w for v,w in zip(phi,weights)),sum(v*round(w*256)for v,w in zip(phi,weights))]
 for a in aa:
  ch=copy(s);ch.submit(a);count['reference_edges']+=1
  if ch.result.status.value!='ongoing':v=leafval(ch,1)
  else:
   bb=ch.legal_actions();values=[]
   for b in bb:
    poll();x=copy(ch);x.submit(b);count['reference_edges']+=1;values.append(leafval(x,2))
   fn=max if ch.state.position.side_to_move==0 else min;v=[fn(v[j]for v in values)for j in(0,1)]
  vv.append(v)
 assert vv==ref['action_values'];fn=max if s.state.position.side_to_move==0 else min;best=fn(v[1]for v in vv);assert best==ref['quantized_best'];assert[i for i,v in enumerate(vv)if v[1]==best]==ref['quantized_optimal_indices'];parents[idx]=s;cps[idx]=cp;count['full_reference_inputs']+=1
seen=set()
for q in qs:
 poll();idx=q['source_index'];assert(idx,q['mode'])not in seen;seen.add((idx,q['mode']));s=parents[idx];ref=refs[idx];assert q['parent_state_sha256']==ref['parent_state_sha256']and q['parent_unchanged']and q['checkpoint_id']==ref['checkpoint_id'];assert q['root_window']==q['mode']and q['nodes']<=8192 and q['qnodes']==0;leaf=copy(s)
 for raw in q['decision_line']:
  a=decode(raw)
  if isinstance(a,str):leaf.declare(a)
  else:leaf.submit(a);count['PV_core_edges']+=1
 if q['depth']==2 and not q['fallback']:
  assert ref['actions'].index(q['action'])in ref['quantized_optimal_indices'];assert q['score']*(1 if s.state.position.side_to_move==0 else-1)==ref['quantized_best'];count['completed_D2_correct']+=1
 else:count['UNRESOLVED']+=1
 count['queries']+=1;count['nodes']+=q['nodes']
assert len(seen)==32 and count['full_reference_inputs']==16
write_json(D/'reader-result.json',dict(status='PASS_SIGNED_CORE_OPTIMA_AND_PV',counts=dict(count),seconds=time.perf_counter()-start,scope='Searchdisabled fullCoreenumeration of16publishednegativeP completeinputs and32pairedNative receipts; exactintegeroptimalsets/value andPV/history/parenthash. Tiesallowed; no signmanipulation/newgames/training/gradientreference/strength/all-domainclaim.'))
print('SIGNED_READER',dict(count),time.perf_counter()-start)
