"""All five-condition TRAIN record pairs: decision sensitivity is not reward gain."""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
import json,time
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2373')
def run(task=2358):
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());f=Path(f'results/dev_aux/task{task}');p=json.loads((f/'plan.json').read_text());gs=[json.loads(x)for x in(f/'games.jsonl').read_text().splitlines()];by=defaultdict(dict);ds=defaultdict(list)
 for slot in json.loads((f/'slots.json').read_text()):by[(slot['root'],slot['opponent'],slot['candidate_color'])]
 for g in gs:by[(g['root'],g['opponent'],g['candidate_color'])][g['ratio']]=g
 for d in map(json.loads,(f/'decisions.jsonl').read_text().splitlines()):ds[d['slot']].append(d)
 grid=[.5,1.,1.5,2.,3.];profiles=[];details=[];incomplete=False
 for a,b in combinations(grid,2):
  counts=Counter();net=0;families=set()
  for key,rr in sorted(by.items()):
   stop()
   if a not in rr or b not in rr or rr[a]['reward']is None or rr[b]['reward']is None:incomplete=True;counts['missing_or_UNKNOWN']+=1;continue
   ga,gb=rr[a],rr[b];counts['pairs']+=1;families.add(key[0]);net+=gb['reward']-ga['reward'];same=ga['record']==gb['record'];counts['identical_actual_record']+=same;da=ds[ga['slot']][:ga['plies']];db=ds[gb['slot']][:gb['plies']];first=None
   for i,(x,y)in enumerate(zip(da,db)):
    if x['choice']!=y['choice']:
     assert x['root_record']==y['root_record']and x['root_state_sha']==y['root_state_sha'];normal=all(d['source']=='FULL_SESSION_MATERIAL_SEARCH'for d in(x,y));fullD3=normal and all(d['normal_receipt']['completed_depth']==3 and d['normal_receipt']['exit_cause']=='depth_budget'for d in(x,y));kind=('candidate'if x['is_candidate']else'foe')+'_first';counts[kind]+=1;counts['candidate_normal_fullD3_first']+=x['is_candidate']and fullD3;first=dict(prices=[a,b],family=key[0],opponent=key[1],color=key[2],ply=i,kind=kind,sources=[x['source'],y['source']],normal_depths=[None if d['normal_receipt']is None else d['normal_receipt']['completed_depth']for d in(x,y)],normal_causes=[None if d['normal_receipt']is None else d['normal_receipt']['exit_cause']for d in(x,y)],choices=[x['choice'],y['choice']],root_record=x['root_record'],actual_rewards=[ga['reward'],gb['reward']],delta=gb['reward']-ga['reward']);details.append(first);break
   if first is None:assert same and ga['reward']==gb['reward']
  profiles.append(dict(prices=[a,b],counts=dict(counts),family_clusters=len(families),net_B_minus_A_sum=net))
 result=dict(status='INCOMPLETE_AVAILABLE_ACTUAL_PAIR_DIAGNOSIS'if incomplete else'PASS_ALL_FIVE_CONDITION_ACTUAL_PAIRS',task=task,profiles=profiles,first_differences=details,seconds=time.perf_counter()-t,scope='Everypair in exposedTRAINonly; role/foe/pricepairs share8families and areNOTindependentsamples. Foe-first atidenticalhistory demonstratesnon-price operationalvariation; candidateproof-first canlikewise bebudgetvariation. CandidateordinaryfullD3changes supportmaterialsensitivity, notstrategiccausality orrewardgain. Identicalrecord/outcome counts diagnosefiniteobjectiveflatness, notall-domain equivalence/metricidentification. No newpricequery/selectionchange/DEVread.')
 with(OUT/f'task{task}-mechanism.json').open('x')as fp:json.dump(result,fp,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='first_differences'}))
if __name__=='__main__':import sys;run(int(sys.argv[1])if len(sys.argv)>1 else 2358)
