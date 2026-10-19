"""All registered reset-distribution comparisons; no selected seed/price/root."""
from pathlib import Path
from collections import Counter,defaultdict
import json,itertools,hashlib
from results.dev_aux.task2568.summary import bounds,contrast
from results.dev_aux.task2580.train import initial
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2565.train import prefix
from results.dev_aux.task2571.trajectory import compare
D=Path('results/dev_aux/task2580');E=Path('results/dev_aux/task2581')
def load(p):return json.loads(Path(p).read_text())
def run():
 p=load(D/'plan.json');reg=load(D/'registration.json');ep=load(E/'eval-plan.json');t=load(D/'result.json');ev=load(E/'eval-result.json');bind=load(E/'result.json')
 assert reg['registered_at']<load(D/'started.json')['utc']<load(E/'eval-started.json')['utc']
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 assert bind['training_sha']==hashlib.sha256((D/'result.json').read_bytes()).hexdigest()
 src={(a['seed'],a['method']):a for a in t['arms']}
 for a in bind['arms']:assert a['weights']==(initial(a['seed'])if a['original_method']=='initial'else src[a['seed'],a['original_method']]['weights'])
 methods=('initial','TD_early','TD_mixed');families=sorted(map(int,ep['root_recipes']))
 expected=set(itertools.product([0],p['seeds'],families,(0,1),(m+'|plain'for m in methods),ep['foes']))
 assert len(ep['slots'])==768 and set(map(tuple,ep['slots']))==expected
 rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())};assert len(rows)==ev['actual']
 out={}
 for context in ('all','8','64'):
  slots=[s for s in ep['slots']if context=='all'or ep['root_recipes'][str(s[2])]['plies']==int(context)]
  out[context]={}
  for left,right in (('TD_early','initial'),('TD_mixed','initial'),('TD_mixed','TD_early')):
   a,b=left+'|plain',right+'|plain'
   out[context][left+'-'+right]=dict(all=contrast(rows,slots,a,b),by_foe={o:contrast(rows,[s for s in slots if s[5]==o],a,b)for o in ep['foes']},by_seed={str(seed):{o:contrast(rows,[s for s in slots if s[1]==seed and s[5]==o],a,b)for o in ep['foes']}for seed in p['seeds']},by_role={str(c):{o:contrast(rows,[s for s in slots if s[3]==c and s[5]==o],a,b)for o in ep['foes']}for c in(0,1)},by_family={str(f):contrast(rows,[s for s in slots if s[2]==f],a,b)for f in sorted({s[2]for s in slots})})
 absolute={}
 for ctx,m,o in itertools.product((8,64),methods,ep['foes']):
  ss=[s for s in ep['slots']if ep['root_recipes'][str(s[2])]['plies']==ctx and s[4]==m+'|plain'and s[5]==o];cc=Counter();v=[0.,0.]
  for s in ss:
   g=rows.get(tuple(s));bb=bounds(g);v=[x+y for x,y in zip(v,bb)];cc['missing'if g is None else'U'if g['reward']is None else'W'if g['reward']>0 else'L'if g['reward']<0 else'D']+=1
  absolute[f'{ctx}/{m}/{o}']=dict(n=len(ss),counts=dict(cc),bounds=[x/len(ss)for x in v])
 groups=defaultdict(Counter);loss=Counter();trainroots=set();root_examples={}
 for g in map(json.loads,(D/'games.jsonl').open()):
  key=str((g['seed'],g['method']));n=g['prefix_plies'];cc=groups[key];cc.update(dict(games=1,nodes=g['nodes'],queries=g['queries'],terms=g['stats']['samples'],terminal=g['outcome']is not None,U=g['outcome']is None,updates=g['initial_weights']!=g['weights']));cc['prefix'+str(n)]+=1;loss[key]+=(g['stats']['loss']or 0)*g['stats']['samples']
  raw=json.dumps(g['initial_record'],sort_keys=True);trainroots.add(raw);root_examples[g['method'],g['family'],n]=g['initial_record']
 train={k:dict(counts=dict(c),changing_data_weighted_loss=loss[k]/max(1,c['terms']))for k,c in groups.items()}
 roots={json.dumps(g['initial_record'],sort_keys=True)for g in rows.values()}
 recipes=[]
 for code,rec in ep['root_recipes'].items():
  e=ChessEnv();prefix(e,0,rec['family'],rec['plies']);rr=e.record();phi=e.features()
  actual={json.dumps(g['initial_record'],sort_keys=True)for g in rows.values()if g['slot'][2]==int(code)}
  assert actual<=set([json.dumps(rr,sort_keys=True)])
  recipes.append(dict(code=int(code),recipe=rec,actual_random_plies=len(rr['moves']),root_terminal=e.terminal(),free_phi=phi[1:],root_sha=hashlib.sha256(json.dumps(rr,sort_keys=True).encode()).hexdigest()))
 costs=defaultdict(Counter)
 for q in map(json.loads,(E/'eval-queries.jsonl').open()):
  c=q['slot'][3];label=q['slot'][4];assert not q['candidate_q2']and q['search_stats']['qnodes']==0
  costs[label+('/candidate'if q['actor']==c else'/fixed_foe')].update(dict(nodes=q['nodes'],queries=1,failed=not q['complete']))
 orders={m:[sorted(range(5),key=lambda j:a['weights'][j])for a in t['arms']if a['method']==m]for m in('TD_early','TD_mixed')}
 trajectory={}
 for a,b in(('TD_early','initial'),('TD_mixed','initial'),('TD_mixed','TD_early')):
  cells=[dict(seed=s,family=f,color=c,foe=o,**compare(rows.get((0,s,f,c,a+'|plain',o)),rows.get((0,s,f,c,b+'|plain',o))))for s,f,c,o in itertools.product(p['seeds'],families,(0,1),ep['foes'])]
  trajectory[a+'-'+b]=dict(counts=dict(Counter(x['kind']for x in cells)),cells=cells)
 result=dict(status='PASS_ALL_REGISTERED_DISTRIBUTIONS',TRAIN=t,EVAL=ev,contrasts=out,absolute_WLD=absolute,TRAIN_loss=train,query_policy_costs=dict(costs),orders=orders,price_order_unanimity={m:len(v)==4 and len(set(map(tuple,v)))==1 for m,v in orders.items()},root_recipes=recipes,exposure=dict(TRAIN_records=len(trainroots),EVAL_records=len(roots),current_record_overlap=len(trainroots&roots)),paid_nodes=t['nodes']+ev['nodes'],producer_seconds=t['seconds']+ev['seconds'],scope='Finite reset-protocol effects, not pure rank/material/policy-gradient causality, CI or population/universal price statement. Equal TRAIN ALLpaidnodes; all seeds/roles/foes/partial failures paid, no selected price/root. EVAL prefix8/64 histories share mechanical ancestors and are not independent populations. Changing-data loss not calibration/strength. Actual audit/engineering/packaging/transport additional.')
 (E/'summary.json').write_text(json.dumps(result,indent=2));(E/'trajectory-divergence.json').write_text(json.dumps(dict(status='PASS_FIXED_FOE_FIRST_DIVERGENCE',pairs=trajectory),indent=2))
 print(json.dumps(dict(status=result['status'],contrasts={c:{m:{o:v['bounds']for o,v in z['by_foe'].items()}for m,z in x.items()}for c,x in out.items()},EVAL=ev,orders=result['price_order_unanimity'],nodes=result['paid_nodes'],seconds=result['producer_seconds'])))
if __name__=='__main__':run()
