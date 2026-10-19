"""ALL registered Fixednu/SelfCandidate/initial contrasts; no selected seed/price/root/snapshot."""
from pathlib import Path
from collections import Counter,defaultdict
import json,itertools,hashlib
from results.dev_aux.task2568.summary import bounds,contrast
from results.dev_aux.task2580.train import initial
D=Path('results/dev_aux/task2583');E=Path('results/dev_aux/task2584')
def load(p):return json.loads(Path(p).read_text())
def run():
 p=load(D/'plan.json');reg=load(D/'registration.json');ep=load(E/'eval-plan.json');t=load(D/'result.json');ev=load(E/'eval-result.json');bind=load(E/'result.json')
 assert reg['registered_at']<load(D/'started.json')['utc']<load(E/'eval-started.json')['utc']
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 assert bind['training_sha']==hashlib.sha256((D/'result.json').read_bytes()).hexdigest()
 src={(a['seed'],a['method']):a for a in t['arms']}
 for a in bind['arms']:
  if a['original_method']=='initial':assert a['weights']==initial(a['seed'])
  else:assert a['weights']==next(s for s in src[a['seed'],a['original_method']]['snapshots']if s['boundary']==a['boundary'])['weights']
 treatments=sorted({s[4]for s in ep['slots']});families=sorted(map(int,ep['root_recipes']))
 assert len(ep['slots'])==640 and set(map(tuple,ep['slots']))==set(itertools.product([0],p['seeds'],families,(0,1),treatments,ep['foes']))
 rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())};assert len(rows)==ev['actual']
 L=lambda m,b:f'{m}@{b/1e6:g}M|plain'
 pairs=[]
 for b in p['snapshot_nodes']:pairs.append((L('SelfCandidate',b),L('Fixednu',b)))
 for m,b in itertools.product(('Fixednu','SelfCandidate'),p['snapshot_nodes']):pairs.append((L(m,b),'initial|plain'))
 for m in('Fixednu','SelfCandidate'):pairs.append((L(m,p['snapshot_nodes'][1]),L(m,p['snapshot_nodes'][0])))
 out={}
 for context in('all','8','64'):
  slots=[s for s in ep['slots']if context=='all'or ep['root_recipes'][str(s[2])]['plies']==int(context)];out[context]={}
  for a,b in pairs:
   out[context][a+' - '+b]=dict(all=contrast(rows,slots,a,b),by_foe={o:contrast(rows,[s for s in slots if s[5]==o],a,b)for o in ep['foes']},by_seed={str(seed):{o:contrast(rows,[s for s in slots if s[1]==seed and s[5]==o],a,b)for o in ep['foes']}for seed in p['seeds']},by_role={str(c):{o:contrast(rows,[s for s in slots if s[3]==c and s[5]==o],a,b)for o in ep['foes']}for c in(0,1)})
 absolute={}
 for ctx,m,o in itertools.product((8,64),treatments,ep['foes']):
  ss=[s for s in ep['slots']if ep['root_recipes'][str(s[2])]['plies']==ctx and s[4]==m and s[5]==o];cc=Counter();v=[0.,0.]
  for s in ss:
   g=rows.get(tuple(s));bb=bounds(g);v=[x+y for x,y in zip(v,bb)];cc['missing'if g is None else'U'if g['reward']is None else'W'if g['reward']>0 else'L'if g['reward']<0 else'D']+=1
  absolute[f'{ctx}/{m}/{o}']=dict(n=len(ss),counts=dict(cc),bounds=[x/len(ss)for x in v])
 groups=defaultdict(Counter);loss=Counter();trainroots=set()
 for g in map(json.loads,(D/'games.jsonl').open()):
  key=str((g['seed'],g['method']));cc=groups[key];cc.update(dict(games=1,nodes=g['nodes'],queries=g['queries'],terms=g['stats']['samples'],terminal=g['outcome']is not None,U=g['outcome']is None,updates=g['initial_weights']!=g['weights']));cc['prefix'+str(g['prefix_plies'])]+=1;cc[g['ending']]+=1;loss[key]+=(g['stats']['loss']or 0)*g['stats']['samples'];trainroots.add(json.dumps(g['initial_record'],sort_keys=True))
 train={k:dict(counts=dict(c),changing_data_weighted_loss=loss[k]/max(1,c['terms']),terms_per_Mnode=c['terms']/max(1,c['nodes'])*1e6)for k,c in groups.items()}
 roots={json.dumps(g['initial_record'],sort_keys=True)for g in rows.values()}
 costs=defaultdict(Counter)
 for q in map(json.loads,(E/'eval-queries.jsonl').open()):
  c=q['slot'][3];costs[q['slot'][4]+('/candidate'if q['actor']==c else'/fixed_foe')].update(dict(nodes=q['nodes'],queries=1,failed=not q['complete']))
 orders={L(m,b):[sorted(range(5),key=lambda j:x['weights'][j])for x in bind['arms']if x['method']==L(m,b)]for m in('Fixednu','SelfCandidate')for b in p['snapshot_nodes']}
 weights={x['method']+'/'+str(x['seed']):x['weights']for x in bind['arms']}
 lags={x['method']+'/'+str(x['seed']):x.get('snapshot_lag')for x in bind['arms']if x['original_method']!='initial'}
 result=dict(status='PASS_ALL_REGISTERED_CONTRASTS',TRAIN={k:v for k,v in t.items()if k!='arms'},EVAL=ev,contrasts=out,absolute_WLD=absolute,TRAIN_arms=train,query_policy_costs=dict(costs),bound_weights=weights,snapshot_lags=lags,orders=orders,price_order_unanimity={m:len(v)==4 and len(set(map(tuple,v)))==1 for m,v in orders.items()},exposure=dict(TRAIN_records=len(trainroots),EVAL_records=len(roots),overlap=len(trainroots&roots)),paid_nodes=t['nodes']+ev['nodes'],producer_seconds=t['seconds']+ev['seconds'],scope='Finite registered panel paired bounds (U/missing=[-1,1]), not CI/population/universal prices. SelfCandidate vs Fixednu differs in opponent policy AND hence data/episodes/targets at same paid nodes. Snapshots are last closed episode<=boundary with recorded lag. Audit/engineering/packaging costs additional.')
 (E/'summary.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(dict(status=result['status'],contrasts={c:{k:dict(all=v['all']['bounds'],**{o:z['bounds']for o,z in v['by_foe'].items()})for k,v in x.items()}for c,x in out.items()},EVAL=ev,orders=result['price_order_unanimity'],nodes=result['paid_nodes'],seconds=result['producer_seconds']),indent=1))
if __name__=='__main__':run()
