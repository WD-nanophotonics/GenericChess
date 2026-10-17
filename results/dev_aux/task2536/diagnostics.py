from pathlib import Path
from math import sqrt,isfinite
from itertools import combinations
import json
T=Path('results/dev_aux/task2534');O=Path('results/dev_aux/task2536')
def run():
 p=json.loads((T/'registration.json').read_text());r=json.loads((T/'result.json').read_text());rows=[]
 episodes=[json.loads(x)for x in(T/'episodes.jsonl').read_text().splitlines()]
 for a in r['arms']:
  ee=[x for x in episodes if(x['generator_seed'],x['method'],x['seed'])==(a['generator_seed'],a['method'],a['seed'])];path=[a['initial']]+[x['weights']for x in ee];norm=sqrt(sum(x*x for x in a['weights']));ps=[w[0]for w in path]
  assert all(isfinite(x)for w in path for x in w)
  if a['method']=='fixed5':assert set(ps)=={1.}
  rows.append(dict(rule=a['generator_seed'],method=a['method'],seed=a['seed'],raw=a['weights'],norm=norm,P=a['weights'][0],P_min=min(ps),P_max=max(ps),P_sign_crossings=sum((x<0)!=(y<0)for x,y in zip(ps,ps[1:])),nonpositive_P_episodes=sum(x<=0 for x in ps[1:]),direction=None if norm==0 else[x/norm for x in a['weights']],games=a['games'],update_L2_RMS=sqrt(sum(sum((y-x)**2 for x,y in zip(z['initial_weights'],z['weights']))for z in ee)/max(1,len(ee))),P_absolute_update_sum=sum(abs(z['weights'][0]-z['initial_weights'][0])for z in ee),actual_terminal=sum(x['outcome']is not None for x in ee),unknown=sum(x['outcome']is None for x in ee),nonzero_updates=sum(x['initial_weights']!=x['weights']for x in ee),snapshots=a['snapshots']))
 consistency=[]
 for rule in p['generator_seeds']:
  for method in ('fixed5','free6'):
   rr=[x for x in rows if x['rule']==rule and x['method']==method];pairs=list(combinations(rr,2));raw=sqrt(sum(sum((x-y)**2 for x,y in zip(a['raw'],b['raw']))for a,b in pairs)/max(1,6*len(pairs)));dp=[(a,b)for a,b in pairs if a['direction']is not None and b['direction']is not None];direction=sqrt(sum(sum((x-y)**2 for x,y in zip(a['direction'],b['direction']))for a,b in dp)/max(1,6*len(dp)))
   consistency.append(dict(rule=rule,method=method,raw_pairwise_RMS=raw,posthoc_L2_direction_RMS=direction,nonzero_direction_pairs=len(dp)))
 result=dict(status='PASS_ALL_FIXED_AND_FREE_RAW_SIGN_NORM_DIAGNOSTICS',models=rows,consistency=consistency,scope='All32rule-conditionedmodels/all4initials/no selection. L2direction POSTHOC ONLY: actualsearch/trainingusesRAW. Sharedfixedtanhscale10parameterizationnotvalidatedcalibration. Psigncrossings includeeveryclosedepisode notjustendpoint. PositivePimprovementwouldnotprovenegativedirectionmechanism. AddedPcoordinatechangescreditnorm/dynamicsnotpurecapacityablation; per-episodeupdateL2andPmovementretainedwithoutretuning. Dispersionnotidentifiability/priceuniqueness; differentseedalsochangesexploration. No humanpricefit.')
 (O/'diagnostics.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(status=result['status'],models=len(rows),consistency=consistency)))
if __name__=='__main__':run()
