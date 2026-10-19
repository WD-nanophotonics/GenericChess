"""DEV_AUX103 copy of task2565/audit.py: ONLY changes = FixedWarm initial from plan; FixedWarm uses Fixed regime.
Independent reverse lambda-return credits and public typed-history replay."""
from pathlib import Path
import json,time,hashlib,random,sys
from math import tanh,isclose
from collections import Counter,defaultdict
from results.dev_aux.task2565.train import compiled,restore,environment,prefix,CHANNELS
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2529.training_audit import feat,terminal
from results.dev_aux.task2529.incremental_replay import advance

def vector(a,b):assert len(a)==len(b)and all(isclose(x,y,rel_tol=1e-10,abs_tol=1e-11)for x,y in zip(a,b)),(a,b)
def outcome(e,gs):return e.terminal()if gs==0 else terminal(e.session)
def advance_env(e,gs,record,complete):
 if gs:
  advance(e.session,record,complete)
 else:
  old=e.record();assert record['initial']==old['initial']and record['moves'][:len(old['moves'])]==old['moves'];extra=record['moves'][len(old['moves']):];assert len(extra)==int(complete)
  for a in extra:
   import chess
   move=chess.Move.from_uci(a);assert move in e.board.legal_moves;e.push(move)
 assert e.record()==record

def run(directory,stop_root=None):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());done=json.loads((d/'result.json').read_text());assert hashlib.sha256((d/'plan.json').read_bytes()).hexdigest()==json.loads((d/'started.json').read_text())['plan_sha']
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
 stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();began=time.perf_counter();cc={gs:compiled(gs)for gs,_,_ in p['arms_order']};counts=Counter();by=defaultdict(Counter);weights={};paid=Counter();endpoints={};qstream=(json.loads(l)for l in(d/'queries.jsonl').open());q=next(qstream,None);signals=[];selected={}
 for line in(d/'games.jsonl').open():
  stop();g=json.loads(line);gs,seed,method=g['generator_seed'],g['seed'],g['method'];key=(gs,seed,method);bk=str(key);rng=random.Random(seed)
  if key not in weights:weights[key]=[1.]+[rng.uniform(.5,1.5)for _ in range(p['dimension']-1)];weights[key]=list(p['initial_weights'][f'{gs}/{seed}'])if method=='FixedWarm'else weights[key]
  w=weights[key];assert g['initial_weights']==w;assert g['color']==g['index']%2 and g['family']==p['training_family_offset']+g['index']//2
  fresh=environment(gs,cc[gs]);prefix(fresh,gs,g['family'],p['prefix_plies']);assert fresh.record()==g['initial_record'];e=restore(gs,cc[gs],g['initial_record']);previous=e.record();preds=[];grads=[];gqueries=0;gpaid=0;gobs=0
  while q is not None and q['gameid']==g['gameid']:
   assert q['record_before']==previous and q['actor']==e.player()and outcome(e,gs)is None;assert q['generator_seed']==gs and q['seed']==seed and q['method']==method and q['color']==g['color']and q['ply']==gqueries
   learner_actor=method not in('Fixed','FixedWarm')or q['actor']==g['color'];assert q['learner_actor']==learner_actor;vector(q['weights'],w if learner_actor else p['foe']);obs=q['complete']and(method=='SelfEvery'or q['actor']==g['color']);assert q['observed']==obs
   assert 0<q['nodes']<=q['effective_nodes']<=p['nodes_per_query'];assert q['effective_nodes']==min(p['nodes_per_query'],p['nodes_per_arm']-paid[key]);paid[key]+=q['nodes'];gpaid+=q['nodes'];assert paid[key]==q['total_nodes'];assert q['ordering_seed']==gs*100000000+g['family']*1000+q['ply']+p['ordering_seed_offset']
   if obs:
    v=tanh(q['value']/10);phi=q['pv_phi'];grad=[0.]*len(w)if q['pv_terminal']else[x*(1-tanh(sum(a*b for a,b in zip(w,phi))/10)**2)/10 for x in phi]
    if gs==0:grad[0]=0.
    preds.append(v);grads.append(grad);gobs+=1
    sel=selected.setdefault(key,dict(first=q,last=q));sel['last']=q
    by[bk]['terminal_PV']+=q['pv_terminal'];by[bk]['zero_gradient']+=all(x==0 for x in grad)
   if not q['complete']:assert q['value']is None and q['pv_phi']is None;counts['failed_queries']+=1;counts['failed_nodes']+=q['nodes']
   before=e.record();advance_env(e,gs,q['record_after'],q['complete']);previous=e.record();counts['queries']+=1;counts['played_plies']+=q['complete'];counts['nodes']+=q['nodes'];by[bk]['queries']+=1;gqueries+=1;q=next(qstream,None)
  z=outcome(e,gs);assert z==g['outcome']and g['record']==previous and gqueries==g['queries']and gpaid==g['nodes']and gobs==g['observed'];assert(z is not None)==(g['ending']=='ACTUAL_TERMINAL')
  errors=[preds[i+1]-preds[i]for i in range(len(preds)-1)]
  if preds and z is not None:errors.append(z-preds[-1])
  # Independent reverse lambda-return formulation, not producer forward trace.
  credit=[0.]*len(w);ret=0.
  for i in range(len(errors)-1,-1,-1):
   ret=errors[i]+p['lambda']*ret
   for j,x in enumerate(grads[i]):credit[j]+=x*ret
  expected=[a+p['eta']*b for a,b in zip(w,credit)];vector(expected,g['weights']);assert g['stats']['samples']==len(errors)and g['stats']['observed_searches']==len(preds)and g['stats']['censored']==(z is None);assert isclose(g['stats']['loss'],sum(x*x/2 for x in errors)/max(1,len(errors)),rel_tol=1e-10,abs_tol=1e-11)
  weights[key]=g['weights'];endpoints[key]=g;counts.update(dict(games=1,actual_terminal=z is not None,unknown=z is None,observed=len(preds),terms=len(errors),updates=g['initial_weights']!=g['weights']));by[bk].update(dict(games=1,actual_terminal=z is not None,unknown=z is None,observed=len(preds),terms=len(errors),loss_sum=sum(x*x/2 for x in errors),credit_l1=sum(abs(x)for x in credit),updates=g['initial_weights']!=g['weights']))
  signals.append(dict(key=key,index=g['index'],color=g['color'],nodes=g['total_nodes'],outcome=z,terms=len(errors),loss=sum(x*x/2 for x in errors)/max(1,len(errors)),credit=credit,weights=g['weights']))
 assert q is None
 for a in done['arms']:
  key=a['generator_seed'],a['seed'],a['method'];assert weights[key]==a['weights']and paid[key]==a['nodes'];assert by[str(key)]['games']==a['games']and by[str(key)]['terms']==a['terms']and by[str(key)]['observed']==a['observations']
 assert counts['nodes']==done['nodes']
 result=dict(status='PASS',counts=dict(counts),by_arm=dict(by),seconds=time.perf_counter()-began,scope='ALL independent reverse lambda-return updates, exact pre/post full public history/terminal/clock/actor/cost replay. Same rules authority; no external engine/allrule proof. Unknown terminal endpoint omitted, valid bootstrap transitions retained.')
 (d/'audit.json').write_text(json.dumps(result,indent=2));(d/'signals.json').write_text(json.dumps(signals));(d/'witness-queries.json').write_text(json.dumps([dict(key=key,which=which,query=q)for key,v in selected.items()for which,q in v.items()]));print(json.dumps({k:v for k,v in result.items()if k!='by_arm'}))
if __name__=='__main__':run(sys.argv[1])
