import json,math,time,re,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task465';r=json.loads((R/'results/dev_aux/task459/result.json').read_text(encoding='utf-8'));assert r['status']=='completed';t0=time.perf_counter();rows=[]
for task,label in [(457,'few4'),(458,'wide16')]:
 ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_text(encoding='utf-8'))
 for p in ep['endpoints']:
  prefix=label+'-trained-'+p['family']
  for env in ('unit','random'):
   a=sorted([x for x in r['rows'] if x['opponent']==env and prefix+'-initial' in x['names']],key=lambda x:(x['root_index'],x['color']));b=sorted([x for x in r['rows'] if x['opponent']==env and prefix+'-endpoint' in x['names']],key=lambda x:(x['root_index'],x['color']));assert len(a)==len(b)==16
   def metric(x,name):
    t=x['termination'];pure=Fraction(0) if t['winner'] is None else Fraction(32 if t['winner']==x['color'] else -32);qty=Fraction(x['quantity'],19) if t['kind']=='cap24' else Fraction(0);assert pure+qty==Fraction(x['goal']);return pure+qty if name=='mixed' else pure if name=='terminal' else pure+(0 if t['winner'] is None else (1 if t['winner']==x['color'] else -1)*Fraction(24-x['plies'],24))
   for name in ('mixed','terminal','fast'):
    av=[metric(x,name) for x in a];bv=[metric(x,name) for x in b];ds=[y-x for x,y in zip(av,bv)];fam=[sum(ds[i:i+2])/2 for i in range(0,16,2)];rows.append(dict(arm=label,family=p['family'],opponent=env,metric=name,initial_mean=str(sum(av)/16),endpoint_mean=str(sum(bv)/16),gain=str(sum(ds)/16),root_family_gains=list(map(str,fam)),leave_one_family_gains=[str(sum(v for j,v in enumerate(fam) if j!=i)/7) for i in range(8)],initial_wins=sum(x['termination']['winner']==x['color'] for x in a),endpoint_wins=sum(x['termination']['winner']==x['color'] for x in b),paired_gains=list(map(str,ds))))
resources=[]
for task in [457,458,459]:
 folder=R/f'results/dev_aux/task{task}';gs=[json.loads(x) for x in (folder/'games.jsonl').open(encoding='utf-8')];go=0;nodes=[];searchwall=0
 for line in (folder/'queries.jsonl').open(encoding='utf-8'):
  q=json.loads(line);go+=1;searchwall+=q['seconds'];last=[x for x in q['lines'] if re.search(r'\bnodes (\d+)',x)]
  if last:nodes.append(int(re.search(r'\bnodes (\d+)',last[-1]).group(1)))
 result=json.loads((folder/'result.json').read_text(encoding='utf-8'));resources.append(dict(task=task,games=len(gs),actual_go=go,total_plies=sum(len(g['actions']) for g in gs),true_terminals=sum(g['termination']['kind']!='cap24' for g in gs),game_wall_sum=sum(g['seconds'] for g in gs),query_transport_wall_sum=searchwall,reported_last_info_nodes_sum=sum(nodes),reported_node_range=[min(nodes),max(nodes)],unreported_node_queries=go-len(nodes),fit_wall_seconds=result.get('fit_seconds'),logical_games=result.get('fit_logical_games'),cache_hits=result.get('fit_cache_hits')))
out=dict(status='PASS_DERIVATION',metrics=rows,resources=resources,new_go=0,combined_producer_wall_seconds=r['seconds'],seconds=time.perf_counter()-t0,scope='ALLtwoinitials/four frozen endpoints/both environments, 8developmentfamilies; exact components plus unequal-cost breadth curve. Few4 predefined subset of16, commondirections/RNG but changedaggregate path; one cohort, no significance/universal averaging claim ormodelselection. Reportednominalnodes not equal actualwork; ordinaryconcurrency allowed.');assert not(O/'result.json').exists();(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='metrics'}));print(json.dumps([x for x in rows if x['metric']=='mixed']))
