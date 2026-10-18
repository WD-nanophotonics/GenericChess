"""Independent all-history, reverse-credit and raw-TC/WDL accounting audit."""
from pathlib import Path
import json,hashlib,random,time,sys
from math import tanh,isclose
from collections import Counter
from results.dev_aux.task2565.train import restore,prefix
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2565.audit import advance_env,vector
from results.dev_aux.task2392.reader import SharedDeleteStopReader

def run(directory,stop_root=None):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());done=json.loads((d/'result.json').read_text());assert json.loads((d/'started.json').read_text())['plan_sha']==hashlib.sha256((d/'plan.json').read_bytes()).hexdigest()
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
 stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();began=time.perf_counter();counts=Counter();weights={};paid=Counter();tc={};witness={};signals=[];qs=(json.loads(l)for l in(d/'queries.jsonl').open());q=next(qs,None)
 comparisons={g:row for row in map(json.loads,(d/'comparisons.jsonl').open())for g in [row['gameids'][-1]]};rounds={};seen_comparisons=set();armgames=Counter()
 for line in(d/'games.jsonl').open():
  stop();g=json.loads(line);key=g['seed'],g['method'];seed,method=key
  if key not in weights:
   rng=random.Random(seed);weights[key]=[1.]+[rng.uniform(.5,1.5)for _ in range(4)];tc[key]=dict(net=[0.]*5,absolute=[0.]*5)
  w=weights[key];assert g['initial_weights']==w and g['index']==armgames[key];armgames[key]+=1
  if method=='WDL':
   pending=rounds.setdefault(key,[]);ix=len(pending);assert g['variant']==('incumbent','proposal','proposal','incumbent')[ix]and g['color']==(0,0,1,1)[ix];assert g['round_index']==g['index']//4;family=p['training_family_offset']+g['round_index'];cr=comparisons.get(g['gameid'])
   rr=random.Random(seed*100000+g['round_index']+972568000)
   from math import exp,log
   proposal=list(w);proposal[1+g['round_index']%4]*=exp(rr.uniform(-log(2),log(2)))
   played=w if g['variant']=='incumbent'else proposal
  else:family=p['training_family_offset']+g['index']//2;assert g['color']==g['index']%2;played=w
  assert family==g['family'];vector(played,g['played_weights']);fresh=ChessEnv();prefix(fresh,0,family,p['prefix_plies']);assert fresh.record()==g['initial_record'];e=restore(0,None,g['initial_record']);preds=[];grads=[];nq=0;nodes=0;obs=0
  while q is not None and q['gameid']==g['gameid']:
   assert q['seed']==seed and q['method']==method and q['record_before']==e.record()and q['ply']==nq and q['actor']==e.player()and e.terminal()is None
   expected_w=played if q['actor']==g['color']else p['foes'][g['foe_name']];vector(q['weights'],expected_w);assert g['foe_name']==p['foe_cycle'][g['index']%len(p['foe_cycle'])]and q['foe_name']==g['foe_name']
   assert q['effective_nodes']==min(p['nodes_per_query'],p['nodes_per_arm']-paid[key],p['nodes_per_game']-nodes);assert 0<q['nodes']<=q['effective_nodes']and 0<q['effective_seconds']<=p['seconds_per_query'];paid[key]+=q['nodes'];nodes+=q['nodes'];assert paid[key]==q['total_nodes'];assert q['ordering_seed']==family*1000+nq+p['ordering_seed_offset']
   admitted=method!='WDL'and q['actor']==g['color']and q['complete'];assert q['observed']==admitted
   if q['complete']:
    if q['pv_terminal']:assert q['pv_phi']is None and q['value']in(-1000000.,0.,1000000.)
    else:assert isclose(q['value'],sum(a*b for a,b in zip(expected_w,q['pv_phi'])),rel_tol=1e-12,abs_tol=1e-12)
    if q['actor']==g['color']:
     projected=dict(q,generator_seed=0);entry=witness.setdefault(key,dict(first=projected,last=projected));entry['last']=projected
   else:assert q['value']is None and q['pv_phi']is None;counts['failed_queries']+=1;counts['failed_nodes']+=q['nodes']
   if admitted:
    value=tanh(q['value']/10.);preds.append(value);phi=q['pv_phi'];grad=[0.]*5 if q['pv_terminal']else[x*(1-tanh(sum(a*b for a,b in zip(w,phi))/10.)**2)/10. for x in phi];grad[0]=0.;grads.append(grad);obs+=1
   advance_env(e,0,q['record_after'],q['complete']);nq+=1;q=next(qs,None)
  z=e.terminal();assert z==g['outcome']and e.record()==g['record']and nq==g['queries']and nodes==g['nodes']and obs==g['observed'];assert(z is not None)==(g['ending']=='ACTUAL_TERMINAL');assert nodes<=p['nodes_per_game'];assert len(g['record']['moves'])-len(g['initial_record']['moves'])<=p['H']
  errors=[b-a for a,b in zip(preds,preds[1:])]
  if preds and z is not None:errors.append(z-preds[-1])
  credit=[0.]*5;back=0.
  for i in range(len(errors)-1,-1,-1):
   back=errors[i]+p['lambda']*back
   for j in range(5):credit[j]+=back*grads[i][j]
  oldrates=[abs(n)/a if a else 1. for n,a in zip(tc[key]['net'],tc[key]['absolute'])];expected=list(w)
  if method!='WDL':
   rates=oldrates if method=='TC'else[1.]*5;expected=[a+p['eta']*b*r for a,b,r in zip(w,credit,rates)];assert g['stats']['samples']==len(errors)and g['stats']['observed_searches']==obs and g['stats']['censored']==(z is None);assert isclose(g['stats']['loss'],sum(x*x/2 for x in errors)/max(1,len(errors)),rel_tol=1e-10,abs_tol=1e-11)
   if method=='TC':
    elig=[0.]*5;absrec=[0.]*5;net=[0.]*5
    for err,grad in zip(errors,grads):
     elig=[p['lambda']*a+b for a,b in zip(elig,grad)];imp=[err*x for x in elig];net=[a+b for a,b in zip(net,imp)];absrec=[a+abs(b)for a,b in zip(absrec,imp)]
    vector(net,credit);vector(net,g['stats']['recommended_net']);vector(absrec,g['stats']['recommended_absolute']);vector(oldrates,g['stats']['rates_before']);tc[key]['net']=[a+b for a,b in zip(tc[key]['net'],net)];tc[key]['absolute']=[a+b for a,b in zip(tc[key]['absolute'],absrec)];newrates=[abs(n)/a if a else 1. for n,a in zip(tc[key]['net'],tc[key]['absolute'])];vector(newrates,g['stats']['rates_after'])
   vector(expected,g['weights']);weights[key]=g['weights']
  else:
   vector(w,g['weights']);pending.append(g)
   if cr is not None:
    seen_comparisons.add(g['gameid']);assert cr['gameids']==[x['gameid']for x in pending];vector(cr['incumbent'],w);vector(cr['proposal'],proposal)
    if len(pending)==4:
     bounds={}
     for game in pending:
      z=game['outcome'];v=None if z is None else z*(1 if game['color']==0 else-1);bounds[game['variant'],game['color']]=(-1,1)if v is None else(v,v)
     interval=[sum(bounds['proposal',c][0]-bounds['incumbent',c][1]for c in(0,1))/2,sum(bounds['proposal',c][1]-bounds['incumbent',c][0]for c in(0,1))/2];assert interval==cr['interval'];accept=interval[0]>0;assert accept==cr['accepted'];expected=proposal if accept else w
    else:assert cr['interval']is None and not cr['accepted']and cr['incomplete'];expected=w
    vector(expected,cr['after']);weights[key]=cr['after'];rounds[key]=[];counts['comparisons']+=1;counts['accepted']+=cr['accepted']
  counts['teacher_'+g['foe_name']+'_candidate'+str(g['color'])]+=1;counts.update(dict(games=1,queries=nq,nodes=nodes,actual_terminal=z is not None,unknown=z is None,observed=obs,terms=len(errors),episode_updates=w!=g['weights']));signals.append(dict(key=key,index=g['index'],nodes=paid[key],weights=weights[key],outcome=z,loss=g['stats']['loss'],terms=len(errors),tc_rates=oldrates if method=='TC'else None,credit=credit))
 assert q is None and seen_comparisons==set(comparisons)
 for a in done['arms']:
  key=a['seed'],a['method'];vector(a['weights'],weights[key]);assert a['nodes']==paid[key]and a['games']==armgames[key]
 assert counts['nodes']==done['nodes'];r=dict(status='PASS',counts=dict(counts),seconds=time.perf_counter()-began,scope='ALL typedChess legalhistory/fullclaimpolicy, frozenmodel/actor anddeclaredteacher-cycle/role, independentreverseTDsum andallpaidwork. OnlyTDdeclaredarms; noTC/WDLexperiment here. Same rulesauthority, notexternalengine or humanpriceagreement.')
 (d/'audit.json').write_text(json.dumps(r,indent=2));(d/'signals.json').write_text(json.dumps(signals));(d/'witness-queries.json').write_text(json.dumps([dict(key=[0,*key],which=which,query=query)for key,entry in witness.items()for which,query in entry.items()]));print(json.dumps(r))
if __name__=='__main__':run(sys.argv[1])
