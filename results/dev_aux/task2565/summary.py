"""All seeds/regimes finite WLD bounds and actual training cost, no model selection."""
from pathlib import Path
from collections import Counter,defaultdict
import json,sys,math,hashlib
METHODS=['Fixed','SelfCandidate','SelfEvery']
def run(directory):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());ep=json.loads((d/'eval-plan.json').read_text());train=json.loads((d/'result.json').read_text());ev=json.loads((d/'eval-result.json').read_text());arms={};games=defaultdict(list);keys=set();rows={tuple(r['slot']):r for r in map(json.loads,(d/'eval-games.jsonl').open())}
 for g in map(json.loads,(d/'games.jsonl').open()):games[g['generator_seed'],g['seed'],g['method']].append(g)
 keys={(s[0],s[1],s[2],s[3],s[5])for s in ep['slots']};by={}
 for a in train['arms']:
  k=a['generator_seed'],a['seed'],a['method'];gs=games[k];assert sum(g['nodes']for g in gs)==a['nodes'];c=Counter(g['ending']for g in gs);by[str(k)]=dict(nodes=a['nodes'],games=len(gs),terminal=sum(g['outcome']is not None for g in gs),unknown=sum(g['outcome']is None for g in gs),zeroquery_games=sum(g['queries']==0 for g in gs),observations=a['observations'],terms=a['terms'],episode_updates=a['updates'],seconds=a['seconds'],initial=a['initial'],weights=a['weights'],order=sorted(range(len(a['weights'])),key=lambda i:(a['weights'][i],i)),endings=dict(c))
  keys.update((a['generator_seed'],a['seed'],f,c,foe)for f in sorted({s[2]for s in ep['slots']})for c in [0,1]for foe in ep['foes'])
 def bounds(k,m):
  gs,seed,family,color,foe=k;r=rows.get((gs,seed,family,color,m,foe));v=None if r is None else r['reward'];return[-1,1]if v is None else[v,v]
 pairs=[('SelfCandidate','Fixed'),('SelfEvery','Fixed'),('SelfEvery','SelfCandidate')]+[(m,'initial')for m in METHODS];contrasts=[]
 for foe in ep['foes']:
  for left,right in pairs:
   for stratum,cond in [('all',lambda k:True)]+[(f'color{c}',lambda k,c=c:k[3]==c)for c in [0,1]]+[(f'seed{s}',lambda k,s=s:k[1]==s)for s in p['initial_seeds']]+[(f'rule{g}',lambda k,g=g:k[0]==g)for g in ep['rules']]:
    ks=sorted(k for k in keys if k[4]==foe and cond(k));b=[(bounds(k,left)[0]-bounds(k,right)[1],bounds(k,left)[1]-bounds(k,right)[0])for k in ks];contrasts.append(dict(foe=foe,left=left,right=right,stratum=stratum,cells=len(ks),mean_bounds=[sum(x[i]for x in b)/len(b)for i in [0,1]]if b else None))
 totals={}
 for method in METHODS:
  aa=[r for k,r in by.items()if method==__import__('ast').literal_eval(k)[2]]
  totals[method]={n:sum(a[n]for a in aa)for n in ['nodes','games','terminal','unknown','zeroquery_games','observations','terms','episode_updates','seconds']}
 result=dict(status='COMPLETE_DESCRIPTIVE',training=totals,all_arms=by,contrasts=contrasts,eval=ev,total_producer_nodes=train['nodes']+ev['nodes'],total_producer_wall=train['seconds']+ev['seconds'],scope='Finite matched cells, UNKNOWN AND missing bounded[-1,1]. No independent-game/populationconfidence claim; allfourinitials/roles/foes/rules retained. Three originalClock/policy regimes; lambda physical-horizon/data/episodes differ. Allaudit/engineering/transport work additional. Not stableprice or historicalreproduction proof.')
 (d/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(training=totals,contrasts=[r for r in contrasts if r['stratum']=='all'],nodes=result['total_producer_nodes'],wall=result['total_producer_wall'])))
if __name__=='__main__':run(sys.argv[1])
