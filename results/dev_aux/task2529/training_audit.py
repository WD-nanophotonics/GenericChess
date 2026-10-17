"""Independent scalar credit and full generated-GameSession record audit."""

from pathlib import Path

from collections import defaultdict,Counter

from math import tanh,isclose

import json,time,hashlib,random

from generic_chess.rules.schema import ruleset_from_dict

from generic_chess.rules.compiler import compile_ruleset

from generic_chess.session.session import GameSession
from results.dev_aux.task2529.incremental_replay import advance

from generic_chess.session.serialization import deserialize_game_record,serialize_game_record

D=Path('results/dev_aux/task2527');O=Path('results/dev_aux/task2529')

def near(a,b):return isclose(a,b,rel_tol=1e-10,abs_tol=1e-12)

def terminal(s):

 r=s.result

 assert r.status.value!='no_contest'and r.declaration_outcome not in('RESTART','NO_CONTEST')

 return None if r.status.value=='ongoing'else 0 if r.winner is None else 1 if r.winner==0 else-1

def feat(s,names):

 board=Counter();hand=Counter()

 for pc in s.state.position.board:

  if pc:board[pc.current_type_id]+=1 if pc.owner==0 else-1

 for owner,h in enumerate(s.state.position.hands):

  for t,n in h.counts:hand[t]+=(1 if owner==0 else-1)*n

 return [(board if kind=='board'else hand)[t]for kind,t in names]

