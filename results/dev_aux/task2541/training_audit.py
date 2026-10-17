"""Independent full-history, reverse-credit and paid-selection reconstruction."""
from pathlib import Path
from collections import Counter,defaultdict
from math import tanh,isclose
import json,random,time,hashlib
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from results.dev_aux.task2529.training_audit import terminal
from results.dev_aux.task2529.incremental_replay import advance
from scripts.generic_session_win_proof import SessionChoice
D=Path('results/dev_aux/task2539');O=Path('results/dev_aux/task2541')
def near(x,y):return isclose(x,y,rel_tol=1e-10,abs_tol=1e-12)
def run(prefix_rule=None):
 began=time.perf_counter();p=json.loads((D/'plan.json').read_text());done=json.loads((D/'result.json').read_text())if prefix_rule is None else None;assert json.loads((D/'started.json').read_text())['plan_sha']==hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()
 for n,h in json.loads((D/'pins.json').read_text())['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 prefix_limit=None
 if prefix_rule is not None:
  early_updates=defaultdict(list);early_games=defaultdict(list)
  for line in(D/'updates.jsonl').open():
   try:u=json.loads(line)
   except json.JSONDecodeError:break
   if u['generator_seed']==prefix_rule:early_updates[u['generator_seed'],u['method'],u['seed']].append(u)
  for line in(D/'games.jsonl').open():
   try:e=json.loads(line)
   except json.JSONDecodeError:break
   if e['generator_seed']==prefix_rule:early_games[e['generator_seed'],e['method'],e['seed']].append(e)
  assert len(early_updates)==8 and all(us[-1]['nodes']==p['nodes_per_arm']for us in early_updates.values()),'First rule not yet closed; no invented arm completion'
  prefix_limit=max(e['gameid']for es in early_games.values()for e in es);aa=[]
  for key,us in early_updates.items():
   es=early_games[key];rng=random.Random(key[2]);initial=[1.]+[rng.uniform(.5,1.5)for _ in range(5)];aa.append(dict(generator_seed=key[0],method=key[1],seed=key[2],initial=initial,weights=us[-1]['after'],nodes=us[-1]['nodes'],games=len(es),updates=sum(u['changed']for u in us),blocks=len(us)if key[1]=='WDL'else 0))
  done=dict(arms=aa,nodes=sum(a['nodes']for a in aa),counts={})
 cc={g:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{g}.json').read_text())))for g in p['generator_seeds']};counts=Counter();index={};armgames=defaultdict(list);previous_gid=0;armnodes=Counter();active=[0]*6;by_method=defaultdict(Counter)
 def queries():
  for line in(D/'queries.jsonl').open():
   q=json.loads(line)
   if prefix_limit is not None and q['gameid']>prefix_limit:break
   yield q
 stream=iter(queries());nextq=next(stream,None)
 for line in(D/'games.jsonl').open():
  e=json.loads(line);gid=e['gameid']
  if prefix_limit is not None and gid>prefix_limit:break
  assert gid==previous_gid+1;previous_gid=gid;key=e['generator_seed'],e['method'],e['seed'];g,m,seed=key;armgames[key].append(e);index[gid]=e;w=e['initial_weights'];s=GameSession.replay(cc[g],deserialize_game_record(json.dumps(e['initial_record'])));previous=e['initial_record'];counts['prefix_plies']+=len(s.to_record().actions)
  # Independently reconstruct prefix from the frozen legal-action recipe.
  prefix=GameSession(cc[g]);rng=random.Random(g*1000000+e['family'])
  for _ in range(p['prefix_plies']):
   if terminal(prefix)is not None:break
   assert not prefix.compiled.declarations
   actions=[SessionChoice('ACTION',action=a)for a in prefix.legal_actions()];prefix.submit(rng.choice(sorted(actions,key=repr)).action)
  assert json.loads(serialize_game_record(prefix.to_record()))==previous
  rr=[]
  while nextq is not None and nextq['gameid']==gid:rr.append(nextq);nextq=next(stream,None)
  preds=[];grads=[];nodes=0
  for ply,q in enumerate(rr):
   assert q['ply']==ply and q['record_before']==previous and terminal(s)is None and(q['generator_seed'],q['method'],q['seed'])==key and q['family']==e['family']and q['color']==e['color']and q['actor']==s.state.position.side_to_move
   expected=w if q['actor']==e['color']else p['foe'];assert q['weights']==expected and q['nodes']<=q['effective_nodes']<=p['nodes_per_query']and 0<q['effective_seconds']<=p['seconds_per_query'];assert q['ordering_seed']==g*100000000+e['family']*1000+ply+p['ordering_seed_offset'];nodes+=q['nodes'];armnodes[key]+=q['nodes'];assert q['total_nodes']==armnodes[key]
   observe=m=='TD'and q['actor']==e['color']and q['complete'];assert q['observed_by_TD']==observe
   if observe:
    value=tanh(q['value']/10);phi=q['pv_phi'];gradient=[0.]*6 if q['pv_terminal']else[x*(1-value*value)/10 for x in phi];preds.append(value);grads.append(gradient)
    if q['pv_terminal']:assert q['value']in(-1e6,0,1e6);counts['terminal_PV_observations']+=1
    else:
     assert near(q['value'],sum(x*y for x,y in zip(w,phi)))
     for j,x in enumerate(gradient):active[j]+=x!=0
   elif m=='TD':counts['foe_queries_excluded_from_TD']+=1
   if not q['complete']:assert q['record_after']==previous and ply==len(rr)-1 and q['value']is None;counts['failed_queries']+=1;counts['failed_query_nodes']+=q['nodes'];counts['full_limit_failed_queries']+=q['effective_nodes']==p['nodes_per_query']
   s=advance(s,q['record_after'],q['complete']);counts['training_plies']+=q['complete'];previous=q['record_after'];counts['queries']+=1;by_method[m]['queries']+=1;by_method[m]['candidate_queries'if q['actor']==e['color']else'foe_queries']+=1
  actual=terminal(s);public=GameSession.replay(cc[g],deserialize_game_record(json.dumps(e['record'])));assert public.state==s.state and public.result==s.result and public.to_record()==s.to_record();assert e['record']==previous and e['outcome']==actual and e['reward']==(None if actual is None else actual*(1 if e['color']==0 else-1))and e['nodes']==nodes and e['total_nodes']==armnodes[key]and e['queries']==len(rr)and e['observed']==len(preds);assert(actual is not None)==(e['ending']=='ACTUAL_TERMINAL')
  if m=='TD':
   errors=[preds[i+1]-preds[i]for i in range(len(preds)-1)]
   if preds and actual is not None:errors.append(actual-preds[-1])
   future=0.;delta=[0.]*6
   for i in reversed(range(len(preds))):
    future=(errors[i]if i<len(errors)else 0)+p['lam']*future;delta=[x+future*y for x,y in zip(delta,grads[i])]
   assert all(near(x,y+p['eta']*z)for x,y,z in zip(e['after_TD_weights'],w,delta));stats=e['stats'];assert stats['samples']==len(errors)and stats['observed_searches']==len(preds)and stats['censored']==(actual is None);assert near(stats['loss'],sum(x*x/2 for x in errors)/max(1,len(errors)));counts['TD_terms']+=len(errors)
   if e['color']==1 and actual is not None and rr and rr[-1]['actor']==0 and preds:counts['black_candidate_white_foe_finisher']+=1;assert e['reward']==-actual and not rr[-1]['observed_by_TD']
  else:assert e['after_TD_weights']==w and e['stats']is None
  counts['games']+=1;counts['actual_terminal']+=actual is not None;counts['unknown']+=actual is None;counts[e['ending']]+=1;counts['nodes']+=nodes;counts['observed']+=len(preds);by_method[m]['games']+=1;by_method[m]['nodes']+=nodes;by_method[m]['actual_terminal']+=actual is not None;by_method[m]['unknown']+=actual is None
 assert nextq is None
 updates=defaultdict(list)
 for line in(D/'updates.jsonl').open():
  u=json.loads(line)
  if prefix_rule is not None and u['generator_seed']!=prefix_rule:continue
  updates[u['generator_seed'],u['method'],u['seed']].append(u)
 for arm in done['arms']:
  key=arm['generator_seed'],arm['method'],arm['seed'];g,m,seed=key;rng=random.Random(seed);initial=[1.]+[rng.uniform(.5,1.5)for _ in range(5)];assert initial==arm['initial'];current=list(initial);ids=[];changed=0
  for i,u in enumerate(updates[key]):
   assert u['index']==i and u['before']==current;rows=[index[x]for x in u['gameids']];assert all((r['generator_seed'],r['method'],r['seed'])==key for r in rows);ids+=u['gameids'];assert u['nodes']==rows[-1]['total_nodes']
   if m=='TD':
    assert len(rows)==1 and rows[0]['family']==p['training_family_offset']+i//2 and rows[0]['color']==i%2 and rows[0]['initial_weights']==current;after=rows[0]['after_TD_weights'];assert u['after']==after and u['changed']==(after!=current)
   else:
    cycle,slot=divmod(i,12);moves=[(j,sgn*p['grid_step'])for j in range(6)for sgn in(-1,1)];random.Random(p['proposal_order_seed']+seed+cycle*1000000).shuffle(moves);j,d=moves[slot];candidate=list(current);candidate[j]+=d;assert u['coordinate']==j and u['delta']==d and u['proposal']==candidate
    slots=[(p['training_family_offset']+i*p['pairs_per_proposal']+f,c,t)for f in range(p['pairs_per_proposal'])for c in(0,1)for t in(('current','proposal')if(i+f+c)%2==0 else('proposal','current'))];assert[(r['family'],r['color'],r['treatment'])for r in rows]==slots[:len(rows)];assert u['expected_games']==len(slots)and u['actual_games']==len(rows)and u['missing']==len(slots)-len(rows);table={(r['family'],r['color'],r['treatment']):r for r in rows};lo=hi=0
    for r in rows:assert r['initial_weights']==(candidate if r['treatment']=='proposal'else current)
    def iv(r):return(-1,1)if r is None or r['reward']is None else(r['reward'],r['reward'])
    for f in range(p['pairs_per_proposal']):
     for c in(0,1):
      family=p['training_family_offset']+i*p['pairs_per_proposal']+f;a=table.get((family,c,'current'));b=table.get((family,c,'proposal'))
      if a and b:assert a['initial_record']==b['initial_record']
      aa=iv(a);bb=iv(b);lo+=bb[0]-aa[1];hi+=bb[1]-aa[0]
    assert u['bounds']==[lo/(2*p['pairs_per_proposal']),hi/(2*p['pairs_per_proposal'])]and u['changed']==(lo>0);after=candidate if lo>0 else current;assert u['after']==after;counts['WDL_proposals']+=1;counts['WDL_accepts']+=lo>0;counts['WDL_missing_proposal_games']+=u['missing']
   changed+=u['changed'];current=list(after)
  assert ids==[r['gameid']for r in armgames[key]]and current==arm['weights']and len(ids)==arm['games']and changed==arm['updates']and arm['nodes']==armnodes[key]<=p['nodes_per_arm'];counts['arms']+=1
  if prefix_rule is None:assert arm['seconds']>=sum(r['seconds']for r in armgames[key])
 assert counts['nodes']==done['nodes']and all(counts[k]==v for k,v in done['counts'].items());assert len(done['arms'])==counts['arms']
 out=dict(audited_prefix_rule=prefix_rule,planned_arms=32,status='PASS_ALL_TYPED_HISTORIES_CANDIDATE_ONLY_TD_AND_PAID_STRICT_WDL',counts=dict(counts),by_method={m:dict(v)for m,v in by_method.items()},active_TD_coordinates=active,audit_seconds=time.perf_counter()-began,scope='Independent reverse future-error convolution/manualgradients/whitez-blackutility, deterministicproposal/rootreconstruction/fullpublichistory. Allcurrent/proposal/foe/failedqueries paid. No independentexternalrulesengine or allquerysearchrerun.')
 (O/('training-audit.json'if prefix_rule is None else'training-audit-first-rule.json')).write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
