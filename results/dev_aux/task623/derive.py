import json,time,hashlib,collections
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task623';O.mkdir(exist_ok=True);start=time.perf_counter();d=json.loads((R/'results/dev_aux/task618/declaration.json').read_bytes());records=[]
for task,obj in [(597,'terminal'),(598,'mixed'),(619,'fast')]:
 e=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())
 for u in e['updates']:
  family=u.get('start',u.get('family'))
  for j,c in enumerate(u['candidates']):records.append(dict(task=task,objective=obj,start=family,iteration=u['iteration'],candidate=j,weights=c['weights'],goals=c['goals'],sources=c['sources']))
# ONLYfaststudy verifiedrecordarrays; cachedbase logicalreuse deliberatelykeptseparate fromuniqueprice count.
fast=[x for x in records if x['objective']=='fast'];byprice={}
for x in fast:
 key=tuple(x['weights']);signature=tuple(x['goals'])
 if key in byprice:assert byprice[key]['signature']==signature
 else:byprice[key]=dict(signature=signature,weights=x['weights'],source=x['sources'],contexts=[])
 byprice[key]['contexts'].append({k:x[k] for k in ['start','iteration','candidate']})
classes=collections.defaultdict(list)
for x in byprice.values():classes[x['signature']].append(x)
aliases=[dict(goal_signature=list(sig),prices=[p['weights'] for p in ps],price_count=len(ps),contexts=[p['contexts'] for p in ps]) for sig,ps in classes.items() if len(ps)>1]
rows=[]
for u in json.loads((R/'results/dev_aux/task619/endpoints.json').read_bytes())['updates']:
 vs=[[F(x) for x in c['goals']] for c in u['candidates']];rr=[x for x in fast if x['start']==u['start'] and x['iteration']==u['iteration']];families=[f['source_family'] for f in d['roots'] if f['phase']=='train' for c in [0,1]];loo=[];means=[sum(v)/104 for v in vs];best=max(range(3),key=lambda j:means[j]);assert best==u['selected_index']
 for f in sorted(set(families)):
  ix=[i for i,x in enumerate(families) if x!=f];mu=[sum(v[i] for i in ix)/len(ix) for v in vs];b=max(range(3),key=lambda j:mu[j]);loo.append(dict(omit=f,selected=b,gain=str(mu[b]-mu[0])))
 rows.append(dict(start=u['start'],iteration=u['iteration'],selected=best,gain=str(means[best]-means[0]),robust=best!=0 and all(x['selected']==best and F(x['gain'])>0 for x in loo),cells_differ=sum(len({v[i] for v in vs})>1 for i in range(104)),all_means_tied=len(set(means))==1,leave_one=loo))
summ=[]
for st in ['unit','random2514']:
 a=[x for x in rows if x['start']==st];summ.append(dict(start=st,accepted=sum(x['selected']!=0 for x in a),robust_same_strict_choice_all8=sum(x['robust'] for x in a),rounds_cells_differ=sum(x['cells_differ']>0 for x in a),all_means_tied=sum(x['all_means_tied'] for x in a)))
out=dict(status='PASS_ACTUAL_FAST_CHOICES_AND_ALIASES',logical_candidate_batches=len(fast),unique_price_vectors=len(byprice),unique_full104cell_fast_reward_signatures=len(classes),aliased_classes=aliases,summary=summ,rows=rows,new_go=0,seconds=time.perf_counter()-start,scope='Actual619 faststudy arrays/basecache; ALLuniquepricevectors/full104cell rewardaliases. Observablealias not globalnonidentifiability andcache repetitions notindependent. Actual24proposalrounds/8originalfamilies, no inventedleave-one trainingtrajectory orhuman/source vectorselection. Priorobjectives retained asprovenance; fast localdecisions hereACTUALnewtrajectory, unlike617posthoc choices.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['aliased_classes','rows']}))