def run():

 began=time.perf_counter();p=json.loads((D/'registration.json').read_text());done=json.loads((D/'result.json').read_text());pins=json.loads((D/'pins.json').read_text())['pins'];assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in pins.items());assert json.loads((D/'started.json').read_text())['registration_sha']==hashlib.sha256((D/'registration.json').read_bytes()).hexdigest()

 compiled={gs:compile_ruleset(ruleset_from_dict(json.loads((D/('rules-'+str(gs)+'.json')).read_text())))for gs in p['generator_seeds']if(D/('rules-'+str(gs)+'.json')).exists()};counts=Counter();current={};used=Counter();closed=defaultdict(list);firstcross=defaultdict(dict);lossbins=defaultdict(lambda:Counter());creditbins=defaultdict(lambda:Counter())

 def readq():

  with(D/'queries.jsonl').open()as f:

   for line in f:yield json.loads(line)

 stream=iter(readq());nextq=next(stream,None)

 for line in(D/'episodes.jsonl').open():

  e=json.loads(line);key=e['generator_seed'],e['seed'];names=e['channels'];cc=compiled[e['generator_seed']];rr=[]

  while nextq is not None and (nextq['generator_seed'],nextq['seed'],nextq['game'])==key+(e['game'],):

   rr.append(nextq);nextq=next(stream,None)

  if key not in current:

   rng=random.Random(e['seed']);current[key]=[1.]+[rng.uniform(.5,1.5)for _ in names[1:]]

  w=current[key];closed[key].append(dict(nodes=used[key],game=e['game']-1,weights=list(w)));assert e['initial_weights']==w and names[0]==['board','P'];previous=e['initial_record'];s=GameSession.replay(cc,deserialize_game_record(json.dumps(previous)));counts['prefix_plies']+=len(s.to_record().actions);preds=[];grads=[];assert e['queries']==len(rr)

  for i,q in enumerate(rr):

   assert q['ply']==i and q['record_before']==previous and q['weights']==w and q['channels']==names;assert terminal(s)is None and q['features']==feat(s,names);assert 0<q['effective_node_limit']<=p['nodes_per_query']and q['nodes']<=q['effective_node_limit']and 0<q['effective_wall_limit']<=p['seconds_per_query'];used[key]+=q['nodes'];assert q['total_nodes']==used[key];counts['queries']+=1

   if q['complete']:

    pred=tanh(q['value']/10);g=[0.]*len(w)if q['pv_terminal']else[0. if j==0 else x*(1-pred*pred)/10 for j,x in enumerate(q['pv_phi'])]

    if not q['pv_terminal']:assert q['value']==sum(x*v for x,v in zip(q['pv_phi'],w))

    else:assert q['value']in(-1e6,0,1e6)

    assert pred==q['prediction']and all(near(x,y)for x,y in zip(g,q['gradient']));preds.append(pred);grads.append(g);counts['terminal_PV_queries']+=q['pv_terminal'];counts['nonzero_PV_gradients']+=any(g);assert len(q['record_after']['actions'])==len(previous['actions'])+1

   else:assert i==len(rr)-1 and q['record_after']==previous and q['prediction']is None and q['gradient']is None;counts['failed_queries']+=1

   # Authoritative public replay of every selected transition, full history retained.

   before_count=len(s.to_record().actions);after=advance(s,q['record_after'],q['complete']);counts['training_plies']+=len(after.to_record().actions)-before_count;

   for action in after.to_record().actions[before_count:]:

    counts['drop_commits']+=type(action).__name__ in('DropMove','SemanticDropMove');counts['promotion_commits']+=getattr(action,'promotion_target_id',None)is not None

   s=after;previous=q['record_after']

  replayed=GameSession.replay(cc,deserialize_game_record(json.dumps(e['record'])));assert replayed.state==s.state and replayed.result==s.result and replayed.to_record()==s.to_record();assert sum(q['nodes']for q in rr)==e['nodes']and used[key]==e['total_nodes'];assert e['record']==previous and terminal(s)==e['outcome'];assert(e['outcome']is not None)==(e['ending']=='ACTUAL_TERMINAL');errors=[preds[i+1]-preds[i]for i in range(len(preds)-1)]

  if preds and e['outcome']is not None:errors.append(e['outcome']-preds[-1])

  future=0.;delta=[0.]*len(w)

  for i in reversed(range(len(preds))):

   future=(errors[i]if i<len(errors)else 0)+p['lambda']*future;delta=[x+future*y for x,y in zip(delta,grads[i])]



  for target in p['checkpoints']:

   if used[key]>=target and target not in firstcross[key]:firstcross[key][target]=dict(nodes=used[key],game=e['game'],weights=e['weights'])if used[key]==target else dict(nodes=used[key]-e['nodes'],game=e['game']-1,weights=w)

  expected=[v+p['eta']*d for v,d in zip(w,delta)];expected[0]=1.;assert all(near(x,y)for x,y in zip(expected,e['weights']));assert e['stats']['samples']==len(errors)and near(e['stats']['loss'],sum(x*x/2 for x in errors)/max(1,len(errors)));assert e['stats']['observed_searches']==len(preds)and e['stats']['censored']==(e['outcome']is None);terminal_l1=0. if not preds or e['outcome']is None else sum(abs(errors[-1]*sum(p['lambda']**(len(preds)-1-i)*grads[i][j]for i in range(len(preds))))for j in range(len(w)));assert near(terminal_l1,e['stats']['terminal_credit_l1']);counts['valid_TD_terms']+=len(errors);counts['nonzero_TD_errors']+=sum(x!=0 for x in errors);current[key]=e['weights'];closed[key].append(dict(nodes=used[key],game=e['game'],weights=e['weights']));bucket=(e['generator_seed'],e['seed'],min(3,max(0,int((used[key]-1)//62500))));lossbins[bucket]['terms']+=len(errors);lossbins[bucket]['half_square_sum']+=sum(x*x/2 for x in errors);creditbins[bucket]['episodes']+=1;creditbins[bucket]['nonzero_updates']+=e['weights']!=w;creditbins[bucket]['unknown']+=e['outcome']is None;creditbins[bucket]['nodes']+=e['nodes'];counts['episodes']+=1;counts['actual_terminal']+=e['outcome']is not None;counts['unknown']+=e['outcome']is None;counts['nonzero_updates']+=e['weights']!=w

 assert nextq is None,'Unconsumedactualqueries'

 for a in done['arms']:

  key=a['generator_seed'],a['seed'];assert current[key]==a['weights']and used[key]==a['nodes']

  for snap in a['snapshots']:

   expected=firstcross[key][snap['target_nodes']];assert all(snap[k]==expected[k]for k in('nodes','game','weights')),(key,snap,expected);counts['verified_checkpoints']+=1

 assert counts['drop_commits']==done['counters'].get('drop_commits',0)and counts['promotion_commits']==done['counters'].get('promotion_commits',0);assert sum(used.values())==done['nodes']and counts['episodes']==done['episodes']and counts['queries']==done['counters'].get('queries',0)

 record=dict(status='PASS_ALL_RETURNED_SCOPED_GENERIC_TD_CREDITS_AND_FULL_SESSION_RECORDS',planned_arms=done['expected_arms'],returned_arms=len(done['arms']),counts=dict(counts),producer_status=done['status'],learning_bins=[dict(generator_seed=gs,seed=seed,node_bin=b,loss=dict(v),credit=dict(creditbins[gs,seed,b]))for(gs,seed,b),v in sorted(lossbins.items())],scope='SAME4TRAIN-exposedrules/ALL4initials/NEWTRAIN/ALLfixedclosedepisodecheckpoints; streamqueryalignmentincludeszeroqueryterminalepisodes. Independent reversecredit/feature/terminalgradients/fullpublicSessionrecords: incrementalsubmit+everyqueryrecordequality+finalpublicreplay. Missing/U preserved; H128newregime, not pureold89updatecontrast. No humanlabels/prover/quantity/unseenrule/full-domain claim; lossbins arechangingTRAINdistribution notfixedvalidationerror.',audit_seconds=time.perf_counter()-began);(O/'training-audit.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))

if __name__=='__main__':run()
