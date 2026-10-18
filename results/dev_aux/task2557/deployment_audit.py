"""Independent complete-rule deployment audit; no learned/search score as outcome."""
from pathlib import Path
from collections import Counter,defaultdict
from dataclasses import replace
import json,hashlib,time,random,math
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2529.incremental_replay import advance
from results.dev_aux.task2529.training_audit import terminal
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2556');O=Path('results/dev_aux/task2557')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def run(stop_root=None):
 start=time.perf_counter();p=load(D/'plan.json');done=load(D/'result.json');binding=load(D/'pre-fitness-binding.json');ph=hashlib.sha256((D/'plan.json').read_bytes()).hexdigest();assert binding['plan_sha']==load(D/'started.json')['plan_sha']==ph
 assert binding['models_sha']==hashlib.sha256(Path(p['training']).read_bytes()).hexdigest()
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 arms={(a['generator_seed'],a['method'],a['seed']):a for a in load(p['training'])['arms']};cc={gs:compile_ruleset(ruleset_from_dict(load(f'results/dev_aux/task2525/rules-{gs}.json')))for gs in p['generator_seeds']};stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();counts=Counter();paid=defaultdict(Counter);index={};records=[]
 def stream():
  with(D/'queries.jsonl').open()as f:
   for line in f:yield json.loads(line)
 it=iter(stream());q=next(it,None);previous_pos=-1;positions={tuple(s):i for i,s in enumerate(p['slots'])}
 for line in(D/'games.jsonl').open():
  r=json.loads(line);key=tuple(r['slot']);assert key not in index and positions[key]>previous_pos;previous_pos=positions[key];index[key]=r;gs,seed,f,c,t,foe,d=key;a=arms[gs,'D2TD'if t=='initial'else t,seed];w=a['initial']if t=='initial'else a['weights'];assert r['weights']==w and r['channels']==a['channels']and r['candidate_depth']==d
  prev=r['initial_record'];s=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(prev)));counts['prefix_plies']+=len(s.to_record().actions);nq=nodes=0
  while q is not None and tuple(q['slot'])==key:
   if counts['queries']%64==0:stop()
   assert q['ply']==nq and q['record_before']==prev and terminal(s)is None;actor=s.state.position.side_to_move;assert q['actor']==actor;expected=w if actor==c else p['opponents'][foe];assert q['weights']==expected;assert q['effective_depth']==(d if actor==c else p['opponent_depth']);assert q['ordering_seed']==gs*100000000+f*1000+nq+p['ordering_seed_offset'];assert q['effective_node_limit']==p['nodes_per_query']and 0<q['nodes']<=p['nodes_per_query'];assert 0<q['effective_wall_limit']<=p['seconds_per_query']and q['effective_wall_limit']<=q['global_remaining_before_query'];counts['queries']+=1;counts['candidate_queries'if actor==c else'foe_queries']+=1;nodes+=q['nodes'];nq+=1
   group=paid[d,t,foe];group['nodes']+=q['nodes'];group['queries']+=1;group['search_seconds']+=q['seconds'];group['candidate_nodes'if actor==c else'foe_nodes']+=q['nodes']
   if q['complete']:
    assert q['reason']=='complete';action=q['record_after']['actions'][-1];counts['drops']+=action['kind']=='drop';counts['promotions']+=action.get('promotion_target_id')is not None
    if q['pv_terminal']:assert q['pv_phi']is None and q['value']in(-1e6,0,1e6)
    else:assert len(q['pv_phi'])==len(expected)and math.isclose(q['value'],sum(a*b for a,b in zip(expected,q['pv_phi'])),rel_tol=1e-12,abs_tol=1e-10)
   else:assert q['value']is None and q['record_before']==q['record_after'];counts['failed_queries']+=1
   before=len(s.to_record().actions);s=advance(s,q['record_after'],q['complete']);counts['played_plies']+=len(s.to_record().actions)-before;prev=q['record_after'];q=next(it,None)
  assert nq==r['queries']and nodes==r['nodes'];end=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(r['record'])));assert end.state==s.state and end.result==s.result and end.to_record()==s.to_record();z=terminal(s);reward=None if z is None else z*(1 if c==0 else-1);assert r['outcome']==z and r['reward']==reward and r['record']==prev;assert(z is not None)==(r['ending']=='ACTUAL_TERMINAL');counts[r['ending']]+=1;counts['games']+=1;paid[d,t,foe]['games']+=1;paid[d,t,foe]['unknown']+=z is None;records.append(r)
 assert q is None;assert len(records)==done['actual']and sum(r['nodes']for r in records)==done['nodes']and counts['queries']==done['queries'];assert done['expected']==len(p['slots'])and done['missing']==len(p['slots'])-len(records)
 cells=[(gs,seed,f,c)for gs in p['generator_seeds']for seed in p['initial_seeds']for f in p['families']for c in(0,1)]
 def bcell(cell,foe,terms):
  gs,seed,f,c=cell;coeff=Counter()
  for t,d,k in terms:coeff[gs,seed,f,c,t,foe,d]+=k
  lo=hi=0
  for key,k in coeff.items():
   if not k:continue
   z=index.get(key,{}).get('reward');a,b=(-1,1)if z is None else(z,z);lo+=k*(a if k>0 else b);hi+=k*(b if k>0 else a)
  return lo,hi
 specs=[]
 for t,b in [('D3TD','D2TD'),('D3Tree','D2Tree'),('D3TD','initial'),('D3Tree','initial'),('D3Tree','D3TD'),('D2Tree','D2TD')]:specs.append((f'{t}-{b}@D3',[(t,3,1),(b,3,-1)]))
 contrasts=[]
 for foe in p['opponents']:
  for name,terms in specs:
   values={c:bcell(c,foe,terms)for c in cells}
   def mean(cs):return[sum(values[c][j]for c in cs)/len(cs)for j in(0,1)]
   rng=random.Random(942553);boot=[]
   for _ in range(3000):
    gs=[rng.choice(p['generator_seeds'])for _ in p['generator_seeds']];ss=[rng.choice(p['initial_seeds'])for _ in p['initial_seeds']];fs=[rng.choice(p['families'])for _ in p['families']];boot.append(mean([(g,s,f,c)for g in gs for s in ss for f in fs for c in(0,1)]))
   strata={axis:[dict(value=x,bounds=mean([c for c in cells if c[i]==x]))for x in sorted(set(c[i]for c in cells))]for i,axis in enumerate(['rule','seed','family','role'])};contrasts.append(dict(foe=foe,name=name,bounds=mean(cells),strata=strata,descriptive_95=[sorted(v[0]for v in boot)[74],sorted(v[1]for v in boot)[2924]],terms=terms))
 # On matched roots, any first action difference between paired policies must be a candidate turn.
 behavior=[]
 for foe in p['opponents']:
  for label,terms in specs:
   if len(terms)!=2:continue
   stats=Counter()
   for gs,seed,f,c in cells:
    (t,d,_),(b,e,_)=terms;x=index.get((gs,seed,f,c,t,foe,d));y=index.get((gs,seed,f,c,b,foe,e))
    if x is None or y is None:stats['missing_pair']+=1;continue
    assert x['initial_record']==y['initial_record'];xa=deserialize_game_record(json.dumps(x['record']));ya=deserialize_game_record(json.dumps(y['record']));i=next((i for i,(a,b)in enumerate(zip(xa.actions,ya.actions))if a!=b),None)
    if i is not None:
     before=GameSession.replay(cc[gs],replace(xa,actions=xa.actions[:i],resigned_by=None,declaration=None));assert before.state.position.side_to_move==c;stats['first_difference_candidate']+=1
    elif xa.actions==ya.actions:stats['identical_record']+=1
    else:assert x['reward']is None or y['reward']is None;stats['censored_prefix']+=1
    if x['reward']is None or y['reward']is None:stats['unresolved_pair']+=1
    else:stats['improved'if x['reward']>y['reward']else'worse'if x['reward']<y['reward']else'same_reward']+=1
   behavior.append(dict(foe=foe,name=label,counts=dict(stats)))
 result=dict(status='PASS_ALL_TYPED_OUTCOMES_AND_FIXED_FOE_DEPTH_DISPATCH',planned=len(p['slots']),returned=len(records),missing=done['missing'],counts=dict(counts),paid=[dict(depth=d,treatment=t,foe=f,**dict(c))for(d,t,f),c in sorted(paid.items())],contrasts=contrasts,behavior=behavior,audit_seconds=time.perf_counter()-start,scope='Actual full typed Session histories/terminals and EVERY recorded role/depth/weight dispatch/PV scalar. No exhaustive correctness of allsearches/externalrulesengine. All candidate deployment D3/fixed D2foe, oldD2trained versus newcandidateD3trained endpoints; same total TRAIN nodes but different visitation/update counts; extra actualwork paid. Finite conditionalpolicy utility, allseeds/roles/UNKNOWN/missing retained; bootstrapdescriptive notconfidence/equivalence/generalprices.')
 (O/'deployment.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k]for k in['status','planned','returned','missing','counts','audit_seconds']}));print(json.dumps([dict(foe=x['foe'],name=x['name'],bounds=x['bounds'],descriptive_95=x['descriptive_95'])for x in contrasts]))
if __name__=='__main__':run()
