from pathlib import Path
import json,collections,statistics
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1298';O.mkdir(exist_ok=False)
D=json.loads((R/'results/dev_aux/task1276/plan.json').read_bytes());D['sources']=[1243,1253,1282];rows=[];trans=[];cost=[]
for n in D['sources']:
 p=R/f'results/dev_aux/task{n}';rp=p/'result.json'
 if not rp.exists():continue
 result=json.loads(rp.read_bytes());assert result['complete'] and not result['error'];groups=collections.defaultdict(list)
 for line in (p/'queries.jsonl').open():
  q=json.loads(line);v={}
  for text in q['metadata']['uci_info']:
   f=text.split()
   if 'nodes' not in f:continue
   for k in ['nodes','depth','seldepth','tbhits']:
    if k in f:v[k]=int(f[f.index(k)+1])
  assert v and v['tbhits']==0
  groups[(q['game'].split('-')[0],q['weights']['R'],q['player'])].append(v)
 for k,z in groups.items():
  dep=[v['depth'] for v in z];nn=[v['nodes'] for v in z]
  rows.append(dict(source=n,arm=k[0],activeR=k[1],player=k[2],go=len(z),last_reported_nodes=sum(nn),depth_distribution=dict(collections.Counter(dep)),nodes_median=statistics.median(nn),nodes_min=min(nn),nodes_max=max(nn)))
 assert sum(v['go'] for v in rows if v['source']==n)==result['actual_go']
 cost.append(dict(source=n,games=result['closed_games'],go=result['actual_go'],stored_seconds=result['seconds'],sum_last_UCI_nodes=sum(v['last_reported_nodes'] for v in rows if v['source']==n)))
for a,b in [(1243,1253)]:
 ga=[json.loads(v) for v in (R/f'results/dev_aux/task{a}/games.jsonl').read_text().splitlines()];gb=[json.loads(v) for v in (R/f'results/dev_aux/task{b}/games.jsonl').read_text().splitlines()]
 key=lambda g:(g['arm'],g['price'],g['opponent'],g['root']['seed'],g['root']['variant'],g['color'])
 by={key(g):g for g in gb};assert len(by)==len(ga);gr=collections.defaultdict(list)
 for g in ga:gr[(g['arm'],g['price'],g['opponent'])].append((g,by[key(g)]))
 for k,zz in gr.items():
  c=collections.Counter(x['label']+'->'+y['label'] for x,y in zz);diff=sum(((y['label']=='W')-(y['label']=='L'))-((x['label']=='W')-(x['label']=='L')) for x,y in zz)
  trans.append(dict(arm=k[0],price=k[1],opponent=k[2],N=len(zz),transitions=dict(c),resource_gain=str(F(diff,len(zz)))))
out=dict(status='ACTUAL_RESOURCE_RESPONSE_AND_OUTCOME_TRANSITIONS',rows=rows,cost=cost,transitions=trans,new_go=0,scope=D)
(O/'result.json').write_text(json.dumps(out,indent=2));print('COST',cost);print('TRANSITIONS',trans)
