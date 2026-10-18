"""Independent complete Core references; never executes Native or training."""
from pathlib import Path
from collections import Counter,defaultdict
import os,sys,json,time,hashlib
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import apply_action,legal_actions
from generic_chess.core.identity import position_identity_key
from generic_chess.learning.material import LearnableMaterialCheckpoint
D=Path(__file__).resolve().parent;start=time.perf_counter();counts=Counter();witnesses=[];pool={}
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def poll():
 assert time.perf_counter()-start<60 and counts['Core_edges']<100000
 for name in ('rollout','advisor','slack'):
  f=json.loads((Path(os.environ.get('GC_REPLAY_STOP_ROOT',Path.cwd()))/'.local_agent'/(name+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
def build(inp,roots,maxdepth):
 c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(inp['rule']));cp=LearnableMaterialCheckpoint.from_dict(inp['checkpoint']);tids=tuple(sorted(c.types_by_id));weights=dict(zip(tids,cp.semantic_quantized_board(tids)));hweights=dict(zip(tids,cp.semantic_quantized_hand(tids)));scale=cp.semantic_native_scale
 out={}
 for p in roots:
  s=GameSession(c)
  for action in p['record']['actions']:
   aa=[a for a in s.legal_actions()if record_value(a)==action];assert len(aa)==1;s.submit(aa[0])
  assert record_value(s.to_record())==p['record']and record_value(s.state)==p['state'];assert digest(s.state)==p.get('state_sha256',p.get('parent_sha256'));cat=defaultdict(list);values={}
  def walk(st,depth,dist,path):
   poll();counts['Core_visits']+=1
   if st.terminal_status.is_terminal:
    assert st.terminal_status.winner is None;value=0
   elif depth==0:value=sum((1 if pc.owner==0 else -1)*weights[pc.current_type_id]for pc in st.position.board if pc)+sum((st.position.hands[0].count(t)-st.position.hands[1].count(t))*hweights[t]for t in tids)
   else:
    vals=[]
    for a in legal_actions(st,c):
     counts['Core_edges']+=1;vals.append(walk(apply_action(st,a,c),depth-1,dist+1,path+[record_value(a)]))
    assert vals;value=(max if st.position.side_to_move==0 else min)(vals)
   key=(str(position_identity_key(st.position,c)),st.position.side_to_move,depth,dist)
   cat[key].append(dict(value=value*(1 if st.position.side_to_move==0 else -1),state=st,path=path,hash=digest(st)))
   return value
  for dep in range(1,maxdepth+1):values[dep]=walk(s.state,dep,0,[])
  out[p.get('ply',0)]=(s,cat,values,c,scale,tids)
 return out
cycle=json.loads((D/'cycle-inputs.json').read_bytes());branch=json.loads((D/'branch-input.json').read_bytes())
catalog={'cycle':build(cycle,cycle['parents'],4),'branch':build(branch,[branch],8)}
arms={}
for name in ('cycle','branch'):
 qs=list(map(json.loads,(D/(name+'-queries.jsonl')).read_bytes().splitlines()))
 for qi,q in enumerate(qs):
  poll();root=q.get('parent_ply',0);s,cat,values,c,scale,tids=catalog[name][root];r=q['result'];dep=q.get('requested_depth',8);assert q['parent_unchanged']and q['parent_sha256']==digest(s.state);assert r['completed_depth']==dep and not r['used_fallback'];expected=values[dep]*(1 if s.state.position.side_to_move==0 else -1);assert r['score']*scale==expected,('ROOT_VALUE',name,qi,r['score'],expected)
  st=s.state
  for action in r['decision_line']:
   aa=[a for a in legal_actions(st,c)if record_value(a)==action];assert len(aa)==1;st=apply_action(st,aa[0],c);counts['Core_PV_edges']+=1
  a=arms.setdefault(name+'-'+str(q['mode']),Counter());a['queries']+=1;a['rows']+=len(r['training_trace']);a['nodes']+=r['nodes']
  for ri,row in enumerate(r['training_trace']):
   key=(row['position_identity'],row['side_to_move'],row['remaining_depth'],row['search_ply']);matches=cat[key];assert matches
   distinct={m['hash']:m for m in matches};vals={m['value']for m in distinct.values()};b=row['bound_class'];z=row['score_native']
   def valid(m):return m['value']==z if b=='EXACT'else m['value']>=z if b=='LOWER'else m['value']<=z
   okay=[m for m in distinct.values()if valid(m)and row['terminal']==m['state'].terminal_status.is_terminal]
   assert okay,('NO_VALID_CONTEXT',name,qi,key,b,z,sorted(vals))
   a['rows_with_multiple_full_states']+=len(distinct)>1;a['rows_with_multiple_values']+=len(vals)>1;a['not_valid_for_every_context']+=len(okay)<len(distinct)
   for m in distinct.values():
    state=m['state'];assert row['board_counts']==[sum(pc is not None and pc.owner==o and pc.current_type_id==t for pc in state.position.board)for o in (0,1)for t in tids];assert row['hand_counts']==[state.position.hands[o].count(t)for o in (0,1)for t in tids]
   if len(vals)>1 and len(witnesses)<12:
    keep=[]
    for v in sorted(vals):
     m=next(x for x in distinct.values()if x['value']==v);keep.append(dict(value_native=v,path=m['path'],full_state_sha256=m['hash'],state=record_value(m['state'])))
    witnesses.append(dict(fixture=name,query=qi,row=ri,trace=row,contexts=keep))
   a[b]+=1;counts['trace_rows']+=1
  rootrows=[row for row in r['training_trace']if row['search_ply']==0 and row['remaining_depth']==dep]
  assert len(rootrows)==1;row=rootrows[0];key=(name,q['mode'],row['position_identity'],row['side_to_move'],dep,row['search_ply'],row['ruleset_fingerprint'])
  pool.setdefault(key,[]).append(dict(parent_ply=root,score_native=row['score_native'],state_hash=digest(s.state)))
  counts['queries']+=1
cross=[dict(key=k,observations=v)for k,v in pool.items()if len({x['score_native']for x in v})>1]
write_json(D/'reader-result.json',dict(status='PASS_ALL_ROOTS_AND_TRACE_CONTEXTS',counts=dict(counts),arms=arms,cross_query_target_collisions=cross,within_query_witnesses=witnesses,seconds=time.perf_counter()-start,scope='Full Core trees under same integer objective. Each emitted bound has at least one matching complete context. Multiple valid history values forbid treating position-only row as universally valid target. This does not identify the actual Native selected trace path or prove a search bug. No Native queries, training or AUX execution.'))
print(dict(counts),arms,'cross',len(cross),'within',len(witnesses),time.perf_counter()-start)
